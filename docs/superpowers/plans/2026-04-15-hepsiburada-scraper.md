# Hepsiburada Scraper + Çoklu Kategori Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hepsiburada platformunu scraper mimarisine ekle; Trendyol ve Hepsiburada'da kozmetik + elektronik kategorilerini izle.

**Architecture:** Mevcut `BaseScraper` arayüzüne uyan `HepsiburadaScraper` eklenir. `main.py`'deki `_DEFAULT_CATEGORIES` 4 girişe genişler; `_make_scraper(platform)` helper'ı doğru scraper'ı seçer. `run_pipeline()` `platform` parametresi alır (geriye dönük uyumlu, default `"trendyol"`).

**Tech Stack:** Python 3.13, Playwright (Chromium headless), BeautifulSoup4 + lxml, pytest

---

## Dosya Haritası

| İşlem | Dosya | Ne yapıyor |
|-------|-------|------------|
| Oluştur | `tests/fixtures/hepsiburada_category_page.html` | Offline test için örnek HTML |
| Oluştur | `scrapers/hepsiburada.py` | `parse_product_card`, `extract_cards_from_page`, `HepsiburadaScraper` |
| Oluştur | `tests/unit/test_hepsiburada_parser.py` | Parse fonksiyonlarının unit testleri |
| Oluştur | `tests/integration/test_hepsiburada_scraper.py` | Fixture HTML ile integration testler |
| Değiştir | `main.py` | 4 kategori, `_make_scraper()`, `run_pipeline` platform param |

---

### Task 1: HTML Fixture

**Files:**
- Create: `tests/fixtures/hepsiburada_category_page.html`

- [ ] **Step 1: Fixture dosyasını oluştur**

```html
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="utf-8"><title>Kozmetik</title></head>
<body>
<ul data-test-id="product-list">
  <li data-test-id="product-card">
    <a href="/loreal-hyaluronic-asit-serum-HBV000001AAA">
      <img src="https://productimages.hepsiburada.net/s/1/u1.jpg" />
      <span data-test-id="brand">L'Oréal</span>
      <span data-test-id="product-name">Hyaluronic Asit Serum 30ml</span>
      <span data-test-id="original-price">189,90 TL</span>
      <span data-test-id="price">127,90 TL</span>
      <button data-test-id="add-to-cart">Sepete Ekle</button>
    </a>
  </li>
  <li data-test-id="product-card">
    <a href="/maybelline-fit-me-fondoten-HBV000002BBB">
      <img src="https://productimages.hepsiburada.net/s/2/u2.jpg" />
      <span data-test-id="brand">Maybelline</span>
      <span data-test-id="product-name">Fit Me Fondöten</span>
      <span data-test-id="price">199,00 TL</span>
      <button data-test-id="add-to-cart">Sepete Ekle</button>
    </a>
  </li>
  <li data-test-id="product-card">
    <a href="/nivea-nemlendirici-krem-HBV000003CCC">
      <img src="https://productimages.hepsiburada.net/s/3/u3.jpg" />
      <span data-test-id="brand">Nivea</span>
      <span data-test-id="product-name">Nemlendirici Krem 200ml</span>
      <span data-test-id="price">89,90 TL</span>
    </a>
  </li>
</ul>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add tests/fixtures/hepsiburada_category_page.html
git commit -m "test: add Hepsiburada category page HTML fixture"
```

---

### Task 2: Unit Testler (önce yaz, sonra implement et)

**Files:**
- Create: `tests/unit/test_hepsiburada_parser.py`
- Create: `scrapers/hepsiburada.py` (parse fonksiyonları)

- [ ] **Step 1: Failing testleri yaz**

`tests/unit/test_hepsiburada_parser.py` dosyasını oluştur:

