import sqlite3
from datetime import datetime, timedelta
import pytest
from storage.database import init_schema, save_snapshot
from storage.models import ProductSnapshot
from analysis.price_changes import top_movers, PriceChange


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn


def _snap(pid, price, days_ago, brand="Nivea"):
    return ProductSnapshot(
        platform="trendyol", platform_product_id=pid, name=f"Urun {pid}",
        brand=brand, category="kozmetik",
        product_url=f"https://trendyol.com/{pid}", image_url=None,
        price=price, original_price=None, discount_rate=None,
        seller_name=None, seller_rating=None, in_stock=True,
        captured_at=datetime.now() - timedelta(days=days_ago),
    )


def test_top_movers_finds_biggest_drops(db):
    save_snapshot(db, _snap("1", 100, days_ago=6))
    save_snapshot(db, _snap("1", 80, days_ago=0))
    save_snapshot(db, _snap("2", 200, days_ago=6))
    save_snapshot(db, _snap("2", 150, days_ago=0))
    save_snapshot(db, _snap("3", 50, days_ago=6))
    save_snapshot(db, _snap("3", 55, days_ago=0))

    movers = top_movers(db, days=7, direction="down")
    assert len(movers) == 2
    assert movers[0].platform_product_id == "2"
    assert movers[0].change_percent == pytest.approx(-0.25)


def test_top_movers_includes_both_directions(db):
    save_snapshot(db, _snap("1", 100, days_ago=6))
    save_snapshot(db, _snap("1", 80, days_ago=0))
    save_snapshot(db, _snap("2", 50, days_ago=6))
    save_snapshot(db, _snap("2", 60, days_ago=0))

    movers = top_movers(db, days=7, direction="both")
    assert len(movers) == 2


def test_top_movers_ignores_products_with_single_snapshot(db):
    save_snapshot(db, _snap("1", 100, days_ago=0))

    movers = top_movers(db, days=7)
    assert len(movers) == 0


def test_top_movers_respects_limit(db):
    for i in range(10):
        save_snapshot(db, _snap(str(i), 100, days_ago=6))
        save_snapshot(db, _snap(str(i), 80 + i, days_ago=0))

    movers = top_movers(db, days=7, limit=3)
    assert len(movers) == 3


def test_price_change_dataclass_fields():
    pc = PriceChange(
        product_id=1, platform_product_id="p1", name="x", brand="y",
        category="kozmetik", old_price=100, new_price=80,
        change_amount=-20, change_percent=-0.2,
        captured_at_old=datetime(2026, 4, 1), captured_at_new=datetime(2026, 4, 7),
        product_url="https://example.com",
    )
    assert pc.change_percent == -0.2
