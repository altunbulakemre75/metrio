# Fiyat Radarı — Hafta 2 Tasarım Dokümanı

**Tarih:** 2026-04-15
**Faz:** Hafta 2 — Analiz Modülleri + Streamlit Dashboard
**Önkoşul:** Hafta 1 tamamlandı (scraper + DB + 25 ürün mevcut)

---

## 1. Amaç

Hafta 1'de toplanan veriyi anlamlı **içgörülere** çevirmek ve **müşteriye gösterilebilir** bir web arayüzünde sunmak. Temel hedef: potansiyel müşteriye "bak, sana sunacağım hizmet bu" diyebilmek.

### Kapsam
- 4 analiz modülü: fiyat değişimi, anomali, trend, yorum
- Tek ürün geçmiş görünümü + filtreler + CSV dışa aktarma
- Streamlit tabanlı dashboard
- Demo verisi seed scripti (gerçek veri birikene kadar)

### Kapsam Dışı (Hafta 3+)
- Multi-tenant müşteri izolasyonu
- Claude API ile gerçek AI yorum
- Telegram bildirim
- PDF rapor üretimi
- Authentication

---

## 2. Teknoloji Eklemeleri

| Paket | Amaç |
|-------|------|
| `streamlit==1.39.0` | Web UI framework |
| `plotly==5.24.1` | İnteraktif grafikler |
| `pandas==2.2.3` | Veri işleme (analiz modüllerinde) |

---

## 3. Klasör Yapısı (eklemeler)

```
analysis/
├── __init__.py
├── queries.py               Ortak DB sorguları (DRY)
├── price_changes.py         Top fırsatlar, en çok hareket eden ürünler
├── anomaly.py               30-gün ortalamadan sapma tespiti
├── trends.py                Marka/kategori zaman serisi
├── product_history.py       Tek ürünün fiyat geçmişi
└── commentary.py            Şablon yorum üretimi

dashboard/
├── __init__.py
├── app.py                   Ana sayfa (Özet)
├── pages/
│   ├── 2_🎯_Fırsatlar.py
│   ├── 3_🚨_Anomaliler.py
│   ├── 4_📈_Trendler.py
│   └── 5_🔍_Ürün_Detay.py
├── components/
│   ├── __init__.py
│   ├── charts.py            Plotly grafik üreticileri
│   ├── cards.py             Özet kart bileşenleri
│   ├── filters.py           Kategori/marka/tarih filtreleri
│   └── exports.py           CSV indirme butonu
└── .streamlit/
    └── config.toml          Tema (Fiyat Radarı markası)

scripts/
└── seed_demo_history.py     Sentetik 30-gün geçmişi üretir

tests/
├── unit/
│   ├── test_price_changes.py
│   ├── test_anomaly.py
│   ├── test_trends.py
│   ├── test_product_history.py
│   └── test_commentary.py
└── integration/
    └── test_analysis_queries.py
```

---

## 4. Analiz Modülü Detayları

### 4.1 `price_changes.py`

**Amaç:** Son N günde fiyatı değişen ürünleri bulur, en büyük hareketleri sıralar.

**API:**
```python
def top_movers(
    conn: sqlite3.Connection,
    days: int = 7,
    limit: int = 20,
    direction: Literal["down", "up", "both"] = "down",
) -> list[PriceChange]:
    """Son N günde en çok fiyat değişen ürünler."""

@dataclass
class PriceChange:
    product_id: int
    name: str
    brand: str | None
    category: str
    old_price: float
    new_price: float
    change_amount: float       # new - old
    change_percent: float      # (new - old) / old
    captured_at_old: datetime
    captured_at_new: datetime
    product_url: str
```

**Algoritma:**
1. Her ürün için: son 7 günden en eski ve en yeni snapshot'ı al
2. Fiyat farkını hesapla
3. Yön filtresine göre (aşağı = indirim, yukarı = zam) sırala
4. İlk `limit` kadarını döndür

### 4.2 `anomaly.py`

**Amaç:** "Normalden" ciddi sapma gösteren fiyatları işaretler.

