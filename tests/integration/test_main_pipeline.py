import sqlite3
from datetime import datetime
from unittest.mock import MagicMock
import pytest

from main import run_pipeline
from storage.database import init_schema
from storage.models import ProductSnapshot


@pytest.fixture
def in_memory_db(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)

    def fake_connect(_path):
        return conn

    monkeypatch.setattr("main.connect", fake_connect)
    yield conn
    conn.close()


def _fake_snap(pid: str, price: float) -> ProductSnapshot:
    return ProductSnapshot(
        platform="trendyol",
        platform_product_id=pid,
        name=f"Urun {pid}",
        brand="Marka",
        category="kozmetik",
        product_url=f"https://trendyol.com/p/{pid}",
        image_url=None,
        price=price,
        original_price=None,
        discount_rate=None,
        seller_name=None,
        seller_rating=None,
        in_stock=True,
        captured_at=datetime(2026, 4, 14, 3, 0),
    )


def test_run_pipeline_saves_all_snapshots(in_memory_db):
    fake_scraper = MagicMock()
    fake_scraper.fetch_category.return_value = [
        _fake_snap("1", 100.0),
        _fake_snap("2", 200.0),
        _fake_snap("3", 300.0),
    ]

    stats = run_pipeline(
        scraper=fake_scraper,
        category_url="https://trendyol.com/kozmetik",
        category_name="kozmetik",
        max_products=500,
    )

    assert stats["status"] == "success"
    assert stats["products_saved"] == 3
    assert stats["products_failed"] == 0

    count = in_memory_db.execute("SELECT COUNT(*) FROM price_snapshots").fetchone()[0]
    assert count == 3


def test_run_pipeline_records_run_stats(in_memory_db):
    fake_scraper = MagicMock()
    fake_scraper.fetch_category.return_value = [_fake_snap("1", 100.0)]

    run_pipeline(
        scraper=fake_scraper,
        category_url="https://trendyol.com/kozmetik",
        category_name="kozmetik",
        max_products=500,
    )

    row = in_memory_db.execute("SELECT * FROM run_stats").fetchone()
    assert row is not None
    assert row["status"] == "success"
    assert row["products_found"] == 1


def test_run_pipeline_handles_scraper_exception(in_memory_db):
    fake_scraper = MagicMock()
    fake_scraper.fetch_category.side_effect = RuntimeError("Anti-bot tetiklendi")

    stats = run_pipeline(
        scraper=fake_scraper,
        category_url="https://trendyol.com/kozmetik",
        category_name="kozmetik",
        max_products=500,
    )

    assert stats["status"] == "failed"
    assert "Anti-bot" in stats["error_message"]

    row = in_memory_db.execute("SELECT status, error_message FROM run_stats").fetchone()
    assert row["status"] == "failed"
    assert "Anti-bot" in row["error_message"]


def test_run_pipeline_closes_scraper_even_on_error(in_memory_db):
    fake_scraper = MagicMock()
    fake_scraper.fetch_category.side_effect = RuntimeError("boom")

    run_pipeline(
        scraper=fake_scraper,
        category_url="https://trendyol.com/kozmetik",
        category_name="kozmetik",
        max_products=500,
    )

    fake_scraper.close.assert_called_once()
