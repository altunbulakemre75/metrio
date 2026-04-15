# Metrio — Hafta 3: Telegram Bildirimleri Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pipeline her çalıştıktan sonra Telegram üzerinden günlük özet ve anomali alarmlarını otomatik gönderen bildirim sistemi.

**Architecture:** `notifications/formatter.py` (saf format fonksiyonları) + `notifications/telegram.py` (HTTP göndermem). `main.py` pipeline sonrası `TelegramNotifier.notify_run()` çağırır. Hata durumunda pipeline bozulmaz, sadece log'a yazılır.

**Tech Stack:** Python 3.13, `requests==2.32.3` (Telegram Bot API için), pytest + unittest.mock.

---

## File Structure

**Create:**
- `notifications/__init__.py`
- `notifications/formatter.py` — saf mesaj format fonksiyonları
- `notifications/telegram.py` — `TelegramNotifier` sınıfı, HTTP çağrıları
- `scripts/setup_telegram.py` — chat ID bulma yardımcısı
- `tests/unit/test_telegram_formatter.py`
- `tests/integration/test_telegram_notifier.py`

**Modify:**
- `config.py` — `telegram_threshold`, `telegram_enabled` alanları
- `main.py` — pipeline sonrası notifier entegrasyonu
- `requirements.txt` — `requests==2.32.3`
- `.env.example` — yeni Telegram değişkenleri
- `README.md` — kurulum adımları

---

## Task 1: `requests` bağımlılığını ekle

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: requirements.txt'e requests ekle**

`requirements.txt` son satırdan sonra:
```
requests==2.32.3
```

- [ ] **Step 2: Kur**

Run: `source .venv/Scripts/activate && pip install requests==2.32.3`
Expected: `Successfully installed requests-2.32.3`

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "feat: add requests dependency for Telegram API"
```

---

## Task 2: Config'e Telegram alanlarını ekle

**Files:**
- Modify: `config.py`
- Modify: `.env.example`

- [ ] **Step 1: config.py güncelle**

`config.py` içindeki `telegram_chat_id: str = ""` satırından sonra ekle:

```python
    telegram_threshold: float = Field(default=0.20, gt=0, lt=1)
    telegram_enabled: bool = False
```

Not: `Field` zaten import edilmiş durumda (scraper_max_products kullanıyor).

- [ ] **Step 2: .env.example güncelle**

`.env.example` dosyasının sonuna ekle (eğer satırlar yoksa):

```
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
TELEGRAM_THRESHOLD=0.20
TELEGRAM_ENABLED=false
```

- [ ] **Step 3: Config yüklenebiliyor mu kontrol**

Run: `source .venv/Scripts/activate && python -c "from config import settings; print(settings.telegram_enabled, settings.telegram_threshold)"`
Expected: `False 0.2`

- [ ] **Step 4: Commit**

```bash
git add config.py .env.example
git commit -m "feat: add Telegram config fields to settings"
```

---

## Task 3: `notifications/__init__.py` oluştur

**Files:**
- Create: `notifications/__init__.py`

- [ ] **Step 1: Boş paket dosyası oluştur**

İçerik:
```python
"""Telegram bildirim paketi."""
```

- [ ] **Step 2: Commit**

```bash
git add notifications/__init__.py
git commit -m "feat: add notifications package"
```

---

## Task 4: Format fonksiyonu — günlük özet (success case)

**Files:**
- Create: `notifications/formatter.py`
- Create: `tests/unit/test_telegram_formatter.py`

- [ ] **Step 1: Failing test yaz**

`tests/unit/test_telegram_formatter.py`:

```python
from notifications.formatter import format_daily_summary


def test_daily_summary_success():
    stats = {
        "status": "success",
        "products_saved": 25,
        "duration_seconds": 18,
        "error_message": None,
    }
    text = format_daily_summary(stats, anomaly_count=3, date_str="2026-04-15")

    assert "2026-04-15" in text
    assert "25 ürün" in text
    assert "3 anomali" in text
    assert "18s" in text
    assert "✅" in text
