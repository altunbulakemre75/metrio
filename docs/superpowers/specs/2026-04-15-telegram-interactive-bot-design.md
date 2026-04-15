# Metrio — Telegram İnteraktif Bot

**Tarih:** 2026-04-15
**Durum:** Onaylandı, implementasyona hazır

## Amaç

Mevcut tek-yönlü Telegram bildirim sistemine komut desteği eklemek. Kullanıcı (admin) bota mesaj attığında anlık yanıt alır: durum sorgulama, PDF rapor, marka trendi grafiği, ürün fiyat arama.

Tek kullanıcı modu (`settings.telegram_chat_id` dışındaki her chat ignore edilir). Periyodik poll (Task Scheduler her 2 dk) — arka planda sürekli çalışan process yok.

## Kapsam dışı

- Çoklu kullanıcı yönetimi (`user_preferences` tablosu) — multi-tenant fazında gelir
- `/alarm` komutu — tek kullanıcıda `.env` threshold yeterli
- Long polling / webhook — periyodik poll yeterli
- Conversation state (`ConversationHandler` vb.) — komutlar tek mesajlık, state'e gerek yok
- `python-telegram-bot` kütüphanesi — mevcut `requests` ile raw API yeterli

## Mimari

```
bot/
  __init__.py
  poll.py              # Giriş noktası: getUpdates → dispatch → state kaydet
  handlers.py          # Komut fonksiyonları (saf, conn alır, Response döner)
  state.py             # bot_state.json'a last_update_id yazar/okur
bot_poll.bat           # Task Scheduler her 2 dk
tests/unit/
  test_bot_handlers.py
tests/integration/
  test_bot_poll.py
```

Mevcut `notifications/telegram.py` tek-yönlü bildirim için kalır, dokunulmaz.

### `bot/state.py`

```python
class BotState:
    def __init__(self, path: Path): ...
    def get_last_update_id(self) -> int: ...      # 0 if file missing
    def set_last_update_id(self, update_id: int) -> None: ...
```

JSON format: `{"last_update_id": 123}`.

### `bot/handlers.py`

Saf fonksiyonlar, veritabanı connection alır, dönen değer `Response` dataclass:

```python
@dataclass
class Response:
    text: str
    photo_png: bytes | None = None
    document_path: Path | None = None
```

Komut fonksiyonları:
- `handle_start(args, conn) -> Response` — hoş geldin metni
- `handle_durum(args, conn) -> Response` — son 5 run istatistiği
- `handle_rapor(args, conn) -> Response` — PDF üret, document_path döner
- `handle_trend(args, conn) -> Response` — 30 günlük marka grafiği (`charts.brand_trend_chart`)
- `handle_fiyat(args, conn) -> Response` — ürün adında arama, ilk 5 eşleşme + fiyat

Bilinmeyen komut: `handle_start` yanıtı (yardım göster).

### `bot/poll.py`

Akış:
1. `BotState` yükle, `last_update_id` al
2. `GET /getUpdates?offset={last+1}&timeout=0` — anında döner, long poll yok
3. Her update için:
   - `message.chat.id != settings.telegram_chat_id` → sessiz ignore
   - `message.text` `/` ile başlıyorsa komut parse et, handler çağır, yanıt gönder
   - Aksi halde `handle_start` fallback
4. En büyük `update_id`'yi state'e yaz

Hata yönetimi: her handler exception'ı log'a yazılır, kullanıcıya "Bir hata oluştu" mesajı, poll devam eder.

### `bot_poll.bat`

```bat
@echo off
cd /d "c:\Users\altun\Desktop\Yeni klasör\verimadenciligi"
call .venv\Scripts\activate.bat
python -m bot.poll
```

Task Scheduler: her 2 dakika, süresiz.

## Komut detayları

### `/start`, `/yardim`

```
🎯 Metrio bot'a hoş geldin!

Komutlar:
/durum — son taramaların özeti
/rapor — haftalık PDF raporu
/trend [marka] — 30 günlük marka trend grafiği
/fiyat [arama] — ürün fiyat sorgulama

Örnekler:
/trend L'Oréal
/fiyat serum
```

