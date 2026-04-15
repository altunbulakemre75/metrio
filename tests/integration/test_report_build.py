import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from reports.builder import build_weekly_report
from storage.database import init_schema, save_snapshot
from storage.models import ProductSnapshot


def _seeded_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    base = datetime.now() - timedelta(days=10)
    for i in range(5):
        for d in range(10):
            snap = ProductSnapshot(
                platform="trendyol",
                platform_product_id=f"p{i}",
                name=f"Ürün {i}",
                brand=f"Marka{i % 2}",
                category="kozmetik",
                product_url=f"https://www.trendyol.com/x/urun-p-{i}",
                image_url=None,
                price=50.0 + i + d * 0.5,
                original_price=60.0 + i,
                discount_rate=0.15,
                seller_name=None,
                seller_rating=None,
                in_stock=True,
                captured_at=base + timedelta(days=d),
            )
            save_snapshot(conn, snap)
    return conn


def test_build_weekly_report_produces_pdf(tmp_path: Path):
    conn = _seeded_conn()
    output = tmp_path / "sub" / "report.pdf"
    result = build_weekly_report(conn, output_path=output, days=7)

    assert result == output
    assert output.exists()
    assert output.stat().st_size > 5000  # > 5KB
    # Minimum PDF header check
    assert output.read_bytes()[:4] == b"%PDF"


def test_build_weekly_report_empty_db(tmp_path: Path):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    output = tmp_path / "empty.pdf"
    build_weekly_report(conn, output_path=output, days=7)
    assert output.exists()
    assert output.read_bytes()[:4] == b"%PDF"
