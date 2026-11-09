"""Instagram için 1080x1350 (4:5) JPEG kartlar: kapak ve ürün başına bir kart."""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from deals.images import trim_white_border
from deals.selector import Deal
from deals.text import PLATFORM_NAMES, format_tl, product_title, turkish_date

CARD_SIZE = (1080, 1350)
_MARGIN = 60

_BG = (246, 241, 234)
_INK = (24, 22, 20)
_MUTED = (118, 110, 102)
_TAG = (255, 210, 63)
_GREEN = (22, 128, 74)
_WHITE = (255, 255, 255)

_WINDOWS_FONTS = Path("C:/Windows/Fonts")
_FONT_FILES = {
    "black": ["seguibl.ttf", "arialbd.ttf"],
    "bold": ["segoeuib.ttf", "arialbd.ttf"],
    "semibold": ["seguisb.ttf", "arialbd.ttf"],
    "regular": ["segoeui.ttf", "arial.ttf"],
}


@dataclass(frozen=True)
class Fonts:
    paths: dict[str, str | None]

    def get(self, weight: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        path = self.paths.get(weight)
        if path:
            return ImageFont.truetype(path, size)
        return ImageFont.load_default(size=size)


def load_fonts(font_dir: str) -> Fonts:
    """Türkçe karakterleri çizebilen sistem fontlarını bulur; yoksa Pillow'un varsayılanı."""
    folder = Path(font_dir) if font_dir else _WINDOWS_FONTS
    paths: dict[str, str | None] = {}
    for weight, names in _FONT_FILES.items():
        found = next((folder / n for n in names if (folder / n).is_file()), None)
        paths[weight] = str(found) if found else None
    return Fonts(paths)


def headline_rate(deal: Deal) -> tuple[float, str] | None:
    """Etikete yazılacak oran: gerçek düşüş varsa o, yoksa satıcının indirimi."""
    if deal.drop_rate:
        return deal.drop_rate, "DÜŞTÜ"
    if deal.discount_rate:
        return deal.discount_rate, "İNDİRİM"
    return None


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int, max_lines: int) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
            continue
        if current:
            lines.append(current)
        current = word
        if len(lines) == max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and " ".join(lines) != " ".join(words):
        last = lines[-1]
        while last and draw.textlength(last + "…", font=font) > max_width:
            last = last[:-1]
        lines[-1] = last.rstrip() + "…"
    return lines


def _fit(img: Image.Image, width: int, height: int) -> Image.Image:
    scale = min(width / img.width, height / img.height)
    size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
    return img.resize(size, Image.Resampling.LANCZOS)


