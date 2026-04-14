# Fiyat Radarı — Hafta 3: Telegram Bildirimleri

**Tarih:** 2026-04-15
**Durum:** Onaylandı, implementasyona hazır

## Amaç

Pipeline her çalıştığında Telegram üzerinden kullanıcıya:
1. **Günlük özet mesajı** — kaç ürün tarandı, kaç anomali bulundu, durum.
2. **Anomali alarmları** — belirlenen eşiğin üstünde fiyat hareketi olan her ürün için ayrı mesaj.

Bu özelliğin asıl değeri: müşteri demosunda "rakibin fiyat indirdi, telefonuna anında mesaj gelir" gösterebilmek. Dashboard'u açmak zorunda kalmadan ürün kullanıcı için pasif olarak çalışır.

## Kapsam dışı (YAGNI)

- Gerçek zamanlı bildirim (scraping günde bir, ona göre günlük bildirim yeterli).
- Birden çok kullanıcı / chat. Şimdilik tek `TELEGRAM_CHAT_ID`.
- Fiyat artış grafiği (ileride PDF rapor ile gelir).
- İki yönlü bot komutları (`/status`, `/latest` gibi). Sadece gönderim.

## Mimari

```
notifications/
  __init__.py
  telegram.py        # TelegramNotifier sınıfı
  formatter.py       # Pure fonksiyonlar: message formatting
scripts/
  setup_telegram.py  # Chat ID'yi otomatik bulur
tests/unit/
  test_telegram_formatter.py  # Formatlamanın unit testi (mock yok)
tests/integration/
  test_telegram_notifier.py   # HTTP mock'lu notifier testi
```

### Sınıf ve fonksiyonlar

**`notifications/formatter.py`** (saf fonksiyonlar, unit test edilir):
- `format_daily_summary(stats: dict) -> str` — run_stats dict'inden Türkçe özet metni üretir.
- `format_anomaly_alert(anomaly: Anomaly) -> str` — tek bir Anomaly için formatlı mesaj.
- `format_grouped_anomalies(anomalies: list[Anomaly], max_detail: int) -> str` — 10+ anomali varsa özet liste.

**`notifications/telegram.py`**:
- `TelegramNotifier(bot_token, chat_id, enabled)` — init.
- `notify_run(stats: dict, anomalies: list[Anomaly]) -> None` — pipeline bittikten sonra çağrılır. İçinde:
  - Enabled değilse sessizce çık.
  - Günlük özet mesajı gönder.
  - Max 10 anomali tek tek gönder; daha fazlası varsa gruplu tek mesaj.
  - Hata olursa log'a yaz, pipeline'ı düşürme.
- `_send(text: str) -> None` — Telegram Bot API çağrısı (`sendMessage` endpoint, `requests` ile).

### Entegrasyon

`main.py` içinde `run_pipeline()` sonrası:

```python
anomalies = detect_anomalies(conn, threshold_percent=settings.telegram_threshold)
notifier = TelegramNotifier(
    bot_token=settings.telegram_bot_token,
    chat_id=settings.telegram_chat_id,
    enabled=settings.telegram_enabled,
)
notifier.notify_run(stats, anomalies)
```

### Konfigürasyon

`config.py` içinde yeni alanlar:
- `telegram_bot_token: str = ""`
- `telegram_chat_id: str = ""`
- `telegram_threshold: float = 0.20`
- `telegram_enabled: bool = False`

`.env.example`'a eklenir. `TELEGRAM_ENABLED=false` varsayılan — kredensiyel girilmediyse çalışmaz.

### `scripts/setup_telegram.py`

Kullanıcı BotFather'dan token aldıktan sonra çalıştırır. Script:
1. `TELEGRAM_BOT_TOKEN` environment'tan okur.
2. `getUpdates` endpoint'ine istek atar.
3. Son mesajdan `chat.id` çıkarır ve ekrana yazar.
4. Kullanıcı bu değeri `.env` dosyasına manuel girer.

### Rate limit

Telegram Bot API: saniyede ~30 mesaj, gruba saniyede ~20. Bizim hiç bu sınıra yaklaşmıyoruz (max 10+1 mesaj/run) ama mesajlar arası 100ms bekleme ekliyoruz tedbiren.

