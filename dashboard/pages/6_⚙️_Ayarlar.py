import streamlit as st
from config import settings
from pathlib import Path
from dashboard.utils.ui import apply_custom_styles

apply_custom_styles(page_title="Ayarlar — Metrio", page_icon="⚙️")

st.title("⚙️ Sistem Ayarları")
st.caption("Uygulama davranışını ve bildirim eşiklerini buradan yönetin.")

with st.expander("📱 Telegram Bildirimleri", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        st.toggle("Bildirimleri Aktif Et", value=settings.telegram_enabled, disabled=True)
        st.text_input("Bot Token", value="********" if settings.telegram_bot_token else "", disabled=True)
    with col2:
        st.number_input(
            "Anomali Eşiği (%)", 
            min_value=5, 
            max_value=90, 
            value=int(settings.telegram_threshold * 100),
            help="Bu orandan fazla fiyat değişimlerinde bildirim gider."
        )
        st.text_input("Chat ID", value=settings.telegram_chat_id, disabled=True)

with st.expander("📧 E-posta Raporları"):
    st.toggle("Haftalık PDF Raporu", value=settings.email_enabled, disabled=True)
    st.text_input("Alıcılar", value=settings.email_recipients, disabled=True)
    st.caption("E-posta ayarları .env dosyası üzerinden yönetilir.")

with st.expander("🕵️ Scraper Ayarları"):
    st.slider("Saniyedeki İstek Sayısı", 0.5, 5.0, settings.scraper_requests_per_second)
    st.checkbox("Headless Mod (Gizli Çalışma)", value=settings.scraper_headless)
    st.number_input("Max Ürün Limiti", value=settings.scraper_max_products)

st.divider()

if st.button("Ayarları Kaydet", type="primary"):
    st.success("Ayarlar (simüle edildi) başarıyla güncellendi!")
    st.info("Kalıcı değişiklikler için .env dosyasını düzenlemeyi unutmayın.")

st.sidebar.title("Metrio")
st.sidebar.caption("Sürüm 1.2.0")
