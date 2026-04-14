from typing import Literal
from analysis.price_changes import PriceChange
from analysis.anomaly import Anomaly


_TREND_PHRASE = {
    "down": "genel olarak düşüş",
    "up": "kayda değer artış",
    "flat": "yatay seyir",
}


def generate_daily_summary(
    top_movers: list[PriceChange],
    anomalies: list[Anomaly],
    trend_direction: Literal["up", "down", "flat"],
) -> str:
    """Analiz çıktılarından Türkçe özet paragraf üretir."""
    lines = []

    if top_movers:
        biggest = top_movers[0]
        direction_word = "indirimi" if biggest.change_percent < 0 else "artışı"
        pct = abs(biggest.change_percent * 100)
        lines.append(
            f"Son 7 günde **{len(top_movers)} üründe** fiyat hareketi tespit edildi. "
            f"En büyük {direction_word} **{biggest.brand or 'bilinmeyen'}** markasında görüldü: "
            f"*{biggest.name[:60]}* → %{pct:.0f} ile {biggest.new_price:.2f} TL."
        )
    else:
        lines.append("Son 7 günde kayda değer fiyat hareketi tespit edilmedi.")

    if anomalies:
        high_conf = [a for a in anomalies if a.confidence == "high"]
        lines.append(
            f"{len(anomalies)} üründe ortalamadan sapma var "
            f"({len(high_conf)} yüksek güvenlikli). Detaylar Anomaliler sayfasında."
        )
    else:
        lines.append("Kategoride anomali tespit edilmedi.")

    lines.append(f"Kategorinin genel fiyat trendi: **{_TREND_PHRASE[trend_direction]}**.")

    return " ".join(lines)
