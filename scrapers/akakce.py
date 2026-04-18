"""Akakçe aggregator scraper — kategori sayfalarından ürün + en düşük fiyat çeker.

Akakçe HTML yapısı (Nisan 2026):
    li.w[data-pr=<id>][data-mk=<brand>]
      a.pw_v8[href=...]
        figure > img
        h3.pn_v8   (ürün adı — marka h3 içinde <b> olarak YA DA data-mk attribute'unda)
        span.pt_v8 (fiyat — "4.999,00 TL" formatında, içinde <i> tag ile)
"""
import re
from datetime import datetime
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from scrapers.trendyol import parse_price_text
from storage.models import ProductSnapshot
from utils.logger import get_logger

_BASE_URL = "https://www.akakce.com"

# NOT: Task 1'de canlı sayfadan tespit edilen selektörler. Akakçe HTML'i değişirse burası güncellenir.
_CARD_SELECTOR = "li.w"
_NAME_SELECTOR = "h3.pn_v8, h3"
_PRICE_SELECTOR = "span.pt_v8"
_LINK_SELECTOR = "a.pw_v8, a[href]"
_IMG_SELECTOR = "img"
_BRAND_TAG = "b"  # h3 içinde <b>Marka</b> varsa (test fixture pattern); yoksa data-mk fallback

log = get_logger("akakce")


def _extract_product_id(card) -> str | None:
    """data-pr (real Akakçe) veya data-id (test fixture) attribute'undan, yoksa href slug'ından."""
    for attr in ("data-pr", "data-id"):
        val = card.get(attr)
        if val:
            return val
    link = card.select_one(_LINK_SELECTOR)
    if link:
        href = link.get("href", "")
        # /parfum/en-ucuz-...-fiyati,1234567.html  -> 1234567
        m = re.search(r",(\d+)\.html", href)
        if m:
            return m.group(1)
        segments = [s for s in href.rstrip("/").split("/") if s]
        if segments:
            return segments[-1].replace(".html", "")
    return None


def _extract_name_and_brand(card) -> tuple[str | None, str | None]:
    """h3 içinden ürün adını çıkarır. Marka önce data-mk attribute'tan, yoksa h3 içindeki <b>'den."""
    name_el = card.select_one(_NAME_SELECTOR)
    if name_el is None:
        return None, None

    # Marka: önce data-mk (canlı Akakçe), sonra h3 içindeki <b> (test fixture)
    brand = card.get("data-mk")
    if not brand:
        brand_el = name_el.find(_BRAND_TAG)
        brand = brand_el.get_text(strip=True) if brand_el else None

    full_name = name_el.get_text(" ", strip=True)
    return full_name, brand


def _extract_price(card) -> float | None:
    """span.pt_v8 içinden fiyat. İç <i> tag'i nedeniyle default get_text() kullanılır (separator YOK)."""
    price_el = card.select_one(_PRICE_SELECTOR)
    if price_el is None:
        return None
    # get_text() separator'sız — <i>,80 TL</i> birleşik kalmalı: "1.198,80 TL"
    return parse_price_text(price_el.get_text())


def _normalize_image_url(src: str | None) -> str | None:
    """Akakçe CDN protokole-göreli URL (//cdn...) kullanır, https:// prefix ekler."""
    if not src:
        return None
    if src.startswith("//"):
        return f"https:{src}"
    return src


def parse_product_card(
    html: str,
    category: str,
    captured_at: datetime,
) -> ProductSnapshot | None:
    """Tek bir Akakçe ürün kartı HTML'ini ProductSnapshot'a çevirir.

    Parse edilemeyen kartlar için None döner.
    """
    soup = BeautifulSoup(html, "lxml")
    card = soup.select_one(_CARD_SELECTOR)
    if card is None:
        return None

    product_id = _extract_product_id(card)
    if not product_id:
        return None

    link = card.select_one(_LINK_SELECTOR)
    if link is None:
        return None

    href = link.get("href", "")
    product_url = href if href.startswith("http") else f"{_BASE_URL}{href}"

    price = _extract_price(card)
    if price is None:
        return None

    name, brand = _extract_name_and_brand(card)
    if name is None:
        return None

    img_el = card.select_one(_IMG_SELECTOR)
    image_url = _normalize_image_url(img_el.get("src") if img_el else None)

    return ProductSnapshot(
        platform="akakce",
        platform_product_id=product_id,
        name=name,
        brand=brand,
        category=category,
        product_url=product_url,
        image_url=image_url,
        price=price,
        original_price=None,
        discount_rate=None,
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
    """Kategori sayfasından ürün kartlarını parse eder.

    Parse edilemeyen kartları atlar (log WARNING).
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


from playwright.sync_api import sync_playwright, Page, Browser

from config import settings
from utils.fingerprint import get_fingerprint
from utils.proxy_pool import ProxyPool
from utils.rate_limiter import jitter_delay
from utils.retry import retry


# Cloudflare Turnstile bypass için webdriver gizleme scripti
_STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
"""


class AkakceScraper(BaseScraper):
    """Playwright ile Akakçe kategori sayfalarını çeker."""

    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None
        self._proxy_pool = ProxyPool(settings.proxy_list, settings.proxy_enabled)

    def _ensure_browser(self) -> Browser:
        if self._browser is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=settings.scraper_headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
        return self._browser

    @jitter_delay(settings.scraper_min_delay, settings.scraper_max_delay)
    @retry(max_attempts=3, backoff_base=2, exceptions=(Exception,))
    def _load_page(self, page: Page, url: str) -> str:
        log.info(f"Sayfa yükleniyor: {url}")
        # Akakçe Cloudflare Turnstile çekiyor — domcontentloaded + bekleme Turnstile
        # tamamlanması için networkidle'dan daha güvenilir.
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        # Turnstile challenge'ı tamamlasın
        page.wait_for_timeout(8000)
        # Ürün kartları yüklendi mi? Beklerken sayfa hazırsa erken döner.
        try:
            page.wait_for_selector(_CARD_SELECTOR, timeout=15000)
        except Exception:
            log.warning("Ürün kartı selector'ı görünmedi, yine de HTML alınıyor")
        return page.content()

    def _paginated_url(self, base_url: str, page_num: int) -> str:
        """Akakçe sayfalama: .html yerine ,N.html (örn: /parfum.html -> /parfum,2.html)."""
        if page_num == 1:
            return base_url
        if base_url.endswith(".html"):
            return base_url[: -len(".html")] + f",{page_num}.html"
        # Fallback: query-param tarzı (beklenmedik URL formatı için)
        separator = "&" if "?" in base_url else "?"
        return f"{base_url}{separator}page={page_num}"

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
        context.add_init_script(_STEALTH_SCRIPT)
        page = context.new_page()
        try:
            captured_at = datetime.now()
            category = self._infer_category_from_url(category_url)
            all_snaps: list[ProductSnapshot] = []
            seen_ids: set[str] = set()

            for page_num in range(1, 26):  # max 25 sayfa
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

    def _infer_category_from_url(self, url: str) -> str:
        url_lower = url.lower()
        known = [
            "parfum", "cilt-bakim", "cilt-bakimi", "makyaj", "kozmetik",
            "cep-telefonu", "bilgisayar", "elektronik", "kulaklik",
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
