from analysis.anomaly import Anomaly
from notifications.formatter import (
    format_daily_summary,
    format_anomaly_alert,
    format_grouped_anomalies,
)


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


def test_anomaly_alert_drop():
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
    a = _fake_anomaly(direction="spike", deviation=0.25)
    text = format_anomaly_alert(a)

    assert "🔺" in text
    assert "FİYAT ARTTI" in text
    assert "+25%" in text


def test_grouped_anomalies_summarizes_excess():
    anomalies = [_fake_anomaly(deviation=-0.30 + i * 0.01) for i in range(12)]
    text = format_grouped_anomalies(anomalies, max_detail=4)

    assert "12 anomali" in text
    detail_lines = [l for l in text.split("\n") if "L'Oréal" in l]
    assert len(detail_lines) == 4
    assert "8 tane daha" in text
