from datetime import datetime
from pathlib import Path
from scrapers.trendyol import parse_product_card


FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load(relative: str) -> str:
    return (FIXTURES / relative).read_text(encoding="utf-8")


def test_parse_full_card():
    html = _load("trendyol_product_card.html")
    snap = parse_product_card(html, category="kozmetik", captured_at=datetime(2026, 4, 14))
    assert snap is not None
    assert snap.platform == "trendyol"
    assert snap.platform_product_id == "123456789"
    assert snap.name == "Nemlendirici Krem 200ml"
    assert snap.brand == "Nivea"
    assert snap.price == 149.90
    assert snap.original_price == 199.90
    assert abs(snap.discount_rate - 0.25) < 0.01
    assert snap.seller_name == "NiveaResmiMagaza"
    assert snap.seller_rating == 9.2
    assert snap.image_url.startswith("https://cdn.dsmcdn.com/")
    assert snap.product_url.startswith("https://www.trendyol.com/")
    assert snap.in_stock is True


def test_parse_card_without_discount():
    html = _load("trendyol_edge_cases/no_discount.html")
    snap = parse_product_card(html, category="kozmetik", captured_at=datetime(2026, 4, 14))
    assert snap is not None
    assert snap.price == 89.50
    assert snap.original_price is None
    assert snap.discount_rate is None


def test_parse_out_of_stock_card():
    html = _load("trendyol_edge_cases/out_of_stock.html")
    snap = parse_product_card(html, category="kozmetik", captured_at=datetime(2026, 4, 14))
    assert snap is not None
    assert snap.in_stock is False


def test_parse_card_without_data_id_returns_none():
    html = '<div class="p-card-wrppr"></div>'
    snap = parse_product_card(html, category="kozmetik", captured_at=datetime.now())
    assert snap is None