```

- [ ] **Step 2: Test fail olduğunu doğrula**

Run: `pytest tests/unit/test_telegram_formatter.py -v`
Expected: FAIL `ModuleNotFoundError: No module named 'notifications.formatter'`

- [ ] **Step 3: Minimal implementation**

`notifications/formatter.py`:

```python
"""Telegram mesaj formatlaması — saf fonksiyonlar."""


def format_daily_summary(stats: dict, anomaly_count: int, date_str: str) -> str:
    if stats["status"] == "success" or stats["status"] == "partial":
        return (
            f"📊 Metrio — {date_str}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✅ {stats['products_saved']} ürün tarandı\n"
            f"🎯 {anomaly_count} anomali tespit edildi\n"
            f"⏱ Süre: {stats['duration_seconds']}s"
        )
    return (
        f"⚠️ Metrio — {date_str}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"❌ Pipeline başarısız\n"
        f"Hata: {stats.get('error_message') or 'bilinmiyor'}"
    )
```

- [ ] **Step 4: Test pass doğrula**

Run: `pytest tests/unit/test_telegram_formatter.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add notifications/formatter.py tests/unit/test_telegram_formatter.py
git commit -m "feat: add daily summary formatter for Telegram"
```

---

## Task 5: Format fonksiyonu — failed status

**Files:**
- Modify: `tests/unit/test_telegram_formatter.py`

- [ ] **Step 1: Failing test ekle**

`tests/unit/test_telegram_formatter.py` sonuna ekle:

```python
def test_daily_summary_failed():
    stats = {
        "status": "failed",
        "products_saved": 0,
        "duration_seconds": 5,
        "error_message": "Trendyol timeout",
    }
    text = format_daily_summary(stats, anomaly_count=0, date_str="2026-04-15")

    assert "⚠️" in text
    assert "başarısız" in text
    assert "Trendyol timeout" in text
```

- [ ] **Step 2: Test pass doğrula** (kod zaten bu case'i kapsıyor)

Run: `pytest tests/unit/test_telegram_formatter.py -v`
Expected: 2 passed

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_telegram_formatter.py
git commit -m "test: add failed status case to summary formatter"
```

---

## Task 6: Format fonksiyonu — tek anomali alarmı

**Files:**
- Modify: `notifications/formatter.py`
- Modify: `tests/unit/test_telegram_formatter.py`

- [ ] **Step 1: Failing test ekle**

`tests/unit/test_telegram_formatter.py` başına import ekle:
```python
from analysis.anomaly import Anomaly
```

Dosya sonuna ekle:

```python
def _fake_anomaly(direction="drop", deviation=-0.30):
    return Anomaly(
        product_id=1,
        platform_product_id="abc",
        name="L'Oréal Hyaluronic Serum",
        brand="L'Oréal",
        category="kozmetik",
        current_price=89.50,
        average_price=127.90,
        deviation_percent=deviation,
        direction=direction,
        confidence="high",
        snapshot_count=20,
        product_url="https://www.trendyol.com/loreal/urun-p-123",
    )


def test_anomaly_alert_drop():
    from notifications.formatter import format_anomaly_alert
    a = _fake_anomaly(direction="drop", deviation=-0.30)
    text = format_anomaly_alert(a)

    assert "🔻" in text
    assert "FİYAT DÜŞTÜ" in text
    assert "-30%" in text
    assert "L'Oréal" in text
    assert "89.50" in text
    assert "127.90" in text
    assert "trendyol.com" in text


def test_anomaly_alert_spike():
    from notifications.formatter import format_anomaly_alert
    a = _fake_anomaly(direction="spike", deviation=0.25)
    text = format_anomaly_alert(a)

    assert "🔺" in text
    assert "FİYAT ARTTI" in text
    assert "+25%" in text
```

- [ ] **Step 2: Test fail doğrula**

Run: `pytest tests/unit/test_telegram_formatter.py -v`
Expected: FAIL (ImportError: format_anomaly_alert)

- [ ] **Step 3: Implementation ekle**

`notifications/formatter.py` sonuna:

