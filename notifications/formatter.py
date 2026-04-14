"""Telegram mesaj formatlaması — saf fonksiyonlar."""


def format_daily_summary(stats: dict, anomaly_count: int, date_str: str) -> str:
    if stats["status"] in ("success", "partial"):
        return (
            f"📊 Fiyat Radarı — {date_str}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✅ {stats['products_saved']} ürün tarandı\n"
            f"🎯 {anomaly_count} anomali tespit edildi\n"
            f"⏱ Süre: {stats['duration_seconds']}s"
        )
    return (
        f"⚠️ Fiyat Radarı — {date_str}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"❌ Pipeline başarısız\n"
        f"Hata: {stats.get('error_message') or 'bilinmiyor'}"
    )
