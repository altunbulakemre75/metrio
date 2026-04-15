# Fiyat Radarı

E-ticaret fiyat istihbaratı sistemi. Trendyol'dan (ve ilerleyen zamanda Hepsiburada, Amazon gibi platformlardan) rakip fiyat takibi yapar.

## Kurulum

```bash
python -m venv .venv
source .venv/Scripts/activate    # Windows bash / Git Bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
```

## Çalıştırma

```bash
python main.py
```

Çıktı:
- `data/fiyat_radari.db` — SQLite veritabanı (products, price_snapshots, run_stats)
- `logs/scraper.log` — günlük rotasyonlu log dosyası

## Test

```bash
pytest                        # Unit + integration testler (hızlı, offline)
pytest -m e2e                 # E2E: gerçek Trendyol'a bağlanır (~20s)
pytest tests/unit             # Sadece unit testler
pytest tests/integration      # Sadece integration testler
```

## Günlük Otomatik Çalıştırma (Windows)

1. `run_daily.bat` dosyası bu dizinde hazır.
2. Windows Task Scheduler aç: `Win + R` → `taskschd.msc`
3. **Create Basic Task** → İsim: "Fiyat Radarı Günlük Çekim"
4. **Trigger:** Daily, saat 03:00
5. **Action:** Start a program → `run_daily.bat` dosyasını seç
6. "Run whether user is logged on or not" işaretle
7. Test et: Task'a sağ tık → Run

## Mimari

- `scrapers/` — Platform bazında scraper modülleri (yeni site = yeni dosya)
- `storage/` — SQLite veri katmanı, normalize şema
- `utils/` — Retry, rate limit, logger decorator'ları
- `tests/unit` — Saf fonksiyonlar (parse, model, decorator)
- `tests/integration` — Fixture ile offline uçtan uca testler
- `tests/e2e` — Gerçek Trendyol testi (haftada 1 manuel)

Detaylı tasarım: [docs/superpowers/specs/2026-04-14-fiyat-radari-design.md](docs/superpowers/specs/2026-04-14-fiyat-radari-design.md)
Uygulama planı: [docs/superpowers/plans/2026-04-14-fiyat-radari-hafta1.md](docs/superpowers/plans/2026-04-14-fiyat-radari-hafta1.md)

## Hafta 1 Tamamlama Durumu

- [x] Trendyol kozmetik kategorisinden 20+ ürün çekilebiliyor
- [x] 7 alan yakalanıyor: ad, fiyat, marka, indirim, görsel, ürün puanı, stok
- [x] Zaman serisi şemasına normalize şekilde kaydediliyor
- [x] `python main.py` uçtan uca çalışıyor
- [x] Zamanlayıcıyla otomatik çalıştırılabilir (Task Scheduler + run_daily.bat)
- [x] 57 test geçiyor (unit + integration), E2E ayrı tetiklenir
- [x] Log yapılandırılmış, günlük rotasyon
- [x] GitHub'a yüklenebilir durumda, commit'ler odaklı

## Dashboard (Hafta 2)

### Çalıştırma
```bash
source .venv/Scripts/activate
streamlit run dashboard/app.py
```
Tarayıcıda `http://localhost:8501` açılır.

### Sayfalar
- **📊 Özet** — Genel durum, günlük yorum, son hareketler/anomaliler
- **🎯 Fırsatlar** — En büyük fiyat hareketleri, filtre + CSV indir
- **🚨 Anomaliler** — Normalden sapan fiyatlar, eşik ayarlanabilir
- **📈 Trendler** — Marka/kategori zaman serisi
- **🔍 Ürün Detay** — Arama + tek ürün fiyat geçmişi

### Demo Verisi
Gerçek veri biriktirilene kadar demo için:
```bash
python scripts/seed_demo_history.py --days 30 --anomalies 3
```
Mevcut ürünlere 30 gün sentetik geçmiş ekler (3 üründe kasıtlı anomali).

## Telegram Bildirimleri (Hafta 3)

Pipeline çalıştığında günlük özet + anomali alarmları telefonuna düşer.

### Kurulum

1. Telegram'da `@BotFather` ile sohbet başlat → `/newbot` → adım adım bot oluştur.
2. Verilen token'ı `.env` dosyasına ekle:
   ```
   TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
   ```
3. Kendi oluşturduğun bota bir "merhaba" mesajı gönder.
4. Chat ID'yi bul:
   ```bash
   python scripts/setup_telegram.py
   ```
5. Çıkan ID'yi `.env`'ye ekle ve aktif et:
   ```
   TELEGRAM_CHAT_ID=987654321
   TELEGRAM_ENABLED=true
   TELEGRAM_THRESHOLD=0.20
   ```
6. `python main.py` çalıştır → telefonda mesaj gelmeli.

### Mesaj çeşitleri

- **Günlük özet** — her çalıştırmada 1 mesaj (kaç ürün, kaç anomali, süre)
- **Anomali alarmı** — eşiği aşan her ürün için 1 mesaj (max 10)
- **Gruplu özet** — 10'dan fazla anomali varsa tek mesajda özet

## Haftalık PDF Raporu (Hafta 4)

Müşteriye mail ile gönderilebilecek profesyonel rapor üret:

```bash
python scripts/generate_report.py --days 7
```

Çıktı: `reports/fiyat_radari_YYYY-MM-DD.pdf` (5-6 sayfa).

İçerik:
- Kapak — dönem, tarih
- Özet — kaç ürün, kaç marka, kaç anomali, top 3 fırsat
- En büyük fiyat hareketleri — top 10 tablo
- Anomaliler — %20+ sapma tablosu
- Marka trendi — zaman serisi grafik
- Tam ürün listesi

## Sonraki Adımlar (Hafta 5+)
- Claude API ile gerçek AI yorumları
- Multi-tenant (birden fazla müşteri)
- Hepsiburada / Amazon scraper'ları
- İkinci kategori (elektronik) testi
