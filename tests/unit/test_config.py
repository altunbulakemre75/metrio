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


def test_deals_settings_have_safe_defaults(monkeypatch):
    monkeypatch.setenv("SCRAPER_USER_AGENT", "test-agent")
    monkeypatch.setenv("DEALS_CATEGORIES", "kozmetik, parfum")
    monkeypatch.setenv("DEALS_EXCLUDE_WORDS", "deterjan,çamaşır")

    settings = Settings(_env_file=None)

    assert settings.instagram_enabled is False
    assert settings.deals_category_list == ["kozmetik", "parfum"]
    assert settings.deals_exclude_word_list == ["deterjan", "çamaşır"]
    assert settings.deals_per_post == 5


def test_deals_category_caps_parse_name_and_limit(monkeypatch):
    monkeypatch.setenv("SCRAPER_USER_AGENT", "test-agent")
    monkeypatch.setenv("DEALS_CATEGORY_CAPS", "canta:2, parfum:1")

    assert Settings(_env_file=None).deals_category_cap_map == {"canta": 2, "parfum": 1}
