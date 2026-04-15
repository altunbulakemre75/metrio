# Fiyat Radarı — Hafta 4: Haftalık PDF Raporu Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `python scripts/generate_report.py --days 7` komutu ile 5-6 sayfalık profesyonel haftalık PDF raporu üretmek.

**Architecture:** `reports/` paketinde 4 modül: `sections.py` (saf fonksiyonlar, Flowable listesi döner), `charts.py` (matplotlib PNG), `builder.py` (ReportLab SimpleDocTemplate wrapper), `scripts/generate_report.py` (CLI).

**Tech Stack:** ReportLab 4.2.5, Matplotlib 3.9.2 (Agg backend), pandas (mevcut), pytest.

---

## File Structure

**Create:**
- `reports/__init__.py`
- `reports/charts.py`
- `reports/sections.py`
- `reports/builder.py`
- `scripts/generate_report.py`
- `tests/unit/test_report_sections.py`
- `tests/integration/test_report_build.py`

**Modify:**
- `requirements.txt`
- `README.md`

---

## Task 1: Bağımlılıkları ekle

- [ ] requirements.txt'e ekle:
  ```
  reportlab==4.2.5
  matplotlib==3.9.2
  ```
- [ ] `pip install reportlab==4.2.5 matplotlib==3.9.2`
- [ ] Commit: `feat: add reportlab and matplotlib for PDF reports`

## Task 2: reports paketi iskeleti

- [ ] `reports/__init__.py` oluştur (docstring only).
- [ ] Commit: `feat: add reports package`

## Task 3: `reports/charts.py` — marka trendi

- [ ] `tests/unit/test_report_sections.py` taslağı (ileride doldurulacak).
- [ ] `reports/charts.py`:
  ```python
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
          ys = [p.avg_price for p in points]
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
  ```
- [ ] Commit.

## Task 4: `reports/sections.py` — cover + summary

- [ ] `tests/unit/test_report_sections.py`:
  ```python
  import sqlite3
  from reports.sections import build_cover, build_summary
  from storage.database import init_schema


  def _mem_conn():
      c = sqlite3.connect(":memory:")
      c.row_factory = sqlite3.Row
      init_schema(c)
      return c


  def test_cover_has_title_flowable():
      items = build_cover(date_from="2026-04-01", date_to="2026-04-07")
      assert len(items) >= 2
      # Title flowable has text
      texts = [str(f.__dict__) for f in items]
      assert any("Haftalık" in t for t in texts)


  def test_summary_returns_flowables_on_empty_db():
      conn = _mem_conn()
      items = build_summary(conn, days=7)
      assert len(items) >= 1
  ```
- [ ] `reports/sections.py` — cover + summary implementasyonu:
  ```python
  from datetime import datetime, timedelta
  from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
  from reportlab.lib.units import mm
  from reportlab.lib.colors import HexColor
  from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak

  from analysis.price_changes import top_movers
  from analysis.anomaly import detect_anomalies
  from analysis.queries import get_latest_snapshots_df, get_unique_brands

  _ORANGE = HexColor("#E85D04")
  _styles = getSampleStyleSheet()
  _title_style = ParagraphStyle("Title", parent=_styles["Title"], textColor=_ORANGE, fontSize=24, spaceAfter=20)
  _h2_style = ParagraphStyle("H2", parent=_styles["Heading2"], textColor=_ORANGE, fontSize=16, spaceAfter=10)
  _body = _styles["BodyText"]


  def build_cover(date_from: str, date_to: str) -> list:
      return [
          Spacer(1, 60 * mm),
          Paragraph("Fiyat Radarı", _title_style),
          Paragraph("Haftalık Rapor", _h2_style),
          Spacer(1, 10 * mm),
          Paragraph(f"Dönem: {date_from} — {date_to}", _body),
          Paragraph(f"Üretildi: {datetime.now():%Y-%m-%d %H:%M}", _body),
          PageBreak(),
      ]


  def build_summary(conn, days: int) -> list:
      items = [Paragraph("📊 Özet", _h2_style)]
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
          Paragraph("🎯 En Büyük 3 Fırsat:", _body),
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
  ```
- [ ] `pytest tests/unit/test_report_sections.py -v` → 2 pass.
- [ ] Commit.

## Task 5: `reports/sections.py` — top_movers, anomalies

- [ ] `build_top_movers(conn, days, limit=10)` — tablo oluşturur (marka, ürün, eski, yeni, %). Boşsa "veri yok" metni.
- [ ] `build_anomalies(conn, threshold=0.20)` — tablo (marka, ürün, güncel, ortalama, sapma %, güven).
- [ ] Her ikisi de başlık + PageBreak ile döner.
- [ ] Unit test: mock/seed ile tabloların oluştuğunu doğrula.
- [ ] Commit.

