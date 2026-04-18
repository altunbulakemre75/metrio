# Akakçe Aggregator Scraper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Akakçe kategori sayfalarından ürün + en düşük fiyat scraping. Mevcut `BaseScraper` arayüzü ile entegre, Trendyol'un sayfalama + hata tolerans pattern'i kopyalanır.

**Architecture:** `scrapers/akakce.py` yeni — parse fonksiyonları + `AkakceScraper` sınıfı. `main.py` 3 akakce kategorisi ekler. Veri modeli `ProductSnapshot` aynen (`platform="akakce"`). Akakçe'nin gerçek HTML selektörleri Task 1'de canlı sayfa ile doğrulanır; sonraki task'lar bunu baz alır.

**Tech Stack:** Python 3.13, Playwright (Chromium headless), BeautifulSoup4 + lxml, pytest

---

## Dosya Haritası

| İşlem | Dosya | Ne yapıyor |
|-------|-------|------------|
| Oluştur | `tests/fixtures/akakce_category_page.html` | 3-ürünlü minimal fixture |
| Oluştur | `scrapers/akakce.py` | `parse_product_card`, `extract_cards_from_page`, `AkakceScraper` |
| Oluştur | `tests/unit/test_akakce_parser.py` | Parse unit testleri (8 test) |
| Oluştur | `tests/integration/test_akakce_scraper.py` | Fixture tabanlı entegrasyon (3 test) |
| Değiştir | `main.py` | `_DEFAULT_CATEGORIES`'e 3 girişi + `_make_scraper` akakce dalı |

Yeni bağımlılık yok.

---

### Task 1: Canlı Akakçe sayfasını keşfet + fixture oluştur

**Files:**
- Create: `tests/fixtures/akakce_category_page.html`

Bu task kod yazmak yerine Akakçe'nin HTML yapısını keşfetmek için. Sonraki task'ların tüm selektörleri bu çıkarımdan gelir.

- [ ] **Step 1: Akakçe parfüm kategorisini canlıda çek ve selektörleri tespit et**

Run:
```bash
cd "c:\Users\altun\Desktop\Yeni klasör\verimadenciligi"
python -c "
import sys; sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from config import settings
import re

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(user_agent=settings.scraper_user_agent)
    page = ctx.new_page()
    page.goto('https://www.akakce.com/parfum.html', wait_until='networkidle', timeout=45000)
    page.wait_for_timeout(2000)
    html = page.content()
    with open('/tmp/akakce_sample.html', 'w', encoding='utf-8') as f:
        pass  # Git bash için — yerine pathlib kullan
    import pathlib
    pathlib.Path('akakce_sample.html').write_text(html, encoding='utf-8')
    print('Length:', len(html))
    m = re.search(r'<title>([^<]+)</title>', html)
    print('Title found:', bool(m))
    soup = BeautifulSoup(html, 'lxml')
    # Yaygın selektör adaylarını tara
    for sel in ['li.w', 'a.pw_v8', 'div.pri', 'span.pt_v8', 'h3', '[data-ph]', 'li[data-id]', 'li.p', 'a.pu']:
        n = len(soup.select(sel))
        print(f'  {sel!r}: {n}')
    browser.close()
"
```

Expected: `akakce_sample.html` dosyası projenin kökünde oluşur (~500KB-1MB), title var, en az bir selektörde 20+ eşleşme olmalı.

**Eğer Akakçe bot engeli döndürürse** (title yok, çok küçük HTML): kategori URL'lerini `https://www.akakce.com/parfum.html` yerine spesifik alt kategori deneyin (örn. `https://www.akakce.com/kadin-parfum.html`). Gerekirse `scraper_user_agent`'ı değiştir.

- [ ] **Step 2: Sample HTML'den ürün kartı selektörlerini tespit et**

Run:
```bash
python -c "
import sys; sys.stdout.reconfigure(encoding='utf-8')
from bs4 import BeautifulSoup
html = open('akakce_sample.html', encoding='utf-8').read()
soup = BeautifulSoup(html, 'lxml')
# Ürün kartının muhtemel yapısı: 'li' içinde 'a.pw_v8', fiyat 'span.pt_v8', isim 'h3' veya 'span.pn_v8'
# Gerçek selektörü Step 1 çıktısından belirle, burada en çok eşleşen kartın HTML'ini bas
cards = soup.select('li')
for c in cards[:3]:
    print('=== CARD ===')
    print(str(c)[:600])
    print()
"
```

