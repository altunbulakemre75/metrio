from unittest.mock import patch

import requests as _rq

from analysis.anomaly import Anomaly
from notifications.telegram import TelegramNotifier


def _fake_anomaly(i: int) -> Anomaly:
    return Anomaly(
        product_id=i, platform_product_id=f"p{i}", name=f"Ürün {i}",
        brand="Marka", category="kozmetik",
        current_price=50.0, average_price=70.0,
        deviation_percent=-0.30, direction="drop",
        confidence="high", snapshot_count=10,
        product_url=f"https://www.trendyol.com/x/urun-p-{i}",
    )


def _stats(saved=10, duration=3, status="success"):
    return {"status": status, "products_saved": saved, "duration_seconds": duration, "error_message": None}


def test_disabled_notifier_does_not_call_api():
    notifier = TelegramNotifier(bot_token="x", chat_id="y", enabled=False)
    with patch("notifications.telegram.requests.post") as mock_post:
        notifier.notify_run(_stats(), anomalies=[])
        assert mock_post.call_count == 0


def test_missing_credentials_disables_notifier():
    notifier = TelegramNotifier(bot_token="", chat_id="", enabled=True)
    with patch("notifications.telegram.requests.post") as mock_post:
        notifier.notify_run(_stats(), anomalies=[])
        assert mock_post.call_count == 0


def test_notify_run_sends_summary_plus_individual_alerts():
    notifier = TelegramNotifier(bot_token="TOK", chat_id="CHT", enabled=True)
    stats = _stats(saved=25, duration=18)
    anomalies = [_fake_anomaly(i) for i in range(3)]

    with patch("notifications.telegram.requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        notifier.notify_run(stats, anomalies)

    assert mock_post.call_count == 4
    first_text = mock_post.call_args_list[0].kwargs["json"]["text"]
    assert "25 ürün" in first_text
    assert "3 anomali" in first_text


def test_notify_run_groups_many_anomalies():
    notifier = TelegramNotifier(bot_token="TOK", chat_id="CHT", enabled=True)
    stats = _stats(saved=50, duration=30)
    anomalies = [_fake_anomaly(i) for i in range(15)]

    with patch("notifications.telegram.requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        notifier.notify_run(stats, anomalies)

    assert mock_post.call_count == 2
    second_text = mock_post.call_args_list[1].kwargs["json"]["text"]
    assert "15 anomali" in second_text
    assert "tane daha" in second_text


def test_notify_run_swallows_network_errors():
    notifier = TelegramNotifier(bot_token="TOK", chat_id="CHT", enabled=True)
    with patch("notifications.telegram.requests.post", side_effect=_rq.exceptions.ConnectionError("no net")):
        notifier.notify_run(_stats(), anomalies=[_fake_anomaly(1)])
