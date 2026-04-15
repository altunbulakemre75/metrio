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
