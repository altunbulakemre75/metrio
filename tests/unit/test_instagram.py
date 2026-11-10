import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from deals.instagram import InstagramClient, InstagramError, current_token

BASE = "https://graph.instagram.com/v27.0"


def _resp(payload, ok=True):
    r = MagicMock()
    r.ok = ok
    r.json.return_value = payload
    r.text = json.dumps(payload)
    return r


class FakeGraph:
    """graph.instagram.com yerine geçer; çağrıları kaydeder."""

    def __init__(self, statuses=None):
        self.posts = []
        self.gets = []
        self.statuses = statuses or {}
        self._next = 0

    def post(self, url, data=None, timeout=None):
        self.posts.append((url, dict(data or {})))
        if url.endswith("/media_publish"):
            return _resp({"id": "MEDIA1"})
        self._next += 1
        return _resp({"id": f"C{self._next}"})

    def get(self, url, params=None, timeout=None):
        self.gets.append((url, dict(params or {})))
        cid = url.rsplit("/", 1)[-1]
        seq = self.statuses.get(cid, ["FINISHED"])
        status = seq.pop(0) if len(seq) > 1 else seq[0]
        return _resp({"status_code": status, "id": cid})


def _client(graph, sleeps=None):
    return InstagramClient("IGID", "TOKEN", poll_interval=7,
                           sleep=(sleeps.append if sleeps is not None else lambda s: None))


def test_publish_carousel_creates_items_then_album_then_publishes():
    graph = FakeGraph()
    with patch("deals.instagram.requests.post", graph.post), \
         patch("deals.instagram.requests.get", graph.get):
        media_id = _client(graph).publish_carousel(["https://h/0.jpg", "https://h/1.jpg"], "Açıklama")

    assert media_id == "MEDIA1"
    (u1, d1), (u2, d2), (u3, d3), (u4, d4) = graph.posts
    assert u1 == u2 == u3 == f"{BASE}/IGID/media"
    assert d1 == {"image_url": "https://h/0.jpg", "is_carousel_item": "true", "access_token": "TOKEN"}
    assert d2["image_url"] == "https://h/1.jpg"
    assert d3 == {"media_type": "CAROUSEL", "children": "C1,C2", "caption": "Açıklama",
                  "access_token": "TOKEN"}
    assert u4 == f"{BASE}/IGID/media_publish"
    assert d4 == {"creation_id": "C3", "access_token": "TOKEN"}
    assert graph.gets[-1] == (f"{BASE}/C3", {"fields": "status_code", "access_token": "TOKEN"})


def test_single_image_is_published_without_carousel():
    graph = FakeGraph()
    with patch("deals.instagram.requests.post", graph.post), \
         patch("deals.instagram.requests.get", graph.get):
        _client(graph).publish_carousel(["https://h/0.jpg"], "Tek")

    assert graph.posts[0][1] == {"image_url": "https://h/0.jpg", "caption": "Tek", "access_token": "TOKEN"}
    assert graph.posts[1][0].endswith("/media_publish")


def test_waits_while_container_is_in_progress():
    graph = FakeGraph(statuses={"C1": ["IN_PROGRESS", "IN_PROGRESS", "FINISHED"]})
    sleeps = []
    with patch("deals.instagram.requests.post", graph.post), \
         patch("deals.instagram.requests.get", graph.get):
        _client(graph, sleeps).publish_carousel(["https://h/0.jpg"], "x")

    assert sleeps == [7, 7]


def test_container_error_stops_publishing():
    graph = FakeGraph(statuses={"C1": ["ERROR"]})
    with patch("deals.instagram.requests.post", graph.post), \
         patch("deals.instagram.requests.get", graph.get):
        with pytest.raises(InstagramError, match="ERROR"):
            _client(graph).publish_carousel(["https://h/0.jpg"], "x")
    assert not any(u.endswith("/media_publish") for u, _ in graph.posts)


FB_BASE = "https://graph.facebook.com/v27.0"