Kod iskeleti:
```python
def _table_or_empty(header: list, rows: list, empty_msg: str) -> list:
    if not rows:
        return [Paragraph(empty_msg, _body)]
    t = Table([header] + rows, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _ORANGE),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#FFFFFF"), HexColor("#FAFAFA")]),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    return [t]


def build_top_movers(conn, days: int, limit: int = 10) -> list:
    items = [Paragraph("🎯 En Büyük Fiyat Hareketleri", _h2_style)]
    try:
        movers = top_movers(conn, days=days, direction="both", limit=limit)
    except Exception:
        movers = []
    rows = [
        [m.brand or "-", m.name[:40], f"{m.old_price:.2f}", f"{m.new_price:.2f}",
         f"{m.change_percent*100:+.1f}%"]
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
    items = [Paragraph("🚨 Anomaliler", _h2_style)]
    try:
        anomalies = detect_anomalies(conn, threshold_percent=threshold)
    except Exception:
        anomalies = []
    rows = [
        [a.brand or "-", a.name[:40], f"{a.current_price:.2f}", f"{a.average_price:.2f}",
         f"{a.deviation_percent*100:+.1f}%", a.confidence]
        for a in anomalies
    ]
    items.extend(_table_or_empty(
        ["Marka", "Ürün", "Güncel", "Ortalama", "Sapma", "Güven"],
        rows,
        "Bu eşikte anomali tespit edilmedi.",
    ))
    items.append(PageBreak())
    return items
```

## Task 6: `reports/sections.py` — brand_trend (grafik)

- [ ] `build_brand_trend(conn, days)` — `charts.brand_trend_chart()` çağırır, PNG bytes'ı ReportLab `Image`'a sarar. None ise "yeterli veri yok" metni.
- [ ] Commit.

Kod:
```python
from reportlab.platypus import Image as RLImage
import io
from reports.charts import brand_trend_chart


def build_brand_trend(conn, days: int) -> list:
    items = [Paragraph("📈 Marka Trendi", _h2_style)]
    try:
        png = brand_trend_chart(conn, days=days)
    except Exception:
        png = None
    if png is None:
        items.append(Paragraph("Yeterli marka verisi yok.", _body))
    else:
        img = RLImage(io.BytesIO(png), width=170 * mm, height=85 * mm)
        items.append(img)
    items.append(PageBreak())
    return items
```

## Task 7: `reports/sections.py` — product_list

- [ ] `build_product_list(conn)` — tüm ürünleri listeler (marka, ürün, güncel fiyat). Büyük olabilir, tablo ile sayfaları otomatik böler (ReportLab otomatik yapar).
- [ ] Commit.

Kod:
```python
def build_product_list(conn) -> list:
    items = [Paragraph("📦 Tüm İzlenen Ürünler", _h2_style)]
    try:
        df = get_latest_snapshots_df(conn)
    except Exception:
        df = None
    if df is None or df.empty:
        items.append(Paragraph("Henüz ürün yok.", _body))
        return items
    rows = [[r.get("brand") or "-", str(r["name"])[:50], f"{r['price']:.2f} TL"]
            for _, r in df.iterrows()]
    t = Table([["Marka", "Ürün", "Fiyat"]] + rows, hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _ORANGE),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    items.append(t)
    return items
```

## Task 8: `reports/builder.py`

- [ ] `build_weekly_report(conn, output_path, days)` üst seviye fonksiyon: tüm section'ları çağırır, `SimpleDocTemplate` ile birleştirir, footer ekler.
- [ ] Commit.

Kod:
```python
from datetime import datetime, timedelta
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate

from reports.sections import (
    build_cover, build_summary, build_top_movers,
    build_anomalies, build_brand_trend, build_product_list,
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
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=20 * mm,
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
```

## Task 9: Integration test

- [ ] `tests/integration/test_report_build.py`:
  - In-memory SQLite + seed (birkaç ürün ve snapshot)
  - `build_weekly_report()` çağır
  - Dosyanın var ve boyutunun > 5KB olduğunu doğrula.
- [ ] Commit.

## Task 10: `scripts/generate_report.py` CLI

- [ ] Argparse ile `--days`, `--output`, `--category`.
- [ ] UTF-8 stdout.
- [ ] Exit 0 başarılı, 1 hata.
- [ ] Commit.

Kod:
```python
import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from config import settings
from storage.database import connect, init_schema
from reports.builder import build_weekly_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Haftalık PDF rapor üret.")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--output", type=Path, default=Path("reports"))
    parser.add_argument("--category", type=str, default=None)  # currently informational
    args = parser.parse_args()

    try:
        conn = connect(settings.database_path)
        init_schema(conn)
    except Exception as e:
        print(f"❌ Veritabanı açılamadı: {e}")
        return 1

    filename = f"fiyat_radari_{datetime.now():%Y-%m-%d}.pdf"
    output_path = args.output / filename

    try:
        build_weekly_report(conn, output_path=output_path, days=args.days)
    except Exception as e:
        print(f"❌ Rapor üretilemedi: {e}")
        return 1

    print(f"✅ Rapor oluşturuldu: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## Task 11: README güncellemesi

- [ ] "## Telegram Bildirimleri (Hafta 3)" bölümünden sonra yeni bölüm ekle:
  ```markdown
  ## Haftalık PDF Raporu (Hafta 4)

  Müşteriye gönderilebilecek profesyonel rapor üret:

  ```bash
  python scripts/generate_report.py --days 7
  ```

  Çıktı: `reports/fiyat_radari_YYYY-MM-DD.pdf`

  İçerik: kapak, özet, en büyük hareketler, anomaliler, marka trendi grafiği, tam ürün listesi.
  ```
- [ ] "Sonraki Adımlar" bölümünden "PDF rapor üretimi" satırını sil.
- [ ] Commit.

## Task 12: Son doğrulama

- [ ] `pytest --ignore=tests/e2e` → hepsi pass.
- [ ] `python scripts/generate_report.py --days 30` elle çalıştır, PDF göz kontrolü.