```python
def format_anomaly_alert(anomaly) -> str:
    if anomaly.direction == "drop":
        arrow, label = "🔻", "FİYAT DÜŞTÜ"
    else:
        arrow, label = "🔺", "FİYAT ARTTI"

    pct = anomaly.deviation_percent * 100
    pct_str = f"{pct:+.0f}%"

    brand = anomaly.brand + " " if anomaly.brand else ""
    return (
        f"{arrow} {label} ({pct_str})\n"
        f"{brand}{anomaly.name}\n"
        f"💰 {anomaly.average_price:.2f} TL → {anomaly.current_price:.2f} TL\n"
        f"🔗 {anomaly.product_url}"
    )
```

- [ ] **Step 4: Testleri çalıştır**

Run: `pytest tests/unit/test_telegram_formatter.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add notifications/formatter.py tests/unit/test_telegram_formatter.py
git commit -m "feat: add anomaly alert formatter"
```

---

## Task 7: Format fonksiyonu — gruplu anomaliler

**Files:**
- Modify: `notifications/formatter.py`
- Modify: `tests/unit/test_telegram_formatter.py`

- [ ] **Step 1: Failing test ekle**

`tests/unit/test_telegram_formatter.py` sonuna:

```python
def test_grouped_anomalies_summarizes_excess():
    from notifications.formatter import format_grouped_anomalies
    anomalies = [
        _fake_anomaly(deviation=-0.30 + i * 0.01) for i in range(12)
    ]
    text = format_grouped_anomalies(anomalies, max_detail=4)

    assert "12 anomali" in text
    detail_lines = [l for l in text.split("\n") if "L'Oréal" in l]
    assert len(detail_lines) == 4
    assert "8 tane daha" in text
```

- [ ] **Step 2: Test fail doğrula**

Run: `pytest tests/unit/test_telegram_formatter.py::test_grouped_anomalies_summarizes_excess -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Implementation**

`notifications/formatter.py` sonuna:

```python
def format_grouped_anomalies(anomalies: list, max_detail: int = 4) -> str:
    total = len(anomalies)
    lines = [f"🎯 {total} anomali tespit edildi", "━━━━━━━━━━━━━━━━━━"]
    for a in anomalies[:max_detail]:
        arrow = "🔻" if a.direction == "drop" else "🔺"
        pct = f"{a.deviation_percent * 100:+.0f}%"
        brand = a.brand + " " if a.brand else ""
        lines.append(f"{arrow} {brand}{a.name} ({pct})")
    remaining = total - max_detail
    if remaining > 0:
        lines.append(f"... ve {remaining} tane daha")
    return "\n".join(lines)
```

- [ ] **Step 4: Test pass**

Run: `pytest tests/unit/test_telegram_formatter.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add notifications/formatter.py tests/unit/test_telegram_formatter.py
git commit -m "feat: add grouped anomaly formatter"
```

---

## Task 8: `TelegramNotifier` — disabled branch

**Files:**
- Create: `notifications/telegram.py`
- Create: `tests/integration/test_telegram_notifier.py`

- [ ] **Step 1: Failing test yaz**

`tests/integration/test_telegram_notifier.py`:

```python
from unittest.mock import patch

from notifications.telegram import TelegramNotifier


def test_disabled_notifier_does_not_call_api():
    notifier = TelegramNotifier(
        bot_token="x", chat_id="y", enabled=False,
    )
    with patch("notifications.telegram.requests.post") as mock_post:
        notifier.notify_run({"status": "success", "products_saved": 10, "duration_seconds": 3, "error_message": None}, anomalies=[])
        assert mock_post.call_count == 0


def test_missing_credentials_disables_notifier():
    notifier = TelegramNotifier(bot_token="", chat_id="", enabled=True)
    with patch("notifications.telegram.requests.post") as mock_post:
        notifier.notify_run({"status": "success", "products_saved": 10, "duration_seconds": 3, "error_message": None}, anomalies=[])
        assert mock_post.call_count == 0
```

- [ ] **Step 2: Test fail doğrula**

Run: `pytest tests/integration/test_telegram_notifier.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Minimal notifier**

`notifications/telegram.py`:

