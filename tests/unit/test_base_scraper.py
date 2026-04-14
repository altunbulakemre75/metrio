import pytest
from scrapers.base import BaseScraper


def test_base_scraper_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BaseScraper()


def test_concrete_subclass_can_be_instantiated():
    class DummyScraper(BaseScraper):
        def fetch_category(self, category_url, max_products=500):
            return []

        def close(self):
            pass

    scraper = DummyScraper()
    assert scraper.fetch_category("https://example.com") == []


def test_subclass_missing_fetch_category_fails():
    class BadScraper(BaseScraper):
        def close(self):
            pass

    with pytest.raises(TypeError):
        BadScraper()
