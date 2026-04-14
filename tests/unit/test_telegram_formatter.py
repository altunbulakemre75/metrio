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
