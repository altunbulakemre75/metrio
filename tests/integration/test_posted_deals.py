import sqlite3
from datetime import datetime

import pytest

from storage.database import (
    get_recently_posted_product_ids, init_schema, record_posted_deals, save_snapshot,
)
from storage.models import ProductSnapshot


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn


def _product(db, pid: str) -> int:
    save_snapshot(db, ProductSnapshot(
        platform="trendyol", platform_product_id=pid, name=f"Urun {pid}",
        brand="Marka", category="kozmetik", product_url=f"https://t.com/{pid}",
        image_url=None, price=100, original_price=None, discount_rate=None,
        seller_name=None, seller_rating=None, in_stock=True,
        captured_at=datetime(2026, 11, 1),
    ))
    return db.execute(
        "SELECT id FROM products WHERE platform_product_id = ?", (pid,)
    ).fetchone()["id"]


def test_recently_posted_returns_only_posts_after_cutoff(db):
    old, new = _product(db, "1"), _product(db, "2")
    record_posted_deals(db, [old], channel="instagram", post_ref="m1",
                        posted_at=datetime(2026, 10, 20))
    record_posted_deals(db, [new], channel="instagram", post_ref="m2",
                        posted_at=datetime(2026, 11, 8))

    assert get_recently_posted_product_ids(db, since=datetime(2026, 11, 1)) == {new}


def test_recently_posted_is_empty_without_posts(db):
    assert get_recently_posted_product_ids(db, since=datetime(2026, 1, 1)) == set()
