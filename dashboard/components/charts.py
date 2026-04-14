import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def price_history_line(history_df: pd.DataFrame, product_name: str) -> go.Figure:
    fig = px.line(
        history_df,
        x="captured_at",
        y="price",
        title=f"Fiyat Geçmişi: {product_name[:60]}",
        labels={"captured_at": "Tarih", "price": "Fiyat (TL)"},
    )
    fig.update_traces(mode="lines+markers", line=dict(color="#E85D04", width=2))
    fig.update_layout(hovermode="x unified", height=400)
    return fig


def top_discounts_bar(movers) -> go.Figure:
    if not movers:
        return go.Figure()
    df = pd.DataFrame([
        {
            "urun": f"{m.brand or '-'}: {m.name[:40]}",
            "indirim": abs(m.change_percent * 100),
            "yeni_fiyat": m.new_price,
        }
        for m in movers[:10]
    ])
    fig = px.bar(
        df, x="indirim", y="urun", orientation="h",
        title="En Büyük 10 İndirim (Son 7 Gün)",
        labels={"indirim": "İndirim %", "urun": ""},
        color="indirim", color_continuous_scale=["#FFD4A8", "#E85D04"],
    )
    fig.update_layout(height=500, showlegend=False, yaxis=dict(autorange="reversed"))
    return fig


def trend_line(trend_points, title: str) -> go.Figure:
    df = pd.DataFrame([
        {"tarih": p.date, "ortalama": p.average_price, "median": p.median_price}
        for p in trend_points
    ])
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["tarih"], y=df["ortalama"], name="Ortalama",
        line=dict(color="#E85D04", width=3),
    ))
    fig.add_trace(go.Scatter(
        x=df["tarih"], y=df["median"], name="Medyan",
        line=dict(color="#6C757D", width=2, dash="dash"),
    ))
    fig.update_layout(title=title, height=400, xaxis_title="Tarih", yaxis_title="Fiyat (TL)")
    return fig
