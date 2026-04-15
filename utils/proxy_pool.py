"""Proxy rotasyonu — Playwright context'ine verilecek proxy config üretir."""
import random
from urllib.parse import urlparse


class ProxyPool:
    """Virgülle ayrılmış proxy listesinden rastgele seçer.

    Disabled modda veya boş listede None döner — scraper proxy kullanmaz.
    """

    def __init__(self, proxy_list: str, enabled: bool):
        self.enabled = enabled
        self.proxies: list[str] = (
            [p.strip() for p in proxy_list.split(",") if p.strip()]
            if proxy_list else []
        )

    def pick(self) -> dict | None:
        if not self.enabled or not self.proxies:
            return None
        url = random.choice(self.proxies)
        parsed = urlparse(url)
        return {
            "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}",
            "username": parsed.username or "",
            "password": parsed.password or "",
        }
