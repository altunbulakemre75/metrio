import sqlite3
from datetime import datetime, timedelta

import pytest

from deals.selector import select_deals
from storage.database import init_schema, save_snapshot
from storage.models import ProductSnapshot

NOW = datetime(2026, 11, 9, 10, 0)
TODAY = datetime(2026, 11, 9, 3, 0)


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn


def _save(db, pid, price, *, original=None, discount=None, at=TODAY, brand=None,
          category="kozmetik", in_stock=True, image: str | None = "https://cdn/x.jpg"):
    save_snapshot(db, ProductSnapshot(
        platform="trendyol", platform_product_id=pid, name=f"Urun {pid}",
        brand=brand or f"Marka{pid}", category=category,
        product_url=f"https://www.trendyol.com/x-p-{pid}", image_url=image,
        price=price, original_price=original, discount_rate=discount,
        seller_name=None, seller_rating=4.5, in_stock=in_stock, captured_at=at,
    ))


def _ids(deals):
    return [d.name for d in deals]


def _select(db, **kw):
    kw.setdefault("categories", ["kozmetik"])
    kw.setdefault("now", NOW)
    return select_deals(db, **kw)


def test_picks_discount_above_threshold_and_skips_small_ones(db):
    _save(db, "1", 60, original=100, discount=0.40)
    _save(db, "2", 90, original=100, discount=0.10)

    assert _ids(_select(db)) == ["Urun 1"]


def test_skips_stale_out_of_stock_and_other_category(db):
    _save(db, "old", 50, original=100, discount=0.5, at=NOW - timedelta(days=5))
    _save(db, "oos", 50, original=100, discount=0.5, in_stock=False)
    _save(db, "tel", 50, original=100, discount=0.5, category="cep-telefonu")
    _save(db, "noimg", 50, original=100, discount=0.5, image=None)

    assert _select(db) == []


def test_category_cap_keeps_bags_from_crowding_out_cosmetics(db):
    # Çantaların üstü çizili indirimi yüksek; sınır olmasa paylaşımın tamamı çanta olurdu.
    for i in range(4):
        _save(db, f"c{i}", 30, original=100, discount=0.70, category="canta")
    for i in range(3):
        _save(db, f"k{i}", 60, original=100, discount=0.40)

    deals = _select(db, categories=["kozmetik", "canta"], category_caps={"canta": 2})

    assert sorted(d.category for d in deals) == ["canta", "canta", "kozmetik", "kozmetik", "kozmetik"]


def test_excludes_recently_posted_products(db):
    _save(db, "1", 50, original=100, discount=0.5)
    pid = db.execute("SELECT id FROM products").fetchone()["id"]

    assert _select(db, exclude_ids={pid}) == []


def test_real_price_drop_counts_as_deal_and_outranks_listed_discount(db):
    _save(db, "drop", 120, at=TODAY - timedelta(days=1))
    _save(db, "drop", 80)
    _save(db, "listed", 70, original=100, discount=0.30)

    deals = _select(db)

    assert _ids(deals) == ["Urun drop", "Urun listed"]
    assert deals[0].previous_price == 120
    assert deals[0].drop_rate == pytest.approx(1 / 3)


def test_previous_price_older_than_a_week_is_not_a_drop(db):
    _save(db, "1", 200, at=TODAY - timedelta(days=60))
    _save(db, "1", 100)

    assert _select(db) == []


def test_lowest_30d_needs_enough_history_and_a_new_low(db):
    for d in range(1, 6):
        _save(db, "low", 100, at=TODAY - timedelta(days=d))
        _save(db, "flat", 60, at=TODAY - timedelta(days=d))
    _save(db, "low", 60, original=100, discount=0.4)
    _save(db, "flat", 60, original=100, discount=0.4)
    _save(db, "new", 60, original=100, discount=0.4)

    flags = {d.name: d.lowest_30d for d in _select(db)}

    assert flags == {"Urun low": True, "Urun flat": False, "Urun new": False}


def test_caps_products_per_brand_and_respects_limit(db):
    for i in range(4):
        _save(db, f"a{i}", 50, original=100, discount=0.5, brand="Pierre Cardin")
    for i in range(4):
        _save(db, f"b{i}", 50, original=100, discount=0.45)

    deals = _select(db, limit=5)

    assert len(deals) == 5
    assert sum(d.brand == "Pierre Cardin" for d in deals) == 2


def test_skips_off_topic_products_by_name_keyword(db):
    _save(db, "1", 50, original=100, discount=0.5)
    save_snapshot(db, ProductSnapshot(
        platform="trendyol", platform_product_id="det", name="Toz Çamaşır Deterjanı 9 Kg",
        brand="AREX", category="kozmetik", product_url="https://t/det", image_url="https://cdn/d.jpg",
        price=50, original_price=100, discount_rate=0.5, seller_name=None, seller_rating=4.0,
        in_stock=True, captured_at=TODAY,
    ))

    assert _ids(_select(db, exclude_words=["deterjan"])) == ["Urun 1"]
