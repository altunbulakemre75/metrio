from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    database_path: str = "data/fiyat_radari.db"

    scraper_max_products: int = Field(default=500, gt=0)
    scraper_headless: bool = True
    scraper_user_agent: str
    scraper_requests_per_second: float = Field(default=1.0, gt=0)

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


settings = Settings()
