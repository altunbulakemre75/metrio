"""Telegram mesaj formatlaması — saf fonksiyonlar."""


def format_daily_summary(stats: dict, anomaly_count: int, date_str: str) -> str:
    if stats["status"] in ("success", "partial"):
        return (
            f"📊 Metrio — {date_str}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✅ {stats['products_saved']} ürün tarandı\n"
            f"🎯 {anomaly_count} anomali tespit edildi\n"
            f"⏱ Süre: {stats['duration_seconds']}s"
        )
    return (
        f"⚠️ Metrio — {date_str}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"❌ Pipeline başarısız\n"
        f"Hata: {stats.get('error_message') or 'bilinmiyor'}"
    )


def format_anomaly_alert(anomaly) -> str:
    if anomaly.direction == "drop":
        arrow, label = "🔻", "FİYAT DÜŞTÜ"
    else:
        arrow, label = "🔺", "FİYAT ARTTI"

    pct_str = f"{anomaly.deviation_percent * 100:+.0f}%"
    brand = anomaly.brand + " " if anomaly.brand else ""
    return (
        f"{arrow} {label} ({pct_str})\n"
        f"{brand}{anomaly.name}\n"
        f"💰 {anomaly.average_price:.2f} TL → {anomaly.current_price:.2f} TL\n"
        f"🔗 {anomaly.product_url}"
    )


def format_grouped_anomalies(anomalies: list, max_detail: int = 4) -> str:
    total = len(anomalies)
    lines = [f"🎯 {total} anomali tespit edildi", "━━━━━━━━━━━━━━━━━━"]
    for a in anomalies[:max_detail]:
        arrow = "🔻" if a.direction == "drop" else "🔺"
        pct = f"{a.deviation_percent * 100:+.0f}%"
        brand = a.brand + " " if a.brand else ""
        lines.append(f"{arrow} {brand}{a.name} ({pct})")
    remaining = total - max_detail
    if remaining > 0:
        lines.append(f"... ve {remaining} tane daha")
    return "\n".join(lines)
