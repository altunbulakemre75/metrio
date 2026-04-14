import pytest
from scrapers.trendyol import parse_price_text, parse_discount_rate


def test_parse_price_simple():
    assert parse_price_text("299,90 TL") == 299.90


def test_parse_price_with_thousands_separator():
    assert parse_price_text("1.299,90 TL") == 1299.90


def test_parse_price_without_currency():
    assert parse_price_text("149,50") == 149.50


def test_parse_price_with_extra_whitespace():
    assert parse_price_text("  299,90 TL  ") == 299.90


def test_parse_price_integer_only():
    assert parse_price_text("100 TL") == 100.0


def test_parse_price_invalid_returns_none():
    assert parse_price_text("") is None
    assert parse_price_text("fiyat yok") is None
    assert parse_price_text(None) is None


def test_parse_discount_rate_calculates_correctly():
    assert parse_discount_rate(original=200.0, current=150.0) == pytest.approx(0.25)


def test_parse_discount_rate_no_discount():
    assert parse_discount_rate(original=100.0, current=100.0) == 0.0


def test_parse_discount_rate_returns_none_when_no_original():
    assert parse_discount_rate(original=None, current=100.0) is None


def test_parse_discount_rate_returns_none_when_invalid():
    assert parse_discount_rate(original=0.0, current=100.0) is None
    assert parse_discount_rate(original=100.0, current=150.0) is None  # current > original
