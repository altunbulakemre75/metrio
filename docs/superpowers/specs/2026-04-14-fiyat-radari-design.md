# Metrio — Tasarım Dokümanı

**Tarih:** 2026-04-14
**Proje:** E-ticaret Fiyat İstihbaratı Servisi
**Faz:** Hafta 1 — Teknik Altyapı

---

## 1. Amaç ve Kapsam

### Amaç
E-ticaret satıcılarına rakip fiyat takibi, fiyat optimizasyonu önerileri ve pazar analizi sunan abonelik tabanlı bir servisin teknik altyapısını kurmak.

### Hafta 1 Kapsamı
- Trendyol kozmetik kategorisinden ürün bilgilerini otomatik toplayan bir scraping sistemi
- Toplanan verinin SQLite'ta zaman serisi olarak saklanması
- Modüler, genişletilebilir bir mimari (gelecekte Hepsiburada, Amazon vb. için hazır)
- Temel hata yönetimi, loglama ve test altyapısı

### Hafta 1 Kapsamı Dışı (Hafta 2+)
- Streamlit dashboard
- Analiz modülleri (fiyat değişimi, anomali tespiti)
- HTML/PDF rapor üretimi
- Telegram bildirim sistemi
- Müşteri portalı

---

## 2. Teknoloji Seçimleri

| Alan | Seçim | Neden |
|------|-------|-------|
| Dil | Python 3.11+ | Veri ekosistemi, AI araçlarıyla uyum |
| Scraping | Playwright | JS-render site desteği, çok siteye uyum, anti-bot dayanıklılığı |
| Veritabanı | SQLite | Sıfır kurulum, tek dosya, 10 müşteriye kadar yeterli |
| Config | pydantic + `.env` | Tipli, doğrulanmış, sır dışarıda |
| Test | pytest | Ekosistem standardı |
| Loglama | `logging` + TimedRotatingFileHandler | Yapılandırılmış, rotasyonlu |
| Paket yönetimi | pip + `requirements.txt` | Başlangıç için yeterli |

**Reddedilen alternatifler:**
- BeautifulSoup: Trendyol JS-render, çalışmaz
- Trendyol iç API: Kırılgan, siteye özel, hukuki gri alan
- SQLAlchemy: Ham SQL daha öğretici, bu ölçekte ORM aşırı
- Docker/Celery/FastAPI: 10 müşteri altında gereksiz karmaşıklık

---

## 3. Klasör Yapısı

Proje kök dizini: `verimadenciligi/` (Metrio ürün markası, klasör adı farklı).

```
verimadenciligi/
├── scrapers/
│   ├── __init__.py
│   ├── base.py              BaseScraper (soyut sınıf)
│   └── trendyol.py          TrendyolScraper(BaseScraper)
├── storage/
│   ├── __init__.py
│   ├── database.py          SQLite bağlantısı + sorgular
│   ├── models.py            Product, ProductSnapshot dataclass'ları
│   └── migrations/
│       └── 001_initial.sql
├── analysis/                (Hafta 2)
│   ├── price_changes.py
│   ├── competitor.py
│   └── anomaly.py
├── reporting/               (Hafta 2)
│   ├── html_report.py
│   └── templates/
├── notifications/           (Hafta 2)
│   └── telegram.py
├── dashboard/               (Hafta 2)
│   └── app.py
├── utils/
│   ├── __init__.py
│   ├── logger.py
│   ├── retry.py             Exponential backoff decorator
│   └── rate_limiter.py      Saniyede istek sınırlayıcı
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
│       ├── trendyol_category_page.html
│       └── trendyol_edge_cases/
├── data/
│   └── metrio.db
├── logs/
│   └── scraper.log
├── .env                     Gizli ayarlar
├── .env.example             Şablon (git'e commit edilir)
├── .gitignore
├── config.py                pydantic ayar doğrulaması
├── main.py                  Pipeline giriş noktası
├── requirements.txt
└── README.md
```

---

## 4. Mimari Prensipler

### 4.1 Modülerlik
Her site bağımsız bir scraper modülüdür. Ana pipeline siteyi bilmez, sadece `BaseScraper` arayüzünü bilir.

### 4.2 Tek Yön Bağımlılık
```
main.py → scrapers + storage + analysis + notifications
scrapers → (hiçbir iç modül)
storage → (hiçbir iç modül)
analysis → storage (sadece okuma)
```

Bileşenler birbirini import etmez. Orchestration sadece `main.py`'dadır.

### 4.3 Arayüz Sözleşmesi

