"""Günlük hesap takibi: Telegram abone ve Instagram takipçi sayısını kaydeder, özet gönderir.

Kullanım:
    python -m deals.stats    # sayıları kaydet, yönetici sohbetine günlük özet gönder

TikTok'un açık bir API'si yok; onu Emre uygulamadan takip ediyor.
"""
import io
import logging
import sqlite3
import sys
from collections.abc import Callable
from datetime import datetime, timedelta
from functools import partial

from deals.text import turkish_date
from storage.database import get_account_stat_at, record_account_stat

log = logging.getLogger(__name__)

_LABELS = {"telegram": ("Telegram", "abone"), "instagram": ("Instagram", "takipçi")}
# Günde bir kez çalışıyor; elle ikinci kez çalıştırılırsa yine dünle karşılaştırsın.
_DAY_AGO = timedelta(hours=12)
_WEEK_AGO = timedelta(days=6, hours=12)


def collect(conn: sqlite3.Connection, now: datetime,
            fetchers: dict[str, Callable[[], int]]) -> dict[str, int]:
    """Her kaynaktan sayıyı alıp kaydeder; hata veren kaynak atlanır (özet yine gider)."""
    counts = {}
    for channel, fetch in fetchers.items():
        try:
            counts[channel] = int(fetch())
        except Exception as e:  # ağ, anahtar, API hatası: diğer kaynakları engellemesin
            log.warning(f"{channel} sayısı alınamadı: {e}")
            continue
        record_account_stat(conn, channel, counts[channel], now)
    return counts


def _change(now_value: int, before: int | None, label: str) -> str | None:
    if before is None:
        return None
    return f"{now_value - before:+d} {label}"


def daily_summary(conn: sqlite3.Connection, now: datetime) -> str:
    lines = [f"📊 Günlük takip · {turkish_date(now)}"]
    for channel, (name, unit) in _LABELS.items():
        current = get_account_stat_at(conn, channel, now)
        if current is None:
            continue
        changes = [c for c in (
            _change(current, get_account_stat_at(conn, channel, now - _DAY_AGO), "bugün"),
            _change(current, get_account_stat_at(conn, channel, now - _WEEK_AGO), "bu hafta"),
        ) if c]
        line = f"{name}: {current} {unit}"
        if changes:
            line += f" ({', '.join(changes)})"
        lines.append(line)
    lines.append("TikTok'u uygulamadan kontrol et; Trendyol hedefi 10.000 takipçi.")
    return "\n".join(lines)


def main() -> int:
    from config import settings
    from deals.instagram import InstagramClient, current_token
    from deals.run import _TOKEN_STORE
    from notifications.telegram import TelegramNotifier, chat_member_count
    from storage.database import connect, init_schema
    from utils.logger import get_logger

    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    get_logger("deals")
    now = datetime.now()
    conn = connect(settings.database_path)
    init_schema(conn)

    fetchers: dict[str, Callable[[], int]] = {}
    if settings.telegram_bot_token and settings.telegram_channel_id:
        fetchers["telegram"] = partial(chat_member_count, settings.telegram_bot_token,
                                       settings.telegram_channel_id)
    if settings.instagram_enabled and settings.instagram_user_id:
        def instagram_followers() -> int:
            token = current_token(_TOKEN_STORE, settings.instagram_access_token, now)
            client = InstagramClient(settings.instagram_user_id, token, settings.instagram_api_version)
            return client.followers_count()
        fetchers["instagram"] = instagram_followers

    collect(conn, now, fetchers)
    text = daily_summary(conn, now)
    TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id,
                     settings.telegram_enabled).send_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