Expected: 3 ürün kartının ham HTML'i. Bu çıktıdan aşağıdaki alanların CSS path'lerini not al:
- Kart kök elementi (genelde `<li>` veya `<a>`)
- Ürün başlığı (muhtemelen `<h3>` veya `<span class="pn_v8">`)
- Fiyat (muhtemelen `<span class="pt_v8">` veya `class="pri">`)
- Ürün URL'i (kök `<a>` href'i)
- Resim URL'i (`<img src="...">`)
- Ürün ID'si (href'teki slug veya `data-id` attribute)

Bu adım tamamlandığında elinde şu değişkenler olmalı:
- `_CARD_SELECTOR = "..."` (ör: `"li.w"` veya `"li[data-id]"`)
- İsim selektörü
- Fiyat selektörü
- Resim selektörü

**Not for implementer:** Akakçe'nin CSS class isimleri hash'lenmiş olabilir (değişiyor). Semantic selektörler (data-id, h3, img) öncelikli, class selektörleri fallback.

- [ ] **Step 3: `tests/fixtures/akakce_category_page.html` dosyasını oluştur**

Step 2'de tespit ettiğin gerçek selektörlere dayanarak minimal fixture yaz. 3 kart:

```html
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="utf-8"><title>Parfüm Fiyatları — Akakçe</title></head>
<body>
<ul id="APL" class="lst">
  <li class="w" data-id="aaa111">
    <a class="pw_v8" href="/parfum/en-ucuz-chanel-no-5-100ml.html">
      <img src="https://cdn.akakce.com/thumbnail/aaa.jpg" alt="Chanel No 5">
      <h3 class="pn_v8"><b>Chanel</b> No 5 EDP 100 ml Kadın Parfüm</h3>
      <span class="pt_v8">4.999 TL</span>
    </a>
  </li>
  <li class="w" data-id="bbb222">
    <a class="pw_v8" href="/parfum/en-ucuz-dior-sauvage-100ml.html">
      <img src="https://cdn.akakce.com/thumbnail/bbb.jpg" alt="Dior Sauvage">
      <h3 class="pn_v8">Dior Sauvage EDT 100 ml Erkek Parfüm</h3>
      <span class="pt_v8">3.499 TL</span>
    </a>
  </li>
  <li class="w" data-id="ccc333">
    <a class="pw_v8" href="/parfum/en-ucuz-bozuk-urun.html">
      <h3 class="pn_v8"><b>Bozuk</b> Ürün</h3>
      <!-- fiyat yok: parse None dönmeli -->
    </a>
  </li>
</ul>
</body>
</html>
```

**Önemli:** Eğer Step 2'de tespit ettiğin selektörler yukarıdaki class adlarından farklıysa (örn. `pw_v8` yerine `pa_v2`), **fixture'ı da aynı şekilde güncelle**. Fixture, gerçek sayfanın minimal yansıması olmalı.

Implementer, Step 2'deki gerçek selektörleri Task 2'nin parser kodunda da kullanacağı için `_CARD_SELECTOR`, ad/fiyat/resim selektörlerini not defterinde tut.

- [ ] **Step 4: Sample HTML'i sil, fixture'ı commit et**

```bash
rm akakce_sample.html
git add tests/fixtures/akakce_category_page.html
git commit -m "test: add Akakçe category page HTML fixture"
```

---

### Task 2: Parse fonksiyonları + unit testler (TDD)

**Files:**
- Create: `tests/unit/test_akakce_parser.py`
- Create: `scrapers/akakce.py`

- [ ] **Step 1: `tests/unit/test_akakce_parser.py` dosyasını oluştur**

