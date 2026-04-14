import sqlite3
from storage.database import connect, init_schema


def test_init_schema_creates_products_table():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='products'"
    ).fetchall()
    assert len(rows) == 1


def test_init_schema_creates_price_snapshots_table():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='price_snapshots'"
    ).fetchall()
    assert len(rows) == 1


def test_init_schema_creates_run_stats_table():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='run_stats'"
    ).fetchall()
    assert len(rows) == 1


def test_products_has_unique_constraint():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    conn.execute(
        "INSERT INTO products (platform, platform_product_id, name, category, product_url, "
        "first_seen_at, last_seen_at) VALUES ('trendyol', 'p1', 'a', 'kozmetik', 'u', '2026-01-01', '2026-01-01')"
    )
    import pytest
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO products (platform, platform_product_id, name, category, product_url, "
            "first_seen_at, last_seen_at) VALUES ('trendyol', 'p1', 'b', 'kozmetik', 'u2', '2026-01-01', '2026-01-01')"
        )


def test_init_schema_idempotent():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    init_schema(conn)  # should not raise
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    table_names = [r[0] for r in rows if not r[0].startswith("sqlite_")]
    assert set(table_names) == {"products", "price_snapshots", "run_stats"}


def test_connect_returns_connection(tmp_path):
    db_path = tmp_path / "test.db"
    conn = connect(str(db_path))
    assert conn is not None
    conn.execute("SELECT 1").fetchone()
    conn.close()
    assert db_path.exists()
