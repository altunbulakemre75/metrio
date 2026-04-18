import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta


@dataclass
class TrendPoint:
    date: date
    average_price: float
    median_price: float
    product_count: int


def _aggregate_query(
    conn: sqlite3.Connection,
    where_clause: str,
    params: tuple,
    days: int,
    platforms: list[str] | None = None,
) -> list[TrendPoint]:
    cutoff = datetime.now() - timedelta(days=days)
    plat_clause = ""
    plat_params: list = []
    if platforms:
        placeholders = ",".join("?" * len(platforms))
        plat_clause = f"AND p.platform IN ({placeholders})"
        plat_params = list(platforms)

    query = f"""
        SELECT DATE(s.captured_at) AS day,
               AVG(s.price) AS avg_price,
               COUNT(DISTINCT s.product_id) AS product_count,
               GROUP_CONCAT(s.price) AS price_list
        FROM price_snapshots s
        JOIN products p ON p.id = s.product_id
        WHERE s.captured_at >= ? AND {where_clause} {plat_clause}
        GROUP BY day
        ORDER BY day ASC
    """
    rows = conn.execute(query, (cutoff, *params, *plat_params)).fetchall()

    points = []
    for r in rows:
        prices = sorted(float(x) for x in r["price_list"].split(","))
        n = len(prices)
        median = prices[n // 2] if n % 2 else (prices[n // 2 - 1] + prices[n // 2]) / 2
        points.append(TrendPoint(
            date=date.fromisoformat(r["day"]),
            average_price=r["avg_price"],
            median_price=median,
            product_count=r["product_count"],
        ))
    return points


def brand_trend(
    conn: sqlite3.Connection,
    brand: str,
    days: int = 30,
    platforms: list[str] | None = None,
) -> list[TrendPoint]:
    return _aggregate_query(conn, "p.brand = ?", (brand,), days, platforms)


def category_trend(
    conn: sqlite3.Connection,
    category: str,
    days: int = 30,
    platforms: list[str] | None = None,
) -> list[TrendPoint]:
    return _aggregate_query(conn, "p.category = ?", (category,), days, platforms)
