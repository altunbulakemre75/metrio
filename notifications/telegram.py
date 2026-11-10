"""Telegram Bot API entegrasyonu."""
import logging
import time
from datetime import datetime
from pathlib import Path

import requests

from notifications.formatter import (
    format_anomaly_alert,
    format_daily_summary,
    format_grouped_anomalies,
)

log = logging.getLogger(__name__)

_API_BASE = "https://api.telegram.org"
_MAX_INDIVIDUAL_ALERTS = 10
_INTER_MESSAGE_DELAY = 0.1
_CAPTION_LIMIT = 1024


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str, enabled: bool):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled and bool(bot_token) and bool(chat_id)

    def notify_run(self, stats: dict, anomalies: list) -> None:
        if not self.enabled:
            return

        date_str = datetime.now().strftime("%Y-%m-%d")
        summary = format_daily_summary(stats, anomaly_count=len(anomalies), date_str=date_str)
        self._send(summary)

        if not anomalies:
            return

        if len(anomalies) <= _MAX_INDIVIDUAL_ALERTS:
            for a in anomalies:
                time.sleep(_INTER_MESSAGE_DELAY)
                self._send(format_anomaly_alert(a))
        else:
            time.sleep(_INTER_MESSAGE_DELAY)
            self._send(format_grouped_anomalies(anomalies))

    def send_text(self, text: str) -> None:
        """Yönetici sohbetine serbest mesaj (ör. paylaşım hatası)."""
        if self.enabled:
            self._send(text)

    def _send(self, text: str) -> None:
        url = f"{_API_BASE}/bot{self.bot_token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": self.chat_id, "text": text}, timeout=10)
        except requests.exceptions.RequestException as e:
            log.warning(f"Telegram send failed: {e}")


def send_photo(bot_token: str, chat_id: str, photo_path: Path, caption: str) -> bool:
    """Kanala ya da sohbete fotoğraf + açıklama gönderir. Başarılıysa True."""
    url = f"{_API_BASE}/bot{bot_token}/sendPhoto"
    try:
        resp = requests.post(
            url,
            data={"chat_id": chat_id, "caption": caption[:_CAPTION_LIMIT]},
            files={"photo": (photo_path.name, photo_path.read_bytes(), "image/jpeg")},
            timeout=30,
        )
    except requests.exceptions.RequestException as e:
        log.warning(f"Telegram sendPhoto failed: {e}")
        return False
    if not resp.ok:
        log.warning(f"Telegram sendPhoto rejected: {resp.text[:200]}")
    return bool(resp.ok)


def send_video(bot_token: str, chat_id: str, video_path: Path, caption: str) -> bool:
    """Sohbete MP4 + açıklama gönderir (Telegram'ın bot dosya sınırı 50 MB). Başarılıysa True."""
    url = f"{_API_BASE}/bot{bot_token}/sendVideo"
    try:
        resp = requests.post(
            url,
            data={"chat_id": chat_id, "caption": caption[:_CAPTION_LIMIT],
                  "supports_streaming": "true"},
            files={"video": (video_path.name, video_path.read_bytes(), "video/mp4")},
            timeout=120,
        )
    except requests.exceptions.RequestException as e:
        log.warning(f"Telegram sendVideo failed: {e}")
        return False
    if not resp.ok:
        log.warning(f"Telegram sendVideo rejected: {resp.text[:200]}")
    return bool(resp.ok)


def chat_member_count(bot_token: str, chat_id: str) -> int:
    """Kanal/grup üye sayısı (bot kanalda yönetici olmalı). Hata olursa RuntimeError."""
    resp = requests.get(f"{_API_BASE}/bot{bot_token}/getChatMemberCount",
                        params={"chat_id": chat_id}, timeout=15)
    body = resp.json()
    if not body.get("ok"):
        raise RuntimeError(f"Telegram getChatMemberCount: {body.get('description')}")
    return int(body["result"])
