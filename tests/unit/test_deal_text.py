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


def test_instagram_caption_stays_under_instagram_limit():
    long_name = "Çok Uzun Ürün Adı " * 40
    caption = instagram_caption(
        [_deal(product_id=i, name=long_name) for i in range(20)],
        when=datetime(2026, 11, 9), footer="", hashtags="",
    )
    assert len(caption) <= 2200
