import re
from datetime import datetime
from bs4 import BeautifulSoup

from storage.models import ProductSnapshot


_PRICE_PATTERN = re.compile(r"[\d.,]+")
_BASE_URL = "https://www.trendyol.com"


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

    Selector şeması Trendyol'a özel. Site değişirse burası güncellenmeli.
    Parse edilemeyen kartlar için None döner (üst katmana atlama sinyali).
    """
    soup = BeautifulSoup(html, "lxml")
    wrapper = soup.select_one(".p-card-wrppr")
    if wrapper is None:
        return None

    product_id = wrapper.get("data-id")
    if not product_id:
        return None

    name_el = wrapper.select_one(".prdct-desc-cntnr-name")
    brand_el = wrapper.select_one(".prdct-desc-cntnr-ttl")
    link_el = wrapper.select_one("a.p-card-chldrn-cntnr")
    img_el = wrapper.select_one("img.p-card-img")

    price_el = wrapper.select_one(".prc-box-dscntd")
    original_price_el = wrapper.select_one(".prc-box-orgnl")

    seller_name_el = wrapper.select_one(".merchant-name")
    seller_rating_el = wrapper.select_one(".merchant-rating")

    out_of_stock_el = wrapper.select_one(".stmp")
    in_stock = True
    if out_of_stock_el and "tükendi" in out_of_stock_el.get_text(strip=True).lower():
        in_stock = False

    if name_el is None or price_el is None:
        return None

    price = parse_price_text(price_el.get_text())
    if price is None:
        return None

    original_price = parse_price_text(original_price_el.get_text()) if original_price_el else None
    discount_rate = parse_discount_rate(original_price, price)

    rating = None
    if seller_rating_el:
        try:
            rating = float(seller_rating_el.get_text(strip=True).replace(",", "."))
        except ValueError:
            rating = None

    href = link_el.get("href", "") if link_el else ""
    product_url = href if href.startswith("http") else f"{_BASE_URL}{href}"

    return ProductSnapshot(
        platform="trendyol",
        platform_product_id=product_id,
        name=name_el.get_text(strip=True),
        brand=brand_el.get_text(strip=True) if brand_el else None,
        category=category,
        product_url=product_url,
        image_url=img_el.get("src") if img_el else None,
        price=price,
        original_price=original_price,
        discount_rate=discount_rate,
        seller_name=seller_name_el.get_text(strip=True) if seller_name_el else None,
        seller_rating=rating,
        in_stock=in_stock,
        captured_at=captured_at,
    )
