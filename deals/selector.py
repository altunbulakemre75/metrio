"""Günün paylaşılacak fırsatlarını seçer."""
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta

# "Son 30 günün en düşük fiyatı" demek için en az bu kadar eski kayıt gerekli.
_MIN_HISTORY_FOR_LOW = 5
_LOW_BONUS = 0.25


@dataclass(frozen=True)
class Deal:
    product_id: int
    platform: str
    name: str
    brand: str | None
    category: str
    product_url: str
    image_url: str
    price: float
    original_price: float | None
    discount_rate: float | None
    previous_price: float | None
    lowest_30d: bool
    rating: float | None

    @property
    def drop_rate(self) -> float | None:
        """Bir önceki taramaya göre gerçek düşüş oranı (son 7 gün)."""
        if self.previous_price and self.previous_price > self.price:
            return 1 - self.price / self.previous_price
        return None

    @property
    def score(self) -> float:
        # Gerçek düşüş, satıcının yazdığı üstü çizili fiyattan daha değerli.
        bonus = _LOW_BONUS if self.lowest_30d else 0.0
        return (self.discount_rate or 0.0) + 2 * (self.drop_rate or 0.0) + bonus


def select_deals(
    conn: sqlite3.Connection,
    categories: list[str],
    now: datetime,
    limit: int = 5,
    exclude_ids: set[int] | frozenset[int] = frozenset(),
    min_discount: float = 0.30,
    min_drop: float = 0.15,
    max_age: timedelta = timedelta(hours=36),
    max_per_brand: int = 2,
    exclude_words: list[str] | tuple[str, ...] = (),
) -> list[Deal]:
    placeholders = ",".join("?" * len(categories))
    rows = conn.execute(
        f"""
        SELECT p.id, p.platform, p.name, p.brand, p.category, p.product_url, p.image_url,
               s.price, s.original_price, s.discount_rate, s.seller_rating,
               (SELECT h.price FROM price_snapshots h
                WHERE h.product_id = p.id AND h.captured_at < s.captured_at
                  AND h.captured_at >= datetime(s.captured_at, '-7 days')
                ORDER BY h.captured_at DESC LIMIT 1) AS previous_price,
               (SELECT MIN(h.price) FROM price_snapshots h
                WHERE h.product_id = p.id AND h.captured_at < s.captured_at
                  AND h.captured_at >= datetime(s.captured_at, '-30 days')) AS min_30d,
               (SELECT COUNT(*) FROM price_snapshots h
                WHERE h.product_id = p.id AND h.captured_at < s.captured_at
                  AND h.captured_at >= datetime(s.captured_at, '-30 days')) AS history_30d
        FROM products p
        JOIN (
            SELECT product_id, MAX(captured_at) AS max_at
            FROM price_snapshots GROUP BY product_id
        ) latest ON latest.product_id = p.id
        JOIN price_snapshots s ON s.product_id = p.id AND s.captured_at = latest.max_at
        WHERE p.category IN ({placeholders})
          AND s.in_stock = 1
          AND s.captured_at >= ?
          AND p.image_url IS NOT NULL
        """,
        (*categories, now - max_age),
    ).fetchall()

    banned = [w.casefold() for w in exclude_words if w.strip()]
    candidates = []
    for r in rows:
        if r["id"] in exclude_ids:
            continue
        if any(w in r["name"].casefold() for w in banned):
            continue
        deal = Deal(
            product_id=r["id"], platform=r["platform"], name=r["name"], brand=r["brand"],
            category=r["category"], product_url=r["product_url"], image_url=r["image_url"],
            price=r["price"], original_price=r["original_price"],
            discount_rate=r["discount_rate"], previous_price=r["previous_price"],
            lowest_30d=(r["history_30d"] >= _MIN_HISTORY_FOR_LOW and r["price"] < r["min_30d"]),
            rating=r["seller_rating"],
        )
        if (deal.discount_rate or 0) >= min_discount or (deal.drop_rate or 0) >= min_drop:
            candidates.append(deal)

    candidates.sort(key=lambda d: (d.score, d.rating or 0), reverse=True)

    picked: list[Deal] = []
    per_brand: dict[str, int] = {}
    for deal in candidates:
        key = (deal.brand or f"#{deal.product_id}").casefold()
        if per_brand.get(key, 0) >= max_per_brand:
            continue
        per_brand[key] = per_brand.get(key, 0) + 1
        picked.append(deal)
        if len(picked) == limit:
            break
    return picked
