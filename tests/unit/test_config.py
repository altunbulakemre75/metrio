import os
from config import Settings


def test_settings_loads_defaults(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_PATH", "data/test.db")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("SCRAPER_MAX_PRODUCTS", "100")
    monkeypatch.setenv("SCRAPER_HEADLESS", "true")
    monkeypatch.setenv("SCRAPER_USER_AGENT", "test-agent")
    monkeypatch.setenv("SCRAPER_REQUESTS_PER_SECOND", "1.0")

    settings = Settings()

    assert settings.app_env == "development"
    assert settings.database_path == "data/test.db"
    assert settings.scraper_max_products == 100
    assert settings.scraper_requests_per_second == 1.0
    assert settings.scraper_headless is True


def test_settings_validates_log_level(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "INVALID")
    monkeypatch.setenv("DATABASE_PATH", "data/test.db")
    monkeypatch.setenv("SCRAPER_USER_AGENT", "test-agent")

    import pytest
    with pytest.raises(Exception):
        Settings()
