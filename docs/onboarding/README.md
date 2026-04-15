# Metrio Müşteri Onboarding Runbook

**Amaç:** Yeni müşteri geldiğinde, ilk iletişimden itibaren **2 saat içinde canlıya alma**.

Bu runbook 4 faz ile tüm süreci kapsar: Demo öncesi hazırlık, kurulum, cron + teslim,
ve uzun vadeli bakım/ölçme. Her faz için süre, sorumlu kişi ve somut çıktı tanımlıdır.

---

## Faz 1 — Demo Öncesi (≈30 dk)

**Süre:** 30 dk (müşteri müsaitliğine göre 1 güne yayılabilir)
**Kim yapar:** Sen (satış + hazırlık) + Müşteri (form doldurma)
**Çıktı:** Demo randevusu onaylı, intake formu doldurulmuş, rakip URL'leri belirlenmiş

### Adımlar

1. **Intake formu gönder** — `docs/onboarding/intake-form.md` içeriğini WhatsApp / e-posta
   ile müşteriye gönder. Format: sade, copy-paste edilebilir alanlar.
2. **Kategori ve rakip seçimi** — Müşteri formu doldurduktan sonra rakip marka adlarını
   Trendyol/Hepsiburada üzerinde ara, karşılık gelen kategori URL'lerini not al.
   (Örn. "Farmasi" araması → `https://www.trendyol.com/kozmetik-x-c89` listesinde
   marka filtresi.)
3. **Demo seansı planı** — 30 dk Zoom/Google Meet. Ajanda: dashboard tur + canlı rakip
   listesi + fiyat alarm örneği + Telegram bot demosu.
4. **Demo seansı akışı** — Sahte müşteri DB'si (`data/demo/metrio.db`) ile dashboard
   aç, 2-3 rakip fiyat düşüşü örneği göster. Telegram botunun `/fiyat`, `/rapor`
   komutlarını canlı dene.
5. **Sözleşme / teklif** — Demo sonunda anında kısa teklif (aylık ücret, rakip sayısı,
   platform sayısı). Onay alındığında Faz 2'ye geç.

---

## Faz 2 — Kurulum (≈60 dk)

**Süre:** 45-60 dk
**Kim yapar:** Sen (tüm teknik işler). Müşteri sadece chat_id ve onay sağlar.
**Çıktı:** Müşteriye özel `.env` + `categories.json` + ilk DB snapshot'ı alınmış,
Telegram test mesajı gönderilmiş, dashboard açılıyor.

### Adımlar

1. **`customer_setup.py` çalıştır**
   ```bash
   python scripts/customer_setup.py
   ```
   Prompt'lara sırayla cevap ver: slug (örn. `acme`), şirket adı, e-posta,
   Telegram chat_id, kategori URL'leri. Script otomatik olarak
   `config/customers/{slug}/.env` + `categories.json` + `data/{slug}/` üretir.

2. **Telegram chat_id al** — Müşteri Telegram botu (`@MetrioFiyatBot`) ile önce
   `/start` yazmalı. Sonra botun `@userinfobot` özellikleri ile chat_id'yi gör.
   Grup ise gruba botu ekle + grupta `/start` + `getUpdates` ile `-100...` başlayan
   grup id'sini çıkar. `scripts/setup_telegram.py` yardımcı olur.

3. **İlk tarama** (sanity check)
   ```bash
   python main.py --config config/customers/{slug}/.env
   ```
   İlk çalıştırmada 5-15 dk sürer. Loglarda "Çekim tamamlandı (success)" + en az 100
   ürün kaydedildi görmelisin. Hata alırsan Troubleshooting bölümüne bak.

4. **Test mesajı** — İlk tarama sonunda Telegram'a otomatik özet mesajı düşmeli.
   Düşmediyse `TELEGRAM_ENABLED=true` ve `TELEGRAM_CHAT_ID` değerini `.env` içinde
   tekrar kontrol et.

5. **Dashboard URL'i hazırla** — Streamlit dashboard'ını müşteri için yayınla:
   ```bash
   streamlit run dashboard/app.py -- --db data/{slug}/metrio.db
   ```
   URL'i (public ise) müşteri ile paylaş. Şimdilik lokal/VPN; v2'de her müşteriye
   subdomain (`{slug}.metrio.app`).

---

## Faz 3 — Cron + Teslim (≈30 dk)

