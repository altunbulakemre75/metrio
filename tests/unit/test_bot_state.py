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
