import sqlite3
from datetime import datetime, timedelta
import pytest
from storage.database import init_schema, save_snapshot
from storage.models import ProductSnapshot
from analysis.trends import brand_trend, category_trend


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn


def _snap(pid, price, days_ago, brand="Nivea", category="kozmetik"):
    return ProductSnapshot(
        platform="trendyol", platform_product_id=pid, name=f"Urun {pid}",
        brand=brand, category=category,
        product_url=f"https://trendyol.com/{pid}", image_url=None,
        price=price, original_price=None, discount_rate=None,
        seller_name=None, seller_rating=None, in_stock=True,
        captured_at=datetime.now() - timedelta(days=days_ago),
    )


def test_brand_trend_returns_daily_averages(db):
    save_snapshot(db, _snap("1", 100, days_ago=2, brand="Nivea"))
    save_snapshot(db, _snap("2", 200, days_ago=2, brand="Nivea"))
    save_snapshot(db, _snap("1", 110, days_ago=1, brand="Nivea"))

    points = brand_trend(db, brand="Nivea", days=7)
    assert len(points) >= 2
    for p in points:
        assert p.product_count > 0
        assert p.average_price > 0


def test_brand_trend_filters_by_brand(db):
    save_snapshot(db, _snap("1", 100, days_ago=1, brand="Nivea"))
    save_snapshot(db, _snap("2", 500, days_ago=1, brand="Loreal"))

    points = brand_trend(db, brand="Nivea", days=7)
    for p in points:
        assert p.average_price == 100


def test_category_trend(db):
    save_snapshot(db, _snap("1", 100, days_ago=1, category="kozmetik"))
    save_snapshot(db, _snap("2", 500, days_ago=1, category="elektronik"))

    kozmetik = category_trend(db, category="kozmetik", days=7)
    for p in kozmetik:
        assert p.average_price == 100
