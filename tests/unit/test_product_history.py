import sqlite3
from datetime import datetime, timedelta
import pytest
from storage.database import init_schema, save_snapshot
from storage.models import ProductSnapshot
from analysis.product_history import search_products, get_product_history


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn


def _snap(pid, price, name="Nivea Krem", days_ago=0):
    return ProductSnapshot(
        platform="trendyol", platform_product_id=pid, name=name,
        brand="Nivea", category="kozmetik",
        product_url=f"https://trendyol.com/{pid}", image_url=None,
        price=price, original_price=None, discount_rate=None,
        seller_name=None, seller_rating=None, in_stock=True,
        captured_at=datetime.now() - timedelta(days=days_ago),
    )


def test_search_finds_by_name_substring(db):
    save_snapshot(db, _snap("1", 100, name="Nivea Nemlendirici Krem"))
    save_snapshot(db, _snap("2", 200, name="Loreal Ruj"))

    results = search_products(db, "nemlendirici")
    assert len(results) == 1
    assert results[0].platform_product_id == "1"


def test_search_case_insensitive(db):
    save_snapshot(db, _snap("1", 100, name="Nivea Nemlendirici"))
    results = search_products(db, "NEMLENDIRICI")
    assert len(results) == 1


def test_get_product_history_returns_ordered(db):
    save_snapshot(db, _snap("1", 100, days_ago=2))
    save_snapshot(db, _snap("1", 90, days_ago=1))
    save_snapshot(db, _snap("1", 85, days_ago=0))

    product_id = db.execute("SELECT id FROM products").fetchone()[0]
    history = get_product_history(db, product_id)
    assert len(history) == 3
    assert history[0].price > history[-1].price
