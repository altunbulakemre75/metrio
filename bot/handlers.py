import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import mkdtemp


@dataclass
class Response:
    text: str
    photo_png: bytes | None = None
    document_path: Path | None = None


_HELP_TEXT = (
    "🎯 Metrio bot'a hoş geldin!\n\n"
    "Komutlar:\n"
    "/durum — son taramaların özeti\n"
    "/rapor — haftalık PDF raporu\n"
    "/trend [marka] — 30 günlük marka trend grafiği\n"
    "/fiyat [arama] — ürün fiyat sorgulama\n\n"
    "Örnekler:\n"
    "/trend L'Oréal\n"
    "/fiyat serum"
)


def handle_start(args: str, conn: sqlite3.Connection) -> Response:
    return Response(text=_HELP_TEXT)


def handle_durum(args: str, conn: sqlite3.Connection) -> Response:
    rows = conn.execute(
        "SELECT started_at, status, products_saved, duration_seconds "
        "FROM run_stats WHERE finished_at IS NOT NULL "
        "ORDER BY started_at DESC LIMIT 5"
    ).fetchall()
    if not rows:
        return Response(text="📊 Henüz tarama yok.")
    lines = ["📊 Son taramalar:", ""]
    for r in rows:
        icon = "✅" if r["status"] == "success" else ("⚠️" if r["status"] == "partial" else "❌")
        ts = str(r["started_at"])[:16]
        lines.append(f"{ts} {icon} {r['products_saved']} ürün, {r['duration_seconds']}s")
    return Response(text="\n".join(lines))


def handle_rapor(args: str, conn: sqlite3.Connection) -> Response:
    from reports.builder import build_weekly_report
    out_dir = Path(mkdtemp(prefix="metrio_bot_"))
    pdf_path = out_dir / f"metrio_{datetime.now():%Y-%m-%d}.pdf"
    try:
        build_weekly_report(conn, pdf_path, days=7)
    except Exception as e:
        return Response(text=f"❌ Rapor oluşturulamadı: {e}")
    return Response(text="📄 Haftalık rapor hazır.", document_path=pdf_path)


def handle_trend(args: str, conn: sqlite3.Connection) -> Response:
    brand = args.strip()
    if not brand:
        return Response(text="Kullanım: /trend [marka adı]\nÖrn: /trend L'Oréal")
    from reports.charts import brand_trend_chart
    png = brand_trend_chart(conn, days=30, top_n=10)
    if png is None:
        return Response(text=f"📉 {brand} için yeterli veri yok.")
    # Veri yeterliyse PNG zaten tüm top markaları içerir — metin caption ile marka vurgula
    return Response(
        text=f"📈 {brand} (ve diğer aktif markalar) — 30 günlük trend",
        photo_png=png,
    )


def handle_fiyat(args: str, conn: sqlite3.Connection) -> Response:
    query = args.strip()
    if not query:
        return Response(text="Kullanım: /fiyat [arama kelimesi]\nÖrn: /fiyat serum")
    rows = conn.execute(
        """
        SELECT p.name, p.brand, ps.price, ps.captured_at
        FROM products p
        JOIN price_snapshots ps ON ps.product_id = p.id
        WHERE p.name LIKE ?
        AND ps.captured_at = (
            SELECT MAX(captured_at) FROM price_snapshots WHERE product_id = p.id
        )
        ORDER BY ps.captured_at DESC
        LIMIT 5
        """,
        (f"%{query}%",),
    ).fetchall()
    if not rows:
        return Response(text=f"🔍 \"{query}\" için sonuç bulunamadı.")
    lines = [f"🔍 \"{query}\" sonuçları:", ""]
    for r in rows:
        brand = f"{r['brand']} " if r["brand"] else ""
        date = str(r["captured_at"])[:10]
        lines.append(f"• {brand}{r['name'][:50]} — {r['price']:.2f} TL ({date})")
    return Response(text="\n".join(lines))
