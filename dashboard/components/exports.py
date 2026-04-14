import pandas as pd
import streamlit as st


def csv_download_button(df: pd.DataFrame, filename: str, label: str = "CSV olarak indir"):
    if df.empty:
        return
    csv = df.to_csv(index=False).encode("utf-8-sig")  # BOM for Excel Turkish
    st.download_button(
        label=label,
        data=csv,
        file_name=filename,
        mime="text/csv",
    )