```python
class BaseScraper(ABC):
    @abstractmethod
    def fetch_category(
        self,
        category_url: str,
        max_products: int = 500
    ) -> list[ProductSnapshot]:
        """Kategori sayfasından ürünleri çeker."""

    @abstractmethod
    def close(self) -> None:
        """Kaynakları serbest bırakır (browser, bağlantı vb.)."""
```

Yeni site eklemek = bu iki metodu implemente eden yeni bir sınıf.

---

## 5. Veri Modeli

### 5.1 SQLite Şeması

**`products` — Ürün kimliği (nadiren değişir)**

```sql
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    platform_product_id TEXT NOT NULL,
    name TEXT NOT NULL,
    brand TEXT,
    category TEXT NOT NULL,
    product_url TEXT NOT NULL,
    image_url TEXT,
    first_seen_at TIMESTAMP NOT NULL,
    last_seen_at TIMESTAMP NOT NULL,
    UNIQUE(platform, platform_product_id)
);
CREATE INDEX idx_products_platform_category ON products(platform, category);
```

**`price_snapshots` — Zaman serisi fiyat verisi**

```sql
CREATE TABLE price_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id),
    price REAL NOT NULL,
    original_price REAL,
    discount_rate REAL,
    seller_name TEXT,
    seller_rating REAL,
    in_stock INTEGER NOT NULL DEFAULT 1,
    captured_at TIMESTAMP NOT NULL
);
CREATE INDEX idx_snapshots_product_time
    ON price_snapshots(product_id, captured_at DESC);
```

**`run_stats` — Çalışma izleme**

```sql
CREATE TABLE run_stats (
    run_id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    category TEXT NOT NULL,
    products_found INTEGER,
    products_saved INTEGER,
    products_failed INTEGER,
    duration_seconds INTEGER,
    status TEXT NOT NULL,
    error_message TEXT,
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP
);
```

### 5.2 Python Veri Modelleri

```python
@dataclass
class ProductSnapshot:
    # Ürün kimliği
    platform: str
    platform_product_id: str
    name: str
    brand: str | None
    category: str
    product_url: str
    image_url: str | None
    # Anlık veri
    price: float
    original_price: float | None
    discount_rate: float | None
    seller_name: str | None
    seller_rating: float | None
    in_stock: bool
    captured_at: datetime
```

### 5.3 Normalizasyon Gerekçesi
Tek tabloyla her snapshot'ta ürün adı/marka/URL tekrar ederdi (1 yılda ~500 MB gereksiz). İki tabloyla aynı veri ~10-20 MB.

---

## 6. Veri Akışı

```
[zamanlayıcı: her gün 03:00]
   (Windows: Task Scheduler, Linux: cron)
        ↓
    main.py
        ↓
┌──────────────────────────────────┐
│ 1. TrendyolScraper.fetch_category│   Playwright açılır, sayfa render edilir,
│                                  │   ürün kartları parse edilir
└──────────────────────────────────┘
        ↓
list[ProductSnapshot]  ← ~500 ürün
        ↓
┌──────────────────────────────────┐
│ 2. database.save_snapshots()     │   products: UPSERT
│                                  │   price_snapshots: INSERT
└──────────────────────────────────┘
        ↓
┌──────────────────────────────────┐
│ 3. analysis.detect_changes()     │   (Hafta 2)
└──────────────────────────────────┘
        ↓
┌──────────────────────────────────┐
│ 4. notifications.send_telegram() │   (Hafta 2)
└──────────────────────────────────┘
        ↓
┌──────────────────────────────────┐
│ 5. reporting.generate_daily()    │   (Hafta 2)
└──────────────────────────────────┘
```

**Hafta 1:** Sadece adım 1 ve 2.

---

## 7. TrendyolScraper İç Akışı

```
fetch_category(url, max_products=500)
    ↓
1. Playwright async context başlat
2. Browser (Chromium, headless) aç
3. Yeni sayfa aç, User-Agent + viewport ayarla
4. Kategori URL'sine git, networkidle bekle
5. Infinite scroll / "Daha fazla yükle" ile ürünleri genişlet
6. Ürün kartı selector'ı ile DOM element'leri topla
7. Her kart için:
   - @rate_limit (saniyede 1 istek)
   - @retry(max=3, backoff=exponential)
   - Kart içinden: isim, fiyat, orijinal fiyat, marka,
     satıcı, puan, stok, görsel URL, ürün URL
   - ProductSnapshot oluştur
8. Browser'ı kapat
9. list[ProductSnapshot] döndür
```

---

## 8. Hata Yönetimi

### 8.1 Hata Kategorileri

