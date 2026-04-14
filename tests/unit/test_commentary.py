from datetime import datetime
from analysis.commentary import generate_daily_summary
from analysis.price_changes import PriceChange
from analysis.anomaly import Anomaly


def _pc(brand, name, pct):
    return PriceChange(
        product_id=1, platform_product_id="1", name=name, brand=brand,
        category="kozmetik", old_price=100, new_price=100 * (1 + pct),
        change_amount=100 * pct, change_percent=pct,
        captured_at_old=datetime(2026, 4, 1), captured_at_new=datetime(2026, 4, 7),
        product_url="https://example.com",
    )


def _anom(direction, pct):
    return Anomaly(
        product_id=1, platform_product_id="1", name="x", brand="y",
        category="kozmetik", current_price=80, average_price=100,
        deviation_percent=pct, direction=direction, confidence="high",
        snapshot_count=20, product_url="https://example.com",
    )


def test_summary_includes_count():
    movers = [_pc("Nivea", "krem", -0.25), _pc("Loreal", "ruj", -0.15)]
    anomalies = [_anom("drop", -0.30)]
    summary = generate_daily_summary(movers, anomalies, trend_direction="down")
    assert "2" in summary
    assert "Nivea" in summary


def test_summary_handles_empty_inputs():
    summary = generate_daily_summary([], [], trend_direction="flat")
    assert len(summary) > 10
    assert isinstance(summary, str)


def test_summary_mentions_trend_direction():
    summary = generate_daily_summary([], [], trend_direction="up")
    assert "artış" in summary.lower() or "yukarı" in summary.lower() or "zam" in summary.lower()
