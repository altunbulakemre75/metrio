import sqlite3
from datetime import datetime
import pandas as pd


def get_latest_snapshots_df(
    conn: sqlite3.Connection,
    platforms: list[str] | None = None,
) -> pd.DataFrame:
    """Her ürün için en son snapshot'ı tek satır halinde döner."""
    plat_clause = ""
    params: list = []
    if platforms:
        placeholders = ",".join("?" * len(platforms))
        plat_clause = f"WHERE p.platform IN ({placeholders})"
        params = list(platforms)

    query = f"""
        SELECT p.id AS product_id, p.platform, p.platform_product_id,
               p.name, p.brand, p.category, p.product_url, p.image_url,
               s.price, s.original_price, s.discount_rate,
               s.seller_rating, s.in_stock, s.captured_at
        FROM products p
        JOIN (
            SELECT product_id, MAX(captured_at) AS max_at
            FROM price_snapshots GROUP BY product_id
        ) latest ON latest.product_id = p.id
        JOIN price_snapshots s
            ON s.product_id = p.id AND s.captured_at = latest.max_at
        {plat_clause}
    """
    return pd.read_sql_query(query, conn, params=params or None)


def get_price_history_df(conn: sqlite3.Connection, product_id: int) -> pd.DataFrame:
    query = """
        SELECT price, original_price, discount_rate, in_stock, captured_at
        FROM price_snapshots
        WHERE product_id = ?
        ORDER BY captured_at ASC
    """
    return pd.read_sql_query(query, conn, params=(product_id,))


def get_unique_platforms(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT platform FROM products ORDER BY platform"
    ).fetchall()
    return [r[0] for r in rows]


def get_unique_brands(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT brand FROM products WHERE brand IS NOT NULL ORDER BY brand"
    ).fetchall()
    return [r[0] for r in rows]


def get_unique_categories(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT category FROM products ORDER BY category"
    ).fetchall()
    return [r[0] for r in rows]


def get_date_range(conn: sqlite3.Connection) -> tuple[datetime | None, datetime | None]:
    row = conn.execute(
        "SELECT MIN(captured_at), MAX(captured_at) FROM price_snapshots"
    ).fetchone()
    return (row[0], row[1]) if row and row[0] else (None, None)