| Hata Türü | Strateji |
|-----------|----------|
| Geçici ağ hatası (timeout, 503) | `@retry`: 3 deneme, 1s→2s→4s backoff |
| Rate limit (429) | 60 saniye bekle, tekrar dene |
| Tek ürün parse hatası | Logla, atla, devam et |
| Tüm sayfa yüklenemedi | 3 denemeden sonra exception |
| Anti-bot tespit (CAPTCHA) | Exception, o gün atla, acil uyarı |
| Veritabanı hatası | Exception, pipeline'ı durdur (veri kaybını önle) |

### 8.2 Prensip
Kurtarılabilir hatalarda devam et, kurtarılamaz hatalarda güvenli dur.

### 8.3 Decorator Örnekleri

```python
@retry(max_attempts=3, backoff_base=2)
@rate_limit(calls_per_second=1)
def fetch_product_card(page, selector):
    ...
```

---

## 9. Loglama

### 9.1 Format

```
[YYYY-MM-DD HH:MM:SS] LEVEL | component | message
```

### 9.2 Dosya Rotasyonu
- `logs/scraper.log` — günlük rotasyon
- 30 gün saklama
- `logging.handlers.TimedRotatingFileHandler`

### 9.3 Seviye Kullanımı
- `INFO`: Normal akış (başlangıç, bitiş, sayı)
- `WARN`: Kurtarılabilir anormallikler (tek ürün atlandı)
- `ERROR`: Çalışmayı etkileyen hatalar (sayfa yüklenemedi)
- `CRITICAL`: Sistem çökmesi (DB bozuk, disk dolu)

---

## 10. Test Stratejisi

### 10.1 Piramit

```
        E2E (1-2 adet, manuel)
      Integration (5-10, her commit)
  Unit (20+, her kayıt)
```

### 10.2 Unit Testler
- Parser fonksiyonları (`parse_price`, `parse_discount`)
- Dataclass serileştirme
- Decorator davranışı (retry sayısı, backoff süresi)
- **Hedef:** 2 saniyede tamamlanır

### 10.3 Integration Testler (Offline Fixture)
`tests/fixtures/` klasöründe gerçek Trendyol sayfalarının kayıtlı HTML kopyaları:
- `trendyol_category_page.html` — normal durum
- `trendyol_edge_cases/no_discount.html` — indirimsiz
- `trendyol_edge_cases/out_of_stock.html` — stokta yok
- `trendyol_edge_cases/missing_brand.html` — eksik veri

Parser'a doğrudan HTML verilir, Playwright bypass edilir.

### 10.4 E2E Test
- `@pytest.mark.e2e` dekoratörü
- Sadece `pytest -m e2e` ile çalışır
- Gerçek Trendyol'dan 3-5 ürün çeker
- Haftada 1 manuel tetiklenir
- Amaç: "Selector hâlâ geçerli mi?"

### 10.5 Veritabanı Testleri
Her test in-memory SQLite kullanır:
```python
@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    run_migrations(conn)
    yield conn
    conn.close()
```

### 10.6 Test EDİLMEYECEKler
- Playwright, SQLite, pandas, requests (3. parti kütüphaneler)
- Streamlit UI görünümü (manuel kontrol)

---

## 11. Yasal ve Etik Sınırlar

- Sadece **kamuya açık veri** toplanır (giriş gerektiren sayfalar değil)
- `robots.txt` kurallarına uyulur
- Saniyede en fazla 1 istek (sunucuya zarar vermeme)
- Kişisel veri toplanmaz (KVKK uyumu)
- Toplanan veri müşteriye özel analiz için kullanılır, yeniden yayınlanmaz

---

## 12. Hafta 1 Başarı Kriterleri

1. Trendyol kozmetik kategorisinden 50+ ürün başarıyla çekilebilir
2. Her ürün için 7 alan da toplanır: ad, fiyat, marka, satıcı, indirim, stok, görsel URL
3. Veri SQLite'a normalize şekilde kaydedilir
4. `python main.py` komutu uçtan uca çalışır
5. Zamanlayıcı ile otomatik çalıştırılabilir (Windows Task Scheduler)
6. En az 10 unit test + 3 integration test geçer
7. Bir haftalık log tutulur, grep'lenebilir
8. Kod GitHub'a commit edilir, README ile belgelenir

---

## 13. Gelecek Genişletme Noktaları (Dondurulmuş Kapsam)

- **Hafta 2:** Streamlit dashboard, analiz modülleri, Telegram bildirim, HTML raporlar
- **Ay 2:** Hepsiburada scraper (sadece `scrapers/hepsiburada.py` eklenir)
- **Ay 3:** Müşteri portalı, çoklu müşteri izolasyonu
- **Ay 4+:** Amazon/eBay (uluslararası), USD fiyatlandırma

Bu spec **sadece Hafta 1'i** kapsar. Sonraki fazlar kendi spec'lerini alacak.
