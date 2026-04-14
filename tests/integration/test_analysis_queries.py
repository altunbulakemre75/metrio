import sqlite3
from datetime import datetime
import pytest
from storage.database import init_schema, save_snapshot
from storage.models import ProductSnapshot
from analysis.queries import (
    get_latest_snapshots_df,
    get_price_history_df,
    get_unique_brands,
    get_unique_categories,
)


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn


def _snap(pid, price, brand="Nivea", captured_at=datetime(2026, 4, 14)):
    return ProductSnapshot(
        platform="trendyol", platform_product_id=pid, name=f"Urun {pid}",
        brand=brand, category="kozmetik",
        product_url=f"https://trendyol.com/{pid}", image_url=None,
        price=price, original_price=None, discount_rate=None,
        seller_name=None, seller_rating=None, in_stock=True,
        captured_at=captured_at,
    )


def test_get_latest_snapshots_df_returns_one_row_per_product(db):
    save_snapshot(db, _snap("1", 100, captured_at=datetime(2026, 4, 10)))
    save_snapshot(db, _snap("1", 90, captured_at=datetime(2026, 4, 14)))
    save_snapshot(db, _snap("2", 200, captured_at=datetime(2026, 4, 14)))

    df = get_latest_snapshots_df(db)
    assert len(df) == 2
    prices = dict(zip(df["platform_product_id"], df["price"]))
    assert prices["1"] == 90
    assert prices["2"] == 200


def test_get_price_history_df_orders_chronologically(db):
    save_snapshot(db, _snap("1", 100, captured_at=datetime(2026, 4, 10)))
    save_snapshot(db, _snap("1", 95, captured_at=datetime(2026, 4, 12)))
    save_snapshot(db, _snap("1", 90, captured_at=datetime(2026, 4, 14)))

    product_id = db.execute("SELECT id FROM products").fetchone()[0]
    df = get_price_history_df(db, product_id)
    assert len(df) == 3
    assert list(df["price"]) == [100, 95, 90]


def test_get_unique_brands_returns_sorted_list(db):
    save_snapshot(db, _snap("1", 100, brand="Nivea"))
    save_snapshot(db, _snap("2", 200, brand="Loreal"))
    save_snapshot(db, _snap("3", 150, brand="Nivea"))

    brands = get_unique_brands(db)
    assert brands == ["Loreal", "Nivea"]


def test_get_unique_categories_returns_list(db):
    save_snapshot(db, _snap("1", 100))
    cats = get_unique_categories(db)
    assert cats == ["kozmetik"]
