from datetime import datetime

import pytest

from deals.selector import Deal
from deals.text import (format_tl, instagram_caption, telegram_caption, tiktok_mentions,
                        turkish_date, video_caption)


def _deal(**kw) -> Deal:
    base = dict(
        product_id=1, platform="trendyol", name="Lip Master Likit Ruj - Tangerine",
        brand="Pierre Cardin", category="kozmetik",
        product_url="https://www.trendyol.com/x-p-1", image_url="https://cdn/x.jpg",
        price=66.4, original_price=166.0, discount_rate=0.6,
        previous_price=None, lowest_30d=False, rating=4.6,
    )
    base.update(kw)
    return Deal(**base)


@pytest.mark.parametrize("amount, text", [
    (345, "345 TL"),
    (65.2, "65,20 TL"),
    (1150, "1.150 TL"),
    (1234.5, "1.234,50 TL"),
    (44999.0, "44.999 TL"),
])
def test_format_tl_uses_turkish_separators(amount, text):
    assert format_tl(amount) == text


def test_turkish_date():
    assert turkish_date(datetime(2026, 11, 9)) == "9 Kasım"


def test_telegram_caption_lists_price_discount_and_link():
    text = telegram_caption(_deal())

    assert "Pierre Cardin Lip Master Likit Ruj - Tangerine" in text
    assert "66,40 TL" in text
    assert "166 TL yerine" in text
    assert "%60" in text
    assert "https://www.trendyol.com/x-p-1" in text


def test_telegram_caption_mentions_real_drop_and_30_day_low():
    text = telegram_caption(_deal(previous_price=120.0, lowest_30d=True,
                                  original_price=None, discount_rate=None, price=80.0))

    assert "120 TL" in text
    assert "%33" in text
    assert "Son 30 günün en düşük fiyatı" in text


def test_instagram_caption_numbers_deals_and_appends_footer_and_hashtags():
    caption = instagram_caption(
        [_deal(), _deal(product_id=2, name="Allık", brand="Flormar", price=99.0)],
        when=datetime(2026, 11, 9, 10, 0),
        footer="Linkler Telegram kanalımızda.",
        hashtags="#indirim #kozmetik",
    )

    assert caption.startswith("Günün kozmetik fırsatları · 9 Kasım")
    assert "1. Pierre Cardin Lip Master Likit Ruj - Tangerine: 66,40 TL" in caption
    assert "2. Flormar Allık: 99 TL" in caption
    assert "Linkler Telegram kanalımızda." in caption
    assert caption.rstrip().endswith("#indirim #kozmetik")


def test_instagram_caption_mentions_bags_when_a_bag_is_included():
    caption = instagram_caption([_deal(), _deal(product_id=2, category="canta", name="Omuz Çantası")],
                                when=datetime(2026, 11, 9), footer="", hashtags="")
    assert caption.startswith("Günün kozmetik ve çanta fırsatları · 9 Kasım")


def test_category_summary_lists_present_categories_in_fixed_order():
    from deals.text import category_summary
    deals = [_deal(category="canta"), _deal(category="kozmetik"), _deal(category="parfum"),
             _deal(category="kozmetik")]
    assert category_summary(deals) == "kozmetik, parfüm, çanta"


def test_instagram_caption_stays_under_instagram_limit():
    long_name = "Çok Uzun Ürün Adı " * 40
    caption = instagram_caption(
        [_deal(product_id=i, name=long_name) for i in range(20)],
        when=datetime(2026, 11, 9), footer="", hashtags="",
    )
    assert len(caption) <= 2200


@pytest.mark.parametrize("raw, clean", [
    ("Power Of You EDP 30 ml Kadın Parfüm 3614274752038", "Power Of You EDP 30 ml Kadın Parfüm"),
    ("Blush On -allık-peach Pop-913", "Blush On -allık-peach Pop-913"),
    ("8690604521234 Nemlendirici Krem 50 ml", "Nemlendirici Krem 50 ml"),
])
def test_clean_name_drops_barcodes_but_keeps_sizes_and_shade_codes(raw, clean):
    from deals.text import clean_name
    assert clean_name(raw) == clean