```python
import pytest
from datetime import datetime
from pathlib import Path
from scrapers.akakce import parse_product_card, extract_cards_from_page

FIXTURES = Path(__file__).parent.parent / "fixtures"
NOW = datetime(2026, 4, 18, 15, 0)


def _card(href, name, price_text, brand=None, img_src=None, data_id="x"):
    """Test helper — tek bir kart için minimal HTML üretir."""
    brand_tag = f"<b>{brand}</b> " if brand else ""
    price_tag = f'<span class="pt_v8">{price_text}</span>' if price_text else ""
    img_tag = f'<img src="{img_src}" alt="{name}">' if img_src else ""
    return f"""
    <li class="w" data-id="{data_id}">
      <a class="pw_v8" href="{href}">
        {img_tag}
        <h3 class="pn_v8">{brand_tag}{name}</h3>
        {price_tag}
      </a>
    </li>
    """


def test_parse_product_card_basic():
    html = _card(
        "/parfum/en-ucuz-urun-xyz.html",
        "Chanel No 5 EDP 100 ml",
        "4.999 TL",
        brand="Chanel",
        img_src="https://cdn.akakce.com/a.jpg",
        data_id="aaa111",
    )
    snap = parse_product_card(html, category="parfum", captured_at=NOW)
    assert snap is not None
    assert snap.platform == "akakce"
    assert snap.platform_product_id == "aaa111"
    assert snap.price == 4999.0
    assert snap.category == "parfum"
    assert snap.product_url == "https://www.akakce.com/parfum/en-ucuz-urun-xyz.html"
    assert snap.image_url == "https://cdn.akakce.com/a.jpg"
    assert snap.in_stock is True
    assert snap.seller_name is None
    assert snap.seller_rating is None
    assert "Chanel No 5" in snap.name or snap.name == "Chanel No 5 EDP 100 ml"


def test_parse_product_card_brand_extracted():
    html = _card(
        "/parfum/x.html", "No 5 EDP 100 ml", "4.999 TL",
        brand="Chanel", data_id="a",
    )
    snap = parse_product_card(html, category="parfum", captured_at=NOW)
    assert snap.brand == "Chanel"


def test_parse_product_card_no_brand():
    html = _card("/parfum/x.html", "Jenerik Ürün", "1.299 TL", brand=None, data_id="a")
    snap = parse_product_card(html, category="parfum", captured_at=NOW)
    assert snap is not None
    assert snap.brand is None


def test_parse_product_card_no_image():
    html = _card("/parfum/x.html", "Ürün", "99 TL", img_src=None, data_id="a")
    snap = parse_product_card(html, category="parfum", captured_at=NOW)
    assert snap.image_url is None


def test_parse_product_card_missing_price_returns_none():
    html = _card("/parfum/x.html", "Fiyatsız Ürün", price_text=None, data_id="a")
    assert parse_product_card(html, category="parfum", captured_at=NOW) is None


def test_parse_product_card_no_card_element_returns_none():
    assert parse_product_card("<div>boş</div>", category="parfum", captured_at=NOW) is None


def test_parse_product_card_absolute_url_preserved():
    html = _card(
        "https://www.akakce.com/parfum/x.html", "Ürün", "100 TL",
        data_id="a",
    )
    snap = parse_product_card(html, category="parfum", captured_at=NOW)
    assert snap.product_url == "https://www.akakce.com/parfum/x.html"


def test_extract_cards_from_fixture_returns_all_valid():
    html = (FIXTURES / "akakce_category_page.html").read_text(encoding="utf-8")
    snaps = extract_cards_from_page(html, category="parfum", captured_at=NOW)
    # Fixture 3 kart içerir, 3. kart fiyatsız → None → atlanır → 2 snap beklenir
    assert len(snaps) == 2
    ids = {s.platform_product_id for s in snaps}
    assert ids == {"aaa111", "bbb222"}


def test_extract_cards_respects_max_products():
    html = (FIXTURES / "akakce_category_page.html").read_text(encoding="utf-8")
    snaps = extract_cards_from_page(html, category="parfum", captured_at=NOW, max_products=1)
    assert len(snaps) == 1
```

- [ ] **Step 2: Testlerin fail ettiğini doğrula**

Run: `python -m pytest tests/unit/test_akakce_parser.py -v`
Expected: `ModuleNotFoundError: No module named 'scrapers.akakce'`

- [ ] **Step 3: `scrapers/akakce.py` dosyasını oluştur**

