from datetime import datetime

import pytest

from deals.selector import Deal
from deals.text import format_tl, instagram_caption, telegram_caption, turkish_date


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
