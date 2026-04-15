import pytest
from datetime import datetime
from scrapers.hepsiburada import parse_product_card, extract_cards_from_page
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures"
NOW = datetime(2026, 4, 15)


def _card(href, name, price, brand=None, original_price=None, in_stock=True, img_src=None):
    brand_span = f'<span data-test-id="brand">{brand}</span>' if brand else ""
    orig_span = f'<span data-test-id="original-price">{original_price}</span>' if original_price else ""
    cart_btn = '<button data-test-id="add-to-cart">Sepete Ekle</button>' if in_stock else ""
    img_tag = f'<img src="{img_src}" />' if img_src else ""
    return f"""
    <li data-test-id="product-card">
      <a href="{href}">
        {img_tag}{brand_span}
        <span data-test-id="product-name">{name}</span>
        {orig_span}
        <span data-test-id="price">{price}</span>
        {cart_btn}
      </a>
    </li>
    """


def test_parse_product_card_basic_fields():
    html = _card(
        "/loreal-serum-HBV000001AAA", "Serum 30ml", "127,90 TL",
        brand="L'Oréal", img_src="https://cdn.hb.net/u1.jpg"
    )
    snap = parse_product_card(html, category="kozmetik", captured_at=NOW)
    assert snap is not None
    assert snap.platform == "hepsiburada"
    assert snap.platform_product_id == "HBV000001AAA"
    assert snap.name == "Serum 30ml"
    assert snap.brand == "L'Oréal"
    assert snap.price == 127.90
    assert snap.category == "kozmetik"
    assert snap.product_url == "https://www.hepsiburada.com/loreal-serum-HBV000001AAA"
    assert snap.image_url == "https://cdn.hb.net/u1.jpg"
    assert snap.in_stock is True
    assert snap.seller_name is None
    assert snap.seller_rating is None


def test_parse_product_card_with_discount():
    html = _card(
        "/urun-HBV000002BBB", "Fondöten", "127,90 TL",
        original_price="189,90 TL"
    )
    snap = parse_product_card(html, category="kozmetik", captured_at=NOW)
    assert snap is not None
    assert snap.original_price == pytest.approx(189.90)
    assert snap.discount_rate == pytest.approx((189.90 - 127.90) / 189.90, rel=0.01)


def test_parse_product_card_out_of_stock():
    html = _card("/urun-HBV000003CCC", "Krem 200ml", "89,90 TL", in_stock=False)
    snap = parse_product_card(html, category="kozmetik", captured_at=NOW)
    assert snap is not None
    assert snap.in_stock is False


def test_parse_product_card_missing_price_returns_none():
    html = """
    <li data-test-id="product-card">
      <a href="/urun-HBV000004DDD">
        <span data-test-id="product-name">Ürün</span>
      </a>
    </li>
    """
    assert parse_product_card(html, category="kozmetik", captured_at=NOW) is None


def test_parse_product_card_no_card_element_returns_none():
    assert parse_product_card("<div>boş sayfa</div>", category="kozmetik", captured_at=NOW) is None


def test_parse_product_card_no_link_returns_none():
    html = """
    <li data-test-id="product-card">
      <span data-test-id="product-name">Ürün</span>
      <span data-test-id="price">99,90 TL</span>
    </li>
    """
    assert parse_product_card(html, category="kozmetik", captured_at=NOW) is None


def test_extract_cards_from_fixture_returns_all():
    html = (FIXTURES / "hepsiburada_category_page.html").read_text(encoding="utf-8")
    snaps = extract_cards_from_page(html, category="kozmetik", captured_at=NOW)
    assert len(snaps) == 3


def test_extract_cards_respects_max_products():
    html = (FIXTURES / "hepsiburada_category_page.html").read_text(encoding="utf-8")
    snaps = extract_cards_from_page(html, category="kozmetik", captured_at=NOW, max_products=2)
    assert len(snaps) == 2


def test_extract_cards_skips_unparseable():
    html = """
    <ul>
      <li data-test-id="product-card">
        <a href="/urun-HBV000001AAA">
          <span data-test-id="product-name">İyi Ürün</span>
          <span data-test-id="price">99,90 TL</span>
          <button data-test-id="add-to-cart">Sepete Ekle</button>
        </a>
      </li>
      <li data-test-id="product-card">
        <a href="/urun-HBV000002BBB">
          <span data-test-id="product-name">Fiyatsız Ürün</span>
        </a>
      </li>
    </ul>
    """
    snaps = extract_cards_from_page(html, category="kozmetik", captured_at=NOW)
    assert len(snaps) == 1
