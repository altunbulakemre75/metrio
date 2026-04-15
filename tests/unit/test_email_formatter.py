import sqlite3
from datetime import datetime, timedelta

from notifications.email import format_email_body, default_subject
from storage.database import init_schema, save_snapshot
from storage.models import ProductSnapshot


def _seeded():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    base = datetime.now() - timedelta(days=10)
    for i in range(3):
        for d in range(5):
            price = 100.0 - (i * 30 if d == 4 else 0)  # last day has drop for i=1,2
            snap = ProductSnapshot(
                platform="trendyol", platform_product_id=f"p{i}",
                name=f"Ürün {i}", brand=f"Marka{i}", category="kozmetik",
                product_url=f"https://x/urun-p-{i}", image_url=None,
                price=price, original_price=120.0, discount_rate=0.15,
                seller_name=None, seller_rating=None, in_stock=True,
                captured_at=base + timedelta(days=d),
            )
            save_snapshot(conn, snap)
    return conn


def test_body_empty_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    text = format_email_body(conn, days=7)
    assert "takip edilen veri yok" in text
    assert "PDF ekinde" in text


def test_body_with_data():
    conn = _seeded()
    text = format_email_body(conn, days=7)
    assert "3 ürün takip edildi" in text
    assert "PDF ekinde" in text
    assert "Metrio" in text


def test_default_subject_contains_date():
    subject = default_subject()
    assert "Metrio" in subject
    assert datetime.now().strftime("%Y-%m-%d") in subject