**API:**
```python
def detect_anomalies(
    conn: sqlite3.Connection,
    lookback_days: int = 30,
    threshold_percent: float = 0.20,  # %20+ sapma
) -> list[Anomaly]:

@dataclass
class Anomaly:
    product_id: int
    name: str
    brand: str | None
    current_price: float
    average_price: float       # son N günün ortalaması
    deviation_percent: float   # (current - avg) / avg
    direction: Literal["drop", "spike"]
    confidence: str            # "low" | "medium" | "high" (veri yeterliliği)
    product_url: str
```

**Algoritma:**
1. Son 30 günün ortalamasını hesapla
2. Güncel fiyatla farkı bul
3. %20+ sapma varsa anomali işaretle
4. Güven (confidence): <5 snapshot = low, 5-15 = medium, 15+ = high

### 4.3 `trends.py`

**Amaç:** Marka veya kategoride zaman içinde fiyat eğilimi.

**API:**
```python
def brand_trend(
    conn: sqlite3.Connection,
    brand: str,
    days: int = 30,
    granularity: Literal["day", "week"] = "day",
) -> list[TrendPoint]:

def category_trend(
    conn: sqlite3.Connection,
    category: str,
    days: int = 30,
) -> list[TrendPoint]:

@dataclass
class TrendPoint:
    date: date
    average_price: float
    product_count: int
    median_price: float
```

### 4.4 `product_history.py`

**API:**
```python
def get_product_history(
    conn: sqlite3.Connection,
    product_id: int,
    days: int = 30,
) -> list[HistoryPoint]:

def search_products(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 20,
) -> list[ProductMatch]:
```

### 4.5 `commentary.py`

**Amaç:** Diğer analizlerin çıktılarından şablon paragraf üretir.

**API:**
```python
def generate_daily_summary(
    top_movers: list[PriceChange],
    anomalies: list[Anomaly],
    trend_direction: Literal["up", "down", "flat"],
) -> str:
```

**Şablon örneği:**
> "Bu hafta kozmetik kategorisinde **{N} üründe** fiyat hareketi tespit edildi.
> En büyük indirim **{brand}** markasında ({product_name}) görüldü: %{percent} ile {price} TL'ye düştü.
> Kategorideki genel trend **{direction}** yönünde.
> {anomaly_count} üründe dikkat çekici sapma var; detaylar Anomaliler sayfasında."

### 4.6 `queries.py`

**Amaç:** Dashboard'un ortak kullandığı SQL sorgularını tek yerde topla.

```python
def get_latest_snapshots_df(conn) -> pd.DataFrame
def get_price_history_df(conn, product_id: int) -> pd.DataFrame
def get_unique_brands(conn) -> list[str]
def get_unique_categories(conn) -> list[str]
def get_date_range(conn) -> tuple[date, date]
```

---

## 5. Dashboard Tasarımı

### 5.1 Sayfa Yapısı

**Ana sayfa (Özet)** — `app.py`
- Üstte: 4 özet kart (toplam ürün, takip edilen marka, son çekim, ortalama indirim)
- Ortada: Komentar paragrafı (commentary.py çıktısı)
- Altta: Mini "son 5 fırsat" tablosu + "son 5 anomali" tablosu

**Fırsatlar** — `pages/2_Fırsatlar.py`
- Filtre: kategori, marka, son X gün
- Tam `top_movers` tablosu
- Yanında: indirimli ürünlerin bar chart'ı (en büyük 10)

**Anomaliler** — `pages/3_Anomaliler.py`
- Filtre: yön (drop/spike), güven seviyesi
- Tablo + her satır için mini spark-line

**Trendler** — `pages/4_Trendler.py`
- Dropdown: marka veya kategori seç
- Time-series plot (günlük ortalama fiyat)
- Karşılaştırma: 2-3 marka üst üste

**Ürün Detay** — `pages/5_Ürün_Detay.py`
- Üstte: arama kutusu (`search_products`)
- Seçilen ürünün: büyük fiyat geçmişi grafiği + son 5 snapshot tablosu
- CSV indir butonu

### 5.2 Ortak Bileşenler

**`components/filters.py`** — Sidebar'da:
- Kategori multiselect
- Marka multiselect
- Tarih aralığı picker
- "Filtreleri temizle" butonu

