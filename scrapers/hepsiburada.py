import re
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Page, Browser

from config import settings
from scrapers.base import BaseScraper
from scrapers.trendyol import parse_price_text, parse_discount_rate
from storage.models import ProductSnapshot
from utils.fingerprint import get_fingerprint
from utils.logger import get_logger
from utils.proxy_pool import ProxyPool
from utils.rate_limiter import rate_limit, jitter_delay
from utils.retry import retry

_BASE_URL = "https://www.hepsiburada.com"
_CARD_SELECTOR = "li[data-test-id='product-card']"
_HBV_PATTERN = re.compile(r"HBV\w+")

log = get_logger("hepsiburada")


def _extract_product_id(href: str) -> str | None:
    """HBV kodu varsa çıkar, yoksa son path segment'i döner."""
    match = _HBV_PATTERN.search(href)
    if match:
        return match.group()
    segments = [s for s in href.split("/") if s]
    return segments[-1] if segments else None


def parse_product_card(
    html: str,
    category: str,
    captured_at: datetime,
) -> ProductSnapshot | None:
    """Tek bir ürün kartı HTML'ini ProductSnapshot'a çevirir.

    Selector şeması Hepsiburada'ya özel (2026 yapısı).
    Parse edilemeyen kartlar için None döner.
    """
    soup = BeautifulSoup(html, "lxml")
    card = soup.select_one(_CARD_SELECTOR)
    if card is None:
        return None

    link = card.select_one("a[href]")
    if link is None:
        return None

    href = link.get("href", "")
    product_id = _extract_product_id(href)
    if not product_id:
        return None

    product_url = href if href.startswith("http") else f"{_BASE_URL}{href}"

    name_el = card.select_one("[data-test-id='product-name']")
    brand_el = card.select_one("[data-test-id='brand']")
    price_el = (
        card.select_one("[data-test-id='price']")
        or card.select_one("[class*='price']")
    )
    original_price_el = (
        card.select_one("[data-test-id='original-price']")
        or card.select_one("[class*='original']")
    )
    img_el = card.select_one("img")

    if name_el is None or price_el is None:
        return None

    price = parse_price_text(price_el.get_text())
    if price is None:
        return None

    original_price = parse_price_text(original_price_el.get_text()) if original_price_el else None
    discount_rate = parse_discount_rate(original_price, price)
    in_stock = card.select_one("[data-test-id='add-to-cart']") is not None

    return ProductSnapshot(
        platform="hepsiburada",
        platform_product_id=product_id,
        name=name_el.get_text(strip=True),
        brand=brand_el.get_text(strip=True) if brand_el else None,
        category=category,
        product_url=product_url,
        image_url=img_el.get("src") if img_el else None,
        price=price,
        original_price=original_price,
        discount_rate=discount_rate,
        seller_name=None,
        seller_rating=None,
        in_stock=in_stock,
        captured_at=captured_at,
    )


def extract_cards_from_page(
    html: str,
    category: str,
    captured_at: datetime,
    max_products: int | None = None,
) -> list[ProductSnapshot]:
    """Tam kategori sayfasından ürün kartlarını parse eder.

    Parse edilemeyen kartları atlar (logla, devam et).
    """
    soup = BeautifulSoup(html, "lxml")
    cards = soup.select(_CARD_SELECTOR)
    snapshots: list[ProductSnapshot] = []

    for card in cards:
        if max_products is not None and len(snapshots) >= max_products:
            break
        snap = parse_product_card(str(card), category=category, captured_at=captured_at)
        if snap is None:
            log.warning("Kart parse edilemedi, atlandı")
            continue
        snapshots.append(snap)

    return snapshots


class HepsiburadaScraper(BaseScraper):
    """Playwright ile Hepsiburada kategori sayfalarını çeker."""

    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None
        self._proxy_pool = ProxyPool(settings.proxy_list, settings.proxy_enabled)

    def _ensure_browser(self) -> Browser:
        if self._browser is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=settings.scraper_headless,
            )
        return self._browser

    @jitter_delay(settings.scraper_min_delay, settings.scraper_max_delay)
    @retry(max_attempts=3, backoff_base=2, exceptions=(Exception,))
    def _load_page(self, page: Page, url: str) -> str:
        log.info(f"Sayfa yükleniyor: {url}")
        page.goto(url, wait_until="networkidle", timeout=45000)
        self._scroll_to_load(page)
        return page.content()

    def _scroll_to_load(self, page: Page, max_scrolls: int = 10) -> None:
        """Infinite scroll sayfasında aşağı in, daha fazla ürün yüklet."""
        for _ in range(max_scrolls):
            previous_height = page.evaluate("document.body.scrollHeight")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == previous_height:
                break

    def fetch_category(
        self,
        category_url: str,
        max_products: int = 500,
    ) -> list[ProductSnapshot]:
        browser = self._ensure_browser()
        fp = get_fingerprint()
        ctx_args = {
            "user_agent": fp["user_agent"],
            "viewport": fp["viewport"],
            "locale": fp["locale"],
        }
        proxy = self._proxy_pool.pick()
        if proxy:
            ctx_args["proxy"] = proxy
        context = browser.new_context(**ctx_args)
        page = context.new_page()
        try:
            html = self._load_page(page, category_url)
            captured_at = datetime.now()
            snapshots = extract_cards_from_page(
                html,
                category=self._infer_category_from_url(category_url),
                captured_at=captured_at,
                max_products=max_products,
            )
            log.info(f"{len(snapshots)} ürün çekildi")
            return snapshots
        finally:
            context.close()

    def _infer_category_from_url(self, url: str) -> str:
        url_lower = url.lower()
        known = ["kozmetik", "elektronik", "giyim", "ev-yasam", "kitap"]
        for k in known:
            if k in url_lower:
                return k
        return "unknown"

    def close(self) -> None:
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