### Hata yönetimi

- Network hatası, 4xx/5xx yanıtlar: log'a WARNING yazılır, pipeline'a etkisi yok.
- Token/chat_id eksikse: notifier init'te `enabled=False` olur, hiçbir şey gönderilmez.
- `requests.exceptions.RequestException` yakalanır, trace log'lanır.

## Mesaj formatları

### Günlük özet

```
📊 Fiyat Radarı — 2026-04-15
━━━━━━━━━━━━━━━━━━
✅ 25 ürün tarandı
🎯 3 anomali tespit edildi
⏱ Süre: 18s
```

`status == "failed"` ise:
```
⚠️ Fiyat Radarı — 2026-04-15
━━━━━━━━━━━━━━━━━━
❌ Pipeline başarısız
Hata: {error_message}
```

### Anomali alarmı

```
🔻 FİYAT DÜŞTÜ (-30%)
L'Oréal Hyaluronic Asit Serum
💰 127.90 TL → 89.50 TL
🔗 trendyol.com/loreal/...
```

`direction == "spike"` ise 🔺 ve "FİYAT ARTTI".

### Gruplanmış (10+ anomali)

```
🎯 12 anomali tespit edildi
━━━━━━━━━━━━━━━━━━
🔻 L'Oréal Serum (-30%)
🔻 Maybelline Ruj (-25%)
🔻 Nivea Krem (-22%)
🔺 Garnier Güneş (+18%)
... ve 8 tane daha
```

## Test stratejisi

### Unit testler (`tests/unit/test_telegram_formatter.py`)
- `format_daily_summary` success case
- `format_daily_summary` failed case
- `format_anomaly_alert` drop case
- `format_anomaly_alert` spike case
- `format_grouped_anomalies` 12 anomali → 4 detay + "8 daha"

### Integration testler (`tests/integration/test_telegram_notifier.py`)
- `notify_run` disabled → hiç HTTP çağrısı yok
- `notify_run` 3 anomali → 1 özet + 3 alarm = 4 HTTP POST
- `notify_run` 15 anomali → 1 özet + 1 gruplu mesaj = 2 HTTP POST
- `notify_run` HTTP hata fırlatırsa → exception propagate etmez
- `requests.post` mock edilir (`responses` veya `httpretty` yerine `unittest.mock.patch`)

### Elle test
Gerçek bot ile `python main.py` çalıştır, telefonda mesaj gelir mi kontrol.

## Kullanıcı kurulum akışı

README'ye eklenir:

1. Telegram'da `@BotFather` ile sohbet başlat, `/newbot` komutu ile bot oluştur.
2. Verilen token'ı `.env` dosyasına `TELEGRAM_BOT_TOKEN=...` olarak ekle.
3. Kendi oluşturduğun bota bir mesaj gönder (herhangi bir şey).
4. `python scripts/setup_telegram.py` çalıştır → chat ID ekrana düşer.
5. `TELEGRAM_CHAT_ID=...` ve `TELEGRAM_ENABLED=true` ekle.
6. `python main.py` çalıştır, telefonda mesajlar gelmeli.

## Bağımlılıklar

`requirements.txt`'e eklenir:
```
requests==2.32.3
```

(Not: `python-telegram-bot` tercih etmedik çünkü async alt yapı gerektiriyor ve bizim kullanımımız için `requests` ile raw API çağrısı daha yalın.)

## Kabul kriterleri

- [ ] `python main.py` çalıştığında Telegram'a 1 günlük özet mesajı gelir.
- [ ] %20+ anomali varsa her biri için ayrı mesaj gelir (max 10).
- [ ] 10'dan fazla anomali gruplu tek mesajda gelir.
- [ ] `TELEGRAM_ENABLED=false` iken hiçbir mesaj gönderilmez, pipeline normal çalışır.
- [ ] Network/token hatası pipeline'ı düşürmez, sadece log'a yazılır.
- [ ] `scripts/setup_telegram.py` chat ID'yi bulup ekrana yazar.
- [ ] Tüm unit+integration testler geçer (`pytest`).
- [ ] README'de kurulum adımları var.