**`components/exports.py`** — Her tablonun yanında "📥 CSV indir" butonu.

**`components/charts.py`** — Plotly sarmalayıcıları:
- `price_history_line(data)` — tek ürün
- `trend_comparison(series_dict)` — çoklu marka
- `top_discounts_bar(movers)` — yatay bar chart

**`components/cards.py`** — Streamlit `st.metric` sarmalayıcıları.

### 5.3 Performans

Streamlit `@st.cache_data(ttl=300)` (5 dakika cache) ile:
- Analiz fonksiyonları
- Queries modülü sonuçları

Her tıklamada DB'ye gitmez, 5 dakikada bir yeniler.

### 5.4 Tema

`.streamlit/config.toml`:
```toml
[theme]
primaryColor = "#E85D04"           # turuncu (fiyat radarı markası)
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F8F9FA"
textColor = "#1E1E1E"
font = "sans serif"
```

---

## 6. Demo Veri Seed Scripti

**Problem:** Şu an 25 ürün × 3 snapshot = 75 veri noktası. Trend ve anomali için yetersiz.

**Çözüm:** `scripts/seed_demo_history.py`

```python
# Mevcut her ürün için son 30 gün için sentetik snapshot'lar üret
# Fiyat rastgele ±%5 dalgalanma + hafif trend
# Bazı ürünlere kasıtlı anomali ekle (%30 düşüş → demo için güzel görünsün)
```

Çalıştırma: `python scripts/seed_demo_history.py --days 30 --anomalies 3`

**Etki:** Dashboard demo için dolu görünür; gerçek veri biriktikçe script'e ihtiyaç azalır.

**Veri ayrımı:** `price_snapshots.captured_at` eski tarih olacağı için gerçek veriyle karışmaz; `run_stats`'a `is_demo=1` satırı ekleyerek demo verinin hangi çalıştırmalardan geldiği takip edilir.

---

## 7. Hata Yönetimi

| Durum | Strateji |
|-------|----------|
| Veri yok (yeni ürün) | "Yeterli veri yok, %d gün daha beklenmeli" boş durum mesajı |
| DB bağlantı hatası | Dashboard en üstte kırmızı uyarı + öneri ("main.py çalıştı mı?") |
| Filtre sonucu boş | "Eşleşen ürün bulunamadı. Filtreleri gevşetin." |
| Grafik render hatası | try/except → boş grafik + log |

---

## 8. Test Stratejisi

**Unit testler (analiz modülleri):**
- Her fonksiyon için in-memory SQLite fixture
- Kenar durumları: veri yok, tek snapshot, aşırı değişim
- Saf fonksiyonlar → hızlı, deterministik

**Integration testler:**
- `queries.py` + gerçek DB şeması
- Analiz fonksiyonlarının birlikte çalışması

**Manuel UI testler:**
- Streamlit görsel doğrulama manuel (otomatik görsel test Hafta 2 kapsamında yok)
- Her sayfa için kontrol listesi (README'de)

**Test etmeyeceğimiz:**
- Streamlit/Plotly iç davranışı
- Tarayıcı rendering

---

## 9. Başarı Kriterleri

1. 4 analiz modülü bağımsız çalışır ve test edilir (30+ unit test)
2. `streamlit run dashboard/app.py` komutu dashboard'u açar
3. 5 sayfa eksiksiz çalışır (Özet, Fırsatlar, Anomaliler, Trendler, Ürün Detay)
4. Filtreler (kategori, marka, tarih) tüm sayfalarda etkili
5. CSV dışa aktarma 2+ sayfada mevcut
6. Demo seed scripti çalıştırıldıktan sonra dashboard dolu ve profesyonel görünür
7. Tüm analiz fonksiyonları boş durum mesajlarıyla graceful çalışır
8. Marka teması aktif

---

## 10. Gelecek Genişletme

- **Hafta 3:** Telegram bildirim + PDF rapor
- **Hafta 4:** Çoklu müşteri, Claude API ile AI yorum
- **Hafta 5+:** Hepsiburada scraper, multi-kategori
