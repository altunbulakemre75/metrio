"""Telegram Bot API entegrasyonu."""
import logging
import time
from datetime import datetime

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

    def _send(self, text: str) -> None:
        url = f"{_API_BASE}/bot{self.bot_token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": self.chat_id, "text": text}, timeout=10)
        except requests.exceptions.RequestException as e:
            log.warning(f"Telegram send failed: {e}")
