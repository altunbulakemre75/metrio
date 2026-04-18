import re
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Page, Browser

from config import settings
from scrapers.base import BaseScraper
from scrapers.trendyol import parse_price_text
from storage.models import ProductSnapshot
from utils.fingerprint import get_fingerprint
from utils.proxy_pool import ProxyPool
from utils.logger import get_logger
from utils.rate_limiter import jitter_delay
from utils.retry import retry


_BASE_URL = "https://www.n11.com"
_CARD_SELECTOR = "li.column"

log = get_logger("n11")


def _extract_product_id(href: str) -> str | None:
    """URL'den ürün slug'ını çıkar. Örn: /urun/abc-p-123456 → '123456'"""
    match = re.search(r"-p-(\d+)", href)
    if match:
        return match.group(1)
    # Fallback: URL path son segmenti
    slug = href.rstrip("/").rsplit("/", 1)[-1]
    return slug if slug else None


def parse_product_card(
    html: str,
    category: str,
    captured_at: datetime,
) -> ProductSnapshot | None:
    soup = BeautifulSoup(html, "lxml")
    card = soup.select_one(_CARD_SELECTOR) or soup

    name_el = (
        card.select_one("h3.productName a")
        or card.select_one("p.description a")
        or card.select_one("a.productName")
    )
    if name_el is None:
        return None

    href = name_el.get("href", "")
    product_url = href if href.startswith("http") else f"{_BASE_URL}{href}"
    product_id = _extract_product_id(href)
    if not product_id:
        return None

    price_el = (
        card.select_one("span.newPrice ins")
        or card.select_one("ins.newPrice")
        or card.select_one("span.price ins")
        or card.select_one(".priceContainer ins")
    )
    if price_el is None:
        return None

    price = parse_price_text(price_el.get_text())
    if price is None:
        return None

    original_price_el = (
        card.select_one("span.oldPrice del")
        or card.select_one("del.oldPrice")
    )
    original_price = parse_price_text(original_price_el.get_text()) if original_price_el else None
    discount_rate = None
    if original_price and original_price > price:
        discount_rate = round((original_price - price) / original_price, 4)

    img_el = card.select_one("img.lazy") or card.select_one("img")
    image_url = img_el.get("data-original") or img_el.get("src") if img_el else None

    return ProductSnapshot(
        platform="n11",
        platform_product_id=product_id,
        name=name_el.get_text(strip=True),
        brand=None,
        category=category,
        product_url=product_url,
        image_url=image_url,
        price=price,
        original_price=original_price,
        discount_rate=discount_rate,
        seller_name=None,
        seller_rating=None,
        in_stock=True,
        captured_at=captured_at,
    )


def extract_cards_from_page(
    html: str,
    category: str,
    captured_at: datetime,
    max_products: int | None = None,
) -> list[ProductSnapshot]:
    soup = BeautifulSoup(html, "lxml")
    cards = soup.select(_CARD_SELECTOR)
    snapshots: list[ProductSnapshot] = []

    for card in cards:
        if max_products is not None and len(snapshots) >= max_products:
            break
        snap = parse_product_card(str(card), category=category, captured_at=captured_at)
        if snap is None:
            log.warning(f"Kart parse edilemedi, atlandı")
            continue
        snapshots.append(snap)

    return snapshots


class N11Scraper(BaseScraper):
    """Playwright ile N11 kategori sayfalarını çeker."""

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
        return page.content()

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
            captured_at = datetime.now()
            category = self._infer_category_from_url(category_url)
            all_snaps: list[ProductSnapshot] = []
            seen_ids: set[str] = set()

            for page_num in range(1, 26):
                if len(all_snaps) >= max_products:
                    break
                url = self._paginated_url(category_url, page_num)
                try:
                    html = self._load_page(page, url)
                except Exception as e:
                    log.warning(f"Sayfa {page_num} yüklenemedi ({e}), atlanıyor")
                    break
                snapshots = extract_cards_from_page(
                    html, category=category, captured_at=captured_at,
                    max_products=max_products - len(all_snaps),
                )
                new_snaps = [s for s in snapshots if s.platform_product_id not in seen_ids]
                if not new_snaps:
                    log.info(f"Sayfa {page_num} boş, duruldu")
                    break
                for s in new_snaps:
                    seen_ids.add(s.platform_product_id)
                all_snaps.extend(new_snaps)
                log.info(f"Sayfa {page_num}: {len(new_snaps)} yeni (toplam {len(all_snaps)})")

            log.info(f"Toplam {len(all_snaps)} ürün çekildi")
            return all_snaps
        finally:
            context.close()

    def _paginated_url(self, base_url: str, page_num: int) -> str:
        if page_num == 1:
            return base_url
        separator = "&" if "?" in base_url else "?"
        return f"{base_url}{separator}pg={page_num}"

    def _infer_category_from_url(self, url: str) -> str:
        url_lower = url.lower()
        known = [
            "kozmetik", "elektronik", "cep-telefonu", "parfum",
            "makyaj", "cilt-bakimi", "vitamin", "giyim",
        ]
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
