# Metrio — Kurulum Checklist (Faz 2-3)

Her müşteri için bu listeyi sırayla yürüt. Beklenen çıktıyı gözlem yapmadan
bir sonraki adıma geçme.

**Müşteri slug:** `__________` (örn. `acme`)

---

## Faz 2 — Kurulum

### [ ] 1. `customer_setup.py` çalıştır

```bash
python scripts/customer_setup.py
```

**Beklenen:** Prompt'lar geliyor, tüm inputlar alındıktan sonra:
```
✓ config/customers/{slug}/.env oluşturuldu
✓ config/customers/{slug}/categories.json oluşturuldu
✓ data/{slug}/ dizini oluşturuldu
```

### [ ] 2. `.env` dosyasını incele

```bash
cat config/customers/{slug}/.env
```

**Beklenen:**
- `DATABASE_PATH=data/{slug}/metrio.db`
- `TELEGRAM_CHAT_ID` dolu
- `TELEGRAM_ENABLED=true`
- `EMAIL_RECIPIENTS` dolu

### [ ] 3. `categories.json` incele

```bash
cat config/customers/{slug}/categories.json
```

**Beklenen:** Liste JSON, her kayıtta `platform`, `name`, `url` alanları var.

### [ ] 4. Telegram chat_id testi

Müşteri botumuza (`@MetrioFiyatBot`) `/start` yazdı mı teyit et.
Ardından şu komutla manuel test mesajı at:

```bash
python -c "from notifications.telegram import TelegramNotifier; \
  import os; os.environ['METRIO_ENV_FILE']='config/customers/{slug}/.env'; \
  from config import settings; \
  TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id, True)\
  .send('Metrio kurulum testi — bu mesajı görüyorsanız her şey yolunda.')"
```

**Beklenen:** Telegram'a mesaj geldi.

### [ ] 5. İlk tarama (full pipeline)

```bash
python main.py --config config/customers/{slug}/.env
```

**Beklenen:**
- 5-15 dk çalışır
- Son satır: `Çekim tamamlandı (success): NNN kaydedildi, 0 hata`
- Telegram'a run özeti düştü
- `data/{slug}/metrio.db` oluştu (`ls -la data/{slug}/`)

### [ ] 6. DB sanity check

```bash
python -c "import sqlite3; c=sqlite3.connect('data/{slug}/metrio.db'); \
  print('products:', c.execute('select count(*) from product_snapshots').fetchone()[0])"
```

**Beklenen:** En az 100 ürün.

### [ ] 7. Dashboard aç

```bash
streamlit run dashboard/app.py -- --db data/{slug}/metrio.db
```

**Beklenen:** `http://localhost:8501` açılıyor, ürünler listeleniyor.

---

## Faz 3 — Cron + Teslim

### [ ] 8. Task Scheduler — Günlük cron

1. Task Scheduler aç (Windows)
2. Create Basic Task → Name: `Metrio-{slug}-daily`
3. Trigger: Daily 03:00
4. Action: Start a program
   - Program: `cmd.exe`
   - Arguments: `/c python main.py --config config/customers/{slug}/.env >> logs/{slug}-cron.log 2>&1`
   - Start in: `c:\Users\altun\Desktop\Yeni klasör\verimadenciligi`
5. "Run whether user is logged on or not" işaretle

**Beklenen:** Right-click → Run → History'de "Last Run Result: (0x0)".

### [ ] 9. Task Scheduler — Pazartesi haftalık e-posta

Name: `Metrio-{slug}-weekly-email`, Trigger: Weekly Monday 09:00
Action arguments: `/c python scripts/send_weekly_email.py --config config/customers/{slug}/.env`

### [ ] 10. Log dönümü konfigürasyonu

```bash
ls logs/{slug}-cron.log
```

**Beklenen:** İlk cron çalışması sonrası dosya oluşmuş olmalı.

### [ ] 11. Teslim e-postası gönder

`docs/onboarding/customer-delivery.md` şablonunu müşteriye özel doldur, e-posta at.

### [ ] 12. Google Calendar — 30 günlük fatura hatırlatması

Event: "Fatura: {slug}" — +30 gün sonrası 10:00.

### [ ] 13. İlk gece izleme takvimi

Yarın sabah 09:00'a alarm kur: `logs/{slug}-cron.log` son satırı success olmalı.

---

## Temizlik (müşteri ayrılırsa)

```bash
# Task Scheduler'dan Metrio-{slug}-* görevlerini sil
# Sonra:
rm -rf config/customers/{slug} data/{slug} logs/{slug}-*.log
```
