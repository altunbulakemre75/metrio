import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st

from dashboard.app import get_conn
from analysis.price_changes import top_movers
from analysis.queries import get_unique_platforms
from dashboard.components.charts import top_discounts_bar
from dashboard.components.exports import csv_download_button
from dashboard.utils.ui import apply_custom_styles


apply_custom_styles(page_title="Fırsatlar | Metrio", page_icon="🎯")

st.title("🎯 Fırsatlar — Fiyat Hareketleri")

conn = get_conn()

all_platforms = get_unique_platforms(conn)
selected_platforms = st.sidebar.multiselect(
    "Platform", all_platforms, default=all_platforms,
    help="Hangi platformların verisi gösterilsin"
)

c1, c2, c3 = st.columns([2, 2, 1])
with c1:
    days = st.slider("Son kaç gün", 1, 30, 7)
with c2:
    direction = st.selectbox(
        "Yön", ["both", "down", "up"],
        format_func=lambda x: {"both": "Hepsi", "down": "İndirimler", "up": "Zamlar"}[x],
    )
with c3:
    limit = st.number_input("Adet", 5, 100, 20)


@st.cache_data(ttl=60)
def _load(days, direction, limit, platforms):
    plat = list(platforms) if platforms else None
    movers = top_movers(conn, days=days, direction=direction, limit=limit, platforms=plat)
    df = pd.DataFrame([
        {
            "Marka": m.brand or "-",
            "Ürün": m.name[:80],
            "Eski": m.old_price,
            "Yeni": m.new_price,
            "Değişim (TL)": m.change_amount,
            "Değişim (%)": m.change_percent * 100,
            "URL": m.product_url,
        } for m in movers
    ])
    return movers, df


movers, df = _load(days, direction, limit, tuple(sorted(selected_platforms)))

if movers:
    drops = [m for m in movers if m.change_percent < 0]
    if drops:
        st.plotly_chart(top_discounts_bar(drops), use_container_width=True)

    st.subheader(f"Tablo — {len(df)} kayıt")
    st.dataframe(
        df,
        column_config={
            "Eski": st.column_config.NumberColumn(format="%.2f TL"),
            "Yeni": st.column_config.NumberColumn(format="%.2f TL"),
            "Değişim (TL)": st.column_config.NumberColumn(format="%.2f"),
            "Değişim (%)": st.column_config.NumberColumn(format="%.1f%%"),
            "URL": st.column_config.LinkColumn("Ürün"),
        },
        hide_index=True,
        use_container_width=True,
    )

    csv_download_button(df, f"firsatlar_{days}gun.csv")
else:
    st.info("Seçilen filtreler için fiyat hareketi bulunamadı.")
