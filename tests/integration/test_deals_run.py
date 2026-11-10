import sqlite3
from datetime import datetime, timedelta

import pytest
from PIL import Image

from deals.hosting import HostingError
from deals.instagram import InstagramError
from deals.run import DealsConfig, run_once
from deals.video import VideoError
from storage.database import init_schema, save_snapshot
from storage.models import ProductSnapshot

NOW = datetime(2026, 11, 9, 10, 0)


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn


def _add_deals(db, n, start=0):
    for i in range(start, start + n):
        save_snapshot(db, ProductSnapshot(
            platform="trendyol", platform_product_id=str(i), name=f"Ruj {i}",
            brand=f"Marka{i}", category="kozmetik",
            product_url=f"https://www.trendyol.com/x-p-{i}", image_url=f"https://cdn/{i}.jpg",
            price=50, original_price=100, discount_rate=0.5,
            seller_name=None, seller_rating=4.5, in_stock=True,
            captured_at=NOW - timedelta(hours=7),
        ))


class FakeHost:
    def __init__(self, fail=False):
        self.files, self.fail = [], fail

    def publish(self, files, when):
        if self.fail:
            raise HostingError("push reddedildi")
        self.files = list(files)
        return [f"https://raw.example/{f.name}" for f in files]


class FakeInstagram:
    def __init__(self, fail=False):
        self.calls, self.reels, self.fail = [], [], fail

    def publish_reel(self, video, caption):
        if self.fail:
            raise InstagramError("Invalid OAuth access token")
        self.reels.append((video, caption))
        return "REEL1"

    def publish_carousel(self, urls, caption):
        if self.fail:
            raise InstagramError("Invalid OAuth access token")
        self.calls.append((urls, caption))
        return "MEDIA1"


class Recorder:
    def __init__(self, result=True):
        self.calls, self.result = [], result

    def __call__(self, *args):
        self.calls.append(args)
        return self.result


def _cfg(**kw):
    base = dict(page_name="Fırsat Radarı", categories=["kozmetik"], per_post=5,
                min_discount=0.3, exclude_words=[], repeat_after=timedelta(days=14),
                caption_footer="Linkler Telegram'da.", hashtags="#indirim", font_dir="")
    base.update(kw)
    return DealsConfig(**base)


def _run(db, tmp_path, **kw):
    kw.setdefault("image_fetcher", lambda url: Image.new("RGB", (300, 300), "pink"))
    kw.setdefault("wait_live", lambda urls: True)
    cfg = kw.pop("cfg", _cfg())
    return run_once(db, cfg, NOW, tmp_path / "out", **kw)


def test_posts_carousel_to_instagram_and_each_deal_to_telegram(db, tmp_path):
    _add_deals(db, 4)
    host, ig, tg, admin = FakeHost(), FakeInstagram(), Recorder(), Recorder()

    result = _run(db, tmp_path, host=host, instagram=ig, telegram_send=tg, notify_admin=admin)

    assert result.status == "posted"
    urls, caption = ig.calls[0]
    assert len(urls) == 5  # kapak + 4 ürün
    assert urls[0].endswith("cover.jpg")
    assert "Ruj 0" in caption and "#indirim" in caption
    assert all(f.exists() and f.suffix == ".jpg" for f in host.files)
    assert len(tg.calls) == 4
    photo, text = tg.calls[0]
    assert photo.exists() and "https://www.trendyol.com/x-p-" in text
    assert admin.calls == []


def test_posted_products_are_not_repeated_on_next_run(db, tmp_path):
    _add_deals(db, 4)
    _run(db, tmp_path, host=FakeHost(), instagram=FakeInstagram(), telegram_send=Recorder())

    ig = FakeInstagram()
    result = _run(db, tmp_path, host=FakeHost(), instagram=ig, telegram_send=Recorder())

    assert result.status == "no_deals"
    assert ig.calls == []


def test_too_few_deals_posts_nothing_and_tells_admin(db, tmp_path):
    _add_deals(db, 2)
    ig, tg, admin = FakeInstagram(), Recorder(), Recorder()

    result = _run(db, tmp_path, host=FakeHost(), instagram=ig, telegram_send=tg, notify_admin=admin)

    assert result.status == "no_deals"
    assert ig.calls == [] and tg.calls == []
    assert "2 fırsat" in admin.calls[0][0]


