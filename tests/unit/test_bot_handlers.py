import sqlite3
from datetime import datetime, timedelta
import pytest
from bot.handlers import Response, handle_start, handle_durum, handle_trend, handle_fiyat
from storage.database import init_schema, save_snapshot, start_run, finish_run
from storage.models import ProductSnapshot


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    init_schema(c)
    return c


def _snap(pid, name, brand, price, days_ago=0):
    return ProductSnapshot(
        platform="trendyol", platform_product_id=pid, name=name, brand=brand,
        category="kozmetik", product_url=f"https://trendyol.com/{pid}",
        image_url=None, price=price, original_price=None, discount_rate=None,
        seller_name=None, seller_rating=None, in_stock=True,
        captured_at=datetime.now() - timedelta(days=days_ago),
    )


def test_handle_start_returns_welcome_text(conn):
    r = handle_start("", conn)
    assert isinstance(r, Response)
    assert "Metrio" in r.text
    assert "/durum" in r.text
    assert r.photo_png is None
    assert r.document_path is None


def test_handle_durum_empty_db(conn):
    r = handle_durum("", conn)
    assert "tarama" in r.text.lower()


def test_handle_durum_with_runs(conn):
    start_run(conn, run_id="r1", platform="trendyol", category="kozmetik", started_at=datetime(2026, 4, 15, 3, 0))
    finish_run(conn, run_id="r1", status="success", products_found=66, products_saved=66,
               products_failed=0, finished_at=datetime(2026, 4, 15, 3, 0, 14), duration_seconds=14,
               error_message=None)
    r = handle_durum("", conn)
    assert "66" in r.text
    assert "success" in r.text.lower() or "✅" in r.text


def test_handle_trend_empty_args(conn):
    r = handle_trend("", conn)
    assert "kullanım" in r.text.lower() or "marka" in r.text.lower()
    assert r.photo_png is None


def test_handle_trend_unknown_brand(conn):
    r = handle_trend("BilinmeyenMarka", conn)
    assert "veri" in r.text.lower()
    assert r.photo_png is None


def test_handle_fiyat_empty_args(conn):
    r = handle_fiyat("", conn)
    assert "kullanım" in r.text.lower() or "arama" in r.text.lower()


def test_handle_fiyat_no_match(conn):
    save_snapshot(conn, _snap("1", "Hyaluronic Serum", "L'Oréal", 127.90))
    r = handle_fiyat("telefon", conn)
    assert "bulunamadı" in r.text.lower() or "sonuç" in r.text.lower()


def test_handle_fiyat_match(conn):
    save_snapshot(conn, _snap("1", "Hyaluronic Serum", "L'Oréal", 127.90))
    save_snapshot(conn, _snap("2", "Vitamin C Serum", "The Ordinary", 89.50))
    save_snapshot(conn, _snap("3", "iPhone 15", "Apple", 45000.0))
    r = handle_fiyat("serum", conn)
    assert "L'Oréal" in r.text or "Serum" in r.text
    assert "Ordinary" in r.text or "Vitamin" in r.text
    assert "127" in r.text  # fiyat
