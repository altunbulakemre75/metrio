import os
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.environ.get("METRIO_ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    database_path: str = "data/metrio.db"
    categories_file: str = ""

    scraper_max_products: int = Field(default=500, gt=0)
    scraper_headless: bool = True
    scraper_user_agent: str
    scraper_requests_per_second: float = Field(default=1.0, gt=0)
    scraper_min_delay: float = Field(default=1.0, gt=0)
    scraper_max_delay: float = Field(default=3.0, gt=0)
    proxy_enabled: bool = False
    proxy_list: str = ""

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_threshold: float = Field(default=0.20, gt=0, lt=1)
    telegram_enabled: bool = False

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = ""
    email_recipients: str = ""
    email_enabled: bool = False


settings = Settings()
