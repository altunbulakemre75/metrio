"""Ürün fotoğrafını indirir; Trendyol küçük önizlemesi yerine büyük boyu ister."""
import io
import logging
import re

import requests
from PIL import Image, ImageChops

log = logging.getLogger(__name__)

# Bu değerin üstündeki pikseller "beyaz boşluk" sayılır (JPEG gürültüsünü yutar).
_WHITE_THRESHOLD = 245
_TRENDYOL_RESIZE = re.compile(r"/mnresize/[^/]+/[^/]+/")
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
)


def full_size_url(url: str) -> str:
    """Trendyol CDN'deki /mnresize/400/-/ kısmını atınca orijinal boy gelir."""
    return _TRENDYOL_RESIZE.sub("/", url, count=1)


def fetch_product_image(url: str, timeout: int = 15) -> Image.Image | None:
    try:
        resp = requests.get(full_size_url(url), timeout=timeout,
                            headers={"User-Agent": _USER_AGENT})
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content))
        img.load()
    except (requests.RequestException, OSError) as e:
        log.warning(f"Ürün görseli indirilemedi ({url}): {e}")
        return None

    if img.mode in ("RGBA", "LA", "P"):
        rgba = img.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return img.convert("RGB")


def trim_white_border(img: Image.Image) -> Image.Image:
    """Ürünün etrafındaki beyaz boşluğu kırpar; karttaki fotoğraf büyük görünsün."""
    rgb = img.convert("RGB")
    diff = ImageChops.difference(rgb, Image.new("RGB", rgb.size, "white"))
    mask = diff.convert("L").point(lambda v: 255 if v > 255 - _WHITE_THRESHOLD else 0)
    box = mask.getbbox()
    return img.crop(box) if box else img