```python
import pytest
from datetime import datetime
from scrapers.hepsiburada import parse_product_card, extract_cards_from_page
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures"
NOW = datetime(2026, 4, 15)


def _card(href, name, price, brand=None, original_price=None, in_stock=True, img_src=None):
    brand_span = f'<span data-test-id="brand">{brand}</span>' if brand else ""
    orig_span = f'<span data-test-id="original-price">{original_price}</span>' if original_price else ""
    cart_btn = '<button data-test-id="add-to-cart">Sepete Ekle</button>' if in_stock else ""
    img_tag = f'<img src="{img_src}" />' if img_src else ""
    return f"""
    <li data-test-id="product-card">
      <a href="{href}">
        {img_tag}{brand_span}
        <span data-test-id="product-name">{name}</span>
        {orig_span}
        <span data-test-id="price">{price}</span>
        {cart_btn}
      </a>
    </li>
    """


def test_parse_product_card_basic_fields():
    html = _card(
        "/loreal-serum-HBV000001AAA", "Serum 30ml", "127,90 TL",
        brand="L'Oréal", img_src="https://cdn.hb.net/u1.jpg"
    )
    snap = parse_product_card(html, category="kozmetik", captured_at=NOW)
    assert snap is not None
    assert snap.platform == "hepsiburada"
    assert snap.platform_product_id == "HBV000001AAA"
    assert snap.name == "Serum 30ml"
    assert snap.brand == "L'Oréal"
    assert snap.price == 127.90
    assert snap.category == "kozmetik"
    assert snap.product_url == "https://www.hepsiburada.com/loreal-serum-HBV000001AAA"
    assert snap.image_url == "https://cdn.hb.net/u1.jpg"
    assert snap.in_stock is True
    assert snap.seller_name is None
    assert snap.seller_rating is None


def test_parse_product_card_with_discount():
    html = _card(
        "/urun-HBV000002BBB", "Fondöten", "127,90 TL",
        original_price="189,90 TL"
    )
    snap = parse_product_card(html, category="kozmetik", captured_at=NOW)
    assert snap is not None
    assert snap.original_price == pytest.approx(189.90)
    assert snap.discount_rate == pytest.approx((189.90 - 127.90) / 189.90, rel=0.01)


def test_parse_product_card_out_of_stock():
    html = _card("/urun-HBV000003CCC", "Krem 200ml", "89,90 TL", in_stock=False)
    snap = parse_product_card(html, category="kozmetik", captured_at=NOW)
    assert snap is not None
    assert snap.in_stock is False


def test_parse_product_card_missing_price_returns_none():
    html = """
    <li data-test-id="product-card">
      <a href="/urun-HBV000004DDD">
        <span data-test-id="product-name">Ürün</span>
      </a>
    </li>
    """
    assert parse_product_card(html, category="kozmetik", captured_at=NOW) is None


def test_parse_product_card_no_card_element_returns_none():
    assert parse_product_card("<div>boş sayfa</div>", category="kozmetik", captured_at=NOW) is None


def test_parse_product_card_no_link_returns_none():
    html = """
    <li data-test-id="product-card">
      <span data-test-id="product-name">Ürün</span>
      <span data-test-id="price">99,90 TL</span>
    </li>
    """
    assert parse_product_card(html, category="kozmetik", captured_at=NOW) is None


def test_extract_cards_from_fixture_returns_all():
    html = (FIXTURES / "hepsiburada_category_page.html").read_text(encoding="utf-8")
    snaps = extract_cards_from_page(html, category="kozmetik", captured_at=NOW)
    assert len(snaps) == 3


def test_extract_cards_respects_max_products():
    html = (FIXTURES / "hepsiburada_category_page.html").read_text(encoding="utf-8")
    snaps = extract_cards_from_page(html, category="kozmetik", captured_at=NOW, max_products=2)
    assert len(snaps) == 2


def test_extract_cards_skips_unparseable():
    html = """
    <ul>
      <li data-test-id="product-card">
        <a href="/urun-HBV000001AAA">
          <span data-test-id="product-name">İyi Ürün</span>
          <span data-test-id="price">99,90 TL</span>
          <button data-test-id="add-to-cart">Sepete Ekle</button>
        </a>
      </li>
      <li data-test-id="product-card">
        <a href="/urun-HBV000002BBB">
          <span data-test-id="product-name">Fiyatsız Ürün</span>
        </a>
      </li>
    </ul>
    """
    snaps = extract_cards_from_page(html, category="kozmetik", captured_at=NOW)
    assert len(snaps) == 1
```

- [ ] **Step 2: Testlerin fail ettiğini doğrula**

```
pytest tests/unit/test_hepsiburada_parser.py -v
```

Beklenen: `ModuleNotFoundError: No module named 'scrapers.hepsiburada'`

