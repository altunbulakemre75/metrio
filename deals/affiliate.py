"""Affiliate linki tek yerden.

Program onayı gelene kadar ürün linki olduğu gibi kullanılır. Onay gelince .env'e
AFFILIATE_URL_TEMPLATE yazılır (örn. "https://…?url={url}"); {url} yerine ürün linki
kodlanmış olarak konur. Trendyol normal günlerde günde en fazla 8 linki komisyona sayıyor;
fazlası düz link kalır. Ücretli/komisyonlu paylaşımda "#işbirliği" etiketi yasal zorunluluk.
"""
import sqlite3
from datetime import datetime
from urllib.parse import quote

DAILY_LIMIT = 8
AFFILIATE_REF = "affiliate"  # posted_deals.post_ref: hangi Telegram paylaşımında affiliate link vardı
DISCLOSURE = "#işbirliği"


def affiliate_url(product_url: str, template: str) -> str:
    if not template:
        return product_url
    return template.replace("{url}", quote(product_url, safe=""))


def affiliate_links_used(conn: sqlite3.Connection, now: datetime) -> int:
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    row = conn.execute(
        "SELECT COUNT(*) FROM posted_deals WHERE channel = 'telegram' AND post_ref = ? "
        "AND posted_at >= ?", (AFFILIATE_REF, start)).fetchone()
    return row[0]


class LinkBudget:
    """Paylaşım sırasıyla (en iyi fırsat önce) günlük affiliate kotasını dağıtır."""

    def __init__(self, template: str, used_today: int, limit: int = DAILY_LIMIT):
        self.template = template
        self.left = max(0, limit - used_today) if template else 0

    def link(self, product_url: str) -> tuple[str, bool]:
        """(kullanılacak link, affiliate mi)."""
        if self.left <= 0:
            return product_url, False
        self.left -= 1
        return affiliate_url(product_url, self.template), True
