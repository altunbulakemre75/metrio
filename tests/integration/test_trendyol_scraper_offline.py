from datetime import datetime
from pathlib import Path
from scrapers.trendyol import extract_cards_from_page


FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_extract_cards_returns_all_products():
    html = (FIXTURES / "trendyol_category_page.html").read_text(encoding="utf-8")
    snaps = extract_cards_from_page(html, category="kozmetik", captured_at=datetime(2026, 4, 14))
    assert len(snaps) == 3
    ids = {s.platform_product_id for s in snaps}
    assert ids == {"111", "222", "333"}


def test_extract_cards_respects_max_products_limit():
    html = (FIXTURES / "trendyol_category_page.html").read_text(encoding="utf-8")
    snaps = extract_cards_from_page(
        html, category="kozmetik", captured_at=datetime(2026, 4, 14), max_products=2,
    )
    assert len(snaps) == 2


def test_extract_cards_skips_unparseable():
    html = """
    <div class="search-result-products">
      <a class="product-card" id="111" href="/u-p-111">
        <span class="product-name">Iyi Urun</span>
        <div class="price-section">99,90 TL</div>
      </a>
      <a class="product-card"><!-- id eksik --></a>
      <a class="product-card" id="333" href="/u-p-333">
        <span class="product-name">Diger Urun</span>
        <div class="price-section">149,50 TL</div>
      </a>
    </div>
    """
    snaps = extract_cards_from_page(html, category="kozmetik", captured_at=datetime(2026, 4, 14))
    assert len(snaps) == 2
