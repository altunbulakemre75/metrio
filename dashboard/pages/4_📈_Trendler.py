import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

from dashboard.app import get_conn
from analysis.queries import get_unique_brands, get_unique_categories
from analysis.trends import brand_trend, category_trend
from dashboard.components.charts import trend_line


st.set_page_config(page_title="Trendler | Metrio", page_icon="📈", layout="wide")

st.title("📈 Trendler — Zaman İçinde Fiyat Eğilimi")

conn = get_conn()

mode = st.radio("Gruplama", ["Marka", "Kategori"], horizontal=True)
days = st.slider("Son kaç gün", 7, 90, 30)

if mode == "Marka":
    brands = get_unique_brands(conn)
    if not brands:
        st.warning("Henüz marka verisi yok.")
        st.stop()
    selected = st.multiselect(
        "Markalar (2-3 tane karşılaştırılabilir)",
        brands, default=brands[:1], max_selections=3,
    )
    if not selected:
        st.info("En az bir marka seçin.")
        st.stop()

    for b in selected:
        points = brand_trend(conn, brand=b, days=days)
        if points:
            st.plotly_chart(trend_line(points, f"{b} — Ortalama Fiyat"), use_container_width=True)
        else:
            st.info(f"'{b}' için yeterli veri yok.")

else:
    cats = get_unique_categories(conn)
    if not cats:
        st.warning("Henüz kategori verisi yok.")
        st.stop()
    selected_cat = st.selectbox("Kategori", cats)

    points = category_trend(conn, category=selected_cat, days=days)
    if points:
        st.plotly_chart(trend_line(points, f"{selected_cat.title()} — Ortalama Fiyat"),
                        use_container_width=True)
    else:
        st.info("Yeterli veri yok.")
