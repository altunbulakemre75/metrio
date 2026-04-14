import re
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Page, Browser

from config import settings
from scrapers.base import BaseScraper
from storage.models import ProductSnapshot
from utils.logger import get_logger
from utils.rate_limiter import rate_limit
from utils.retry import retry


_PRICE_PATTERN = re.compile(r"[\d.,]+")
_BASE_URL = "https://www.trendyol.com"
_CARD_SELECTOR = "a.product-card"

log = get_logger("trendyol")


def parse_price_text(text: str | None) -> float | None:
    """Türkçe formatlı fiyat metnini float'a çevirir.

    Örnekler:
        '299,90 TL'   -> 299.90
        '1.299,90 TL' -> 1299.90
        '100 TL'      -> 100.0
    """
    if not text:
        return None
    match = _PRICE_PATTERN.search(text.strip())
    if not match:
        return None
    raw = match.group()
    # Türkçe: '.' binlik ayırıcı, ',' ondalık
    normalized = raw.replace(".", "").replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return None


def parse_discount_rate(original: float | None, current: float) -> float | None:
    """İndirim oranını 0-1 arası float olarak döndürür.

    original < current veya original geçersizse None döner.
    """
    if original is None or original <= 0:
        return None
    if current > original:
        return None
    return round((original - current) / original, 4)


def parse_product_card(
    html: str,
    category: str,
    captured_at: datetime,
) -> ProductSnapshot | None:
    """Tek bir ürün kartı HTML'ini ProductSnapshot'a çevirir.

    Selector şeması Trendyol'a özel (2026 yapısı). Site değişirse burası güncellenmeli.
    Parse edilemeyen kartlar için None döner (üst katmana atlama sinyali).
    Not: Listeleme sayfasında satıcı adı görünmez → seller_name None kalır.
    """
    soup = BeautifulSoup(html, "lxml")
    card = soup.select_one("a.product-card")
    if card is None:
        return None

    product_id = card.get("id")
    if not product_id:
        return None

    name_el = card.select_one(".product-name")
    brand_el = card.select_one(".product-brand")
    img_el = card.select_one("img[data-testid='image-img']") or card.select_one("img.image")

    # Fiyat: discounted (price-value) veya single (price-section)
    price_el = (
        card.select_one("[data-testid='price-value']")
        or card.select_one("[data-testid='price-section']")
        or card.select_one(".price-value")
        or card.select_one(".price-section")
    )
    original_price_el = card.select_one(".strikethrough-price")

    rating_el = card.select_one(".average-rating")

    # Stok: "sold-out" class veya Tükendi damgası
    card_classes = card.get("class", [])
    in_stock = True
    if "sold-out" in card_classes:
        in_stock = False
    else:
        sold_out_stamp = card.select_one(".sold-out-stamp") or card.select_one(".stamp")
        if sold_out_stamp and "tükendi" in sold_out_stamp.get_text(strip=True).lower():
            in_stock = False

    if name_el is None or price_el is None:
        return None

    price = parse_price_text(price_el.get_text())
    if price is None:
        return None

    original_price = parse_price_text(original_price_el.get_text()) if original_price_el else None
    discount_rate = parse_discount_rate(original_price, price)

    rating = None
    if rating_el:
        try:
            rating = float(rating_el.get_text(strip=True).replace(",", "."))
        except ValueError:
            rating = None

    href = card.get("href", "")
    product_url = href if href.startswith("http") else f"{_BASE_URL}{href}"

    # Brand image/icon temizliği — "resmi satıcı rozeti" <img> alt metin çıkıntısını engelle
    brand_text = None
    if brand_el:
        brand_text = brand_el.get_text(strip=True)
        # Alt metinde ikon açıklaması kalabilir (örn. "Resmi satıcı rozeti")
        # Gerçek marka adı ilk satır olduğu için .get_text() yeterli

    return ProductSnapshot(
        platform="trendyol",
        platform_product_id=product_id,
        name=name_el.get_text(strip=True),
        brand=brand_text,
        category=category,
        product_url=product_url,
        image_url=img_el.get("src") if img_el else None,
        price=price,
        original_price=original_price,
        discount_rate=discount_rate,
        seller_name=None,  # Listeleme sayfasında yok
        seller_rating=rating,
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
            log.warning(f"Kart parse edilemedi (data-id={card.get('data-id')}), atlandı")
            continue
        snapshots.append(snap)

    return snapshots


class TrendyolScraper(BaseScraper):
    """Playwright ile Trendyol kategori sayfalarını çeker."""

    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None

    def _ensure_browser(self) -> Browser:
        if self._browser is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=settings.scraper_headless,
            )
        return self._browser

    @rate_limit(calls_per_second=settings.scraper_requests_per_second)
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
        context = browser.new_context(user_agent=settings.scraper_user_agent)
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
        """URL'den kategori adını çıkar. Örn: .../kozmetik-x-c89 -> 'kozmetik'."""
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
