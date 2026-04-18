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