def test_instagram_failure_alerts_admin_but_telegram_still_posts(db, tmp_path):
    _add_deals(db, 4)
    tg, admin = Recorder(), Recorder()

    result = _run(db, tmp_path, host=FakeHost(), instagram=FakeInstagram(fail=True),
                  telegram_send=tg, notify_admin=admin)

    assert result.status == "partial"
    assert len(tg.calls) == 4
    assert "Invalid OAuth access token" in admin.calls[0][0]


def test_hosting_failure_alerts_admin(db, tmp_path):
    _add_deals(db, 4)
    admin = Recorder()

    result = _run(db, tmp_path, host=FakeHost(fail=True), instagram=FakeInstagram(),
                  notify_admin=admin)

    assert result.status == "failed"
    assert "push reddedildi" in admin.calls[0][0]


def test_images_not_live_in_time_skip_instagram(db, tmp_path):
    _add_deals(db, 4)
    ig, admin = FakeInstagram(), Recorder()

    result = _run(db, tmp_path, host=FakeHost(), instagram=ig, notify_admin=admin,
                  wait_live=lambda urls: False)

    assert result.status == "failed"
    assert ig.calls == []
    assert admin.calls


def test_without_channels_only_renders_cards(db, tmp_path):
    _add_deals(db, 4)

    result = _run(db, tmp_path)

    assert result.status == "rendered"
    assert len(result.files) == 5
    assert all(f.exists() for f in result.files)
    assert db.execute("SELECT COUNT(*) FROM posted_deals").fetchone()[0] == 0


