import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal


@dataclass
class Anomaly:
    product_id: int
    platform_product_id: str
    name: str
    brand: str | None
    category: str
    current_price: float
    average_price: float
    deviation_percent: float
    direction: Literal["drop", "spike"]
    confidence: Literal["low", "medium", "high"]
    snapshot_count: int
    product_url: str


def _confidence(count: int) -> str:
    if count < 5:
        return "low"
    if count < 15:
        return "medium"
    return "high"


def detect_anomalies(
    conn: sqlite3.Connection,
    lookback_days: int = 30,
    threshold_percent: float = 0.20,
    platforms: list[str] | None = None,
) -> list[Anomaly]:
    """Son N günün ortalamasından eşiği aşan sapmaları bulur."""
    cutoff = datetime.now() - timedelta(days=lookback_days)

    plat_clause = ""
    params: list = [cutoff]
    if platforms:
        placeholders = ",".join("?" * len(platforms))
        plat_clause = f"AND p.platform IN ({placeholders})"
        params.extend(platforms)

    query = f"""
        SELECT p.id, p.platform_product_id, p.name, p.brand, p.category, p.product_url,
               (SELECT price FROM price_snapshots s2
                WHERE s2.product_id = p.id ORDER BY s2.captured_at DESC LIMIT 1) AS current_price,
               AVG(s.price) AS avg_price,
               COUNT(s.id) AS snap_count
        FROM products p
        JOIN price_snapshots s ON s.product_id = p.id
        WHERE s.captured_at >= ? {plat_clause}
        GROUP BY p.id
        HAVING snap_count >= 2
    """
    rows = conn.execute(query, params).fetchall()

    anomalies = []
    for r in rows:
        current = r["current_price"]
        avg = r["avg_price"]
        if avg == 0:
            continue
        deviation = (current - avg) / avg
        if abs(deviation) < threshold_percent:
            continue

        direction = "spike" if deviation > 0 else "drop"
        anomalies.append(Anomaly(
            product_id=r["id"],
            platform_product_id=r["platform_product_id"],
            name=r["name"],
            brand=r["brand"],
            category=r["category"],
            current_price=current,
            average_price=avg,
            deviation_percent=deviation,
            direction=direction,
            confidence=_confidence(r["snap_count"]),
            snapshot_count=r["snap_count"],
            product_url=r["product_url"],
        ))

    anomalies.sort(key=lambda a: abs(a.deviation_percent), reverse=True)
    return anomalies