def _pill(draw, xy: tuple[int, int], text: str, font, fill, color) -> None:
    x, y = xy
    width = draw.textlength(text, font=font)
    height = font.size + 26
    draw.rounded_rectangle((x, y, x + width + 48, y + height), radius=height // 2, fill=fill)
    draw.text((x + 24, y + height // 2), text, font=font, fill=color, anchor="lm")


def _save(img: Image.Image, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "JPEG", quality=90, optimize=True)
    return out_path


def render_deal_card(deal: Deal, photo: Image.Image | None, page_name: str,
                     out_path: Path, fonts: Fonts) -> Path:
    img = Image.new("RGB", CARD_SIZE, _BG)
    draw = ImageDraw.Draw(img)
    width, _ = CARD_SIZE
    inner = width - 2 * _MARGIN

    draw.text((_MARGIN, 70), page_name, font=fonts.get("black", 40), fill=_INK, anchor="lm")
    platform = PLATFORM_NAMES.get(deal.platform, deal.platform)
    draw.text((width - _MARGIN, 70), platform, font=fonts.get("semibold", 32),
              fill=_MUTED, anchor="rm")

    box = (_MARGIN, 120, width - _MARGIN, 800)
    draw.rounded_rectangle(box, radius=36, fill=_WHITE)
    if photo is not None:
        fitted = _fit(trim_white_border(photo), box[2] - box[0] - 80, box[3] - box[1] - 60)
        img.paste(fitted, ((width - fitted.width) // 2,
                           box[1] + (box[3] - box[1] - fitted.height) // 2))
    else:
        draw.text((width // 2, (box[1] + box[3]) // 2), "Görsel yok",
                  font=fonts.get("semibold", 40), fill=_MUTED, anchor="mm")

    rate = headline_rate(deal)
    if rate:
        value, label = rate
        draw.rounded_rectangle((40, 100, 330, 270), radius=24, fill=_TAG)
        draw.text((185, 165), f"%{value * 100:.0f}", font=fonts.get("black", 96),
                  fill=_INK, anchor="mm")
        draw.text((185, 240), label, font=fonts.get("bold", 30), fill=_INK, anchor="mm")

    y = 840
    if deal.brand:
        draw.text((_MARGIN, y), deal.brand.upper(), font=fonts.get("semibold", 30), fill=_MUTED)
        y += 48
    name_font = fonts.get("bold", 46)
    for line in _wrap(draw, deal.name, name_font, inner, max_lines=2):
        draw.text((_MARGIN, y), line, font=name_font, fill=_INK)
        y += 58

    price_font = fonts.get("black", 104)
    price_text = format_tl(deal.price)
    price_y = 1100
    draw.text((_MARGIN, price_y), price_text, font=price_font, fill=_INK, anchor="ls")
    old = deal.previous_price if deal.drop_rate else deal.original_price
    if old:
        old_font = fonts.get("regular", 46)
        old_text = format_tl(old)
        x = _MARGIN + draw.textlength(price_text, font=price_font) + 30
        draw.text((x, price_y - 10), old_text, font=old_font, fill=_MUTED, anchor="ls")
        strike_y = price_y - 10 - old_font.size // 3
        draw.line((x, strike_y, x + draw.textlength(old_text, font=old_font), strike_y),
                  fill=_MUTED, width=4)

    if deal.lowest_30d:
        _pill(draw, (_MARGIN, 1150), "SON 30 GÜNÜN EN DÜŞÜK FİYATI",
              fonts.get("bold", 30), _GREEN, _WHITE)
    elif deal.drop_rate:
        _pill(draw, (_MARGIN, 1150), f"ÖNCEKİ FİYATA GÖRE %{deal.drop_rate * 100:.0f} UCUZ",
              fonts.get("bold", 30), _GREEN, _WHITE)

    draw.text((_MARGIN, 1290), "Ürün linki Telegram kanalımızda · link bio'da",
              font=fonts.get("regular", 30), fill=_MUTED, anchor="lm")
    return _save(img, out_path)


def render_cover(deals: list[Deal], when: datetime, page_name: str,
                 out_path: Path, fonts: Fonts) -> Path:
    img = Image.new("RGB", CARD_SIZE, _BG)
    draw = ImageDraw.Draw(img)
    width, _ = CARD_SIZE

    draw.rectangle((0, 0, width, 360), fill=_TAG)
    draw.text((_MARGIN, 70), page_name, font=fonts.get("black", 40), fill=_INK, anchor="lm")
    draw.text((_MARGIN, 200), f"GÜNÜN {len(deals)} FIRSATI", font=fonts.get("black", 92),
              fill=_INK, anchor="lm")
    draw.text((_MARGIN, 300), f"{turkish_date(when)} · kozmetik, parfüm, bakım",
              font=fonts.get("semibold", 38), fill=_INK, anchor="lm")

    y = 420
    tag_font, title_font, sub_font = fonts.get("black", 44), fonts.get("bold", 36), fonts.get("regular", 32)
    for deal in deals[:5]:
        rate = headline_rate(deal)
        tag = f"%{rate[0] * 100:.0f}" if rate else "FIRSAT"
        draw.rounded_rectangle((_MARGIN, y, _MARGIN + 170, y + 110), radius=20, fill=_TAG)
        draw.text((_MARGIN + 85, y + 55), tag, font=tag_font, fill=_INK, anchor="mm")
        text_x = _MARGIN + 200
        title = _wrap(draw, product_title(deal), title_font, width - text_x - _MARGIN, 1)
        draw.text((text_x, y + 32), title[0] if title else "", font=title_font, fill=_INK, anchor="lm")
        platform = PLATFORM_NAMES.get(deal.platform, deal.platform)
        draw.text((text_x, y + 82), f"{format_tl(deal.price)} · {platform}",
                  font=sub_font, fill=_MUTED, anchor="lm")
        y += 150

    draw.text((width - _MARGIN, 1290), "Kaydır →", font=fonts.get("black", 40),
              fill=_INK, anchor="rm")
    draw.text((_MARGIN, 1290), "Linkler Telegram kanalımızda", font=fonts.get("regular", 30),
              fill=_MUTED, anchor="lm")
    return _save(img, out_path)
