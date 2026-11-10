"""Instagram API (Instagram ile Giriş) üzerinden gönderi paylaşımı.

Akış: her görsel için konteyner → kaydırmalı gönderi konteyneri → durum FINISHED
olana kadar bekle → media_publish. Belgeler: developers.facebook.com/docs/instagram-platform
"""
import json
import logging
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

import requests

log = logging.getLogger(__name__)

GRAPH_HOST = "https://graph.instagram.com"
FACEBOOK_GRAPH_HOST = "https://graph.facebook.com"
_UPLOAD_HOST = "https://rupload.facebook.com/ig-api-upload"
DEFAULT_API_VERSION = "v27.0"
_REFRESH_AFTER = timedelta(days=7)


class InstagramError(RuntimeError):
    pass


def is_facebook_token(token: str) -> bool:
    """Meta'nın "Unified login" yolu süresiz sistem anahtarı (EAA…) verir.

    Bu anahtar graph.facebook.com'da çalışır; Instagram ile Giriş anahtarı (IGAA…)
    ise graph.instagram.com'da. Paylaşım uç noktaları ikisinde de aynı.
    """
    return token.startswith("EAA")


def _check(resp: requests.Response) -> dict:
    try:
        payload = resp.json()
    except ValueError:
        payload = {}
    if not resp.ok or "error" in payload:
        message = payload.get("error", {}).get("message") or resp.text[:200]
        raise InstagramError(message)
    return payload


class InstagramClient:
    def __init__(
        self,
        user_id: str,
        access_token: str,
        api_version: str = DEFAULT_API_VERSION,
        poll_interval: float = 10,
        max_polls: int = 30,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.user_id = user_id
        self.access_token = access_token
        self.facebook = is_facebook_token(access_token)
        host = FACEBOOK_GRAPH_HOST if self.facebook else GRAPH_HOST
        self.base = f"{host}/{api_version}"
        self.poll_interval = poll_interval
        self.max_polls = max_polls
        self.sleep = sleep

    def publish_carousel(self, image_urls: list[str], caption: str) -> str:
        """Görselleri tek gönderide paylaşır; tek görselse normal gönderi. Medya ID'si döner."""
        if len(image_urls) == 1:
            container = self._create_container({"image_url": image_urls[0], "caption": caption})
        else:
            children = [
                self._create_container({"image_url": url, "is_carousel_item": "true"})
                for url in image_urls
            ]
            container = self._create_container(
                {"media_type": "CAROUSEL", "children": ",".join(children), "caption": caption}
            )
        self._wait_until_ready(container)
        return self._post(f"{self.user_id}/media_publish", {"creation_id": container})["id"]

    def publish_reel(self, video: Path, caption: str) -> str:
        """Videoyu Reels olarak paylaşır (akışta da görünür). Medya ID'si döner.

        Video herkese açık bir adrese konmadan doğrudan yüklenir (resumable upload):
        GitHub ham adresi MP4'ü video türünde sunmuyor.
        """
        created = self._post(f"{self.user_id}/media", {
            "media_type": "REELS", "upload_type": "resumable",
            "caption": caption, "share_to_feed": "true",
        })
        container = created["id"]
        upload_url = created.get("uri") or f"{_UPLOAD_HOST}/{self.base.rsplit('/', 1)[-1]}/{container}"
        data = video.read_bytes()
        _check(requests.post(upload_url, data=data, timeout=300, headers={
            "Authorization": f"OAuth {self.access_token}",
            "offset": "0", "file_size": str(len(data)),
        }))
        self._wait_until_ready(container)
        return self._post(f"{self.user_id}/media_publish", {"creation_id": container})["id"]

    def account(self) -> dict:
        """Kurulum kontrolü: hesap kimliği ve kullanıcı adı."""
        if self.facebook:  # sistem anahtarında "me" sistem kullanıcısıdır, hesap değil
            node = self._get(self.user_id, {"fields": "id,username"})
            return {"user_id": node.get("id"), "username": node.get("username")}
        return self._get("me", {"fields": "user_id,username"})

    def followers_count(self) -> int:
        return int(self._get(self.user_id, {"fields": "followers_count"})["followers_count"])

    def publishing_limit(self) -> dict:
        return self._get(f"{self.user_id}/content_publishing_limit", {"fields": "quota_usage,config"})

    def _create_container(self, params: dict) -> str:
        return self._post(f"{self.user_id}/media", params)["id"]

    def _wait_until_ready(self, container_id: str) -> None:
        for _ in range(self.max_polls):
            status = self._get(container_id, {"fields": "status_code"}).get("status_code")
            if status == "FINISHED":
                return
            if status in ("ERROR", "EXPIRED"):
                raise InstagramError(f"Konteyner {container_id} durumu: {status}")
            self.sleep(self.poll_interval)
        raise InstagramError(f"Konteyner {container_id} hazır olmadı")

    def _post(self, path: str, params: dict) -> dict:
        data = {**params, "access_token": self.access_token}
        return _check(requests.post(f"{self.base}/{path}", data=data, timeout=30))

    def _get(self, path: str, params: dict) -> dict:
        query = {**params, "access_token": self.access_token}
        return _check(requests.get(f"{self.base}/{path}", params=query, timeout=30))


def refresh_long_lived_token(token: str) -> str:
    """60 günlük anahtarı yeniler. Anahtar en az 24 saatlik olmalı."""
    resp = requests.get(
        f"{GRAPH_HOST}/refresh_access_token",
        params={"grant_type": "ig_refresh_token", "access_token": token},
        timeout=30,
    )
    return _check(resp)["access_token"]


def current_token(
    store_path: Path,
    env_token: str,
    now: datetime,
    refresher: Callable[[str], str] = refresh_long_lived_token,
) -> str:
    """Kullanılacak anahtarı verir; haftada bir yeniler ve dosyaya yazar.

    .env'deki anahtar değişirse (yeni anahtar üretildiyse) dosyadakini bırakıp onu kullanır.
    Süresiz sistem anahtarı (EAA…) olduğu gibi kullanılır.
    """
    if is_facebook_token(env_token):
        return env_token
    stored = {}
    if store_path.is_file():
        stored = json.loads(store_path.read_text(encoding="utf-8"))

    if env_token and env_token != stored.get("seed"):
        stored = {"access_token": env_token, "seed": env_token, "refreshed_at": None}
    token = stored.get("access_token")
    if not token:
        raise InstagramError("Instagram erişim anahtarı yok (.env: INSTAGRAM_ACCESS_TOKEN)")

    last = stored.get("refreshed_at")
    if last and now - datetime.fromisoformat(last) < _REFRESH_AFTER:
        return token

    try:
        token = refresher(token)
    except (InstagramError, requests.exceptions.RequestException) as e:
        log.warning(f"Instagram anahtarı yenilenemedi, mevcut anahtarla devam: {e}")
        return token

    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(
        json.dumps({"access_token": token, "seed": stored.get("seed"),
                    "refreshed_at": now.isoformat()}),
        encoding="utf-8",
    )
    return token