```python
import re
from datetime import datetime
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from scrapers.trendyol import parse_price_text
from storage.models import ProductSnapshot
from utils.logger import get_logger

_BASE_URL = "https://www.akakce.com"
# NOT: Task 1'de canlı sayfadan tespit edilen selektörler. Akakçe HTML'i değişirse burası güncellenir.
_CARD_SELECTOR = "li[data-id]"
_NAME_SELECTOR = "h3"
_PRICE_SELECTOR = ".pt_v8, span.pt_v8, [class*='pt_']"
_LINK_SELECTOR = "a[href]"
_IMG_SELECTOR = "img"
_BRAND_TAG = "b"  # Akakçe'de marka h3 içinde <b>Marka</b> Ürün adı şeklinde

log = get_logger("akakce")


def _extract_product_id(card) -> str | None:
    """data-id attribute veya href'ten slug."""
    data_id = card.get("data-id")
    if data_id:
        return data_id
    link = card.select_one(_LINK_SELECTOR)
    if link:
        href = link.get("href", "")
        segments = [s for s in href.rstrip("/").split("/") if s]
        if segments:
            return segments[-1].replace(".html", "")
    return None


def _extract_name_and_brand(card) -> tuple[str | None, str | None]:
    """h3 içinden marka (<b>) ve ürün adını çıkarır."""
    name_el = card.select_one(_NAME_SELECTOR)
    if name_el is None:
        return None, None
    brand_el = name_el.find(_BRAND_TAG)
    brand = brand_el.get_text(strip=True) if brand_el else None
    # Tüm h3 metni — marka dahil ama temizlenmiş
    full_name = name_el.get_text(" ", strip=True)
    return full_name, brand


def parse_product_card(
    html: str,
    category: str,
    captured_at: datetime,
) -> ProductSnapshot | None:
    """Tek bir Akakçe ürün kartı HTML'ini ProductSnapshot'a çevirir.

    Parse edilemeyen kartlar için None döner.
    """
    soup = BeautifulSoup(html, "lxml")
    card = soup.select_one(_CARD_SELECTOR)
    if card is None:
        return None

    product_id = _extract_product_id(card)
    if not product_id:
        return None

    link = card.select_one(_LINK_SELECTOR)
    if link is None:
        return None

    href = link.get("href", "")
    product_url = href if href.startswith("http") else f"{_BASE_URL}{href}"

    price_el = card.select_one(_PRICE_SELECTOR)
    if price_el is None:
        return None
    price = parse_price_text(price_el.get_text())
    if price is None:
        return None

    name, brand = _extract_name_and_brand(card)
    if name is None:
        return None

    img_el = card.select_one(_IMG_SELECTOR)
    image_url = img_el.get("src") if img_el else None

    return ProductSnapshot(
        platform="akakce",
        platform_product_id=product_id,
        name=name,
        brand=brand,
        category=category,
        product_url=product_url,
        image_url=image_url,
        price=price,
        original_price=None,
        discount_rate=None,
        seller_name=None,
        seller_rating=None,
        in_stock=True,
        captured_at=captured_at,
    )


def extract_cards_from_page(
    html: str,
    category: str,
    captured_at: datetime,
    max_products: int | None = None,
) -> list[ProductSnapshot]:
    """Kategori sayfasından ürün kartlarını parse eder.

    Parse edilemeyen kartları atlar (log WARNING).
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

Run: `python -m pytest tests/unit/test_akakce_parser.py -v`
Expected: 9 test PASS

- [ ] **Step 5: Commit**

```bash
git add scrapers/akakce.py tests/unit/test_akakce_parser.py
git commit -m "feat: add Akakçe parse functions with unit tests"
```

---

### Task 3: `AkakceScraper` sınıfı + entegrasyon testleri (TDD)

**Files:**
- Modify: `scrapers/akakce.py` (sınıfı ekle)
- Create: `tests/integration/test_akakce_scraper.py`

- [ ] **Step 1: `tests/integration/test_akakce_scraper.py` oluştur**

```python
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
    # Akakçe sayfalama formatı: ?page=3 (Task 1'de canlı doğrulanır)
    assert "page=3" in url or "pg=3" in url
```

- [ ] **Step 2: Testin fail ettiğini doğrula**

Run: `python -m pytest tests/integration/test_akakce_scraper.py -v`
Expected: `ImportError: cannot import name 'AkakceScraper'`

- [ ] **Step 3: `AkakceScraper` sınıfını `scrapers/akakce.py` sonuna ekle**

Dosyanın en sonuna (extract_cards_from_page altına) ekle:

```python
from playwright.sync_api import sync_playwright, Page, Browser

