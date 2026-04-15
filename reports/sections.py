"""PDF rapor sayfa bölümleri — her fonksiyon Flowable listesi döner."""
import io
from datetime import datetime

from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image as RLImage,
    PageBreak,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from analysis.anomaly import detect_anomalies
from analysis.price_changes import top_movers
from analysis.queries import get_latest_snapshots_df, get_unique_brands
from reports.charts import brand_trend_chart

_ORANGE = HexColor("#E85D04")
_WHITE = HexColor("#FFFFFF")
_STRIPE = HexColor("#FAFAFA")
_GRID = HexColor("#CCCCCC")

_styles = getSampleStyleSheet()
_title_style = ParagraphStyle(
    "BigTitle", parent=_styles["Title"], textColor=_ORANGE, fontSize=24, spaceAfter=20,
)
_h2_style = ParagraphStyle(
    "H2", parent=_styles["Heading2"], textColor=_ORANGE, fontSize=16, spaceAfter=10,
)
_body = _styles["BodyText"]


def _table_or_empty(header: list, rows: list, empty_msg: str) -> list:
    if not rows:
        return [Paragraph(empty_msg, _body)]
    t = Table([header] + rows, hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _ORANGE),
        ("TEXTCOLOR", (0, 0), (-1, 0), _WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, _GRID),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_WHITE, _STRIPE]),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return [t]


def build_cover(date_from: str, date_to: str) -> list:
    return [
        Spacer(1, 60 * mm),
        Paragraph("Fiyat Radarı — Haftalık Rapor", _title_style),
        Spacer(1, 10 * mm),
        Paragraph(f"Dönem: {date_from} — {date_to}", _body),
        Paragraph(f"Üretildi: {datetime.now():%Y-%m-%d %H:%M}", _body),
        PageBreak(),
    ]


def build_summary(conn, days: int) -> list:
    items = [Paragraph("Özet", _h2_style)]
    try:
        df = get_latest_snapshots_df(conn)
        brands = get_unique_brands(conn)
        movers = top_movers(conn, days=days, direction="both", limit=3)
        anomalies = detect_anomalies(conn, threshold_percent=0.20)
    except Exception:
        df = None
        brands, movers, anomalies = [], [], []

    if df is None or df.empty:
        items.append(Paragraph("Henüz veri yok.", _body))
        items.append(PageBreak())
        return items

    items.extend([
        Paragraph(f"İzlenen ürün: <b>{len(df)}</b>", _body),
        Paragraph(f"İzlenen marka: <b>{len(brands)}</b>", _body),
        Paragraph(f"Tespit edilen anomali: <b>{len(anomalies)}</b>", _body),
        Spacer(1, 5 * mm),
        Paragraph("En Büyük 3 Fırsat:", _body),
    ])
    if movers:
        for m in movers:
            pct = m.change_percent * 100
            items.append(Paragraph(
                f"• {m.brand or '-'} — {m.name[:60]}: {m.old_price:.2f} → {m.new_price:.2f} TL ({pct:+.0f}%)",
                _body,
            ))
    else:
        items.append(Paragraph("Bu dönemde önemli hareket yok.", _body))
    items.append(PageBreak())
    return items


def build_top_movers(conn, days: int, limit: int = 10) -> list:
    items = [Paragraph("En Büyük Fiyat Hareketleri", _h2_style)]
    try:
        movers = top_movers(conn, days=days, direction="both", limit=limit)
    except Exception:
        movers = []
    rows = [
        [m.brand or "-", m.name[:40], f"{m.old_price:.2f}", f"{m.new_price:.2f}",
         f"{m.change_percent * 100:+.1f}%"]
        for m in movers
    ]
    items.extend(_table_or_empty(
        ["Marka", "Ürün", "Eski", "Yeni", "Değişim"],
        rows,
        "Bu dönemde önemli hareket tespit edilmedi.",
    ))
    items.append(PageBreak())
    return items


def build_anomalies(conn, threshold: float = 0.20) -> list:
    items = [Paragraph("Anomaliler", _h2_style)]
    try:
        anomalies = detect_anomalies(conn, threshold_percent=threshold)
    except Exception:
        anomalies = []
    rows = [
        [a.brand or "-", a.name[:40], f"{a.current_price:.2f}", f"{a.average_price:.2f}",
         f"{a.deviation_percent * 100:+.1f}%", a.confidence]
        for a in anomalies
    ]
    items.extend(_table_or_empty(
        ["Marka", "Ürün", "Güncel", "Ortalama", "Sapma", "Güven"],
        rows,
        "Bu eşikte anomali tespit edilmedi.",
    ))
    items.append(PageBreak())
    return items


def build_brand_trend(conn, days: int) -> list:
    items = [Paragraph("Marka Trendi", _h2_style)]
    try:
        png = brand_trend_chart(conn, days=days)
    except Exception:
        png = None
    if png is None:
        items.append(Paragraph("Yeterli marka verisi yok.", _body))
    else:
        items.append(RLImage(io.BytesIO(png), width=170 * mm, height=85 * mm))
    items.append(PageBreak())
    return items


def build_product_list(conn) -> list:
    items = [Paragraph("Tüm İzlenen Ürünler", _h2_style)]
    try:
        df = get_latest_snapshots_df(conn)
    except Exception:
        df = None
    if df is None or df.empty:
        items.append(Paragraph("Henüz ürün yok.", _body))
        return items
    rows = [
        [row.get("brand") or "-", str(row["name"])[:50], f"{row['price']:.2f} TL"]
        for _, row in df.iterrows()
    ]
    items.extend(_table_or_empty(
        ["Marka", "Ürün", "Fiyat"],
        rows,
        "Henüz ürün yok.",
    ))
    return items
