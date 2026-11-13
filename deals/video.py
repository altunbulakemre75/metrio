"""Kartlardan Instagram Reels videosu: 1080x1920 (9:16), kartlar arası yumuşak geçiş.

Kartlar 4:5; dikey çerçevede biraz yukarıda durur, çünkü Reels'in alt kısmını
Instagram'ın açıklama ve kullanıcı adı satırı kapatıyor. Sessiz bir ses kanalı
ekleniyor: Instagram ses kanalı olmayan videoyu zaman zaman "desteklenmeyen biçim"
diye reddediyor. Müzik yok (API, Instagram'ın müzik kütüphanesini kullanamıyor).
"""
import subprocess
from pathlib import Path

REEL_SIZE = (1080, 1920)
CARD_SECONDS = 1.8  # TikTok'ta sonuna kadar izlenen kısa video öne çıkıyor
FADE_SECONDS = 0.3
_CARD_TOP = 160
_BG = "0xF6F1EA"  # kartların zemin rengi
_FPS = 30


class VideoError(RuntimeError):
    pass


def reel_duration(card_count: int) -> float:
    """Geçişler üst üste bindiği için her geçiş toplamdan FADE_SECONDS düşer."""
    return card_count * CARD_SECONDS - (card_count - 1) * FADE_SECONDS


def reel_command(cards: list[Path], out: Path, ffmpeg: str = "ffmpeg") -> list[str]:
    width, height = REEL_SIZE
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
    for card in cards:
        cmd += ["-loop", "1", "-t", f"{CARD_SECONDS}", "-i", str(card)]
    total = reel_duration(len(cards))
    cmd += ["-f", "lavfi", "-t", f"{total}", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]

    steps = [
        f"[{i}:v]scale={width}:-2:out_range=tv,pad={width}:{height}:0:{_CARD_TOP}:color={_BG},"
        f"fps={_FPS},format=yuv420p,setsar=1[v{i}]"
        for i in range(len(cards))
    ]
    last = "v0"
    for i in range(1, len(cards)):
        offset = i * (CARD_SECONDS - FADE_SECONDS)
        steps.append(f"[{last}][v{i}]xfade=transition=fade:duration={FADE_SECONDS}:offset={offset}[x{i}]")
        last = f"x{i}"

    cmd += [
        "-filter_complex", ";".join(steps),
        "-map", f"[{last}]", "-map", f"{len(cards)}:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-r", str(_FPS), "-c:a", "aac", "-b:a", "128k", "-shortest",
        "-movflags", "+faststart", str(out),
    ]
    return cmd


def render_reel(cards: list[Path], out: Path, ffmpeg: str = "ffmpeg") -> Path:
    if not cards:
        raise VideoError("videoya konacak kart yok")
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Zamanlanmış görevde (pythonw) ffmpeg için konsol penceresi açılmasın.
        subprocess.run(reel_command(cards, out, ffmpeg), check=True, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=300,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except FileNotFoundError as e:
        raise VideoError(f"ffmpeg bulunamadı ({ffmpeg}); video üretilemedi") from e
    except subprocess.CalledProcessError as e:
        raise VideoError(f"ffmpeg hata verdi: {(e.stderr or '').strip()[-300:]}") from e
    except subprocess.TimeoutExpired as e:
        raise VideoError("ffmpeg 5 dakikada bitmedi") from e
    return out
