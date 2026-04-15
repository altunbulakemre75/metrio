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