- [ ] **Step 3: `scrapers/hepsiburada.py` oluştur (parse fonksiyonları)**

```python
import re
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Page, Browser

from config import settings
from scrapers.base import BaseScraper
from scrapers.trendyol import parse_price_text, parse_discount_rate
from storage.models import ProductSnapshot
from utils.logger import get_logger
from utils.rate_limiter import rate_limit
from utils.retry import retry

_BASE_URL = "https://www.hepsiburada.com"
_CARD_SELECTOR = "li[data-test-id='product-card']"
_HBV_PATTERN = re.compile(r"HBV\w+")

log = get_logger("hepsiburada")


def _extract_product_id(href: str) -> str | None:
    """HBV kodu varsa çıkar, yoksa son path segment'i döner."""
    match = _HBV_PATTERN.search(href)
    if match:
        return match.group()
    segments = [s for s in href.split("/") if s]
    return segments[-1] if segments else None


def parse_product_card(
    html: str,
    category: str,
    captured_at: datetime,
) -> ProductSnapshot | None:
    """Tek bir ürün kartı HTML'ini ProductSnapshot'a çevirir.

    Selector şeması Hepsiburada'ya özel (2026 yapısı).
    Parse edilemeyen kartlar için None döner.
    """
    soup = BeautifulSoup(html, "lxml")
    card = soup.select_one(_CARD_SELECTOR)
    if card is None:
        return None

    link = card.select_one("a[href]")
    if link is None:
        return None

    href = link.get("href", "")
    product_id = _extract_product_id(href)
    if not product_id:
        return None

    product_url = href if href.startswith("http") else f"{_BASE_URL}{href}"

    name_el = card.select_one("[data-test-id='product-name']")
    brand_el = card.select_one("[data-test-id='brand']")
    price_el = (
        card.select_one("[data-test-id='price']")
        or card.select_one("[class*='price']")
    )
    original_price_el = (
        card.select_one("[data-test-id='original-price']")
        or card.select_one("[class*='original']")
    )
    img_el = card.select_one("img")

    if name_el is None or price_el is None:
        return None

    price = parse_price_text(price_el.get_text())
    if price is None:
        return None

    original_price = parse_price_text(original_price_el.get_text()) if original_price_el else None
    discount_rate = parse_discount_rate(original_price, price)
    in_stock = card.select_one("[data-test-id='add-to-cart']") is not None

    return ProductSnapshot(
        platform="hepsiburada",
        platform_product_id=product_id,
        name=name_el.get_text(strip=True),
        brand=brand_el.get_text(strip=True) if brand_el else None,
        category=category,
        product_url=product_url,
        image_url=img_el.get("src") if img_el else None,
        price=price,
        original_price=original_price,
        discount_rate=discount_rate,
        seller_name=None,
        seller_rating=None,
        in_stock=in_stock,
        captured_at=captured_at,
    )


def extract_cards_from_page(
    html: str,
    category: str,
    captured_at: datetime,
    max_products: int | None = None,
) -> list[ProductSnapshot]:
    """Tam kategori sayfasından ürün kartlarını parse eder.

    Parse edilemeyen kartları atlar (logla, devam et).
    """
    soup = BeautifulSoup(html, "lxml")
    cards = soup.select(_CARD_SELECTOR)
    snapshots: list[ProductSnapshot] = []

    for card in cards:
        if max_products is not None and len(snapshots) >= max_products:
            break
        snap = parse_product_card(str(card), category=category, captured_at=captured_at)
        if snap is None:
            log.warning("Kart parse edilemedi, atlandı")
            continue
        snapshots.append(snap)

    return snapshots
```

- [ ] **Step 4: Unit testlerin geçtiğini doğrula**

```
pytest tests/unit/test_hepsiburada_parser.py -v
```

Beklenen: 9 test PASS

- [ ] **Step 5: Commit**

```bash
git add scrapers/hepsiburada.py tests/unit/test_hepsiburada_parser.py
git commit -m "feat: add Hepsiburada parse functions with unit tests"
```

---

### Task 3: HepsiburadaScraper Sınıfı + Integration Testler

**Files:**
- Modify: `scrapers/hepsiburada.py` (sınıfı ekle)
- Create: `tests/integration/test_hepsiburada_scraper.py`

