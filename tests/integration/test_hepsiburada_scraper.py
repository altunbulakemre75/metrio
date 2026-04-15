from datetime import datetime
from pathlib import Path
from scrapers.hepsiburada import extract_cards_from_page, HepsiburadaScraper

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_extract_cards_returns_all_products():
    html = (FIXTURES / "hepsiburada_category_page.html").read_text(encoding="utf-8")
    snaps = extract_cards_from_page(
        html, category="kozmetik", captured_at=datetime(2026, 4, 15)
    )
    assert len(snaps) == 3
    ids = {s.platform_product_id for s in snaps}
    assert ids == {"HBV000001AAA", "HBV000002BBB", "HBV000003CCC"}


def test_extract_cards_first_product_has_discount():
    html = (FIXTURES / "hepsiburada_category_page.html").read_text(encoding="utf-8")
    snaps = extract_cards_from_page(
        html, category="kozmetik", captured_at=datetime(2026, 4, 15)
    )
    first = next(s for s in snaps if s.platform_product_id == "HBV000001AAA")
    assert first.original_price == 189.90
    assert first.discount_rate is not None


def test_extract_cards_third_product_out_of_stock():
    html = (FIXTURES / "hepsiburada_category_page.html").read_text(encoding="utf-8")
    snaps = extract_cards_from_page(
        html, category="kozmetik", captured_at=datetime(2026, 4, 15)
    )
    third = next(s for s in snaps if s.platform_product_id == "HBV000003CCC")
    assert third.in_stock is False


def test_extract_cards_respects_max_products_limit():
    html = (FIXTURES / "hepsiburada_category_page.html").read_text(encoding="utf-8")
    snaps = extract_cards_from_page(
        html, category="kozmetik", captured_at=datetime(2026, 4, 15), max_products=2
    )
    assert len(snaps) == 2


def test_scraper_close_is_idempotent():
    scraper = HepsiburadaScraper()
    scraper.close()  # browser hiç açılmadı
    scraper.close()  # exception fırlatmamalı
