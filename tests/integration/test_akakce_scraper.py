from datetime import datetime
from pathlib import Path
from scrapers.akakce import extract_cards_from_page, AkakceScraper

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_extract_cards_returns_valid_products():
    html = (FIXTURES / "akakce_category_page.html").read_text(encoding="utf-8")
    snaps = extract_cards_from_page(html, category="parfum", captured_at=datetime(2026, 4, 18))
    assert len(snaps) == 2
    ids = {s.platform_product_id for s in snaps}
    assert ids == {"aaa111", "bbb222"}


def test_extract_cards_first_has_brand():
    html = (FIXTURES / "akakce_category_page.html").read_text(encoding="utf-8")
    snaps = extract_cards_from_page(html, category="parfum", captured_at=datetime(2026, 4, 18))
    chanel = next(s for s in snaps if s.platform_product_id == "aaa111")
    assert chanel.brand == "Chanel"
    assert chanel.price == 4999.0


def test_scraper_close_is_idempotent():
    scraper = AkakceScraper()
    scraper.close()  # browser açılmadı
    scraper.close()  # exception fırlatmamalı


def test_paginated_url_page_one_unchanged():
    scraper = AkakceScraper()
    url = scraper._paginated_url("https://www.akakce.com/parfum.html", 1)
    assert url == "https://www.akakce.com/parfum.html"


def test_paginated_url_adds_page_param():
    scraper = AkakceScraper()
    url = scraper._paginated_url("https://www.akakce.com/parfum.html", 3)
    # Akakçe sayfalama formatı: /parfum,3.html (Task 1'de canlı doğrulandı)
    assert url == "https://www.akakce.com/parfum,3.html"