**Süre:** 30 dk + ilk 7 gün gözetim
**Kim yapar:** Sen. Müşteriye sadece teslim e-postası gider.
**Çıktı:** Windows Task Scheduler'da günlük cron kayıtlı, teslim e-postası gönderilmiş,
ilk hafta için izleme takvimi belirlenmiş, 30 günlük fatura takvimde.

### Adımlar

1. **Task Scheduler kaydı** — Windows'ta Task Scheduler aç → "Create Basic Task".
   - **Trigger:** Günlük, 03:00
   - **Action:** `run_daily.bat {slug}` (veya direkt komut:
     `python main.py --config config/customers/{slug}/.env`)
   - Çalıştırma kullanıcısı: kendi hesabın. "Run whether user is logged on or not" işaretli.
   Test için "Run" butonuna bas, Task History'de "Last Run Result: 0x0" olmalı.

2. **İlk 7 gün bakım** — Her sabah `logs/pipeline.log` üzerinden gece çalışmasının
   success döndüğünü kontrol et. Hata varsa hemen müdahale. Müşteriye soru sormadan
   önce çözmeye çalış.

3. **Pazartesi haftalık rapor e-postası** —
   ```bash
   python scripts/send_weekly_email.py --config config/customers/{slug}/.env
   ```
   Her pazartesi 09:00 için ayrı bir Task Scheduler görevi kur. İlk hafta manuel tetikle,
   müşteri mailini aldı mı teyit et.

4. **30 gün faturalama** — Bugünün tarihini +30 olarak Google Calendar'a
   "Fatura: {slug}" kaydı aç. Fatura şablonu için `docs/onboarding/billing-template.md`.

---

## Faz 4 — Bakım / Ölçme (sürekli)

**Süre:** Haftada ~1 saat. İkinci müşteri geldiğinde refaktör için 1 gün.
**Kim yapar:** Sen.
**Çıktı:** Sürekli çalışan sistem, müşteri memnuniyeti ölçülüyor,
ikinci müşteri geldiğinde multi-tenant refaktör tamam.

### Adımlar

1. **Bot durumu izleme** — `@MetrioFiyatBot`'a `/durum` komutu: son çalışma
   tarihi + başarı durumu. Haftada 1 kez kendin çalıştır.
2. **Haftalık check-in** — Her cuma müşteriye kısa WhatsApp: "Bu hafta X fiyat
   değişikliği yakaladık, Y rakipte stok azaldı. Bir sorun var mı?"
3. **2. müşteri geldiğinde refaktör** — Şu anki yapı per-customer `.env` + cron task.
   2. müşteri sonrası: multi-tenant ORM (customer_id her tabloda), tek cron, tenant
   routing middleware. Plan: `docs/superpowers/plans/` altına yeni spec yaz.

---

## Sık Karşılaşılan Problemler

### "Hiçbir ürün kaydedilemedi"
- Trendyol sayfa yapısı değişmiş olabilir. `tests/test_trendyol.py::test_parse_real_sample`
  çalıştır — fail ederse selector güncelleme gerek.
- Proxy aktif ve blokluysa `PROXY_ENABLED=false` geçici yap.

### Telegram mesajı gelmiyor
- `TELEGRAM_ENABLED=true` mi? Çoğu zaman atlanıyor.
- `chat_id` doğru mu? Grup ise `-100...` başlamalı.
- Bot grupta admin değilse mesaj göndermez. Müşteriye admin yap dedirt.

### "FileNotFoundError: data/{slug}/metrio.db"
- `customer_setup.py` `data/{slug}/` dizinini oluşturmuş olmalı. Yoksa manuel
  `mkdir data/{slug}`. İlk `main.py` çalışması DB'yi init eder.

### Task Scheduler çalışmıyor
- "Run whether user is logged on or not" + kullanıcı şifresi girildi mi?
- Action'da absolute path kullan, working directory'yi proje köküne ayarla.
- Log dosyasına yönlendir: `python main.py --config ... > logs/{slug}-cron.log 2>&1`

### Dashboard açılmıyor
- Streamlit portu çakışıyor olabilir. `--server.port 8502` ile dene.
- DB path yanlışsa boş dashboard gelir. `DATABASE_PATH` değerini teyit et.

---

## Referanslar

- `docs/onboarding/intake-form.md` — Demo öncesi müşteriye gönderilecek form
- `docs/onboarding/checklist.md` — Faz 2-3 için adım-adım checklist
- `docs/onboarding/customer-delivery.md` — Teslim e-postası ve kullanım rehberi
- `docs/onboarding/billing-template.md` — Fatura şablonu
- `scripts/customer_setup.py` — İnteraktif kurulum CLI
