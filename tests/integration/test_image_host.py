import subprocess
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from deals.hosting import GitImageHost, wait_until_live


def _git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout


@pytest.fixture
def repo(tmp_path):
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    _git("init", "--bare", "-b", "main", str(remote), cwd=tmp_path)
    _git("clone", str(remote), str(work), cwd=tmp_path)
    _git("config", "user.email", "bot@test", cwd=work)
    _git("config", "user.name", "bot", cwd=work)
    (work / "README.md").write_text("gorseller")
    _git("add", "-A", cwd=work)
    _git("commit", "-m", "init", cwd=work)
    _git("push", "origin", "main", cwd=work)
    return work, remote


def _cards(tmp_path, names):
    folder = tmp_path / "cards"
    folder.mkdir(exist_ok=True)
    paths = []
    for n in names:
        p = folder / n
        p.write_bytes(b"jpeg")
        paths.append(p)
    return paths


def test_publish_pushes_files_and_returns_public_urls(repo, tmp_path):
    work, remote = repo
    host = GitImageHost(work, "https://raw.example/u/r/main/")

    urls = host.publish(_cards(tmp_path, ["0.jpg", "1.jpg"]), when=datetime(2026, 11, 9, 10, 0))

    assert urls == ["https://raw.example/u/r/main/20261109-1000/0.jpg",
                    "https://raw.example/u/r/main/20261109-1000/1.jpg"]
    pushed = _git("ls-tree", "-r", "--name-only", "main", cwd=remote).split()
    assert "20261109-1000/0.jpg" in pushed and "20261109-1000/1.jpg" in pushed


def test_publish_removes_batches_older_than_a_week(repo, tmp_path):
    work, remote = repo
    host = GitImageHost(work, "https://raw.example/u/r/main")
    host.publish(_cards(tmp_path, ["a.jpg"]), when=datetime(2026, 10, 20, 10, 0))

    host.publish(_cards(tmp_path, ["b.jpg"]), when=datetime(2026, 11, 9, 10, 0))

    pushed = _git("ls-tree", "-r", "--name-only", "main", cwd=remote).split()
    assert "20261109-1000/b.jpg" in pushed
    assert not any(p.startswith("20261020-1000/") for p in pushed)
    assert "README.md" in pushed


def _head(status, ctype="image/jpeg"):
    resp = MagicMock()
    resp.status_code = status
    resp.headers = {"Content-Type": ctype}
    return resp


def test_wait_until_live_polls_until_every_url_serves_an_image():
    sleeps = []
    with patch("deals.hosting.requests.head",
               side_effect=[_head(404), _head(200), _head(200)]):
        ok = wait_until_live(["https://a/0.jpg", "https://a/1.jpg"], timeout=60,
                             interval=5, sleep=sleeps.append)
    assert ok is True
    assert sleeps == [5]


def test_wait_until_live_gives_up_after_timeout():
    with patch("deals.hosting.requests.head", return_value=_head(404)):
        ok = wait_until_live(["https://a/0.jpg"], timeout=10, interval=5, sleep=lambda s: None)
    assert ok is False


def test_remote_url_reports_where_images_are_pushed(repo):
    work, remote = repo
    assert GitImageHost(work, "https://raw.example").remote_url() == str(remote)