```python
"""Telegram Bot API entegrasyonu."""
import time
import logging

import requests

from notifications.formatter import (
    format_daily_summary,
    format_anomaly_alert,
    format_grouped_anomalies,
)

log = logging.getLogger(__name__)

_API_BASE = "https://api.telegram.org"
_MAX_INDIVIDUAL_ALERTS = 10
_INTER_MESSAGE_DELAY = 0.1


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str, enabled: bool):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled and bool(bot_token) and bool(chat_id)

    def notify_run(self, stats: dict, anomalies: list) -> None:
        if not self.enabled:
            return
        # full implementation in later tasks
        pass

    def _send(self, text: str) -> None:
        url = f"{_API_BASE}/bot{self.bot_token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": self.chat_id, "text": text}, timeout=10)
        except requests.exceptions.RequestException as e:
            log.warning(f"Telegram send failed: {e}")
```

- [ ] **Step 4: Test pass**

Run: `pytest tests/integration/test_telegram_notifier.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add notifications/telegram.py tests/integration/test_telegram_notifier.py
git commit -m "feat: add TelegramNotifier with disabled branch"
```

---

## Task 9: `notify_run` — özet + bireysel anomaliler

**Files:**
- Modify: `notifications/telegram.py`
- Modify: `tests/integration/test_telegram_notifier.py`

- [ ] **Step 1: Failing test ekle**

`tests/integration/test_telegram_notifier.py` sonuna:

```python
from analysis.anomaly import Anomaly


def _fake_anomaly(i: int) -> Anomaly:
    return Anomaly(
        product_id=i, platform_product_id=f"p{i}", name=f"Ürün {i}",
        brand="Marka", category="kozmetik",
        current_price=50.0, average_price=70.0,
        deviation_percent=-0.30, direction="drop",
        confidence="high", snapshot_count=10,
        product_url=f"https://www.trendyol.com/x/urun-p-{i}",
    )


def test_notify_run_sends_summary_plus_individual_alerts():
    notifier = TelegramNotifier(bot_token="TOK", chat_id="CHT", enabled=True)
    stats = {"status": "success", "products_saved": 25, "duration_seconds": 18, "error_message": None}
    anomalies = [_fake_anomaly(i) for i in range(3)]

    with patch("notifications.telegram.requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        notifier.notify_run(stats, anomalies)

    # 1 özet + 3 anomali = 4 POST
    assert mock_post.call_count == 4
    first_call_text = mock_post.call_args_list[0].kwargs["json"]["text"]
    assert "25 ürün" in first_call_text
    assert "3 anomali" in first_call_text
```

- [ ] **Step 2: Test fail doğrula**

Run: `pytest tests/integration/test_telegram_notifier.py::test_notify_run_sends_summary_plus_individual_alerts -v`
Expected: FAIL (call_count == 0)

- [ ] **Step 3: notify_run implementation**

`notifications/telegram.py` içindeki `notify_run` metodunu güncelle:

```python
    def notify_run(self, stats: dict, anomalies: list) -> None:
        if not self.enabled:
            return

        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")

        summary = format_daily_summary(stats, anomaly_count=len(anomalies), date_str=date_str)
        self._send(summary)

        if len(anomalies) <= _MAX_INDIVIDUAL_ALERTS:
            for a in anomalies:
                time.sleep(_INTER_MESSAGE_DELAY)
                self._send(format_anomaly_alert(a))
        else:
            time.sleep(_INTER_MESSAGE_DELAY)
            self._send(format_grouped_anomalies(anomalies))
```

- [ ] **Step 4: Test pass**

Run: `pytest tests/integration/test_telegram_notifier.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add notifications/telegram.py tests/integration/test_telegram_notifier.py
git commit -m "feat: send daily summary and individual anomaly alerts"
```

---

## Task 10: `notify_run` — 10+ anomali gruplu

**Files:**
- Modify: `tests/integration/test_telegram_notifier.py`

- [ ] **Step 1: Failing test ekle**

Dosya sonuna:

```python
def test_notify_run_groups_many_anomalies():
    notifier = TelegramNotifier(bot_token="TOK", chat_id="CHT", enabled=True)
    stats = {"status": "success", "products_saved": 50, "duration_seconds": 30, "error_message": None}
    anomalies = [_fake_anomaly(i) for i in range(15)]

    with patch("notifications.telegram.requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        notifier.notify_run(stats, anomalies)

    # 1 özet + 1 gruplu = 2 POST
    assert mock_post.call_count == 2
    second_text = mock_post.call_args_list[1].kwargs["json"]["text"]
    assert "15 anomali" in second_text
    assert "tane daha" in second_text
```