### `/durum`

Son 5 `run_stats` satırını formatlar:
```
📊 Son taramalar:

2026-04-15 03:00 ✅ 66 ürün, 14s
2026-04-14 03:00 ✅ 62 ürün, 13s
2026-04-13 03:00 ✅ 58 ürün, 15s
...
```

### `/rapor`

1. `build_weekly_report(conn, temp_dir/metrio.pdf, days=7)` çağır
2. `sendDocument` ile PDF'i gönder
3. Başarılıysa "📄 Haftalık rapor hazır.", aksi halde hata metni

### `/trend [marka]`

1. args'ten marka adı al (trim)
2. Boşsa: "Kullanım: /trend [marka adı]"
3. `brand_trend_chart(conn, days=30, brands=[marka])` PNG bytes döner
4. Veri yoksa: "Bu marka için veri yok"
5. `sendPhoto` ile gönder, caption = "📈 {marka} — 30 günlük trend"

### `/fiyat [arama]`

1. args'ten arama kelimesini al
2. `SELECT p.name, p.brand, ps.price, ps.captured_at FROM products p JOIN (son snapshot) ...` — name LIKE %arama%
3. İlk 5 eşleşme:
```
🔍 "serum" için sonuçlar:

• L'Oréal Hyaluronic Serum — 127,90 TL (15 Nis)
• The Ordinary Niacinamide — 89,50 TL (15 Nis)
...
```

## Telegram API çağrıları

- `sendMessage` — text yanıt
- `sendPhoto` — PNG (multipart form, `InputFile`)
- `sendDocument` — PDF (multipart form)

`notifications/telegram.py`'deki pattern korunur: `_BASE = https://api.telegram.org/bot{token}`, `requests.post(url, ...)`, `RequestException` yakalanır.

## Auth kontrolü

```python
def is_authorized(update: dict) -> bool:
    chat_id = str(update.get("message", {}).get("chat", {}).get("id", ""))
    return chat_id == settings.telegram_chat_id
```

Yetkisiz update → log INFO, hiç yanıt gönderilmez (bot görünmez olur).

## Testler

### Unit (`tests/unit/test_bot_handlers.py`)

- `handle_start` → beklenen metin içerir "Metrio"
- `handle_durum` boş DB → "Henüz tarama yok"
- `handle_durum` 3 run ekli → 3 satır döner
- `handle_fiyat` eşleşme yok → "Sonuç bulunamadı"
- `handle_fiyat` 3 ürün eşleşir → 3 satırlık Response
- `handle_trend` marka boş args → kullanım mesajı
- `handle_trend` bilinmeyen marka → "veri yok"
- `BotState.get_last_update_id` dosya yok → 0
- `BotState.set_last_update_id` + `get` roundtrip → aynı değer

### Integration (`tests/integration/test_bot_poll.py`)

- `poll_once` yetkisiz chat_id update'i gelirse hiç HTTP POST yok
- `poll_once` `/durum` komutu gelirse `sendMessage` mock'u çağrılır
- `poll_once` iki ardışık run — ikincisi aynı mesajı tekrar işlemez
- `poll_once` HTTP hata — exception sessizce loglanır, state bozulmaz

### Elle

Gerçek bot ile `python -m bot.poll` çalıştır, Telegram'dan her komutu dene.

## Kabul kriterleri

- [ ] `python -m bot.poll` yeni mesaj yoksa 1 saniyeden kısa sürer ve çıkar
- [ ] Yetkili `chat_id`'den `/durum` komutu gelir, doğru özet gelir
- [ ] `/rapor` komutu PDF'i gerçek mail eki gibi gönderir
- [ ] `/trend L'Oréal` 30 günlük PNG grafiği döner
- [ ] `/fiyat serum` ilk 5 eşleşmeyi listeler
- [ ] Yetkisiz `chat_id` bot'a yazarsa hiçbir yanıt gönderilmez
- [ ] Tüm unit + integration testler geçer
- [ ] `bot_poll.bat` Task Scheduler'da 2 dakikada bir çalışır
- [ ] `bot_state.json` her run sonunda güncellenir, aynı mesaj iki kez işlenmez
