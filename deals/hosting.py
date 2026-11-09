"""Kart görsellerini herkese açık bir adrese koyar.

Instagram görseli kendisi indirdiği için JPEG'in internetten erişilebilir olması
gerekiyor. Ayrı bir GitHub reposuna push edip raw.githubusercontent.com adresini
veriyoruz; GitHub Pages derlemesini beklemek gerekmiyor.
"""
import logging
import re
import shutil
import subprocess
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

import requests

log = logging.getLogger(__name__)

_BATCH_FORMAT = "%Y%m%d-%H%M"
_BATCH_DIR = re.compile(r"^\d{8}-\d{4}$")


class HostingError(RuntimeError):
    pass


class GitImageHost:
    def __init__(self, repo_dir: Path | str, base_url: str, keep_days: int = 7):
        self.repo_dir = Path(repo_dir)
        self.base_url = base_url.rstrip("/")
        self.keep_days = keep_days

    def publish(self, files: list[Path], when: datetime) -> list[str]:
        """Dosyaları tarihli klasöre kopyalar, eski klasörleri siler, push eder."""
        batch = when.strftime(_BATCH_FORMAT)
        self._git("pull", "--rebase", "--quiet")

        dest = self.repo_dir / batch
        dest.mkdir(parents=True, exist_ok=True)
        for f in files:
            shutil.copy2(f, dest / f.name)
        self._remove_old_batches(when)

        self._git("add", "-A")
        self._git("commit", "-m", f"Görseller {batch}")
        self._git("push", "origin", "HEAD")
        return [f"{self.base_url}/{batch}/{f.name}" for f in files]

    def remote_url(self) -> str:
        return self._git("remote", "get-url", "origin").strip()

    def _remove_old_batches(self, when: datetime) -> None:
        cutoff = when - timedelta(days=self.keep_days)
        for child in self.repo_dir.iterdir():
            if child.is_dir() and _BATCH_DIR.match(child.name):
                if datetime.strptime(child.name, _BATCH_FORMAT) < cutoff:
                    shutil.rmtree(child)

    def _git(self, *args: str) -> str:
        try:
            return subprocess.run(
                ["git", *args], cwd=self.repo_dir, check=True,
                capture_output=True, text=True, encoding="utf-8",
            ).stdout
        except (subprocess.CalledProcessError, OSError) as e:
            detail = getattr(e, "stderr", "") or str(e)
            raise HostingError(f"git {args[0]} başarısız: {detail.strip()}") from e


def wait_until_live(
    urls: list[str],
    timeout: int = 300,
    interval: int = 10,
    sleep: Callable[[float], None] | None = None,
) -> bool:
    """Her adres görsel döndürene kadar bekler. Süre dolarsa False."""
    if sleep is None:
        import time
        sleep = time.sleep

    pending = list(urls)
    elapsed = 0
    while True:
        pending = [u for u in pending if not _serves_image(u)]
        if not pending:
            return True
        if elapsed >= timeout:
            log.warning(f"Görseller {timeout}s içinde yayına çıkmadı: {pending}")
            return False
        sleep(interval)
        elapsed += interval


def _serves_image(url: str) -> bool:
    try:
        resp = requests.head(url, timeout=10, allow_redirects=True)
    except requests.exceptions.RequestException:
        return False
    return resp.status_code == 200 and resp.headers.get("Content-Type", "").startswith("image/")
