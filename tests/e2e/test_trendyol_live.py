import pytest
from scrapers.trendyol import TrendyolScraper


TRENDYOL_KOZMETIK_URL = "https://www.trendyol.com/kozmetik-x-c89"


@pytest.mark.e2e
def test_trendyol_scraper_fetches_real_products():
    """Gerçek Trendyol'a bağlanır, 5 ürün çeker.

    Selector değişikliklerini erken tespit etmek için haftada 1 çalıştır.
    """
    scraper = TrendyolScraper()
    try:
        snapshots = scraper.fetch_category(TRENDYOL_KOZMETIK_URL, max_products=5)
    finally:
        scraper.close()

    assert len(snapshots) >= 3, f"En az 3 ürün beklendi, {len(snapshots)} bulundu"

    for snap in snapshots:
        assert snap.platform == "trendyol"
        assert snap.platform_product_id
        assert snap.name
        assert snap.price > 0
        assert snap.product_url.startswith("https://www.trendyol.com/")
