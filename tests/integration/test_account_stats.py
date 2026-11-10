import sqlite3
from datetime import datetime, timedelta

import pytest

from deals.stats import collect, daily_summary, reach_line
from storage.database import init_schema, record_account_stat

NOW = datetime(2026, 11, 10, 21, 30)


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn


def test_summary_shows_count_with_daily_and_weekly_change(db):
    record_account_stat(db, "telegram", 2, NOW - timedelta(days=8))
    record_account_stat(db, "telegram", 9, NOW - timedelta(days=1))
    record_account_stat(db, "telegram", 12, NOW)
    record_account_stat(db, "instagram", 3, NOW - timedelta(days=1))
    record_account_stat(db, "instagram", 5, NOW)

    text = daily_summary(db, NOW)

    assert "10 Kasım" in text
    assert "Telegram: 12 abone (+3 bugün, +10 bu hafta)" in text
    assert "Instagram: 5 takipçi (+2 bugün)" in text  # haftalık veri yok


def test_first_day_summary_has_no_change(db):
    record_account_stat(db, "telegram", 12, NOW)

    assert "Telegram: 12 abone\n" in daily_summary(db, NOW) + "\n"


def test_reach_line_compares_average_reach_by_post_type():
    line = reach_line([("CAROUSEL_ALBUM", 1), ("VIDEO", 69), ("VIDEO", 15)])

    assert line == "Son 7 gün ortalama erişim: Reels 42 (2 gönderi), kaydırmalı 1 (1 gönderi)"


def test_reach_line_is_none_without_posts():
    assert reach_line([]) is None


def test_summary_puts_reach_line_before_tiktok_reminder(db):
    record_account_stat(db, "telegram", 12, NOW)

    lines = daily_summary(db, NOW, reach="Son 7 gün ortalama erişim: Reels 42 (2 gönderi)").splitlines()

    assert lines[-2] == "Son 7 gün ortalama erişim: Reels 42 (2 gönderi)"
    assert lines[-1].startswith("TikTok")


def test_collect_records_counts_and_skips_failed_sources(db):
    def broken():
        raise RuntimeError("Instagram cevap vermedi")

    counts = collect(db, NOW, {"telegram": lambda: 12, "instagram": broken})

    assert counts == {"telegram": 12}
    rows = db.execute("SELECT channel, followers FROM account_stats").fetchall()
    assert [tuple(r) for r in rows] == [("telegram", 12)]
