"""Matplotlib PNG üretimi — ReportLab Image'a beslenir."""
import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analysis.queries import get_unique_brands
from analysis.trends import brand_trend


def brand_trend_chart(conn, days: int, top_n: int = 3) -> bytes | None:
    brands = get_unique_brands(conn)[:top_n]
    if not brands:
        return None

    fig, ax = plt.subplots(figsize=(8, 4))
    plotted = False
    for b in brands:
        points = brand_trend(conn, brand=b, days=days)
        if not points:
            continue
        xs = [p.date for p in points]
        ys = [p.average_price for p in points]
        ax.plot(xs, ys, label=b, marker="o")
        plotted = True

    if not plotted:
        plt.close(fig)
        return None

    ax.set_title(f"Marka Trendi — Son {days} Gün")
    ax.set_ylabel("Ortalama Fiyat (TL)")
    ax.legend()
    fig.autofmt_xdate()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()
