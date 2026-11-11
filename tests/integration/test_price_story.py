import sqlite3
from datetime import datetime, timedelta

import pytest
from PIL import Image

from deals.card import CARD_SIZE, load_fonts
from deals.story import pick_story, render_story_cards, story_caption, verdict_lines
from storage.database import init_schema, save_snapshot
from storage.models import ProductSnapshot

NOW = datetime(2026, 11, 11, 15, 0)
SPRING = datetime(2026, 4, 19, 3, 0)


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn


def _history(db, pid, prices, *, brand="Marka", original=None, last_seen=NOW - timedelta(hours=5),
             category="kozmetik"):
    """prices: baharda art arda günlerin fiyatları; sonuncusu bugünkü fiyat."""
    times = [SPRING + timedelta(days=i) for i in range(len(prices) - 1)] + [last_seen]
    for when, price in zip(times, prices):
        latest = when == last_seen
        save_snapshot(db, ProductSnapshot(
            platform="trendyol", platform_product_id=str(pid), name=f"Krem {pid}", brand=brand,
            category=category, product_url=f"https://www.trendyol.com/x-p-{pid}",
            image_url=f"https://cdn/{pid}.jpg", price=price,
            original_price=original if latest else None,
            discount_rate=(1 - price / original) if latest and original else None,
            seller_name=None, seller_rating=4.5, in_stock=True, captured_at=when,
        ))


def test_price_at_its_lowest_and_well_below_spring_is_a_real_discount(db):
    _history(db, 1, [657, 640, 650, 397])

    story = pick_story(db, NOW)

    assert story.verdict == "real"
    assert (story.first_price, story.price) == (657, 397)
    assert verdict_lines(story) == [
        "EVET, GERÇEK",
        "Nisan'da 657 TL'ydi, bugün 397 TL.",
        "Nisan'dan beri kayıtlarımızdaki en düşük fiyat.",
    ]


def test_label_discount_that_is_not_cheaper_than_spring_is_flagged(db):
    _history(db, 1, [1139.81, 1150, 1187.21, 1175.93], original=1679.9)

    story = pick_story(db, NOW)

    assert story.verdict == "not_real"
    assert verdict_lines(story) == [
        "ASLINDA UCUZLAMADI",
        "Etikette 1.679,90 TL yerine 1.175,93 TL yazıyor.",
        "Ama Nisan'da 1.139,81 TL'ydi.",
    ]


def test_products_without_a_clear_verdict_or_fresh_price_are_skipped(db):
    _history(db, 1, [300, 310, 305, 290])                                    # küçük fark
    _history(db, 2, [657, 640, 650, 397], last_seen=NOW - timedelta(days=3))  # fiyat bayat
    _history(db, 3, [657, 397])                                              # geçmiş çok kısa

    assert pick_story(db, NOW) is None


def test_known_brand_wins_and_already_told_products_are_skipped(db):
    _history(db, 1, [1000, 990, 980, 400], brand="Bilinmeyen")
    _history(db, 2, [657, 640, 650, 397], brand="CeraVe")

    assert pick_story(db, NOW, preferred_brands=("CeraVe",)).product_id == 2
    assert pick_story(db, NOW, preferred_brands=("CeraVe",), exclude_ids={2}).product_id == 1


def test_only_beauty_categories_are_told(db):
    _history(db, 1, [657, 640, 650, 397], category="cep-telefonu")

    assert pick_story(db, NOW) is None


def test_story_renders_three_cards_and_a_caption(db, tmp_path):
    _history(db, 1, [657, 640, 650, 397], brand="CeraVe")
    story = pick_story(db, NOW)

    cards = render_story_cards(story, Image.new("RGB", (300, 300), "pink"), "Kozmetik Avcısı",
                               tmp_path / "out", load_fonts(""))
    caption = story_caption(story, "@kozmetikavcisi", "#indirim")

    assert [c.name for c in cards] == ["1.jpg", "2.jpg", "3.jpg"]
    assert all(Image.open(c).size == CARD_SIZE for c in cards)
    assert caption.startswith("Bu indirim gerçek mi? CeraVe Krem 1")
    assert "Nisan'da 657 TL'ydi, bugün 397 TL." in caption
    assert "@cerave" not in caption and caption.endswith("#indirim")
