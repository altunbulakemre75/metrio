# Metrio — Hafta 5: E-posta Otomasyonu

**Tarih:** 2026-04-15
**Durum:** Onaylandı.

## Amaç

Haftalık PDF raporunu SMTP üzerinden otomatik e-posta ile müşterilere göndermek. Pipeline halkasını kapatır: scrape → analiz → PDF → mail.

Tek komut:
```
python scripts/send_weekly_email.py
```

## Kapsam dışı

- HTML mail şablonu (plain text yeterli, spam puanı düşer).
- Bounce handling, retry queue.
- Per-customer templates / multi-tenant.

## Mimari

```
notifications/
  email.py           # EmailSender + format_email_body
scripts/
  send_weekly_email.py  # PDF üret + mail at
```

### `notifications/email.py`

- `format_email_body(conn, days: int) -> str` — saf fonksiyon, veriden metin üretir.
- `EmailSender(smtp_host, smtp_port, smtp_user, smtp_password, email_from, recipients, enabled)`:
  - `send(subject, body, attachment_path) -> None`
  - `send_weekly(subject, body, attachment_path)` iç metod değil, `send` genel amaçlı.
  - Disabled / eksik kredensiyel: sessiz çık.
  - Exception'ları `RequestException` benzeri yakalar, log'a yazar, yukarı fırlatmaz.

### `scripts/send_weekly_email.py`

1. PDF'i `build_weekly_report()` ile geçici dizinde üret.
2. `format_email_body()` ile metin.
3. `EmailSender.send(subject, body, attachment_path)`.
4. Başarılı / başarısız log.

### Konfigürasyon (.env)

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=sender@gmail.com
SMTP_PASSWORD=
EMAIL_FROM=sender@gmail.com
EMAIL_RECIPIENTS=musteri1@firma.com,musteri2@firma.com
EMAIL_ENABLED=false
```

`EMAIL_RECIPIENTS` virgülle ayrılmış; pydantic-settings'te `str`, runtime'da `.split(",")`.

### Mail şablonu (plain text)

```
Konu: Metrio — Haftalık Rapor (2026-04-15)

Merhaba,

Haftalık fiyat izleme raporunuz ektedir.

Bu hafta:
- 25 ürün takip edildi
- 3 anomali tespit edildi
- En büyük fırsat: L'Oréal Serum -30%

Detaylar PDF ekinde.

— Metrio
```

## Testler

### Unit (`tests/unit/test_email_formatter.py`)
- `format_email_body` boş DB → "veri yok" metni
- `format_email_body` seed DB → beklenen rakamlar
- Top 3 fırsat satırı doğru

### Integration (`tests/integration/test_email_sender.py`)
- `EmailSender(enabled=False)` → SMTP çağrısı yok
- `smtplib.SMTP` mock → `starttls`, `login`, `send_message` çağrıları tetiklendi mi
- PDF eki base64 encode edilip `MIMEApplication` olarak eklendi mi

### Elle
- Gerçek Gmail App Password ile `python scripts/send_weekly_email.py` → mail kutusunda PDF ekli mail.

## Otomatik çalıştırma

`run_weekly_email.bat` — Windows Task Scheduler Pazartesi 09:00.

## Kabul kriterleri

- [ ] `python scripts/send_weekly_email.py` disabled modda sessiz çalışır.
- [ ] Gerçek SMTP ile çalıştığında PDF ekli mail alıcılara ulaşır.
- [ ] SMTP hatası pipeline'ı düşürmez, log'a yazılır.
- [ ] Tüm testler geçer.
- [ ] README'de kurulum adımları (Gmail App Password dahil).
