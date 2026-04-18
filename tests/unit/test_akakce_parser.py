import pytest
from datetime import datetime
from pathlib import Path
from scrapers.akakce import parse_product_card, extract_cards_from_page

FIXTURES = Path(__file__).parent.parent / "fixtures"
NOW = datetime(2026, 4, 18, 15, 0)


def _card(href, name, price_text, brand=None, img_src=None, data_id="x"):
    """Test helper — tek bir kart için minimal HTML üretir."""
    brand_tag = f"<b>{brand}</b> " if brand else ""
    price_tag = f'<span class="pt_v8">{price_text}</span>' if price_text else ""
    img_tag = f'<img src="{img_src}" alt="{name}">' if img_src else ""
    return f"""
    <li class="w" data-id="{data_id}">
      <a class="pw_v8" href="{href}">
        {img_tag}
        <h3 class="pn_v8">{brand_tag}{name}</h3>
        {price_tag}
      </a>
    </li>
    """


def test_parse_product_card_basic():
    html = _card(
        "/parfum/en-ucuz-urun-xyz.html",
        "Chanel No 5 EDP 100 ml",
        "4.999 TL",
        brand="Chanel",
        img_src="https://cdn.akakce.com/a.jpg",
        data_id="aaa111",
    )
    snap = parse_product_card(html, category="parfum", captured_at=NOW)
    assert snap is not None
    assert snap.platform == "akakce"
    assert snap.platform_product_id == "aaa111"
    assert snap.price == 4999.0
    assert snap.category == "parfum"
    assert snap.product_url == "https://www.akakce.com/parfum/en-ucuz-urun-xyz.html"
    assert snap.image_url == "https://cdn.akakce.com/a.jpg"
    assert snap.in_stock is True
    assert snap.seller_name is None
    assert snap.seller_rating is None
    assert "Chanel No 5" in snap.name or snap.name == "Chanel No 5 EDP 100 ml"


def test_parse_product_card_brand_extracted():
    html = _card(
        "/parfum/x.html", "No 5 EDP 100 ml", "4.999 TL",
        brand="Chanel", data_id="a",
    )
    snap = parse_product_card(html, category="parfum", captured_at=NOW)
    assert snap.brand == "Chanel"


def test_parse_product_card_no_brand():
    html = _card("/parfum/x.html", "Jenerik Ürün", "1.299 TL", brand=None, data_id="a")
    snap = parse_product_card(html, category="parfum", captured_at=NOW)
    assert snap is not None
    assert snap.brand is None


def test_parse_product_card_no_image():
    html = _card("/parfum/x.html", "Ürün", "99 TL", img_src=None, data_id="a")
    snap = parse_product_card(html, category="parfum", captured_at=NOW)
    assert snap.image_url is None


def test_parse_product_card_missing_price_returns_none():
    html = _card("/parfum/x.html", "Fiyatsız Ürün", price_text=None, data_id="a")
    assert parse_product_card(html, category="parfum", captured_at=NOW) is None


def test_parse_product_card_no_card_element_returns_none():
    assert parse_product_card("<div>boş</div>", category="parfum", captured_at=NOW) is None


def test_parse_product_card_absolute_url_preserved():
    html = _card(
        "https://www.akakce.com/parfum/x.html", "Ürün", "100 TL",
        data_id="a",
    )
    snap = parse_product_card(html, category="parfum", captured_at=NOW)
    assert snap.product_url == "https://www.akakce.com/parfum/x.html"


def test_extract_cards_from_fixture_returns_all_valid():
    html = (FIXTURES / "akakce_category_page.html").read_text(encoding="utf-8")
    snaps = extract_cards_from_page(html, category="parfum", captured_at=NOW)
    # Fixture 3 kart içerir, 3. kart fiyatsız → None → atlanır → 2 snap beklenir
    assert len(snaps) == 2
    ids = {s.platform_product_id for s in snaps}
    assert ids == {"aaa111", "bbb222"}


def test_extract_cards_respects_max_products():
    html = (FIXTURES / "akakce_category_page.html").read_text(encoding="utf-8")
    snaps = extract_cards_from_page(html, category="parfum", captured_at=NOW, max_products=1)
    assert len(snaps) == 1
