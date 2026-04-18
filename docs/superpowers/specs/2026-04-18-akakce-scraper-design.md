# Metrio — Akakçe Aggregator Scraper

**Tarih:** 2026-04-18
**Durum:** Onaylandı, implementasyona hazır

## Amaç

Akakçe'yi (Türkiye'nin en büyük fiyat karşılaştırma sitesi) pilot aggregator olarak ekle. Bir tek scraper ile Trendyol, Hepsiburada, Amazon ve diğer pazaryerlerindeki ortak ürünlerin "en düşük fiyat" verisini tek kaynaktan al. Hepsiburada/Amazon'daki bot-block sorununu aggregator üzerinden dolaylı aş.

Faz 1 — kategori listesi scraping (Mod A): ürün adı + en düşük fiyat. Satıcı bazlı detay (Mod B) ertelendi, müşteri #1 gerçek ihtiyacı belirleyince eklenecek.

## Kapsam dışı (YAGNI)

- Detay sayfası scraping / çoklu satıcı fiyatı (Mod B — sonraki faz)
- Akakçe dışı aggregator'lar (Cimri, Epey — aynı pattern'le sonra eklenir)
- Ürün eşleştirme (Akakçe'deki ürün = Trendyol'daki ürün mü? — şu an yok, müşteri ihtiyacı ortaya çıkınca)
- Yorum/rating çekme

## Mimari

```
scrapers/
  akakce.py              # yeni — parse fonksiyonları + AkakceScraper
main.py                  # _DEFAULT_CATEGORIES'e 3 akakce girişi
tests/
  unit/test_akakce_parser.py
  integration/test_akakce_scraper.py
  fixtures/akakce_category_page.html
```

Mevcut `BaseScraper` arayüzü dokunulmaz. `_make_scraper` fonksiyonuna yeni dal eklenir:

```python
def _make_scraper(platform: str) -> BaseScraper:
    if platform == "hepsiburada":
        return HepsiburadaScraper()
    if platform == "akakce":
        return AkakceScraper()
    return TrendyolScraper()
```

## `scrapers/akakce.py`

Trendyol scraper'ının aynı pattern'i:

### Sabitler
- `_BASE_URL = "https://www.akakce.com"`
- `_CARD_SELECTOR` — kategori sayfasında her ürün kartı (gerçek selektör implementasyonda canlı HTML'den tespit edilir)
- Fiyat formatı Akakçe'de `1.234 TL` veya `1.234,56 TL` — `scrapers.trendyol.parse_price_text` import edilir, aynı mantık

### Parse fonksiyonları

```python
def parse_product_card(html, category, captured_at) -> ProductSnapshot | None:
    # Kart HTML'inden:
    #   - platform_product_id: href'ten slug (örn. akakce.com/xyz/eniyi-urun.html → "eniyi-urun")
    #   - name: ürün başlığı
    #   - brand: marka (varsa, yoksa None)
    #   - price: en düşük fiyat (kartta "en ucuz XX TL" olarak görünür)
    #   - product_url: tam URL
    #   - image_url: thumbnail
    #   - seller_name = None (aggregator)
    #   - seller_rating = None
    #   - in_stock = True (aggregator stokta olanları listeler)

def extract_cards_from_page(html, category, captured_at, max_products=None) -> list[ProductSnapshot]:
    # BeautifulSoup ile kartları sel, parse_product_card ile birer birer dönüştür
```

### `AkakceScraper(BaseScraper)`

Trendyol ile birebir aynı yapı:
- `_ensure_browser()` — Playwright Chromium headless
- `_load_page(page, url)` — `@jitter_delay` + `@retry(max_attempts=3)`
- `fetch_category(category_url, max_products=500)` — sayfalama ile döngü, page timeout'unda önceki sayfalar korunur (Trendyol'daki fix aynen uygulanır)
- `_paginated_url(base, page_num)` — Akakçe sayfalama parametresi canlıda doğrulanır (`?page=2` veya `/?pg=2` — implementation sırasında verify)
- `_infer_category_from_url(url)` — tanınan slug'ları eşleştir (parfum, cilt-bakim, cep-telefonu, elektronik, …)
- `close()` — browser + playwright temizlenir

## `main.py` değişiklikleri

```python
_DEFAULT_CATEGORIES = [
    # ... mevcut trendyol girişleri
    {"platform": "akakce", "name": "parfum", "url": "https://www.akakce.com/parfum.html"},
    {"platform": "akakce", "name": "cilt-bakimi", "url": "https://www.akakce.com/cilt-bakim.html"},
    {"platform": "akakce", "name": "cep-telefonu", "url": "https://www.akakce.com/cep-telefonu.html"},
]
```

Gerçek URL'ler implementation'da canlı sayfa üzerinden doğrulanır. Yanlış URL → "unknown" kategori veya 404 → pipeline log'a yazar, diğer kategoriler devam eder.

## Anti-bot

Aggregator olduğu için Akakçe bot-block riski düşük. Mevcut fingerprint rotation (`utils/fingerprint.py`) + jitter delay (1-3s arası) yeterli. Proxy pool disabled kalır — müşteri talep ederse devreye alınır.

## Hata yönetimi

- Sayfa timeout → log.warning, o kategori için "önceki sayfalardaki ürünler kaydedilir" (Trendyol'daki pattern aynen)
- Parse edilemeyen kart → log.warning, atlanır
- Kategori URL'si 404/5xx → run_stats'a `failed` + error_message, diğer kategoriler etkilenmez
- Akakçe HTML yapısı değişirse → parser fail, fixture testleri göstergeci olur (CI'da yakalanır)

## Testler

### Unit (`tests/unit/test_akakce_parser.py`)
- `parse_product_card` tam dolu kart → doğru ProductSnapshot
- `parse_product_card` fiyat eksik → None
- `parse_product_card` marka eksik → brand=None ama diğer alanlar dolu
- `parse_product_card` resim yok → image_url=None
- `parse_product_card` href bozuk → None
- `extract_cards_from_page` fixture HTML → N ürün (fixture'a göre)
- `extract_cards_from_page` max_products=2 → sadece 2 ürün
- `extract_cards_from_page` tüm kartlar bozuk → boş liste

### Integration (`tests/integration/test_akakce_scraper.py`)
- `extract_cards_from_page` fixture dosyası ile → beklenen id'ler set'i
- Sayfalama döngüsü: `_load_page` mock, 3 sayfa sonra boş → 3 sayfa × ürünler dönmeli
- `AkakceScraper.close()` idempotent (iki kez çağrılırsa exception yok)

### Fixture
`tests/fixtures/akakce_category_page.html` — 3 ürün içeren minimal ama gerçekçi HTML. İlki tam dolu (marka, fiyat, resim), ikincisi markasız, üçüncüsü parse edilemez (eksik fiyat → atlanmalı).

## Kabul kriterleri

- [ ] `python main.py` çalıştığında 3 akakce kategorisinin her biri için `run_stats` kaydı oluşur
- [ ] Akakçe'den gelen snapshot'lar DB'de `platform='akakce'` ile saklanır, diğer platform verilerine karışmaz
- [ ] Tüm mevcut testler geçer (regresyon yok)
- [ ] Yeni testler (~11) geçer, toplam ~161 test
- [ ] Anomali tespiti Akakçe verisi üzerinde çalışır (otomatik — platform ayrımı yapmıyor)
- [ ] Bir kategori URL'si yanlışsa diğerleri çalışmaya devam eder
