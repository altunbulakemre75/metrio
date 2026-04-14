import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class ProductMatch:
    product_id: int
    platform_product_id: str
    name: str
    brand: str | None
    current_price: float


@dataclass
class HistoryPoint:
    captured_at: datetime
    price: float
    original_price: float | None
    discount_rate: float | None
    in_stock: bool


def search_products(conn: sqlite3.Connection, query: str, limit: int = 20) -> list[ProductMatch]:
    pattern = f"%{query.lower()}%"
    rows = conn.execute("""
        SELECT p.id, p.platform_product_id, p.name, p.brand,
               (SELECT price FROM price_snapshots
                WHERE product_id = p.id ORDER BY captured_at DESC LIMIT 1) AS cur_price
        FROM products p
        WHERE LOWER(p.name) LIKE ? OR LOWER(p.brand) LIKE ?
        ORDER BY p.name ASC
        LIMIT ?
    """, (pattern, pattern, limit)).fetchall()

    return [
        ProductMatch(
            product_id=r["id"],
            platform_product_id=r["platform_product_id"],
            name=r["name"],
            brand=r["brand"],
            current_price=r["cur_price"] or 0.0,
        )
        for r in rows
    ]


def get_product_history(
    conn: sqlite3.Connection,
    product_id: int,
    days: int = 30,
) -> list[HistoryPoint]:
    cutoff = datetime.now() - timedelta(days=days)
    rows = conn.execute("""
        SELECT price, original_price, discount_rate, in_stock, captured_at
        FROM price_snapshots
        WHERE product_id = ? AND captured_at >= ?
        ORDER BY captured_at ASC
    """, (product_id, cutoff)).fetchall()

    return [
        HistoryPoint(
            captured_at=datetime.fromisoformat(r["captured_at"]),
            price=r["price"],
            original_price=r["original_price"],
            discount_rate=r["discount_rate"],
            in_stock=bool(r["in_stock"]),
        )
        for r in rows
    ]
