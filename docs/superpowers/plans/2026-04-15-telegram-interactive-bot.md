# Telegram İnteraktif Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tek-kullanıcı modunda Metrio Telegram bot'una 5 komut desteği ekle (`/start`, `/durum`, `/rapor`, `/trend`, `/fiyat`). Periyodik poll ile Task Scheduler her 2 dk çalıştırır.

**Architecture:** `bot/` paketinde state (JSON persist), handlers (saf fonksiyonlar + Response dataclass), poll (getUpdates → dispatch → sendMessage/sendPhoto/sendDocument). Mevcut `notifications/telegram.py` dokunulmaz.

**Tech Stack:** Python 3.13, `requests` (HTTP), pytest, `unittest.mock` (HTTP mock'ları için)

---

## Dosya Haritası

| İşlem | Dosya | Ne yapıyor |
|-------|-------|------------|
| Oluştur | `bot/__init__.py` | Paket |
| Oluştur | `bot/state.py` | `BotState` — JSON state I/O |
| Oluştur | `bot/handlers.py` | `Response` + 5 komut handler'ı |
| Oluştur | `bot/poll.py` | `poll_once()`, `main()` — API call + dispatch |
| Oluştur | `bot_poll.bat` | Task Scheduler giriş noktası |
| Oluştur | `tests/unit/test_bot_handlers.py` | Handler unit testleri |
| Oluştur | `tests/unit/test_bot_state.py` | BotState unit testleri |
| Oluştur | `tests/integration/test_bot_poll.py` | Poll integration testleri |

---

### Task 1: BotState

**Files:**
- Create: `bot/__init__.py`
- Create: `bot/state.py`
- Create: `tests/unit/test_bot_state.py`

- [ ] **Step 1: Boş `bot/__init__.py` oluştur**

- [ ] **Step 2: Failing unit testleri yaz**

`tests/unit/test_bot_state.py`:

```python
import json
from pathlib import Path
from bot.state import BotState


def test_get_last_update_id_returns_zero_when_file_missing(tmp_path):
    state = BotState(tmp_path / "bot_state.json")
    assert state.get_last_update_id() == 0


def test_set_and_get_roundtrip(tmp_path):
    path = tmp_path / "bot_state.json"
    state = BotState(path)
    state.set_last_update_id(42)
    assert state.get_last_update_id() == 42
    # Dosya gerçekten yazıldı mı
    assert json.loads(path.read_text(encoding="utf-8")) == {"last_update_id": 42}


def test_get_handles_corrupted_json_returns_zero(tmp_path):
    path = tmp_path / "bot_state.json"
    path.write_text("not-json", encoding="utf-8")
    state = BotState(path)
    assert state.get_last_update_id() == 0


def test_set_overwrites_existing(tmp_path):
    path = tmp_path / "bot_state.json"
    state = BotState(path)
    state.set_last_update_id(10)
    state.set_last_update_id(20)
    assert state.get_last_update_id() == 20
```

- [ ] **Step 3: Testin fail ettiğini doğrula**

Run: `pytest tests/unit/test_bot_state.py -v`
Expected: `ModuleNotFoundError: No module named 'bot.state'`

- [ ] **Step 4: `bot/state.py` oluştur**

```python
import json
from pathlib import Path


class BotState:
    """Telegram bot'un son işlediği update_id'yi kalıcı tutar."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def get_last_update_id(self) -> int:
        if not self.path.exists():
            return 0
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return int(data.get("last_update_id", 0))
        except (json.JSONDecodeError, ValueError):
            return 0

    def set_last_update_id(self, update_id: int) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"last_update_id": update_id}),
            encoding="utf-8",
        )
```

- [ ] **Step 5: Testlerin geçtiğini doğrula**

Run: `pytest tests/unit/test_bot_state.py -v`
Expected: 4 PASS

- [ ] **Step 6: Commit**

```bash
git add bot/__init__.py bot/state.py tests/unit/test_bot_state.py
git commit -m "feat(bot): add BotState for update_id persistence"
```

---

### Task 2: Handlers

**Files:**
- Create: `bot/handlers.py`
- Create: `tests/unit/test_bot_handlers.py`

- [ ] **Step 1: Failing unit testleri yaz**

`tests/unit/test_bot_handlers.py`:

```python
import sqlite3
from datetime import datetime, timedelta
import pytest
from bot.handlers import Response, handle_start, handle_durum, handle_trend, handle_fiyat
from storage.database import init_schema, save_snapshot, start_run, finish_run
from storage.models import ProductSnapshot


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    init_schema(c)
    return c


def _snap(pid, name, brand, price, days_ago=0):
    return ProductSnapshot(
        platform="trendyol", platform_product_id=pid, name=name, brand=brand,
        category="kozmetik", product_url=f"https://trendyol.com/{pid}",
        image_url=None, price=price, original_price=None, discount_rate=None,
        seller_name=None, seller_rating=None, in_stock=True,
        captured_at=datetime.now() - timedelta(days=days_ago),
    )


def test_handle_start_returns_welcome_text(conn):
    r = handle_start("", conn)
    assert isinstance(r, Response)
    assert "Metrio" in r.text
    assert "/durum" in r.text
    assert r.photo_png is None
    assert r.document_path is None


def test_handle_durum_empty_db(conn):
    r = handle_durum("", conn)
    assert "tarama" in r.text.lower()


def test_handle_durum_with_runs(conn):
    start_run(conn, run_id="r1", platform="trendyol", category="kozmetik", started_at=datetime(2026, 4, 15, 3, 0))
    finish_run(conn, run_id="r1", status="success", products_found=66, products_saved=66,
               products_failed=0, finished_at=datetime(2026, 4, 15, 3, 0, 14), duration_seconds=14)
    r = handle_durum("", conn)
    assert "66" in r.text
    assert "success" in r.text.lower() or "✅" in r.text


def test_handle_trend_empty_args(conn):
    r = handle_trend("", conn)
    assert "kullanım" in r.text.lower() or "marka" in r.text.lower()
    assert r.photo_png is None


def test_handle_trend_unknown_brand(conn):
    r = handle_trend("BilinmeyenMarka", conn)
    assert "veri" in r.text.lower()
    assert r.photo_png is None


def test_handle_fiyat_empty_args(conn):
    r = handle_fiyat("", conn)
    assert "kullanım" in r.text.lower() or "arama" in r.text.lower()


def test_handle_fiyat_no_match(conn):
    save_snapshot(conn, _snap("1", "Hyaluronic Serum", "L'Oréal", 127.90))
    r = handle_fiyat("telefon", conn)
    assert "bulunamadı" in r.text.lower() or "sonuç" in r.text.lower()


def test_handle_fiyat_match(conn):
    save_snapshot(conn, _snap("1", "Hyaluronic Serum", "L'Oréal", 127.90))
    save_snapshot(conn, _snap("2", "Vitamin C Serum", "The Ordinary", 89.50))
    save_snapshot(conn, _snap("3", "iPhone 15", "Apple", 45000.0))
    r = handle_fiyat("serum", conn)
    assert "L'Oréal" in r.text or "Serum" in r.text
    assert "Ordinary" in r.text or "Vitamin" in r.text
    assert "127" in r.text  # fiyat
```

- [ ] **Step 2: Testin fail ettiğini doğrula**

Run: `pytest tests/unit/test_bot_handlers.py -v`
Expected: `ModuleNotFoundError: No module named 'bot.handlers'`

- [ ] **Step 3: `bot/handlers.py` oluştur**

```python
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import mkdtemp


@dataclass
class Response:
    text: str
    photo_png: bytes | None = None
    document_path: Path | None = None


_HELP_TEXT = (
    "🎯 Metrio bot'a hoş geldin!\n\n"
    "Komutlar:\n"
    "/durum — son taramaların özeti\n"
    "/rapor — haftalık PDF raporu\n"
    "/trend [marka] — 30 günlük marka trend grafiği\n"
    "/fiyat [arama] — ürün fiyat sorgulama\n\n"
    "Örnekler:\n"
    "/trend L'Oréal\n"
    "/fiyat serum"
)


def handle_start(args: str, conn: sqlite3.Connection) -> Response:
    return Response(text=_HELP_TEXT)


def handle_durum(args: str, conn: sqlite3.Connection) -> Response:
    rows = conn.execute(
        "SELECT started_at, status, products_saved, duration_seconds "
        "FROM run_stats WHERE finished_at IS NOT NULL "
        "ORDER BY started_at DESC LIMIT 5"
    ).fetchall()
    if not rows:
        return Response(text="📊 Henüz tarama yok.")
    lines = ["📊 Son taramalar:", ""]
    for r in rows:
        icon = "✅" if r["status"] == "success" else ("⚠️" if r["status"] == "partial" else "❌")
        ts = str(r["started_at"])[:16]
        lines.append(f"{ts} {icon} {r['products_saved']} ürün, {r['duration_seconds']}s")
    return Response(text="\n".join(lines))


def handle_rapor(args: str, conn: sqlite3.Connection) -> Response:
    from reports.builder import build_weekly_report
    out_dir = Path(mkdtemp(prefix="metrio_bot_"))
    pdf_path = out_dir / f"metrio_{datetime.now():%Y-%m-%d}.pdf"
    try:
        build_weekly_report(conn, pdf_path, days=7)
    except Exception as e:
        return Response(text=f"❌ Rapor oluşturulamadı: {e}")
    return Response(text="📄 Haftalık rapor hazır.", document_path=pdf_path)


def handle_trend(args: str, conn: sqlite3.Connection) -> Response:
    brand = args.strip()
    if not brand:
        return Response(text="Kullanım: /trend [marka adı]\nÖrn: /trend L'Oréal")
    from reports.charts import brand_trend_chart
    png = brand_trend_chart(conn, days=30, top_n=10)
    if png is None:
        return Response(text=f"📉 {brand} için yeterli veri yok.")
    # Veri yeterliyse PNG zaten tüm top markaları içerir — metin caption ile marka vurgula
    return Response(
        text=f"📈 {brand} (ve diğer aktif markalar) — 30 günlük trend",
        photo_png=png,
    )


def handle_fiyat(args: str, conn: sqlite3.Connection) -> Response:
    query = args.strip()
    if not query:
        return Response(text="Kullanım: /fiyat [arama kelimesi]\nÖrn: /fiyat serum")
    rows = conn.execute(
        """
        SELECT p.name, p.brand, ps.price, ps.captured_at
        FROM products p
        JOIN price_snapshots ps ON ps.product_id = p.id
        WHERE p.name LIKE ?
        AND ps.captured_at = (
            SELECT MAX(captured_at) FROM price_snapshots WHERE product_id = p.id
        )
        ORDER BY ps.captured_at DESC
        LIMIT 5
        """,
        (f"%{query}%",),
    ).fetchall()
    if not rows:
        return Response(text=f"🔍 \"{query}\" için sonuç bulunamadı.")
    lines = [f"🔍 \"{query}\" sonuçları:", ""]
    for r in rows:
        brand = f"{r['brand']} " if r["brand"] else ""
        date = str(r["captured_at"])[:10]
        lines.append(f"• {brand}{r['name'][:50]} — {r['price']:.2f} TL ({date})")
    return Response(text="\n".join(lines))
```

- [ ] **Step 4: Testlerin geçtiğini doğrula**

Run: `pytest tests/unit/test_bot_handlers.py -v`
Expected: 8 PASS

- [ ] **Step 5: Commit**

```bash
git add bot/handlers.py tests/unit/test_bot_handlers.py
git commit -m "feat(bot): add command handlers for /start /durum /rapor /trend /fiyat"
```

---

### Task 3: Poll + Dispatch

**Files:**
- Create: `bot/poll.py`
- Create: `tests/integration/test_bot_poll.py`

- [ ] **Step 1: Failing integration testleri yaz**

`tests/integration/test_bot_poll.py`:

```python
import json
import sqlite3
from unittest.mock import patch, MagicMock
import pytest
from bot.poll import poll_once
from bot.state import BotState
from storage.database import init_schema


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    init_schema(c)
    return c


@pytest.fixture
def state(tmp_path):
    return BotState(tmp_path / "bot_state.json")


def _update(update_id: int, chat_id: str, text: str) -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "from": {"id": chat_id},
            "chat": {"id": int(chat_id), "type": "private"},
            "text": text,
        },
    }


def test_poll_once_ignores_unauthorized_chat(conn, state):
    updates = [_update(1, "999", "/durum")]
    with patch("bot.poll._api_get", return_value={"ok": True, "result": updates}) as m_get, \
         patch("bot.poll._api_post") as m_post:
        poll_once(conn, state, bot_token="TOKEN", authorized_chat_id="8364682419")
        assert m_post.call_count == 0  # Hiç yanıt gönderilmedi
    assert state.get_last_update_id() == 1  # Ama state güncellendi


def test_poll_once_handles_durum(conn, state):
    updates = [_update(5, "8364682419", "/durum")]
    with patch("bot.poll._api_get", return_value={"ok": True, "result": updates}), \
         patch("bot.poll._api_post") as m_post:
        poll_once(conn, state, bot_token="TOKEN", authorized_chat_id="8364682419")
        assert m_post.call_count == 1
        call_args = m_post.call_args
        assert "sendMessage" in call_args[0][0]  # endpoint
        assert "tarama" in call_args[1]["json"]["text"].lower()
    assert state.get_last_update_id() == 5


def test_poll_once_offset_prevents_reprocessing(conn, state):
    state.set_last_update_id(10)
    with patch("bot.poll._api_get", return_value={"ok": True, "result": []}) as m_get, \
         patch("bot.poll._api_post"):
        poll_once(conn, state, bot_token="TOKEN", authorized_chat_id="8364682419")
        # getUpdates çağrısı offset=11 içermeli
        params = m_get.call_args[1]["params"]
        assert params["offset"] == 11


def test_poll_once_no_updates_does_nothing(conn, state):
    with patch("bot.poll._api_get", return_value={"ok": True, "result": []}), \
         patch("bot.poll._api_post") as m_post:
        poll_once(conn, state, bot_token="TOKEN", authorized_chat_id="8364682419")
        assert m_post.call_count == 0
    assert state.get_last_update_id() == 0


def test_poll_once_handles_http_error_gracefully(conn, state):
    with patch("bot.poll._api_get", side_effect=Exception("network down")), \
         patch("bot.poll._api_post"):
        # Exception propagate etmemeli
        poll_once(conn, state, bot_token="TOKEN", authorized_chat_id="8364682419")
    assert state.get_last_update_id() == 0  # State bozulmadı
```

- [ ] **Step 2: Testin fail ettiğini doğrula**

Run: `pytest tests/integration/test_bot_poll.py -v`
Expected: `ModuleNotFoundError: No module named 'bot.poll'`

- [ ] **Step 3: `bot/poll.py` oluştur**

```python
import logging
import sqlite3
import sys
from pathlib import Path

import requests

from bot.handlers import (
    Response,
    handle_durum,
    handle_fiyat,
    handle_rapor,
    handle_start,
    handle_trend,
)
from bot.state import BotState
from config import settings
from storage.database import connect, init_schema
from utils.logger import get_logger

log = get_logger("bot")

_API = "https://api.telegram.org"
_STATE_PATH = Path("bot_state.json")

_HANDLERS = {
    "/start": handle_start,
    "/yardim": handle_start,
    "/durum": handle_durum,
    "/rapor": handle_rapor,
    "/trend": handle_trend,
    "/fiyat": handle_fiyat,
}


def _api_get(url: str, params: dict) -> dict:
    r = requests.get(url, params=params, timeout=10)
    return r.json()


def _api_post(url: str, *, json: dict | None = None, data: dict | None = None,
              files: dict | None = None) -> None:
    requests.post(url, json=json, data=data, files=files, timeout=30)


def _send_response(bot_token: str, chat_id: str, response: Response) -> None:
    base = f"{_API}/bot{bot_token}"
    if response.photo_png:
        _api_post(
            f"{base}/sendPhoto",
            data={"chat_id": chat_id, "caption": response.text},
            files={"photo": ("chart.png", response.photo_png, "image/png")},
        )
        return
    if response.document_path:
        with open(response.document_path, "rb") as f:
            _api_post(
                f"{base}/sendDocument",
                data={"chat_id": chat_id, "caption": response.text},
                files={"document": (response.document_path.name, f, "application/pdf")},
            )
        return
    _api_post(f"{base}/sendMessage", json={"chat_id": chat_id, "text": response.text})


def _parse_command(text: str) -> tuple[str, str]:
    """'/trend L'Oréal' -> ('/trend', 'L'Oréal'). Bilinmeyen komut → ('/start', '')."""
    text = text.strip()
    if not text.startswith("/"):
        return "/start", ""
    parts = text.split(maxsplit=1)
    cmd = parts[0].split("@")[0].lower()  # '/trend@bot' -> '/trend'
    args = parts[1] if len(parts) > 1 else ""
    if cmd not in _HANDLERS:
        return "/start", ""
    return cmd, args


def poll_once(
    conn: sqlite3.Connection,
    state: BotState,
    *,
    bot_token: str,
    authorized_chat_id: str,
) -> None:
    """Tek tur: updates al, yetkili komutları işle, state güncelle."""
    if not bot_token or not authorized_chat_id:
        log.warning("Bot token veya chat_id yok, atlandı")
        return

    last = state.get_last_update_id()
    try:
        data = _api_get(
            f"{_API}/bot{bot_token}/getUpdates",
            params={"offset": last + 1, "timeout": 0},
        )
    except Exception as e:
        log.warning(f"getUpdates başarısız: {e}")
        return

    if not data.get("ok"):
        log.warning(f"API hatası: {data}")
        return

    updates = data.get("result", [])
    if not updates:
        return

    max_id = last
    for update in updates:
        update_id = update.get("update_id", 0)
        max_id = max(max_id, update_id)

        msg = update.get("message") or {}
        chat = msg.get("chat") or {}
        chat_id = str(chat.get("id", ""))
        text = msg.get("text", "")

        if chat_id != authorized_chat_id:
            log.info(f"Yetkisiz chat {chat_id} ignore edildi")
            continue

        cmd, args = _parse_command(text)
        handler = _HANDLERS[cmd]
        try:
            response = handler(args, conn)
            _send_response(bot_token, chat_id, response)
        except Exception as e:
            log.error(f"Handler {cmd} çöktü: {e}")
            try:
                _send_response(bot_token, chat_id, Response(text=f"❌ Bir hata oluştu: {e}"))
            except Exception:
                pass

    state.set_last_update_id(max_id)


def main() -> int:
    conn = connect(settings.database_path)
    init_schema(conn)
    state = BotState(_STATE_PATH)
    poll_once(
        conn,
        state,
        bot_token=settings.telegram_bot_token,
        authorized_chat_id=settings.telegram_chat_id,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Integration testlerin geçtiğini doğrula**

Run: `pytest tests/integration/test_bot_poll.py -v`
Expected: 5 PASS

- [ ] **Step 5: Tüm test suite'i çalıştır**

Run: `pytest --tb=short -q`
Expected: Tüm testler PASS (önceki 120 + 17 yeni ~= 137)

- [ ] **Step 6: Commit**

```bash
git add bot/poll.py tests/integration/test_bot_poll.py
git commit -m "feat(bot): add poll loop with command dispatch and auth"
```

---

### Task 4: Task Scheduler Integration

**Files:**
- Create: `bot_poll.bat`

- [ ] **Step 1: `bot_poll.bat` oluştur**

```bat
@echo off
cd /d "c:\Users\altun\Desktop\Yeni klasör\verimadenciligi"
call .venv\Scripts\activate.bat
python -m bot.poll
```

- [ ] **Step 2: Elle tek bir poll çalıştır (token'lar gerçek olduğundan gerçek bağlantı kurulur)**

Run: `python -m bot.poll`
Expected: 1-2 saniye içinde çıkar, hata yoksa sessiz

- [ ] **Step 3: Task Scheduler'a kaydet**

PowerShell'den:
```powershell
$action = New-ScheduledTaskAction -Execute 'c:\Users\altun\Desktop\Yeni klasör\verimadenciligi\bot_poll.bat'
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 2)
Register-ScheduledTask -TaskName 'Metrio Bot Poll' -Action $action -Trigger $trigger -Force
```

- [ ] **Step 4: Elle test**

Telegram'dan yetkili hesaptan `/durum` gönder, 2 dk içinde yanıt gelmeli.

- [ ] **Step 5: Commit**

```bash
git add bot_poll.bat
git commit -m "feat(bot): add Task Scheduler entry point for periodic poll"
```

---

## Self-Review

**Spec coverage:**
- [x] BotState JSON persist → Task 1
- [x] 5 komut handler → Task 2
- [x] Auth filtering → Task 3 `poll_once`
- [x] Offset → Task 3
- [x] HTTP hata yönetimi → Task 3 try/except
- [x] Task Scheduler → Task 4

**Type consistency:**
- `Response` dataclass: aynı fields Task 2 ve Task 3'te
- `handle_*(args: str, conn: sqlite3.Connection) -> Response` imzası tutarlı
- `poll_once(conn, state, *, bot_token, authorized_chat_id)` — keyword-only

**Placeholder yok.** Tüm test ve implementation kodu inline.