from config import settings
from utils.fingerprint import get_fingerprint
from utils.proxy_pool import ProxyPool
from utils.rate_limiter import jitter_delay
from utils.retry import retry


class AkakceScraper(BaseScraper):
    """Playwright ile Akakçe kategori sayfalarını çeker."""

    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None
        self._proxy_pool = ProxyPool(settings.proxy_list, settings.proxy_enabled)

    def _ensure_browser(self) -> Browser:
        if self._browser is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=settings.scraper_headless,
            )
        return self._browser

    @jitter_delay(settings.scraper_min_delay, settings.scraper_max_delay)
    @retry(max_attempts=3, backoff_base=2, exceptions=(Exception,))
    def _load_page(self, page: Page, url: str) -> str:
        log.info(f"Sayfa yükleniyor: {url}")
        page.goto(url, wait_until="networkidle", timeout=45000)
        return page.content()

    def _paginated_url(self, base_url: str, page_num: int) -> str:
        """Akakçe sayfalama: ?page=N."""
        if page_num == 1:
            return base_url
        separator = "&" if "?" in base_url else "?"
        return f"{base_url}{separator}page={page_num}"

    def fetch_category(
        self,
        category_url: str,
        max_products: int = 500,
    ) -> list[ProductSnapshot]:
        browser = self._ensure_browser()
        fp = get_fingerprint()
        ctx_args = {
            "user_agent": fp["user_agent"],
            "viewport": fp["viewport"],
            "locale": fp["locale"],
        }
        proxy = self._proxy_pool.pick()
        if proxy:
            ctx_args["proxy"] = proxy
        context = browser.new_context(**ctx_args)
        page = context.new_page()
        try:
            captured_at = datetime.now()
            category = self._infer_category_from_url(category_url)
            all_snaps: list[ProductSnapshot] = []
            seen_ids: set[str] = set()

            for page_num in range(1, 26):  # max 25 sayfa
                if len(all_snaps) >= max_products:
                    break
                url = self._paginated_url(category_url, page_num)
                try:
                    html = self._load_page(page, url)
                except Exception as e:
                    log.warning(f"Sayfa {page_num} yüklenemedi ({e}), atlanıyor")
                    break
                snapshots = extract_cards_from_page(
                    html, category=category, captured_at=captured_at,
                    max_products=max_products - len(all_snaps),
                )
                new_snaps = [s for s in snapshots if s.platform_product_id not in seen_ids]
                if not new_snaps:
                    log.info(f"Sayfa {page_num} boş, duruldu")
                    break
                for s in new_snaps:
                    seen_ids.add(s.platform_product_id)
                all_snaps.extend(new_snaps)
                log.info(f"Sayfa {page_num}: {len(new_snaps)} yeni (toplam {len(all_snaps)})")

            log.info(f"Toplam {len(all_snaps)} ürün çekildi")
            return all_snaps
        finally:
            context.close()

    def _infer_category_from_url(self, url: str) -> str:
        url_lower = url.lower()
        known = [
            "parfum", "cilt-bakim", "cilt-bakimi", "makyaj", "kozmetik",
            "cep-telefonu", "bilgisayar", "elektronik", "kulaklik",
        ]
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

- [ ] **Step 4: Entegrasyon testlerinin geçtiğini doğrula**

Run: `python -m pytest tests/integration/test_akakce_scraper.py -v`
Expected: 5 test PASS

- [ ] **Step 5: Commit**

```bash
git add scrapers/akakce.py tests/integration/test_akakce_scraper.py
git commit -m "feat: add AkakceScraper class with pagination + integration tests"
```

---

### Task 4: `main.py` entegrasyonu

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Import satırı ekle**

`main.py` dosyasının üstünde `from scrapers.hepsiburada import HepsiburadaScraper` satırının ALTINA ekle:

```python
from scrapers.akakce import AkakceScraper
```

- [ ] **Step 2: `_make_scraper` fonksiyonunu güncelle**

`main.py` içindeki `_make_scraper` fonksiyonunu bul ve aşağıdaki ile değiştir:

```python
def _make_scraper(platform: str) -> BaseScraper:
    if platform == "hepsiburada":
        return HepsiburadaScraper()
    if platform == "akakce":
        return AkakceScraper()
    return TrendyolScraper()
```

