"""Mevcut ürünlere sentetik 30 günlük fiyat geçmişi ekler (demo amaçlı).

Gerçek veri biriktikçe bu script'e ihtiyaç kalmaz.

Kullanım:
    python scripts/seed_demo_history.py --days 30 --anomalies 3
"""
import argparse
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent to path so 'config' and 'storage' imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings
from storage.database import connect, init_schema


def seed_history(days: int = 30, anomaly_count: int = 3, seed: int = 42):
    random.seed(seed)
    conn = connect(settings.database_path)
    init_schema(conn)

    products = conn.execute(
        "SELECT p.id, s.price FROM products p "
        "JOIN (SELECT product_id, MAX(captured_at) m FROM price_snapshots GROUP BY product_id) latest "
        "ON latest.product_id = p.id "
        "JOIN price_snapshots s ON s.product_id = p.id AND s.captured_at = latest.m"
    ).fetchall()

    if not products:
        print("HATA: Veritabaninda urun yok. Once 'python main.py' calistir.")
        return 1

    anomaly_ids = set(random.sample([p[0] for p in products], min(anomaly_count, len(products))))

    total_inserted = 0
    now = datetime.now()

    for product_id, current_price in products:
        for d in range(days, 0, -1):
            ts = now - timedelta(days=d)
            variation = random.uniform(-0.05, 0.05)
            price = current_price * (1 + variation)

            # Anomali: ortadaki bir günde %30 düşüş
            if product_id in anomaly_ids and d == 5:
                price = current_price * 0.70

            conn.execute("""
                INSERT INTO price_snapshots (
                    product_id, price, original_price, discount_rate,
                    seller_name, seller_rating, in_stock, captured_at
                ) VALUES (?, ?, NULL, NULL, NULL, NULL, 1, ?)
            """, (product_id, round(price, 2), ts))
            total_inserted += 1

    conn.commit()
    print(f"OK: {len(products)} urune {total_inserted} sentetik snapshot eklendi")
    print(f"    ({anomaly_count} urune kasitli anomali eklendi)")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--anomalies", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    return seed_history(args.days, args.anomalies, args.seed)


if __name__ == "__main__":
    sys.exit(main())
