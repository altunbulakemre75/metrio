import sqlite3
from datetime import datetime, timedelta
import pytest
from storage.database import init_schema, save_snapshot
from storage.models import ProductSnapshot
from analysis.anomaly import detect_anomalies


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


def test_detects_price_drop_anomaly(db):
    for days_ago in range(30, 0, -1):
        save_snapshot(db, _snap("1", 100, days_ago=days_ago))
    save_snapshot(db, _snap("1", 60, days_ago=0))

    anomalies = detect_anomalies(db, threshold_percent=0.20)
    assert len(anomalies) == 1
    assert anomalies[0].direction == "drop"
    assert anomalies[0].deviation_percent < -0.30


def test_detects_price_spike_anomaly(db):
    for days_ago in range(30, 0, -1):
        save_snapshot(db, _snap("1", 100, days_ago=days_ago))
    save_snapshot(db, _snap("1", 140, days_ago=0))

    anomalies = detect_anomalies(db, threshold_percent=0.20)
    assert len(anomalies) == 1
    assert anomalies[0].direction == "spike"


def test_ignores_minor_changes(db):
    for days_ago in range(30, 0, -1):
        save_snapshot(db, _snap("1", 100, days_ago=days_ago))
    save_snapshot(db, _snap("1", 105, days_ago=0))

    anomalies = detect_anomalies(db, threshold_percent=0.20)
    assert len(anomalies) == 0


def test_low_confidence_for_sparse_data(db):
    save_snapshot(db, _snap("1", 100, days_ago=5))
    save_snapshot(db, _snap("1", 50, days_ago=0))

    anomalies = detect_anomalies(db, threshold_percent=0.20)
    if anomalies:
        assert anomalies[0].confidence == "low"


def test_high_confidence_for_dense_data(db):
    for days_ago in range(20, 0, -1):
        save_snapshot(db, _snap("1", 100, days_ago=days_ago))
    save_snapshot(db, _snap("1", 50, days_ago=0))

    anomalies = detect_anomalies(db, threshold_percent=0.20)
    assert anomalies[0].confidence == "high"