- [ ] **Step 1: Failing integration testleri yaz**

`tests/integration/test_hepsiburada_scraper.py` dosyasını oluştur:

```python
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
```

- [ ] **Step 2: Testlerin fail ettiğini doğrula**

```
pytest tests/integration/test_hepsiburada_scraper.py -v
```

Beklenen: `ImportError: cannot import name 'HepsiburadaScraper'`

- [ ] **Step 3: `HepsiburadaScraper` sınıfını `scrapers/hepsiburada.py`'e ekle**

`extract_cards_from_page` fonksiyonunun hemen altına ekle:

```python
class HepsiburadaScraper(BaseScraper):
    """Playwright ile Hepsiburada kategori sayfalarını çeker."""

    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None

    def _ensure_browser(self) -> Browser:
        if self._browser is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=settings.scraper_headless,
            )
        return self._browser

    @rate_limit(calls_per_second=settings.scraper_requests_per_second)
    @retry(max_attempts=3, backoff_base=2, exceptions=(Exception,))
    def _load_page(self, page: Page, url: str) -> str:
        log.info(f"Sayfa yükleniyor: {url}")
        page.goto(url, wait_until="networkidle", timeout=45000)
        self._scroll_to_load(page)
        return page.content()

    def _scroll_to_load(self, page: Page, max_scrolls: int = 10) -> None:
        """Infinite scroll sayfasında aşağı in, daha fazla ürün yüklet."""
        for _ in range(max_scrolls):
            previous_height = page.evaluate("document.body.scrollHeight")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == previous_height:
                break

    def fetch_category(
        self,
        category_url: str,
        max_products: int = 500,
    ) -> list[ProductSnapshot]:
        browser = self._ensure_browser()
        context = browser.new_context(user_agent=settings.scraper_user_agent)
        page = context.new_page()
        try:
            html = self._load_page(page, category_url)
            captured_at = datetime.now()
            snapshots = extract_cards_from_page(
                html,
                category=self._infer_category_from_url(category_url),
                captured_at=captured_at,
                max_products=max_products,
            )
            log.info(f"{len(snapshots)} ürün çekildi")
            return snapshots
        finally:
            context.close()

    def _infer_category_from_url(self, url: str) -> str:
        url_lower = url.lower()
        known = ["kozmetik", "elektronik", "giyim", "ev-yasam", "kitap"]
        for k in known:
            if k in url_lower:
                return k
        return "unknown"

    def close(self) -> None:
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
```

- [ ] **Step 4: Integration testlerin geçtiğini doğrula**

```
pytest tests/integration/test_hepsiburada_scraper.py -v
```

Beklenen: 5 test PASS

- [ ] **Step 5: Commit**

```bash
git add scrapers/hepsiburada.py tests/integration/test_hepsiburada_scraper.py
git commit -m "feat: add HepsiburadaScraper class with integration tests"
```

---

### Task 4: main.py Güncelleme

**Files:**
- Modify: `main.py`

- [ ] **Step 1: `run_pipeline` imzasına `platform` parametresi ekle**

`main.py` dosyasındaki `run_pipeline` fonksiyonunu bul. İmzayı şu şekilde değiştir (sadece `platform: str = "trendyol"` parametresini ekle ve `start_run` çağrısındaki hardcoded `"trendyol"` stringini değiştir):

```python
def run_pipeline(
    scraper: BaseScraper,
    category_url: str,
    category_name: str,
    max_products: int = 500,
    platform: str = "trendyol",          # <-- yeni parametre
) -> dict:
    """Tek bir kategori için uçtan uca çalışır. run_stats sözlüğü döner."""
    run_id = f"{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}"
    started_at = datetime.now()
    conn = connect(settings.database_path)
    init_schema(conn)

    start_run(conn, run_id=run_id, platform=platform, category=category_name, started_at=started_at)
    # ... geri kalan kod değişmez
```

- [ ] **Step 2: Mevcut testlerin hâlâ geçtiğini doğrula (geriye dönük uyumluluk)**

```
pytest tests/integration/test_main_pipeline.py -v
```

Beklenen: 4 test PASS (hiç değişiklik yok, default `platform="trendyol"` çalışıyor)

- [ ] **Step 3: Import ve `_DEFAULT_CATEGORIES` güncelle**

