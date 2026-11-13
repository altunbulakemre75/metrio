"""Günlük hesap takibi: Telegram abone ve Instagram takipçi sayısını kaydeder, özet gönderir.

Kullanım:
    python -m deals.stats              # sayıları kaydet, yönetici sohbetine günlük özet gönder
    python -m deals.stats --tiktok 48  # TikTok takipçi sayısını elle kaydet (özet gönderilmez)

TikTok'un açık bir API'si yok ve sayfası tarayıcısız/görünmez tarayıcıyla açılmıyor; sayıyı
Emre uygulamadan bakıp kaydediyor.
"""
import argparse
import math
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

_LABELS = {"telegram": ("Telegram", "abone"), "instagram": ("Instagram", "takipçi"),
           "tiktok": ("TikTok", "takipçi")}
# Trendyol Influencer programının TikTok şartı (organik takipçi).
TIKTOK_GOAL = 10_000
# Günde bir kez çalışıyor; elle ikinci kez çalıştırılırsa yine dünle karşılaştırsın.
_DAY_AGO = timedelta(hours=12)
_WEEK_AGO = timedelta(days=6, hours=12)
_POST_TYPES = {"VIDEO": "Reels", "CAROUSEL_ALBUM": "kaydırmalı", "IMAGE": "tek görsel"}


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


def reach_line(posts: list[tuple[str, int]]) -> str | None:
    """Gönderi türüne göre ortalama erişim: hangi biçimin yeni kişilere ulaştığını gösterir."""
    parts = []
    for media_type, name in _POST_TYPES.items():
        reaches = [reach for kind, reach in posts if kind == media_type]
        if reaches:
            parts.append(f"{name} {round(sum(reaches) / len(reaches))} ({len(reaches)} gönderi)")
    return f"Son 7 gün ortalama erişim: {', '.join(parts)}" if parts else None


def _thousands(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def tiktok_goal_line(conn: sqlite3.Connection, now: datetime) -> str:
    """Trendyol hedefine kalan takipçi; son 7 günün hızıyla tahmini gün sayısı."""
    current = get_account_stat_at(conn, "tiktok", now)
    if current is None:
        return ("TikTok sayısını kaydet: python -m deals.stats --tiktok <sayı> "
                f"(Trendyol hedefi {_thousands(TIKTOK_GOAL)})")
    remaining = max(0, TIKTOK_GOAL - current)
    line = f"TikTok hedefi {_thousands(TIKTOK_GOAL)}: kalan {_thousands(remaining)}"
    first = conn.execute(
        "SELECT followers, captured_at FROM account_stats WHERE channel = 'tiktok' "
        "AND captured_at >= ? AND captured_at <= ? ORDER BY captured_at LIMIT 1",
        (now - _WEEK_AGO, now),
    ).fetchone()
    if first:
        start = first[1] if isinstance(first[1], datetime) else datetime.fromisoformat(first[1])
        days = (now - start).total_seconds() / 86400
        if days >= 1 and current > first[0] and remaining:
            per_day = (current - first[0]) / days
            line += f", bu hızla yaklaşık {_thousands(math.ceil(remaining / per_day))} gün"
    return line


def daily_summary(conn: sqlite3.Connection, now: datetime, reach: str | None = None) -> str:
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
    if reach:
        lines.append(reach)
    lines.append(tiktok_goal_line(conn, now))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    from config import settings
    from deals.instagram import InstagramClient, current_token
    from deals.run import _TOKEN_STORE
    from notifications.telegram import TelegramNotifier, chat_member_count
    from storage.database import connect, init_schema
    from utils.logger import get_logger

    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    get_logger("deals")
    parser = argparse.ArgumentParser(description="Günlük takipçi takibi")
    parser.add_argument("--tiktok", type=int, help="TikTok takipçi sayısını kaydet ve çık")
    args = parser.parse_args(argv)
    now = datetime.now()
    conn = connect(settings.database_path)
    init_schema(conn)
    if args.tiktok is not None:
        record_account_stat(conn, "tiktok", args.tiktok, now)
        print(tiktok_goal_line(conn, now))
        return 0

    fetchers: dict[str, Callable[[], int]] = {}
    if settings.telegram_bot_token and settings.telegram_channel_id:
        fetchers["telegram"] = partial(chat_member_count, settings.telegram_bot_token,
                                       settings.telegram_channel_id)
    instagram = None
    if settings.instagram_enabled and settings.instagram_user_id:
        token = current_token(_TOKEN_STORE, settings.instagram_access_token, now)
        instagram = InstagramClient(settings.instagram_user_id, token, settings.instagram_api_version)
        fetchers["instagram"] = instagram.followers_count

    collect(conn, now, fetchers)
    reach = None
    if instagram is not None:
        try:
            reach = reach_line(instagram.media_reach(now.astimezone() - timedelta(days=7)))
        except Exception as e:  # istatistik izni yoksa özet yine gitsin
            log.warning(f"Instagram erişim sayıları alınamadı: {e}")
    text = daily_summary(conn, now, reach)
    TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id,
                     settings.telegram_enabled).send_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
