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

    # Kozmetik indirim sayfası (deals/) — Instagram + Telegram kanalı
    deals_page_name: str = "Fırsat Radarı"
    deals_categories: str = "kozmetik,parfum,vitamin,cilt-bakimi"
    deals_per_post: int = Field(default=5, ge=1, le=10)
    deals_min_discount: float = Field(default=0.30, gt=0, lt=1)
    deals_exclude_words: str = "deterjan,çamaşır,bulaşık,yumuşatıcı"
    deals_category_caps: str = ""  # "canta:2" → paylaşım başına en fazla 2 çanta
    deals_special_days: str = ""  # "11-11=11.11" → o gün kapak "11.11 FIRSATLARI"
    deals_repeat_after_days: int = Field(default=14, ge=1)
    deals_caption_footer: str = ("Ürün linkleri Telegram kanalımızda, link bio'da. "
                                 "Kaçırmasın, arkadaşına gönder 👭")
    deals_hashtags: str = "#indirim #kozmetik #fırsat #makyaj #ciltbakımı #parfüm #trendyol"
    deals_font_dir: str = ""
    telegram_channel_id: str = ""
    instagram_enabled: bool = False
    instagram_user_id: str = ""
    instagram_access_token: str = ""
    instagram_api_version: str = "v27.0"
    instagram_reel_hours: str = ""  # "19" → 19:00 paylaşımı kaydırmalı yerine Reels videosu
    image_host_repo_dir: str = ""
    image_host_base_url: str = ""

    @property
    def deals_category_list(self) -> list[str]:
        return [c.strip() for c in self.deals_categories.split(",") if c.strip()]

    @property
    def deals_exclude_word_list(self) -> list[str]:
        return [w.strip() for w in self.deals_exclude_words.split(",") if w.strip()]

    @property
    def deals_special_day_map(self) -> dict[str, str]:
        days = {}
        for item in self.deals_special_days.split(","):
            day, _, label = item.partition("=")
            if day.strip() and label.strip():
                days[day.strip()] = label.strip()
        return days

    @property
    def instagram_reel_hour_set(self) -> set[int]:
        return {int(h) for h in self.instagram_reel_hours.split(",") if h.strip()}

    @property
    def deals_category_cap_map(self) -> dict[str, int]:
        caps = {}
        for item in self.deals_category_caps.split(","):
            name, _, limit = item.partition(":")
            if name.strip() and limit.strip():
                caps[name.strip()] = int(limit)
        return caps


settings = Settings()
