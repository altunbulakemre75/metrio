import json
import shutil
import subprocess

import pytest
from PIL import Image

from deals.video import (CARD_SECONDS, FADE_SECONDS, REEL_SIZE, VideoError, reel_duration,
                         render_reel)

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
                                reason="ffmpeg kurulu değil")


def _cards(tmp_path, n):
    paths = []
    for i, color in zip(range(n), ["gold", "white", "pink", "navy"]):
        p = tmp_path / f"{i}.jpg"
        Image.new("RGB", (1080, 1350), color).save(p, "JPEG")
        paths.append(p)
    return paths


def _probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json",
                          str(path)], check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def test_reel_is_vertical_h264_with_audio_track_and_expected_length(tmp_path):
    out = render_reel(_cards(tmp_path, 3), tmp_path / "reel.mp4")

    info = _probe(out)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    assert (video["width"], video["height"]) == REEL_SIZE
    assert video["codec_name"] == "h264" and video["pix_fmt"] == "yuv420p"
    # Instagram sessiz videoyu bazen reddediyor; sessiz de olsa ses kanalı olmalı.
    assert any(s["codec_type"] == "audio" and s["codec_name"] == "aac" for s in info["streams"])
    assert float(info["format"]["duration"]) == pytest.approx(reel_duration(3), abs=0.2)


def test_six_card_reel_is_short_but_each_card_is_still_readable():
    # TikTok'ta sonuna kadar izlenen kısa video öne çıkıyor; kart yine de ~1,5 sn net görünmeli.
    assert reel_duration(6) <= 10
    assert CARD_SECONDS - FADE_SECONDS >= 1.4


def test_missing_ffmpeg_raises_video_error(tmp_path):
    with pytest.raises(VideoError, match="ffmpeg"):
        render_reel(_cards(tmp_path, 2), tmp_path / "reel.mp4", ffmpeg="ffmpeg-yok-boyle-bir-sey")
