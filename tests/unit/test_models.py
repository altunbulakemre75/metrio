from datetime import datetime
from dataclasses import asdict
from storage.models import ProductSnapshot


def test_product_snapshot_creates_with_all_fields():
    snap = ProductSnapshot(
        platform="trendyol",
        platform_product_id="123456",
        name="Nemlendirici Krem",
        brand="Nivea",
        category="kozmetik",
        product_url="https://trendyol.com/p/123456",
        image_url="https://cdn.trendyol.com/p/123456.jpg",
        price=149.90,
        original_price=199.90,
        discount_rate=0.25,
        seller_name="TestMagaza",
        seller_rating=9.2,
        in_stock=True,
        captured_at=datetime(2026, 4, 14, 3, 0, 0),
    )
    assert snap.name == "Nemlendirici Krem"
    assert snap.price == 149.90
    assert snap.in_stock is True


def test_product_snapshot_optional_fields_can_be_none():
    snap = ProductSnapshot(
        platform="trendyol",
        platform_product_id="123",
        name="Urun",
        brand=None,
        category="kozmetik",
        product_url="https://trendyol.com/p/123",
        image_url=None,
        price=99.90,
        original_price=None,
        discount_rate=None,
        seller_name=None,
        seller_rating=None,
        in_stock=False,
        captured_at=datetime.now(),
    )
    assert snap.brand is None
    assert snap.discount_rate is None


def test_product_snapshot_to_dict():
    snap = ProductSnapshot(
        platform="trendyol",
        platform_product_id="1",
        name="x",
        brand="y",
        category="kozmetik",
        product_url="u",
        image_url="i",
        price=1.0,
        original_price=2.0,
        discount_rate=0.5,
        seller_name="s",
        seller_rating=8.0,
        in_stock=True,
        captured_at=datetime(2026, 1, 1),
    )
    d = asdict(snap)
    assert d["name"] == "x"
    assert d["price"] == 1.0
