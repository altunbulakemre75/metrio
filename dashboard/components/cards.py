import streamlit as st


def summary_row(total_products: int, total_brands: int, last_run: str | None, avg_discount: float | None):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Takip Edilen Ürün", total_products)
    c2.metric("Takip Edilen Marka", total_brands)
    c3.metric("Son Çekim", last_run or "-")
    if avg_discount is not None:
        c4.metric("Ortalama İndirim", f"%{avg_discount * 100:.1f}")
    else:
        c4.metric("Ortalama İndirim", "-")
