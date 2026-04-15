import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st

from dashboard.app import get_conn
from analysis.anomaly import detect_anomalies
from dashboard.components.exports import csv_download_button


st.set_page_config(page_title="Anomaliler | Metrio", page_icon="🚨", layout="wide")

st.title("🚨 Anomaliler — Normalden Sapanlar")
st.caption("Son 30 günün ortalama fiyatından eşiği aşan sapmalar")

conn = get_conn()

c1, c2, c3 = st.columns(3)
with c1:
    threshold = st.slider("Sapma Eşiği (%)", 10, 50, 20) / 100
with c2:
    direction_filter = st.selectbox(
        "Yön", ["all", "drop", "spike"],
        format_func=lambda x: {"all": "Hepsi", "drop": "Düşüş", "spike": "Artış"}[x],
    )
with c3:
    confidence_filter = st.selectbox(
        "Güven", ["all", "high", "medium", "low"],
        format_func=lambda x: {"all": "Hepsi", "high": "Yüksek", "medium": "Orta", "low": "Düşük"}[x],
    )


@st.cache_data(ttl=60)
def _load(threshold):
    return detect_anomalies(conn, lookback_days=30, threshold_percent=threshold)


anomalies = _load(threshold)

if direction_filter != "all":
    anomalies = [a for a in anomalies if a.direction == direction_filter]
if confidence_filter != "all":
    anomalies = [a for a in anomalies if a.confidence == confidence_filter]

if anomalies:
    df = pd.DataFrame([
        {
            "Yön": "🔻 Düşüş" if a.direction == "drop" else "🔺 Artış",
            "Güven": {"high": "🟢 Yüksek", "medium": "🟡 Orta", "low": "🔴 Düşük"}[a.confidence],
            "Marka": a.brand or "-",
            "Ürün": a.name[:80],
            "Güncel": a.current_price,
            "Ortalama": a.average_price,
            "Sapma (%)": a.deviation_percent * 100,
            "Veri Noktası": a.snapshot_count,
            "URL": a.product_url,
        } for a in anomalies
    ])

    st.subheader(f"Tespit edilen sapmalar: {len(df)}")
    st.dataframe(
        df,
        column_config={
            "Güncel": st.column_config.NumberColumn(format="%.2f TL"),
            "Ortalama": st.column_config.NumberColumn(format="%.2f TL"),
            "Sapma (%)": st.column_config.NumberColumn(format="%.1f%%"),
            "URL": st.column_config.LinkColumn("Ürün"),
        },
        hide_index=True,
        use_container_width=True,
    )

    csv_download_button(df, "anomaliler.csv")
else:
    st.info("Seçilen kriterlerde anomali bulunamadı. Eşiği düşürebilir veya daha fazla veri toplayabilirsiniz.")