- [ ] **Step 3: `_DEFAULT_CATEGORIES`'e Akakçe girişleri ekle**

`main.py`'deki `_DEFAULT_CATEGORIES` listesinin SONUNA (kapanış `]` öncesine) ekle:

```python
    {
        "platform": "akakce",
        "name": "parfum",
        "url": "https://www.akakce.com/parfum.html",
    },
    {
        "platform": "akakce",
        "name": "cilt-bakimi",
        "url": "https://www.akakce.com/cilt-bakim.html",
    },
    {
        "platform": "akakce",
        "name": "cep-telefonu",
        "url": "https://www.akakce.com/cep-telefonu.html",
    },
```

- [ ] **Step 4: Tüm testleri çalıştır (regresyon kontrolü)**

Run: `python -m pytest --tb=short -q`
Expected: 164 passed (mevcut 150 + 14 yeni), 1 deselected. Regresyon yok.

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "feat: wire Akakçe scraper into main pipeline (3 categories)"
```

---

### Task 5: Canlı doğrulama + push

**Files:**
- Yok (sadece doğrulama + push)

- [ ] **Step 1: Küçük max_products ile Akakçe canlı tarama doğrula**

Run:
```bash
python -c "
import sys; sys.stdout.reconfigure(encoding='utf-8')
from scrapers.akakce import AkakceScraper
s = AkakceScraper()
try:
    snaps = s.fetch_category('https://www.akakce.com/parfum.html', max_products=20)
    print(f'Canlı test: {len(snaps)} ürün çekildi')
    for snap in snaps[:3]:
        print(f'  - {snap.name[:50]} | {snap.brand} | {snap.price} TL')
finally:
    s.close()
"
```

Expected: 15-20 ürün (ilk sayfa kapasitesi), isim + marka + fiyat ile.

**Eğer 0 ürün dönerse:**
- Task 1 Step 2'deki selektör tespiti yanlıştı → fixture + `scrapers/akakce.py` sabitlerini güncelle
- Akakçe bot engeli döndürüyor olabilir → User-Agent'ı farklılaştır, `page.wait_for_timeout(5000)` ekle

- [ ] **Step 2: Origin'e push**

```bash
git push origin main
```

Expected: 3 yeni commit push edilir (fixture, parser+tests, scraper+tests, main.py).

- [ ] **Step 3: Task Scheduler'ın yarın gece 03:00 run'ında Akakçe kategorilerinin de tarandığını doğrula (sonraki gün — manuel)**

Gün sonrası kontrol:
```bash
python -c "
import sys; sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
from config import settings
c = sqlite3.connect(settings.database_path)
c.row_factory = sqlite3.Row
for r in c.execute(\"SELECT category, status, products_saved FROM run_stats WHERE platform='akakce' ORDER BY started_at DESC LIMIT 5\"):
    print(f\"  {r['category']:15} | {r['status']:8} | {r['products_saved']:3} ürün\")
"
```

---

## Self-Review

**Spec coverage:**
- [x] `scrapers/akakce.py` — Task 2 & 3
- [x] `ProductSnapshot` modeli korunmuş, `platform="akakce"` — Task 2
- [x] 3 kategori `_DEFAULT_CATEGORIES`'de — Task 4
- [x] Sayfalama + tek-sayfa hata toleransı (Trendyol pattern) — Task 3
- [x] Fingerprint + jitter (proxy disabled) — Task 3
- [x] Testler: unit (9) + integration (5) = 14 → Task 2 & 3
- [x] Anomali tespiti değişmez — platform bağımsız

**Type consistency:**
- `parse_product_card(html, category, captured_at) -> ProductSnapshot | None` — Task 2 & 3 boyunca aynı
- `extract_cards_from_page` imzası tutarlı
- `AkakceScraper` — tek isim, tüm tasklarda

**Placeholder yok:** Tüm adımlarda gerçek çalışan kod. Task 1'deki "selektörleri keşfet" manuel bir adım ama çıktısı (CSS selector isimleri) Task 2'de kullanılıyor — implementer Task 1 Step 2 sonunda bu değerleri elde eder.

**Bilinen risk:** Task 1 Step 1'de Akakçe bot engeli veya Step 2'de selektörlerin fixture'dan farklı olması. Her iki durum da implementer'ın Task 1 içinde çözmesi beklenen kapsamında.