- [ ] **Step 2: Test pass** (kod zaten kapsıyor)

Run: `pytest tests/integration/test_telegram_notifier.py -v`
Expected: 4 passed

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_telegram_notifier.py
git commit -m "test: verify grouped anomaly path for 10+ anomalies"
```

---

## Task 11: `_send` hata toleranslı olmalı

**Files:**
- Modify: `tests/integration/test_telegram_notifier.py`

- [ ] **Step 1: Failing test ekle**

Dosya sonuna:

```python
import requests as _rq


def test_notify_run_swallows_network_errors():
    notifier = TelegramNotifier(bot_token="TOK", chat_id="CHT", enabled=True)
    stats = {"status": "success", "products_saved": 5, "duration_seconds": 3, "error_message": None}

    with patch("notifications.telegram.requests.post", side_effect=_rq.exceptions.ConnectionError("no net")):
        # Exception yükseltmemeli
        notifier.notify_run(stats, anomalies=[_fake_anomaly(1)])
```

- [ ] **Step 2: Test çalıştır**

Run: `pytest tests/integration/test_telegram_notifier.py::test_notify_run_swallows_network_errors -v`
Expected: PASS (`_send` zaten yakalıyor)

Eğer fail ederse `_send` içine `requests.exceptions.RequestException` yakalama eklendi mi kontrol et. Task 8'deki koda göre zaten var, PASS beklenir.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_telegram_notifier.py
git commit -m "test: verify notifier tolerates network errors"
```

---

## Task 12: `scripts/setup_telegram.py` — chat ID bulma

**Files:**
- Create: `scripts/setup_telegram.py`

- [ ] **Step 1: Script yaz**

`scripts/setup_telegram.py`:

```python
"""Telegram chat ID'yi bulmak için yardımcı.

Kullanım:
  1. BotFather'dan token al.
  2. .env dosyasına TELEGRAM_BOT_TOKEN=... ekle.
  3. Bota Telegram'dan herhangi bir mesaj gönder.
  4. python scripts/setup_telegram.py çalıştır.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

import requests
from config import settings


def main() -> int:
    token = settings.telegram_bot_token
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN boş. Önce .env'ye ekle.")
        return 1

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        response = requests.get(url, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"❌ Bağlantı hatası: {e}")
        return 1

    data = response.json()
    if not data.get("ok"):
        print(f"❌ API hatası: {data}")
        return 1

    updates = data.get("result", [])
    if not updates:
        print("ℹ️  Henüz mesaj yok. Botuna Telegram'dan bir mesaj gönder, sonra tekrar çalıştır.")
        return 1

    chat_ids = {u["message"]["chat"]["id"] for u in updates if "message" in u}
    print("✅ Bulunan chat ID'ler:")
    for cid in chat_ids:
        print(f"   {cid}")
    print()
    print("Bu değeri .env dosyasına TELEGRAM_CHAT_ID=... olarak ekle.")
    print("TELEGRAM_ENABLED=true yapmayı unutma.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Çalıştırılabilir olduğunu doğrula**

Run: `source .venv/Scripts/activate && python scripts/setup_telegram.py`
Expected: `❌ TELEGRAM_BOT_TOKEN boş...` (token henüz eklenmemiş olduğu için normal).

- [ ] **Step 3: Commit**

```bash
git add scripts/setup_telegram.py
git commit -m "feat: add setup script to discover Telegram chat ID"
```

---

## Task 13: Pipeline entegrasyonu (`main.py`)

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Import'ları ekle**

`main.py` başındaki import bloğuna ekle:

```python
from analysis.anomaly import detect_anomalies
from notifications.telegram import TelegramNotifier
```

- [ ] **Step 2: `main()` fonksiyonunu güncelle**

`main.py` içindeki `main()` fonksiyonunu şu şekilde değiştir:

```python
def main() -> int:
    """CLI giriş noktası. Default kategori listesini çalıştırır."""
    overall_status = 0
    all_stats = []
    for cat in _DEFAULT_CATEGORIES:
        scraper = TrendyolScraper()
        stats = run_pipeline(
            scraper=scraper,
            category_url=cat["url"],
            category_name=cat["name"],
            max_products=settings.scraper_max_products,
        )
        all_stats.append(stats)
        if stats["status"] == "failed":
            overall_status = 1

    # Telegram bildirimi — pipeline sonrası, kategoriden bağımsız tek özet.
    try:
        conn = connect(settings.database_path)
        init_schema(conn)
        anomalies = detect_anomalies(conn, threshold_percent=settings.telegram_threshold)
        combined_stats = _combine_stats(all_stats)
        notifier = TelegramNotifier(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
            enabled=settings.telegram_enabled,
        )
        notifier.notify_run(combined_stats, anomalies)
    except Exception as e:
        log.warning(f"Telegram bildirimi başarısız: {e}")

    return overall_status


