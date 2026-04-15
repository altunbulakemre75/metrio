import sqlite3

from reports.sections import (
    build_anomalies,
    build_cover,
    build_product_list,
    build_summary,
    build_top_movers,
)
from storage.database import init_schema


def _mem_conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    init_schema(c)
    return c


def _flatten_text(flowables) -> str:
    out = []
    for f in flowables:
        txt = getattr(f, "text", None) or getattr(f, "_text", None)
        if txt:
            out.append(str(txt))
    return " | ".join(out)


def test_cover_has_title():
    items = build_cover(date_from="2026-04-01", date_to="2026-04-07")
    assert len(items) >= 5
    assert "Haftalık" in _flatten_text(items) or "Metrio" in _flatten_text(items)


def test_summary_empty_db_returns_flowables():
    conn = _mem_conn()
    items = build_summary(conn, days=7)
    assert len(items) >= 2
    assert "veri yok" in _flatten_text(items).lower()


def test_top_movers_empty_db():
    conn = _mem_conn()
    items = build_top_movers(conn, days=7)
    assert len(items) >= 2
    assert "tespit edilmedi" in _flatten_text(items).lower()


def test_anomalies_empty_db():
    conn = _mem_conn()
    items = build_anomalies(conn)
    assert len(items) >= 2


def test_product_list_empty_db():
    conn = _mem_conn()
    items = build_product_list(conn)
    assert len(items) >= 1
