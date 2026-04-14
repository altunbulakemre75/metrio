import sqlite3
from datetime import datetime
from pathlib import Path

from storage.models import ProductSnapshot


_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def _adapt_datetime(dt: datetime) -> str:
    return dt.isoformat(sep=" ", timespec="seconds")


sqlite3.register_adapter(datetime, _adapt_datetime)


def connect(db_path: str) -> sqlite3.Connection:
    """SQLite bağlantısı açar, gerekirse veritabanı dosyasını oluşturur."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Tüm migration SQL dosyalarını sırayla çalıştırır. Idempotent."""
    for sql_file in sorted(_MIGRATIONS_DIR.glob("*.sql")):
        sql = sql_file.read_text(encoding="utf-8")
        conn.executescript(sql)
    conn.commit()


def save_snapshot(conn: sqlite3.Connection, snap: ProductSnapshot) -> int:
    """Ürünü upsert eder, price_snapshots'a yeni satır atar. Snapshot ID'si döner."""
    existing = get_product_by_platform_id(conn, snap.platform, snap.platform_product_id)

    if existing is None:
        cursor = conn.execute(
            """
            INSERT INTO products (
                platform, platform_product_id, name, brand, category,
                product_url, image_url, first_seen_at, last_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snap.platform, snap.platform_product_id, snap.name, snap.brand,
                snap.category, snap.product_url, snap.image_url,
                snap.captured_at, snap.captured_at,
            ),
        )
        product_id = cursor.lastrowid
    else:
        product_id = existing["id"]
        conn.execute(
            """
            UPDATE products
            SET name = ?, brand = ?, product_url = ?, image_url = ?, last_seen_at = ?
            WHERE id = ?
            """,
            (snap.name, snap.brand, snap.product_url, snap.image_url, snap.captured_at, product_id),
        )

    cursor = conn.execute(
        """
        INSERT INTO price_snapshots (
            product_id, price, original_price, discount_rate,
            seller_name, seller_rating, in_stock, captured_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            product_id, snap.price, snap.original_price, snap.discount_rate,
            snap.seller_name, snap.seller_rating,
            1 if snap.in_stock else 0, snap.captured_at,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def get_product_by_platform_id(
    conn: sqlite3.Connection, platform: str, platform_product_id: str
) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM products WHERE platform = ? AND platform_product_id = ?",
        (platform, platform_product_id),
    ).fetchone()


def get_latest_snapshot(conn: sqlite3.Connection, product_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM price_snapshots WHERE product_id = ? ORDER BY captured_at DESC LIMIT 1",
        (product_id,),
    ).fetchone()


def start_run(
    conn: sqlite3.Connection,
    run_id: str,
    platform: str,
    category: str,
    started_at: datetime,
) -> None:
    conn.execute(
        "INSERT INTO run_stats (run_id, platform, category, status, started_at) "
        "VALUES (?, ?, ?, 'running', ?)",
        (run_id, platform, category, started_at),
    )
    conn.commit()


def finish_run(
    conn: sqlite3.Connection,
    run_id: str,
    status: str,
    products_found: int,
    products_saved: int,
    products_failed: int,
    finished_at: datetime,
    duration_seconds: int,
    error_message: str | None,
) -> None:
    conn.execute(
        """
        UPDATE run_stats
        SET status = ?, products_found = ?, products_saved = ?,
            products_failed = ?, finished_at = ?, duration_seconds = ?,
            error_message = ?
        WHERE run_id = ?
        """,
        (status, products_found, products_saved, products_failed,
         finished_at, duration_seconds, error_message, run_id),
    )
    conn.commit()
