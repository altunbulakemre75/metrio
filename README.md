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

## Sonraki Adımlar (Hafta 2)

- `analysis/` modülleri (fiyat değişim tespiti, anomali)
- Streamlit `dashboard/` sayfası
- HTML/PDF rapor üretimi
- Telegram bildirim sistemi
- İkinci kategori (elektronik) ile sistemin çoklu kategoride testi
