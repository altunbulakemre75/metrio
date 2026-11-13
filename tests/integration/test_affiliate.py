"""Affiliate linki: program onayı gelince tek ayarla açılır, günde en fazla 8 link."""
from datetime import timedelta

from deals.affiliate import DAILY_LIMIT, affiliate_url
from storage.database import record_posted_deals
from tests.integration.test_deals_run import NOW, Recorder, _add_deals, _cfg, _run, db  # noqa: F401

TEMPLATE = "https://ty.example/r?u={url}"


def test_without_template_the_plain_product_link_is_used():
    assert affiliate_url("https://www.trendyol.com/x-p-1", "") == "https://www.trendyol.com/x-p-1"


def test_template_wraps_the_encoded_product_link():
    assert affiliate_url("https://www.trendyol.com/x-p-1?a=1", TEMPLATE) == (
        "https://ty.example/r?u=https%3A%2F%2Fwww.trendyol.com%2Fx-p-1%3Fa%3D1")


def test_affiliate_posts_carry_the_link_and_the_legal_disclosure(db, tmp_path):
    _add_deals(db, 4)
    tg = Recorder()

    _run(db, tmp_path, cfg=_cfg(affiliate_template=TEMPLATE), telegram_send=tg)

    captions = [caption for _, caption in tg.calls]
    assert all("ty.example/r?u=" in c and c.endswith("#işbirliği") for c in captions)
    refs = db.execute("SELECT post_ref FROM posted_deals WHERE channel='telegram'").fetchall()
    assert [r[0] for r in refs] == ["affiliate"] * 4


def test_only_eight_affiliate_links_count_per_day_the_rest_stay_plain(db, tmp_path):
    record_posted_deals(db, list(range(900, 900 + DAILY_LIMIT - 2)), "telegram", "affiliate",
                        NOW - timedelta(hours=2))
    _add_deals(db, 4)
    tg = Recorder()

    _run(db, tmp_path, cfg=_cfg(affiliate_template=TEMPLATE), telegram_send=tg)

    captions = [caption for _, caption in tg.calls]
    assert sum("ty.example" in c for c in captions) == 2
    assert sum("#işbirliği" in c for c in captions) == 2


def test_yesterdays_affiliate_links_do_not_use_up_todays_limit(db, tmp_path):
    record_posted_deals(db, list(range(900, 900 + DAILY_LIMIT)), "telegram", "affiliate",
                        NOW - timedelta(days=1))
    _add_deals(db, 4)
    tg = Recorder()

    _run(db, tmp_path, cfg=_cfg(affiliate_template=TEMPLATE), telegram_send=tg)

    assert all("ty.example" in caption for _, caption in tg.calls)


def test_no_disclosure_without_affiliate(db, tmp_path):
    _add_deals(db, 4)
    tg = Recorder()

    _run(db, tmp_path, telegram_send=tg)

    assert not any("#işbirliği" in caption for _, caption in tg.calls)
