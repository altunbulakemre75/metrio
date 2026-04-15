"""PDF rapor üst seviye derleyici."""
from datetime import datetime, timedelta
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate

from reports.sections import (
    build_anomalies,
    build_brand_trend,
    build_cover,
    build_product_list,
    build_summary,
    build_top_movers,
)


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(HexColor("#888888"))
    canvas.drawString(15 * mm, 10 * mm, f"Fiyat Radarı · {datetime.now():%Y-%m-%d}")
    canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Sayfa {doc.page}")
    canvas.restoreState()


def build_weekly_report(conn, output_path: Path, days: int = 7) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    today = datetime.now().date()
    date_from = (today - timedelta(days=days)).isoformat()
    date_to = today.isoformat()

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=20 * mm,
        title="Fiyat Radarı — Haftalık Rapor",
    )

    story = []
    story.extend(build_cover(date_from=date_from, date_to=date_to))
    story.extend(build_summary(conn, days=days))
    story.extend(build_top_movers(conn, days=days, limit=10))
    story.extend(build_anomalies(conn))
    story.extend(build_brand_trend(conn, days=days))
    story.extend(build_product_list(conn))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output_path