def test_facebook_token_publishes_through_facebook_graph():
    # Meta'nın "Unified login" yolu EAA… ile başlayan sistem anahtarı veriyor;
    # bu anahtar graph.instagram.com'da "Cannot parse access token" hatası alır.
    graph = FakeGraph()
    with patch("deals.instagram.requests.post", graph.post), \
         patch("deals.instagram.requests.get", graph.get):
        InstagramClient("IGID", "EAAsys").publish_carousel(["https://h/0.jpg"], "x")

    assert graph.posts[0][0] == f"{FB_BASE}/IGID/media"
    assert graph.posts[1][0] == f"{FB_BASE}/IGID/media_publish"


def test_account_with_facebook_token_reads_the_instagram_account_node():
    with patch("deals.instagram.requests.get",
               return_value=_resp({"id": "IGID", "username": "kozmetikavcisi.tr"})) as get:
        account = InstagramClient("IGID", "EAAsys").account()

    assert account == {"user_id": "IGID", "username": "kozmetikavcisi.tr"}
    assert get.call_args.args[0] == f"{FB_BASE}/IGID"
    assert get.call_args.kwargs["params"]["fields"] == "id,username"


class FakeReelGraph(FakeGraph):
    """Reels: konteyner yükleme adresi verir, video rupload'a ham bayt olarak gider."""

    def __init__(self, statuses=None, upload_ok=True):
        super().__init__(statuses)
        self.uploads = []
        self.upload_ok = upload_ok

    def post(self, url, data=None, timeout=None, headers=None):
        if url.startswith("https://rupload.facebook.com/"):
            self.uploads.append((url, dict(headers or {}), data))
            if not self.upload_ok:
                return _resp({"debug_info": {"message": "Upload failed"}}, ok=False)
            return _resp({"success": True})
        resp = super().post(url, data, timeout)
        if url.endswith("/media") and (data or {}).get("media_type") == "REELS":
            cid = resp.json.return_value["id"]
            resp.json.return_value["uri"] = f"https://rupload.facebook.com/ig-api-upload/v27.0/{cid}"
        return resp


def test_publish_reel_uploads_video_file_then_publishes(tmp_path):
    video = tmp_path / "reel.mp4"
    video.write_bytes(b"mp4-bytes")
    graph = FakeReelGraph(statuses={"C1": ["IN_PROGRESS", "FINISHED"]})
    with patch("deals.instagram.requests.post", graph.post), \
         patch("deals.instagram.requests.get", graph.get):
        media_id = InstagramClient("IGID", "EAAsys", sleep=lambda s: None).publish_reel(video, "Açıklama")

    assert media_id == "MEDIA1"
    (u1, d1), (u2, d2) = graph.posts
    assert u1 == f"{FB_BASE}/IGID/media"
    assert d1 == {"media_type": "REELS", "upload_type": "resumable", "caption": "Açıklama",
                  "share_to_feed": "true", "access_token": "EAAsys"}
    url, headers, body = graph.uploads[0]
    assert url == "https://rupload.facebook.com/ig-api-upload/v27.0/C1"
    assert headers == {"Authorization": "OAuth EAAsys", "offset": "0", "file_size": "9"}
    assert body == b"mp4-bytes"
    assert u2 == f"{FB_BASE}/IGID/media_publish" and d2["creation_id"] == "C1"


def test_failed_video_upload_does_not_publish(tmp_path):
    video = tmp_path / "reel.mp4"
    video.write_bytes(b"x")
    graph = FakeReelGraph(upload_ok=False)
    with patch("deals.instagram.requests.post", graph.post), \
         patch("deals.instagram.requests.get", graph.get):
        with pytest.raises(InstagramError, match="Upload failed"):
            InstagramClient("IGID", "EAAsys").publish_reel(video, "x")
    assert not any(u.endswith("/media_publish") for u, _ in graph.posts)


def test_api_error_message_is_raised():
    bad = _resp({"error": {"message": "Invalid OAuth access token", "code": 190}}, ok=False)
    with patch("deals.instagram.requests.post", return_value=bad):
        with pytest.raises(InstagramError, match="Invalid OAuth access token"):
            InstagramClient("IGID", "TOKEN").publish_carousel(["https://h/0.jpg"], "x")


NOW = datetime(2026, 11, 9, 10, 0)


