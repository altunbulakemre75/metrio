"""Toplanan ürünleri terminalde okunabilir şekilde göster.

Kullanım:
    python show_products.py              # En son snapshot'ları listeler
    python show_products.py --discounts  # Sadece indirimli ürünler
    python show_products.py --top 5      # En pahalı 5 ürün
"""
import argparse
import sqlite3
import sys
from pathlib import Path

# Windows cp1254 terminali için UTF-8'e zorla
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from config import settings


def _connect() -> sqlite3.Connection:
    path = Path(settings.database_path)
    if not path.exists():
        print(f"HATA: Veritabanı bulunamadı: {path}")
        print("Önce 'python main.py' çalıştır.")
        sys.exit(1)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def _truncate(text: str, length: int) -> str:
    if text is None:
        return "-"
    return text if len(text) <= length else text[: length - 1] + "…"


def _print_row(rank, brand, name, price, original, discount, rating):
    discount_str = f"%{int(discount * 100)}" if discount else "-"
    original_str = f"{original:>8.2f}" if original else "       -"
    rating_str = f"{rating:.1f}" if rating else "-"
    print(
        f"  {rank:>3}. {_truncate(brand or '-', 18):<18} | "
        f"{price:>8.2f} TL | eski {original_str} | ind {discount_str:>4} | ★{rating_str:>3}"
    )
    print(f"       {_truncate(name, 75)}")


def show_latest(conn, top=None, discounts_only=False):
    where = "WHERE s.discount_rate IS NOT NULL" if discounts_only else ""
    order = "ORDER BY s.discount_rate DESC" if discounts_only else "ORDER BY s.price DESC"
    limit = f"LIMIT {top}" if top else ""

    query = f"""
        SELECT p.brand, p.name, s.price, s.original_price, s.discount_rate, s.seller_rating
        FROM products p
        JOIN (
            SELECT product_id, MAX(captured_at) AS max_at
            FROM price_snapshots GROUP BY product_id
        ) latest ON latest.product_id = p.id
        JOIN price_snapshots s
            ON s.product_id = p.id AND s.captured_at = latest.max_at
        {where}
        {order}
        {limit}
    """

    rows = conn.execute(query).fetchall()

    if discounts_only:
        print(f"\n=== İNDİRİMLİ ÜRÜNLER ({len(rows)} adet) ===\n")
    elif top:
        print(f"\n=== EN PAHALI {top} ÜRÜN ===\n")
    else:
        print(f"\n=== TÜM ÜRÜNLER ({len(rows)} adet) — fiyat büyükten küçüğe ===\n")

    for i, r in enumerate(rows, 1):
        _print_row(i, r["brand"], r["name"], r["price"], r["original_price"],
                   r["discount_rate"], r["seller_rating"])


def show_summary(conn):
    products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    snapshots = conn.execute("SELECT COUNT(*) FROM price_snapshots").fetchone()[0]
    runs = conn.execute("SELECT COUNT(*) FROM run_stats").fetchone()[0]

    last_run = conn.execute(
        "SELECT started_at, status, products_saved, duration_seconds "
        "FROM run_stats ORDER BY started_at DESC LIMIT 1"
    ).fetchone()

    print("=" * 78)
    print("  FİYAT RADARI — Veri Özeti")
    print("=" * 78)
    print(f"  Benzersiz ürün    : {products}")
    print(f"  Toplam snapshot   : {snapshots}")
    print(f"  Çalıştırma sayısı : {runs}")
    if last_run:
        print(f"  Son çekim         : {last_run['started_at']} → "
              f"{last_run['status']} ({last_run['products_saved']} ürün, "
              f"{last_run['duration_seconds']}s)")


def main():
    parser = argparse.ArgumentParser(description="Toplanan ürünleri göster")
    parser.add_argument("--top", type=int, help="Sadece ilk N ürünü göster")
    parser.add_argument("--discounts", action="store_true", help="Sadece indirimli ürünler")
    args = parser.parse_args()

    conn = _connect()
    show_summary(conn)
    show_latest(conn, top=args.top, discounts_only=args.discounts)


if __name__ == "__main__":
    main()
