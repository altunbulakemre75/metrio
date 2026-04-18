import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal


@dataclass
class PriceChange:
    product_id: int
    platform_product_id: str
    name: str
    brand: str | None
    category: str
    old_price: float
    new_price: float
    change_amount: float
    change_percent: float
    captured_at_old: datetime
    captured_at_new: datetime
    product_url: str


def top_movers(
    conn: sqlite3.Connection,
    days: int = 7,
    limit: int = 20,
    direction: Literal["down", "up", "both"] = "both",
    platforms: list[str] | None = None,
) -> list[PriceChange]:
    """Son N günde fiyat hareketi olan ürünleri bulur."""
    cutoff = datetime.now() - timedelta(days=days)

    plat_clause = ""
    params: list = [cutoff]
    if platforms:
        placeholders = ",".join("?" * len(platforms))
        plat_clause = f"AND p.platform IN ({placeholders})"
        params.extend(platforms)

    query = f"""
        WITH product_range AS (
            SELECT s.product_id,
                   MIN(s.captured_at) AS first_at,
                   MAX(s.captured_at) AS last_at
            FROM price_snapshots s
            WHERE s.captured_at >= ?
            GROUP BY s.product_id
            HAVING COUNT(*) >= 2
        )
        SELECT p.id, p.platform_product_id, p.name, p.brand, p.category,
               p.product_url,
               s_old.price AS old_price, s_old.captured_at AS old_at,
               s_new.price AS new_price, s_new.captured_at AS new_at
        FROM product_range pr
        JOIN products p ON p.id = pr.product_id {plat_clause}
        JOIN price_snapshots s_old
            ON s_old.product_id = pr.product_id AND s_old.captured_at = pr.first_at
        JOIN price_snapshots s_new
            ON s_new.product_id = pr.product_id AND s_new.captured_at = pr.last_at
        WHERE s_old.price != s_new.price
    """
    rows = conn.execute(query, params).fetchall()

    changes = []
    for r in rows:
        change_amount = r["new_price"] - r["old_price"]
        if r["old_price"] == 0:
            continue
        change_percent = change_amount / r["old_price"]

        if direction == "down" and change_percent >= 0:
            continue
        if direction == "up" and change_percent <= 0:
            continue

        changes.append(PriceChange(
            product_id=r["id"],
            platform_product_id=r["platform_product_id"],
            name=r["name"],
            brand=r["brand"],
            category=r["category"],
            old_price=r["old_price"],
            new_price=r["new_price"],
            change_amount=change_amount,
            change_percent=change_percent,
            captured_at_old=datetime.fromisoformat(r["old_at"]),
            captured_at_new=datetime.fromisoformat(r["new_at"]),
            product_url=r["product_url"],
        ))

    changes.sort(key=lambda c: abs(c.change_percent), reverse=True)
    return changes[:limit]