def test_first_run_refreshes_env_token_and_stores_it(tmp_path):
    store = tmp_path / "ig_token.json"
    refresher = MagicMock(return_value="NEW")

    token = current_token(store, env_token="SEED", now=NOW, refresher=refresher)

    assert token == "NEW"
    refresher.assert_called_once_with("SEED")
    saved = json.loads(store.read_text())
    assert saved == {"access_token": "NEW", "seed": "SEED", "refreshed_at": NOW.isoformat()}


def test_recently_refreshed_token_is_reused(tmp_path):
    store = tmp_path / "ig_token.json"
    store.write_text(json.dumps({"access_token": "NEW", "seed": "SEED",
                                 "refreshed_at": (NOW - timedelta(days=2)).isoformat()}))
    refresher = MagicMock()

    assert current_token(store, env_token="SEED", now=NOW, refresher=refresher) == "NEW"
    refresher.assert_not_called()


def test_old_token_is_refreshed_after_a_week(tmp_path):
    store = tmp_path / "ig_token.json"
    store.write_text(json.dumps({"access_token": "NEW", "seed": "SEED",
                                 "refreshed_at": (NOW - timedelta(days=8)).isoformat()}))

    assert current_token(store, env_token="SEED", now=NOW, refresher=lambda t: "NEWER") == "NEWER"


def test_new_env_token_replaces_stored_one(tmp_path):
    store = tmp_path / "ig_token.json"
    store.write_text(json.dumps({"access_token": "OLD", "seed": "SEED",
                                 "refreshed_at": NOW.isoformat()}))

    assert current_token(store, env_token="SEED2", now=NOW, refresher=lambda t: t + "-R") == "SEED2-R"


def test_refresh_failure_falls_back_to_current_token(tmp_path):
    store = tmp_path / "ig_token.json"

    def broken(_):
        raise InstagramError("token 24 saatten yeni")

    assert current_token(store, env_token="SEED", now=NOW, refresher=broken) == "SEED"


def test_facebook_system_token_is_used_as_is_without_refresh(tmp_path):
    # Sistem kullanıcısı anahtarının süresi dolmuyor; ig_refresh_token onu tanımıyor.
    store = tmp_path / "ig_token.json"
    refresher = MagicMock()

    assert current_token(store, env_token="EAAsys", now=NOW, refresher=refresher) == "EAAsys"
    refresher.assert_not_called()
    assert not store.exists()


def test_missing_token_is_an_error(tmp_path):
    with pytest.raises(InstagramError):
        current_token(tmp_path / "none.json", env_token="", now=NOW, refresher=lambda t: t)


def test_media_reach_lists_reach_of_posts_since_given_time():
    since = datetime(2026, 11, 9, 0, 0, tzinfo=timezone.utc)
    reach = {"M2": 69, "M1": 1}

    def fake_get(url, params=None, timeout=None):
        if url == f"{FB_BASE}/IGID/media":
            return _resp({"data": [
                {"id": "M2", "media_type": "VIDEO", "timestamp": "2026-11-10T06:10:00+0000"},
                {"id": "M1", "media_type": "CAROUSEL_ALBUM", "timestamp": "2026-11-09T07:01:00+0000"},
                {"id": "M0", "media_type": "IMAGE", "timestamp": "2026-11-08T23:59:00+0000"},
            ]})
        media_id = url.rsplit("/", 2)[-2]
        assert url.endswith("/insights") and params["metric"] == "reach"
        return _resp({"data": [{"name": "reach", "values": [{"value": reach[media_id]}]}]})

    with patch("deals.instagram.requests.get", fake_get):
        result = InstagramClient("IGID", "EAAsys").media_reach(since)

    assert result == [("VIDEO", 69), ("CAROUSEL_ALBUM", 1)]


def test_followers_count_reads_the_account_node():
    with patch("deals.instagram.requests.get",
               return_value=_resp({"followers_count": 7, "id": "IGID"})) as get:
        assert InstagramClient("IGID", "EAAsys").followers_count() == 7

    assert get.call_args.args[0] == f"{FB_BASE}/IGID"
    assert get.call_args.kwargs["params"]["fields"] == "followers_count"