`main.py` dosyasının en üstündeki import bloğunu güncelle — `HepsiburadaScraper` import'unu ekle:

```python
from scrapers.hepsiburada import HepsiburadaScraper
from scrapers.trendyol import TrendyolScraper
```

`_DEFAULT_CATEGORIES` listesini şu şekilde değiştir:

```python
_DEFAULT_CATEGORIES = [
    {
        "platform": "trendyol",
        "name": "kozmetik",
        "url": "https://www.trendyol.com/kozmetik-x-c89",
    },
    {
        "platform": "trendyol",
        "name": "elektronik",
        "url": "https://www.trendyol.com/elektronik-x-c1",
    },
    {
        "platform": "hepsiburada",
        "name": "kozmetik",
        "url": "https://www.hepsiburada.com/kozmetik-c-14003",
    },
    {
        "platform": "hepsiburada",
        "name": "elektronik",
        "url": "https://www.hepsiburada.com/elektronik-c-14002",
    },
]
```

- [ ] **Step 4: `_make_scraper` helper ekle ve `main()` güncelle**

`_DEFAULT_CATEGORIES` tanımının hemen altına ekle:

```python
def _make_scraper(platform: str) -> BaseScraper:
    if platform == "hepsiburada":
        return HepsiburadaScraper()
    return TrendyolScraper()
```

`main()` fonksiyonu içindeki for döngüsünü güncelle — `TrendyolScraper()` yerine `_make_scraper` kullan ve `platform` parametresini `run_pipeline`'a geç:

```python
def main() -> int:
    overall_status = 0
    all_stats = []
    for cat in _DEFAULT_CATEGORIES:
        scraper = _make_scraper(cat["platform"])
        stats = run_pipeline(
            scraper=scraper,
            category_url=cat["url"],
            category_name=cat["name"],
            max_products=settings.scraper_max_products,
            platform=cat["platform"],
        )
        all_stats.append(stats)
        if stats["status"] == "failed":
            overall_status = 1

    try:
        conn = connect(settings.database_path)
        init_schema(conn)
        anomalies = detect_anomalies(conn, threshold_percent=settings.telegram_threshold)
        combined_stats = _combine_stats(all_stats)
        notifier = TelegramNotifier(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
            enabled=settings.telegram_enabled,
        )
        notifier.notify_run(combined_stats, anomalies)
    except Exception as e:
        log.warning(f"Telegram bildirimi başarısız: {e}")

    return overall_status
```

- [ ] **Step 5: Tüm pipeline testlerini çalıştır**

```
pytest tests/integration/test_main_pipeline.py tests/unit/ -v
```

Beklenen: Tüm testler PASS

- [ ] **Step 6: Commit**

```bash
git add main.py
git commit -m "feat: add Hepsiburada + elektronik categories to pipeline"
```

---

### Task 5: Tam Test Süiti + Final Commit

**Files:**
- Yok (sadece doğrulama)

- [ ] **Step 1: Tüm testleri çalıştır**

```
pytest --tb=short -q
```

Beklenen: Tüm testler PASS, en az 120 test (önceki 106 + 14 yeni)

- [ ] **Step 2: Eğer test sayısı beklenenden azsa, hangi testlerin eksik olduğunu bul**

```
pytest --collect-only -q 2>&1 | tail -5
```

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: Hepsiburada scraper + multi-category pipeline complete"
```

---

## Self-Review Notları

**Spec coverage:**
- [x] `scrapers/hepsiburada.py` → Task 2 + 3
- [x] `main.py` 4 kategori → Task 4 Step 3
- [x] `_make_scraper()` → Task 4 Step 4
- [x] Unit testler → Task 2
- [x] Integration testler → Task 3
- [x] `platform` param fix → Task 4 Step 1
- [x] Bir platform çökerse diğeri devam eder → mevcut `run_pipeline` davranışı, değişmedi

**Tip tutarlılığı:**
- `parse_product_card(html: str, category: str, captured_at: datetime)` — Task 2'den Task 3'e tutarlı
- `extract_cards_from_page` imzası Task 2 ve Task 3 boyunca aynı
- `HepsiburadaScraper` her yerde aynı isim, `BaseScraper` inherit ediyor

**Placeholder yok:** Tüm adımlarda gerçek kod mevcut.
