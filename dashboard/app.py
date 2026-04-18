import sqlite3
import sys
from pathlib import Path

# Add parent to path so imports work when run via `streamlit run dashboard/app.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from config import settings
from analysis.queries import get_latest_snapshots_df, get_unique_brands, get_unique_platforms
from analysis.price_changes import top_movers
from analysis.anomaly import detect_anomalies
from analysis.commentary import generate_daily_summary
from dashboard.components.cards import summary_row
from dashboard.utils.ui import apply_custom_styles


apply_custom_styles(page_title="Metrio Dash", page_icon="📈")



@st.cache_resource
def get_conn():
    conn = sqlite3.connect(settings.database_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@st.cache_data(ttl=300)
def _load_overview(platforms: tuple[str, ...] | None):
    conn = get_conn()
    plat = list(platforms) if platforms else None
    df = get_latest_snapshots_df(conn, platforms=plat)
    brands = get_unique_brands(conn)
    movers = top_movers(conn, days=7, direction="both", limit=5, platforms=plat)
    anomalies = detect_anomalies(conn, lookback_days=30, threshold_percent=0.20, platforms=plat)[:5]

    avg_discount = None
    if "discount_rate" in df.columns:
        non_null = df["discount_rate"].dropna()
        if len(non_null) > 0:
            avg_discount = float(non_null.mean())

    last_run = conn.execute(
        "SELECT MAX(finished_at) FROM run_stats WHERE status='success'"
    ).fetchone()[0]

    trend_direction = "flat"
    if movers:
        down = sum(1 for m in movers if m.change_percent < 0)
        up = sum(1 for m in movers if m.change_percent > 0)
        trend_direction = "down" if down > up else ("up" if up > down else "flat")

    return {
        "df": df,
        "brands": brands,
        "movers": movers,
        "anomalies": anomalies,
        "avg_discount": avg_discount,
        "last_run": last_run,
        "trend_direction": trend_direction,
    }


def main():
    st.title("📊 Metrio")
    st.caption("E-ticaret fiyat istihbaratı")

    conn = get_conn()
    all_platforms = get_unique_platforms(conn)
    selected_platforms = st.sidebar.multiselect(
        "Platform", all_platforms, default=all_platforms,
        help="Hangi platformların verisi gösterilsin"
    )
    plat_key = tuple(sorted(selected_platforms)) if selected_platforms else None

    try:
        data = _load_overview(plat_key)
    except Exception as e:
        st.error(f"Veritabanı hatası: {e}")
        st.info("`python main.py` çalıştırarak önce veri toplayın.")
        return

    if len(data["df"]) == 0:
        st.warning("Henüz veri yok. `python main.py` çalıştırarak veri toplamaya başlayın.")
        return

    summary_row(
        total_products=len(data["df"]),
        total_brands=len(data["brands"]),
        last_run=data["last_run"],
        avg_discount=data["avg_discount"],
    )

    st.divider()

    st.subheader("📝 Günlük Yorum")
    commentary = generate_daily_summary(
        data["movers"],
        data["anomalies"],
        trend_direction=data["trend_direction"],
    )
    st.markdown(commentary)

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🎯 En Son 5 Hareket")
        if data["movers"]:
            for m in data["movers"]:
                arrow = "🔻" if m.change_percent < 0 else "🔺"
                pct = abs(m.change_percent * 100)
                st.write(f"{arrow} **{m.brand or '-'}** — {m.name[:50]}")
                st.caption(f"{m.old_price:.2f} → {m.new_price:.2f} TL ({pct:.1f}%)")
        else:
            st.info("Yeterli veri yok. Birkaç gün sonra tekrar kontrol edin.")

    with col2:
        st.subheader("🚨 Son Anomaliler")
        if data["anomalies"]:
            for a in data["anomalies"]:
                emoji = "🔻" if a.direction == "drop" else "🔺"
                pct = abs(a.deviation_percent * 100)
                st.write(f"{emoji} **{a.brand or '-'}** — {a.name[:50]}")
                st.caption(
                    f"{a.current_price:.2f} TL (ortalama {a.average_price:.2f}, "
                    f"%{pct:.0f} sapma, güven: {a.confidence})"
                )
        else:
            st.info("Anomali tespit edilmedi.")


if __name__ == "__main__":
    main()
else:
    main()
