import re
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Page, Browser

from config import settings
from scrapers.base import BaseScraper
from scrapers.trendyol import parse_price_text, parse_discount_rate
from storage.models import ProductSnapshot
from utils.logger import get_logger
from utils.rate_limiter import rate_limit
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