def _fake_video(cards, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(b"mp4")
    return out


def test_reel_run_posts_video_instead_of_carousel_without_image_hosting(db, tmp_path):
    _add_deals(db, 4)
    ig, tg = FakeInstagram(), Recorder()

    result = _run(db, tmp_path, host=FakeHost(fail=True), instagram=ig, telegram_send=tg,
                  reel=True, video_maker=_fake_video)

    assert result.status == "posted"
    assert ig.calls == []
    video, caption = ig.reels[0]
    assert video.name == "reel.mp4" and video.exists()
    assert "Ruj 0" in caption
    assert len(tg.calls) == 4
    refs = db.execute("SELECT DISTINCT post_ref FROM posted_deals WHERE channel='instagram'").fetchall()
    assert [r[0] for r in refs] == ["REEL1"]


def test_reel_video_is_also_sent_to_admin_for_tiktok(db, tmp_path):
    _add_deals(db, 4)
    shared = Recorder()

    _run(db, tmp_path, instagram=FakeInstagram(), reel=True, video_maker=_fake_video,
         share_video=shared)

    video, caption = shared.calls[0]
    assert video.name == "reel.mp4"
    assert "#indirim" in caption


def test_carousel_run_sends_no_video(db, tmp_path):
    _add_deals(db, 4)
    shared = Recorder()

    _run(db, tmp_path, host=FakeHost(), instagram=FakeInstagram(), share_video=shared)

    assert shared.calls == []


def test_reel_run_without_channels_still_renders_the_video_for_preview(db, tmp_path):
    _add_deals(db, 4)

    result = _run(db, tmp_path, reel=True, video_maker=_fake_video)

    assert result.status == "rendered"
    assert result.video is not None and result.video.exists()


def test_video_failure_falls_back_to_carousel_and_tells_admin(db, tmp_path):
    _add_deals(db, 4)
    ig, admin = FakeInstagram(), Recorder()

    def broken(cards, out):
        raise VideoError("ffmpeg bulunamadı")

    result = _run(db, tmp_path, host=FakeHost(), instagram=ig, notify_admin=admin,
                  reel=True, video_maker=broken)

    assert result.status == "posted"
    assert ig.reels == [] and len(ig.calls) == 1
    assert "ffmpeg bulunamadı" in admin.calls[0][0]


def test_check_setup_reports_missing_channels():
    from types import SimpleNamespace
    from deals.run import check_setup
    settings = SimpleNamespace(telegram_bot_token="", telegram_channel_id="",
                               instagram_enabled=False)

    lines = check_setup(settings, NOW)

    assert lines[0].startswith("YOK") and "TELEGRAM_CHANNEL_ID" in lines[0]
    assert lines[1].startswith("YOK") and "INSTAGRAM_ENABLED" in lines[1]


def test_check_setup_names_missing_instagram_settings():
    from types import SimpleNamespace
    from deals.run import check_setup
    settings = SimpleNamespace(telegram_bot_token="", telegram_channel_id="",
                               instagram_enabled=True, instagram_user_id="",
                               image_host_repo_dir="", image_host_base_url="")

    lines = check_setup(settings, NOW)

    assert lines[1].startswith("HATA")
    assert "INSTAGRAM_USER_ID" in lines[1] and "IMAGE_HOST_REPO_DIR" in lines[1]


def test_special_day_posts_use_the_day_label(db, tmp_path):
    when = datetime(2026, 11, 11, 10, 0)
    for i in range(4):
        save_snapshot(db, ProductSnapshot(
            platform="trendyol", platform_product_id=str(i), name=f"Ruj {i}", brand=f"M{i}",
            category="kozmetik", product_url=f"https://www.trendyol.com/x-p-{i}",
            image_url="https://cdn/x.jpg", price=50, original_price=100, discount_rate=0.5,
            seller_name=None, seller_rating=4.5, in_stock=True, captured_at=when - timedelta(hours=7)))
    ig = FakeInstagram()

    run_once(db, _cfg(special_days={"11-11": "11.11"}), when, tmp_path / "out", host=FakeHost(),
             instagram=ig, image_fetcher=lambda url: Image.new("RGB", (300, 300), "pink"),
             wait_live=lambda urls: True)

    assert ig.calls[0][1].startswith("11.11 kozmetik fırsatları · 11 Kasım")


def test_preferred_brands_reach_the_selection(db, tmp_path):
    _add_deals(db, 4)  # hepsi %50; eşitlikte ilk üçü seçilirdi
    ig = FakeInstagram()

    run_once(db, _cfg(per_post=3, preferred_brands=["Marka3"]), NOW, tmp_path / "out",
             host=FakeHost(), instagram=ig, image_fetcher=lambda url: Image.new("RGB", (300, 300)),
             wait_live=lambda urls: True)

    assert "Ruj 3" in ig.calls[0][1]


def test_manual_reel_goes_to_admin_with_music_note_instead_of_instagram(db, tmp_path):
    # Telifli şarkı API ile eklenemiyor: Emre uygulamadan müzik ekleyip kendisi paylaşıyor.
    _add_deals(db, 4)
    ig, tg, shared, texts = FakeInstagram(), Recorder(), Recorder(), Recorder()

    result = _run(db, tmp_path, cfg=_cfg(reel_manual=True, reel_music="BbY WOW"),
                  instagram=ig, telegram_send=tg, reel=True, video_maker=_fake_video,
                  share_video=shared, share_text=texts)

    assert result.status == "posted" and len(tg.calls) == 4
    assert ig.reels == [] and ig.calls == []
    assert db.execute("SELECT COUNT(*) FROM posted_deals WHERE channel='instagram'").fetchone()[0] == 0
    note, instagram_text = texts.calls[0][0], texts.calls[1][0]
    assert "BbY WOW" in note
    assert shared.calls[0][0].name == "reel.mp4"
    assert instagram_text.startswith("Günün kozmetik fırsatları") and "Ruj 0" in instagram_text
    assert "Linkler Telegram'da." in instagram_text


def test_manual_mode_still_posts_carousel_when_video_fails(db, tmp_path):
    _add_deals(db, 4)
    ig = FakeInstagram()

    def broken(cards, out):
        raise VideoError("ffmpeg bulunamadı")

    _run(db, tmp_path, cfg=_cfg(reel_manual=True), host=FakeHost(), instagram=ig,
         reel=True, video_maker=broken, share_text=Recorder())

    assert len(ig.calls) == 1
