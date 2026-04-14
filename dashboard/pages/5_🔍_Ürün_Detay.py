import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st

from dashboard.app import get_conn
from analysis.product_history import search_products, get_product_history
from dashboard.components.charts import price_history_line
from dashboard.components.exports import csv_download_button


st.set_page_config(page_title="Ürün Detay | Fiyat Radarı", page_icon="🔍", layout="wide")

st.title("🔍 Ürün Detay & Arama")

conn = get_conn()

query = st.text_input("Ürün veya marka ara", placeholder="Örn: nemlendirici, loreal, güneş kremi")

if query:
    results = search_products(conn, query, limit=20)
    if not results:
        st.info("Eşleşen ürün bulunamadı.")
        st.stop()

    labels = {
        r.product_id: f"{r.brand or '-'} — {r.name[:70]} ({r.current_price:.2f} TL)"
        for r in results
    }
    selected_id = st.selectbox("Ürün seç", list(labels.keys()), format_func=lambda k: labels[k])

    if selected_id:
        days = st.slider("Geçmiş (gün)", 7, 90, 30)
        history = get_product_history(conn, selected_id, days=days)

        if not history:
            st.warning("Bu ürün için henüz geçmiş veri yok.")
        else:
            product = next(r for r in results if r.product_id == selected_id)

            c1, c2, c3 = st.columns(3)
            prices = [h.price for h in history]
            c1.metric("Güncel Fiyat", f"{history[-1].price:.2f} TL")
            c2.metric("En Düşük", f"{min(prices):.2f} TL")
            c3.metric("En Yüksek", f"{max(prices):.2f} TL")

            df = pd.DataFrame([
                {
                    "captured_at": h.captured_at, "price": h.price,
                    "original_price": h.original_price, "discount_rate": h.discount_rate,
                    "in_stock": h.in_stock,
                }
                for h in history
            ])
            st.plotly_chart(price_history_line(df, product.name), use_container_width=True)

            with st.expander("Ham veri tablosu"):
                st.dataframe(df, hide_index=True, use_container_width=True)

            csv_download_button(df, f"urun_{selected_id}_gecmis.csv")
else:
    st.info("Yukarıdan ürün adı veya marka arayın.")
