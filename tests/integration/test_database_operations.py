import sqlite3
from datetime import datetime
import pytest
from storage.database import (
    init_schema,
    save_snapshot,
    get_product_by_platform_id,
    get_latest_snapshot,
)
from storage.models import ProductSnapshot


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    yield conn
    conn.close()


def _snap(**overrides) -> ProductSnapshot:
    base = dict(
        platform="trendyol",
        platform_product_id="123",
        name="Nemlendirici",
        brand="Nivea",
        category="kozmetik",
        product_url="https://trendyol.com/p/123",
        image_url="https://cdn/img.jpg",
        price=99.90,
        original_price=149.90,
        discount_rate=0.33,
        seller_name="Magaza",
        seller_rating=9.0,
        in_stock=True,
        captured_at=datetime(2026, 4, 14, 3, 0),
    )
    base.update(overrides)
    return ProductSnapshot(**base)


def test_save_snapshot_creates_new_product(db):
    save_snapshot(db, _snap())
    row = db.execute("SELECT COUNT(*) FROM products").fetchone()
    assert row[0] == 1


def test_save_snapshot_creates_price_row(db):
    save_snapshot(db, _snap())
    row = db.execute("SELECT COUNT(*) FROM price_snapshots").fetchone()
    assert row[0] == 1


def test_save_snapshot_twice_keeps_one_product_row(db):
    save_snapshot(db, _snap(price=99.90, captured_at=datetime(2026, 4, 14)))
    save_snapshot(db, _snap(price=89.90, captured_at=datetime(2026, 4, 15)))
    products = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    snaps = db.execute("SELECT COUNT(*) FROM price_snapshots").fetchone()[0]
    assert products == 1
    assert snaps == 2


def test_save_snapshot_updates_last_seen_at(db):
    save_snapshot(db, _snap(captured_at=datetime(2026, 4, 14)))
    save_snapshot(db, _snap(captured_at=datetime(2026, 4, 20)))
    row = db.execute("SELECT first_seen_at, last_seen_at FROM products").fetchone()
    assert row["first_seen_at"] == "2026-04-14 00:00:00"
    assert row["last_seen_at"] == "2026-04-20 00:00:00"


def test_get_product_by_platform_id_found(db):
    save_snapshot(db, _snap())
    p = get_product_by_platform_id(db, "trendyol", "123")
    assert p is not None
    assert p["name"] == "Nemlendirici"


def test_get_product_by_platform_id_not_found(db):
    assert get_product_by_platform_id(db, "trendyol", "999") is None


def test_get_latest_snapshot_returns_most_recent(db):
    save_snapshot(db, _snap(price=100.0, captured_at=datetime(2026, 4, 14)))
    save_snapshot(db, _snap(price=90.0, captured_at=datetime(2026, 4, 15)))
    save_snapshot(db, _snap(price=95.0, captured_at=datetime(2026, 4, 16)))

    product = get_product_by_platform_id(db, "trendyol", "123")
    latest = get_latest_snapshot(db, product["id"])
    assert latest["price"] == 95.0


def test_save_snapshot_handles_null_fields(db):
    save_snapshot(db, _snap(brand=None, original_price=None, discount_rate=None,
                             seller_name=None, seller_rating=None, image_url=None))
    row = db.execute("SELECT brand, image_url FROM products").fetchone()
    assert row["brand"] is None
    assert row["image_url"] is None
