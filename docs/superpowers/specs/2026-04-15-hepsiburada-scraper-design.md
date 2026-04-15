# Metrio — Hepsiburada Scraper + Çoklu Kategori

**Tarih:** 2026-04-15
**Durum:** Onaylandı, implementasyona hazır

## Amaç

Trendyol'a ek olarak Hepsiburada platformunu eklemek ve her iki platformda kozmetik + elektronik kategorilerini otomatik olarak izlemek. Pipeline günlük 4 kategori çeker; dashboard, Telegram alarmları ve PDF raporları iki platform verisini birlikte gösterir.

## Kapsam dışı

- Amazon scraper (ileride ayrı hafta).
- Per-platform anomali eşiği (tek global eşik yeterli).
- Hepsiburada satıcı sayfası (sadece kategori listeleri).

## Mimari

Dokunulacak dosyalar:

```
scrapers/
  hepsiburada.py      # yeni — HepsiburadaScraper(BaseScraper)
main.py               # _DEFAULT_CATEGORIES genişletilir, scraper seçimi eklenir
tests/unit/
  test_hepsiburada_parser.py    # yeni
tests/integration/
  test_hepsiburada_scraper.py   # yeni
```

Yeni bağımlılık yok — Playwright zaten kurulu.

## `scrapers/hepsiburada.py`

`TrendyolScraper` ile aynı yapı; sadece selektörler farklı.

### Parse fonksiyonları

**`parse_product_card(html, category, captured_at) -> ProductSnapshot | None`**

Hepsiburada selektörleri (2026):
- Kart: `li[data-test-id="product-card"]`
- İsim: `[data-test-id="product-name"]`
- Fiyat: `[data-test-id="price"]` → fallback `[class*="price"]`
- Orijinal fiyat: `[data-test-id="original-price"]` → fallback `[class*="original"]`
- Marka: `[data-test-id="brand"]`
- Ürün linki: kart `<a>` href → `https://www.hepsiburada.com` prefix eklenir
- Ürün ID: href'den slug çıkarılır (son path segment)
- Stok: `[data-test-id="add-to-cart"]` yoksa `in_stock=False`

Fiyat parse için `scrapers.trendyol.parse_price_text` import edilir (aynı TL format).

**`extract_cards_from_page(html, category, captured_at, max_products) -> list[ProductSnapshot]`**

Trendyol'daki ile özdeş mantık; parse edilemeyen kartlar loglanıp atlanır.

### `HepsiburadaScraper(BaseScraper)`

- `_ensure_browser()` — Playwright Chromium, headless modda
- `_load_page(page, url)` — `@rate_limit` + `@retry(max_attempts=3)`, `networkidle` bekler
- `_scroll_to_load(page)` — infinite scroll için max 10 adım aşağı kaydır
- `fetch_category(category_url, max_products=500)` — tam akış
- `_infer_category_from_url(url)` — URL'den kategori adı çıkar (`kozmetik`, `elektronik`, …)
- `close()` — browser ve playwright durdurulur

## `main.py` değişiklikleri

### `_DEFAULT_CATEGORIES`

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

### Scraper seçimi

`main()` içinde platform'a göre doğru scraper seçilir:

```python
def _make_scraper(platform: str) -> BaseScraper:
    if platform == "hepsiburada":
        return HepsiburadaScraper()
    return TrendyolScraper()
```

`run_pipeline()` değişmez — platform string'i zaten `start_run()` a geçilir.

## Hata yönetimi

- Selektör bulunamazsa kart atlanır (parse_product_card → None), log WARNING.
- Sayfa yüklenemezse retry (3 deneme, exponential backoff). Tükendikten sonra kategori `failed` olarak işaretlenir.
- Bir kategori başarısız olursa diğerleri devam eder (mevcut davranış korunur).

## Testler

### Unit (`tests/unit/test_hepsiburada_parser.py`)

- `parse_product_card` geçerli HTML → doğru `ProductSnapshot`
- `parse_product_card` fiyat elementi eksik → `None`
- `parse_product_card` stok elementi yok → `in_stock=False`
- `extract_cards_from_page` 3 geçerli + 1 bozuk kart → 3 snapshot döner

### Integration (`tests/integration/test_hepsiburada_scraper.py`)

- `HepsiburadaScraper.fetch_category` mock browser HTML ile → liste döner
- `close()` iki kez çağrılırsa exception fırlatmaz

## Kabul kriterleri

- [ ] `python main.py` dört kategoriyi sırayla çeker (trendyol/kozmetik, trendyol/elektronik, hepsiburada/kozmetik, hepsiburada/elektronik).
- [ ] Hepsiburada snapshot'ları `platform="hepsiburada"` ile veritabanına kaydedilir.
- [ ] Tüm unit + integration testler geçer.
- [ ] Bir platform çökerse diğeri çalışmaya devam eder.
