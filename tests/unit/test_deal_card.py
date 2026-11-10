import io
from datetime import datetime
from unittest.mock import patch

import requests
from PIL import Image

from deals.card import CARD_SIZE, headline_rate, load_fonts, render_cover, render_deal_card
from deals.images import fetch_product_image, full_size_url, trim_white_border
from deals.selector import Deal


def _deal(**kw) -> Deal:
    base = dict(
        product_id=1, platform="trendyol", name="Lip Master Likit Ruj - Tangerine",
        brand="Pierre Cardin", category="kozmetik",
        product_url="https://www.trendyol.com/x-p-1", image_url="https://cdn/x.jpg",
        price=66.4, original_price=166.0, discount_rate=0.6,
        previous_price=None, lowest_30d=True, rating=4.6,
    )
    base.update(kw)
    return Deal(**base)


def _assert_instagram_jpeg(path):
    with Image.open(path) as img:
        assert img.format == "JPEG"
        assert img.size == CARD_SIZE == (1080, 1350)
        assert img.mode == "RGB"


def test_deal_card_is_portrait_jpeg_with_product_photo(tmp_path):
    photo = Image.new("RGB", (400, 600), "red")
    out = render_deal_card(_deal(), photo, "Fırsat Radarı", tmp_path / "card.jpg", load_fonts(""))
    _assert_instagram_jpeg(out)


def test_deal_card_survives_missing_photo_and_very_long_name(tmp_path):
    deal = _deal(name="Çok Uzun İsimli Şampuan Ğ " * 30, brand=None,
                 original_price=None, discount_rate=None, previous_price=200.0, price=50.0)
    out = render_deal_card(deal, None, "Fırsat Radarı", tmp_path / "card.jpg", load_fonts(""))
    _assert_instagram_jpeg(out)


def test_cover_lists_deals_as_portrait_jpeg(tmp_path):
    out = render_cover([_deal(product_id=i) for i in range(5)], datetime(2026, 11, 9),
                       "Fırsat Radarı", tmp_path / "cover.jpg", load_fonts(""))
    _assert_instagram_jpeg(out)


def test_cover_without_swipe_hint_for_video(tmp_path):
    # Reels'te kapak kendiliğinden geçiyor; "Kaydır →" yazısı yanıltıcı olur.
    deals, when, fonts = [_deal(product_id=i) for i in range(5)], datetime(2026, 11, 9), load_fonts("")
    swipe = render_cover(deals, when, "Fırsat Radarı", tmp_path / "a.jpg", fonts)
    plain = render_cover(deals, when, "Fırsat Radarı", tmp_path / "b.jpg", fonts, cta="")

    corner = (700, 1240, 1080, 1340)
    with Image.open(swipe) as a, Image.open(plain) as b:
        assert a.crop(corner).getextrema() != b.crop(corner).getextrema()
        assert all(lo > 200 for lo, _ in b.crop(corner).getextrema())  # köşe boş


def test_full_size_url_drops_trendyol_thumbnail_resize():
    thumb = "https://cdn.dsmcdn.com/mnresize/400/-/ty1891/prod/a/1_org_zoom.jpg"
    assert full_size_url(thumb) == "https://cdn.dsmcdn.com/ty1891/prod/a/1_org_zoom.jpg"
    other = "https://cdn.akakce.com/x/marka/urun.jpg"
    assert full_size_url(other) == other


def test_fetch_product_image_returns_none_when_download_fails():
    with patch("deals.images.requests.get", side_effect=requests.ConnectionError("boom")):
        assert fetch_product_image("https://cdn/x.jpg") is None


def test_fetch_product_image_returns_rgb_image():
    buf = io.BytesIO()
    Image.new("RGBA", (10, 20), (0, 0, 255, 128)).save(buf, "PNG")
    with patch("deals.images.requests.get") as get:
        get.return_value.content = buf.getvalue()
        get.return_value.raise_for_status.return_value = None
        img = fetch_product_image("https://cdn/x.png")
    assert img is not None
    assert img.mode == "RGB" and img.size == (10, 20)


def test_trim_white_border_keeps_only_the_product():
    img = Image.new("RGB", (100, 300), "white")
    img.paste(Image.new("RGB", (50, 40), "red"), (25, 130))

    assert trim_white_border(img).size == (50, 40)


def test_trim_white_border_leaves_all_white_image_alone():
    img = Image.new("RGB", (100, 300), "white")
    assert trim_white_border(img).size == (100, 300)


def test_long_cover_title_shrinks_to_stay_inside_the_card(tmp_path):
    deals, fonts = [_deal(product_id=i) for i in range(5)], load_fonts("")
    out = render_cover(deals, datetime(2026, 11, 27), "Fırsat Radarı", tmp_path / "c.jpg", fonts,
                       title="EFSANE CUMA FIRSATLARI")

    with Image.open(out) as img:
        right_edge = img.crop((1030, 140, 1080, 260)).convert("RGB")
        assert all(lo > 150 for lo, _ in right_edge.getextrema()[:2])  # sarı zemin, yazı taşmadı


def test_small_real_drop_does_not_hide_a_big_discount_on_the_tag():
    # %40 indirimli ürün dünden %7 ucuzladı diye kapakta "%7" yazmasın.
    assert headline_rate(_deal(price=93.0, previous_price=100.0, discount_rate=0.4)) == (0.4, "İNDİRİM")


def test_meaningful_real_drop_is_shown_on_the_tag():
    rate, label = headline_rate(_deal(price=66.0, previous_price=100.0, discount_rate=0.5))
    assert label == "DÜŞTÜ" and round(rate, 2) == 0.34