def _combine_stats(all_stats: list[dict]) -> dict:
    """Birden çok kategorinin istatistiklerini tek özete indir."""
    if not all_stats:
        return {"status": "failed", "products_saved": 0, "duration_seconds": 0, "error_message": "Hiç kategori çalıştırılmadı"}
    saved = sum(s["products_saved"] for s in all_stats)
    duration = sum(s["duration_seconds"] for s in all_stats)
    any_failed = any(s["status"] == "failed" for s in all_stats)
    status = "failed" if any_failed and saved == 0 else ("partial" if any_failed else "success")
    error = next((s["error_message"] for s in all_stats if s["error_message"]), None)
    return {
        "status": status,
        "products_saved": saved,
        "duration_seconds": duration,
        "error_message": error,
    }
```

- [ ] **Step 3: Sanity check — mevcut testler kırılmadı mı**

Run: `pytest tests/ -v --ignore=tests/e2e`
Expected: Tüm testler PASS (Hafta 2'den 80 test + Hafta 3'ten ~10 test ≈ 90 passed)

- [ ] **Step 4: Pipeline elle test (Telegram disabled)**

Run: `source .venv/Scripts/activate && python main.py`
Expected: Normal scraping çalışır, Telegram uyarısı çıkmaz (enabled=false varsayılan).

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "feat: integrate Telegram notifier into main pipeline"
```

---

## Task 14: README güncellemesi

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Telegram bölümü ekle**

`README.md` içinde "## Sonraki Adımlar (Hafta 3+)" başlığından ÖNCE yeni bölüm ekle:

```markdown
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
```

- [ ] **Step 2: "Sonraki Adımlar" listesinden Telegram'ı kaldır**

`README.md` içindeki:
```
- Telegram bildirim sistemi (anomali alarmları)
```
satırını sil.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add Telegram notification setup to README"
```

---

## Task 15: Son kontrol — tam test süiti

**Files:** yok, sadece doğrulama.

- [ ] **Step 1: Tüm testleri çalıştır**

Run: `source .venv/Scripts/activate && pytest -v --ignore=tests/e2e`
Expected: Tüm testler PASS (Hafta 3 ile birlikte en az 90 test).

- [ ] **Step 2: Pipeline'ı disabled modda çalıştır**

Run: `python main.py`
Expected: Normal scraping, Telegram hatası yok.

- [ ] **Step 3: (Opsiyonel) Gerçek bot ile manuel doğrulama**

Kullanıcı BotFather'dan bot oluşturup `.env` ayarlarsa:
- `python main.py` → telefonda mesajlar gelir
- Bu adım CI/otomatik değil, elle doğrulama.

- [ ] **Step 4: Log kontrolü**

Run: `tail -20 logs/scraper.log`
Expected: "Telegram" ile ilgili hiç WARNING yok (enabled=false olduğu için sessizce atlıyor).

---

## Kabul Kriterleri (spec'ten)

- [x] Task 13 — `python main.py` sonrası günlük özet mesajı.
- [x] Task 9 — %20+ anomali için bireysel alarmlar (max 10).
- [x] Task 10 — 10+ anomali için gruplu mesaj.
- [x] Task 8 — `TELEGRAM_ENABLED=false` iken hiçbir mesaj gönderilmez.
- [x] Task 11 — Network hatası pipeline'ı düşürmez.
- [x] Task 12 — `setup_telegram.py` chat ID'yi bulur.
- [x] Task 15 — Tüm testler geçer.
- [x] Task 14 — README'de kurulum adımları.