def test_captions_hide_barcode_in_product_name():
    deal = _deal(name="Power Of You EDP 30 ml 3614274752038", brand="Emporio Armani")
    assert "3614274752038" not in telegram_caption(deal)
    assert "3614274752038" not in instagram_caption([deal], datetime(2026, 11, 9), "", "")


def test_card_name_drops_repeated_brand_prefix():
    from deals.text import card_name
    deal = _deal(name="SAINT DE LUMIERE LUMIWHITE Serum 8681234567890", brand="Saint De Lumiere")
    assert card_name(deal) == "LUMIWHITE Serum"
    assert card_name(_deal(name="Lip Master Ruj", brand="Pierre Cardin")) == "Lip Master Ruj"


def test_video_caption_is_short_and_points_to_telegram_channel():
    # TikTok'ta bio linki 1.000 takipçiye kadar yok; ürün listesi yerine kanal adı yazılır.
    deals = [_deal(product_id=1), _deal(product_id=2, category="canta", name="Omuz Çantası")]

    text = video_caption(deals, datetime(2026, 11, 10), "@kozmetikavcisi", "#indirim #kozmetik")

    assert text.splitlines()[1] == "Günün kozmetik ve çanta fırsatları · 10 Kasım"
    assert "Telegram kanalımızda: @kozmetikavcisi" in text
    assert text.endswith("#indirim #kozmetik")
    assert "Omuz Çantası" not in text and "bio" not in text


def test_special_day_label_replaces_daily_headline():
    deals = [_deal(product_id=1)]
    when = datetime(2026, 11, 11)

    assert instagram_caption(deals, when, "", "", label="11.11").startswith(
        "11.11 kozmetik fırsatları · 11 Kasım")
    assert video_caption(deals, when, "@k", "", label="11.11").splitlines()[1].startswith(
        "11.11 kozmetik fırsatları · 11 Kasım")


def test_tiktok_mentions_tag_known_brands_once_then_trendyol():
    deals = [_deal(product_id=1, brand="Erbatab"), _deal(product_id=2, brand="Bilinmeyen"),
             _deal(product_id=3, brand="DR. ÜMİT AKTAŞ"), _deal(product_id=4, brand="Erbatab")]

    assert tiktok_mentions(deals) == "@erbatab @umitaktasofficial @trendyolcom"


def test_tiktok_mentions_stay_at_four_tags():
    # Fazla etiket spam gibi durur: en fazla 3 marka + Trendyol.
    brands = ["Erbatab", "Wella", "The Ceel", "INO Beauty", "DeFacto"]
    deals = [_deal(product_id=i, brand=b) for i, b in enumerate(brands)]

    assert tiktok_mentions(deals) == "@erbatab @wellaturkiye @theceelcom @trendyolcom"


def test_tiktok_mentions_skip_trendyol_for_other_platforms():
    assert tiktok_mentions([_deal(brand="Bilinmeyen", platform="akakce")]) == ""


def test_video_caption_puts_mentions_before_hashtags():
    text = video_caption([_deal()], datetime(2026, 11, 10), "@k", "#indirim",
                         mentions="@erbatab @trendyolcom")

    assert text.endswith("@erbatab @trendyolcom\n\n#indirim")


def test_video_caption_opens_with_a_question_that_invites_comments():
    deals = [_deal(product_id=i) for i in range(1, 6)]

    first = video_caption(deals, datetime(2026, 11, 13), "@k", "").splitlines()[0]

    assert first == "Hangisini alırdın? 1'den 5'e yaz 👇"


def test_question_suffix_follows_turkish_vowel_harmony():
    two = [_deal(product_id=1), _deal(product_id=2)]

    assert video_caption(two, datetime(2026, 11, 13), "@k", "").startswith(
        "Hangisini alırdın? 1'den 2'ye yaz")
