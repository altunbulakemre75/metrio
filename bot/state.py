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
