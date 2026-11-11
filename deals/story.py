""""Bu indirim gerçek mi?" videosu: tek ürünün aylara yayılan fiyat geçmişi ve hükmü.

Kullanım:
    python -m deals.story              # videoyu üret, açıklamasıyla yönetici sohbetine gönder
    python -m deals.story --dry-run    # sadece kartları ve videoyu üret (data/deals/gercekmi-…)

Video elle paylaşılır (müzik uygulamadan eklenir). Hüküm yalnızca kendi kayıtlarımıza
dayanır; aradaki boşluklar grafikte kesik çizgiyle gösterilir.
"""
import argparse
import io
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw

from deals.brands import brand_key
from deals.card import (_BG, _GREEN, _INK, _MARGIN, _MUTED, _TAG, _WHITE, CARD_SIZE, Fonts, _fit,
                        _save, _wrap)
from deals.images import trim_white_border
from deals.text import _MONTHS, clean_name, format_tl

STORY_CHANNEL = "story"
_CATEGORIES = ("kozmetik", "parfum", "cilt-bakimi")
_MIN_SPAN = timedelta(days=60)
_MIN_DAYS = 4
_REAL_DROP = 0.15       # ilk kayda göre en az bu kadar ucuzsa "gerçek"
_LABEL_DISCOUNT = 0.20  # etiket en az bu kadar indirim iddia ediyorsa incelenir
_GAP = timedelta(days=30)
# Tek ürünlük videoda tanınan marka, adı bilinmeyen markanın daha büyük farkından değerli.
_BRAND_BONUS = 0.5
_RED = (190, 50, 40)
# "Nisan'da", "Mart'ta", "Eylül'de": bulunma eki ve "-dan beri" eki ay adına göre değişir.
_IN = ["ta", "ta", "ta", "da", "ta", "da", "da", "ta", "de", "de", "da", "ta"]
_SINCE = ["tan", "tan", "tan", "dan", "tan", "dan", "dan", "tan", "den", "den", "dan", "tan"]


@dataclass(frozen=True)
class PriceStory:
    product_id: int
    name: str
    brand: str | None
    product_url: str
    image_url: str
    points: list[tuple[datetime, float]]  # gün başına son fiyat, eskiden yeniye
    original_price: float | None

    @property
    def price(self) -> float:
        return self.points[-1][1]

    @property
    def first_price(self) -> float:
        return self.points[0][1]

    @property
    def first_month(self) -> int:
        return self.points[0][0].month

    @property
    def title(self) -> str:
        name = clean_name(self.name)
        if self.brand and not name.casefold().startswith(self.brand.casefold()):
            return f"{self.brand} {name}"
        return name

    @property
    def verdict(self) -> str | None:
        """"real": kayıtlarımızdaki en düşük fiyat ve ilk kayıttan belirgin ucuz.
        "not_real": etiket indirim diyor ama fiyat aylar önceki fiyattan ucuz değil."""
        lowest = min(p for _, p in self.points)
        if self.price <= lowest * 1.01 and self.price <= self.first_price * (1 - _REAL_DROP):
            return "real"
        if (self.original_price and self.price <= self.original_price * (1 - _LABEL_DISCOUNT)
                and self.price >= self.first_price * 0.97):
            return "not_real"
        return None

    @property
    def strength(self) -> float:
        if self.verdict == "real":
            return 1 - self.price / self.first_price
        return 1 - self.price / (self.original_price or self.price)


def _month_in(month: int) -> str:
    return f"{_MONTHS[month - 1]}'{_IN[month - 1]}"


def verdict_lines(story: PriceStory) -> list[str]:
    then = f"{_month_in(story.first_month)} {format_tl(story.first_price)}'ydi"
    if story.verdict == "real":
        since = f"{_MONTHS[story.first_month - 1]}'{_SINCE[story.first_month - 1]}"
        return ["EVET, GERÇEK", f"{then}, bugün {format_tl(story.price)}.",
                f"{since} beri kayıtlarımızdaki en düşük fiyat."]
    return ["ASLINDA UCUZLAMADI",
            f"Etikette {format_tl(story.original_price or 0)} yerine {format_tl(story.price)} yazıyor.",
            f"Ama {then}."]


def story_caption(story: PriceStory, channel: str, hashtags: str) -> str:
    _, *facts = verdict_lines(story)
    lines = [f"Bu indirim gerçek mi? {story.title}", *facts,
             "Karşılaştırma, kendi tuttuğumuz fiyat kayıtlarına göredir."]
    if channel:
        lines.append(f"Ürün linki Telegram kanalımızda: {channel}")
    if hashtags:
        lines += ["", hashtags]
    return "\n".join(lines)


def pick_story(conn: sqlite3.Connection, now: datetime, *, exclude_ids: set[int] | frozenset[int] = frozenset(),
               preferred_brands: tuple[str, ...] = (),
               max_age: timedelta = timedelta(hours=36)) -> PriceStory | None:
    """Hükmü net olan, fiyatı taze ve geçmişi aylara yayılan en çarpıcı ürünü seçer."""
    products = conn.execute(
        """SELECT p.id, p.name, p.brand, p.product_url, p.image_url
            FROM products p JOIN price_snapshots s ON s.product_id = p.id
            WHERE p.platform = 'trendyol' AND p.category IN (?, ?, ?)
            GROUP BY p.id
            HAVING MIN(s.captured_at) <= ? AND MAX(s.captured_at) >= ?""",
        (*_CATEGORIES, now - _MIN_SPAN, now - max_age),
    ).fetchall()
    known = {brand_key(b) for b in preferred_brands}
    best, best_rank = None, -1.0
    for pid, name, brand, url, image in products:
        if pid in exclude_ids or not image:
            continue
        rows = conn.execute(
            "SELECT captured_at, price, original_price, in_stock FROM price_snapshots "
            "WHERE product_id = ? ORDER BY captured_at", (pid,)).fetchall()
        if not rows[-1][3]:
            continue
        daily: dict[str, tuple[datetime, float]] = {}
        for captured, price, _, _ in rows:
            when = captured if isinstance(captured, datetime) else datetime.fromisoformat(captured)
            daily[when.strftime("%Y-%m-%d")] = (when, price)
        if len(daily) < _MIN_DAYS:
            continue
        story = PriceStory(pid, name, brand, url, image, list(daily.values()), rows[-1][2])
        if story.verdict is None:
            continue
        rank = story.strength + (_BRAND_BONUS if brand and brand_key(brand) in known else 0.0)
        if rank > best_rank:
            best, best_rank = story, rank
    return best


def _header(draw, page_name: str, fonts: Fonts) -> None:
    draw.text((_MARGIN, 70), page_name, font=fonts.get("black", 40), fill=_INK, anchor="lm")
    draw.text((CARD_SIZE[0] - _MARGIN, 70), "Bu indirim gerçek mi?",
              font=fonts.get("semibold", 32), fill=_MUTED, anchor="rm")


def _dashed(draw, a, b, fill, width: int, dash: int = 14) -> None:
    (x1, y1), (x2, y2) = a, b
    length = max(1.0, ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5)
    for i in range(0, int(length), dash * 2):
        s, e = i / length, min(1.0, (i + dash) / length)
        draw.line((x1 + (x2 - x1) * s, y1 + (y2 - y1) * s, x1 + (x2 - x1) * e, y1 + (y2 - y1) * e),
                  fill=fill, width=width)


def _hook_card(story: PriceStory, photo, page_name: str, out: Path, fonts: Fonts) -> Path:
    img = Image.new("RGB", CARD_SIZE, _BG)
    draw = ImageDraw.Draw(img)
    width = CARD_SIZE[0]
    _header(draw, page_name, fonts)
    box = (_MARGIN, 120, width - _MARGIN, 760)
    draw.rounded_rectangle(box, radius=36, fill=_WHITE)
    if photo is not None:
        fitted = _fit(trim_white_border(photo), box[2] - box[0] - 80, box[3] - box[1] - 60)
        img.paste(fitted, ((width - fitted.width) // 2,
                           box[1] + (box[3] - box[1] - fitted.height) // 2))
    draw.rounded_rectangle((_MARGIN, 800, width - _MARGIN, 1010), radius=28, fill=_TAG)
    draw.text((width // 2, 905), "BU İNDİRİM GERÇEK Mİ?", font=fonts.get("black", 72),
              fill=_INK, anchor="mm")
    y = 1050
    name_font = fonts.get("bold", 44)
    for line in _wrap(draw, story.title, name_font, width - 2 * _MARGIN, max_lines=2):
        draw.text((_MARGIN, y), line, font=name_font, fill=_INK)
        y += 56
    label = f"Bugün {format_tl(story.price)}"
    if story.original_price and story.original_price > story.price:
        label += f" · etikette {format_tl(story.original_price)} yerine"
    draw.text((_MARGIN, y + 20), label, font=fonts.get("semibold", 38), fill=_MUTED)
    return _save(img, out)


def _chart_card(story: PriceStory, page_name: str, out: Path, fonts: Fonts) -> Path:
    img = Image.new("RGB", CARD_SIZE, _BG)
    draw = ImageDraw.Draw(img)
    width = CARD_SIZE[0]
    _header(draw, page_name, fonts)
    draw.text((_MARGIN, 190), "FİYAT GEÇMİŞİ", font=fonts.get("black", 76), fill=_INK, anchor="lm")
    draw.text((_MARGIN, 270), "Kendi kayıtlarımız, Trendyol", font=fonts.get("regular", 34),
              fill=_MUTED, anchor="lm")

    left, top, right, bottom = _MARGIN + 30, 430, width - _MARGIN - 30, 1050
    draw.rounded_rectangle((_MARGIN, 340, width - _MARGIN, 1160), radius=36, fill=_WHITE)
    prices = [p for _, p in story.points]
    low, high = min(prices), max(prices)
    spread = (high - low) or 1.0
    start, end = story.points[0][0], story.points[-1][0]
    total = (end - start).total_seconds() or 1.0

    def xy(when: datetime, price: float) -> tuple[float, float]:
        return (left + (right - left) * (when - start).total_seconds() / total,
                bottom - (bottom - top) * (price - low) / spread)

    color = _GREEN if story.verdict == "real" else _RED
    dots = [xy(w, p) for w, p in story.points]
    for (a, b), ((wa, _), (wb, _)) in zip(zip(dots, dots[1:]), zip(story.points, story.points[1:])):
        if wb - wa > _GAP:  # arada kayıt yok: düz çizgi veri varmış gibi göstermesin
            _dashed(draw, a, b, _MUTED, 5)
        else:
            draw.line((*a, *b), fill=color, width=8)
    for x, y in dots:
        draw.ellipse((x - 9, y - 9, x + 9, y + 9), fill=color)
    fx, fy = dots[0]
    lx, ly = dots[-1]
    draw.ellipse((lx - 18, ly - 18, lx + 18, ly + 18), fill=color, outline=_WHITE, width=5)
    tag = fonts.get("bold", 40)
    draw.text((fx, fy - 30), format_tl(story.first_price), font=tag, fill=_INK, anchor="lb")
    draw.text((lx, ly - 34), format_tl(story.price), font=tag, fill=color, anchor="rb")
    axis = fonts.get("semibold", 34)
    draw.text((left, 1105), f"{_MONTHS[start.month - 1]} {start.year}", font=axis,
              fill=_MUTED, anchor="lm")
    draw.text((right, 1105), "Bugün", font=axis, fill=_MUTED, anchor="rm")
    if any(wb - wa > _GAP for (wa, _), (wb, _) in zip(story.points, story.points[1:])):
        draw.text((_MARGIN, 1215), "Kesik çizgi: o aralıkta kayıt yok.",
                  font=fonts.get("regular", 30), fill=_MUTED, anchor="lm")
    return _save(img, out)


def _verdict_card(story: PriceStory, page_name: str, out: Path, fonts: Fonts) -> Path:
    img = Image.new("RGB", CARD_SIZE, _BG)
    draw = ImageDraw.Draw(img)
    width = CARD_SIZE[0]
    _header(draw, page_name, fonts)
    head, *facts = verdict_lines(story)
    color = _GREEN if story.verdict == "real" else _RED
    draw.rounded_rectangle((_MARGIN, 300, width - _MARGIN, 560), radius=36, fill=color)
    head_font = fonts.get("black", 84 if len(head) <= 13 else 66)
    draw.text((width // 2, 430), head, font=head_font, fill=_WHITE, anchor="mm")
    y = 660
    fact_font = fonts.get("bold", 50)
    for fact in facts:
        for line in _wrap(draw, fact, fact_font, width - 2 * _MARGIN, max_lines=3):
            draw.text((_MARGIN, y), line, font=fact_font, fill=_INK)
            y += 68
        y += 30
    draw.text((_MARGIN, 1210), "Kaynak: kendi fiyat kayıtlarımız.", font=fonts.get("semibold", 36),
              fill=_MUTED, anchor="lm")
    draw.text((_MARGIN, 1270), "Takip et, ürün linki Telegram kanalımızda.",
              font=fonts.get("semibold", 36), fill=_INK, anchor="lm")
    return _save(img, out)


def render_story_cards(story: PriceStory, photo: Image.Image | None, page_name: str,
                       out_dir: Path, fonts: Fonts) -> list[Path]:
    return [_hook_card(story, photo, page_name, out_dir / "1.jpg", fonts),
            _chart_card(story, page_name, out_dir / "2.jpg", fonts),
            _verdict_card(story, page_name, out_dir / "3.jpg", fonts)]


def _told_ids(conn: sqlite3.Connection) -> set[int]:
    rows = conn.execute("SELECT DISTINCT product_id FROM posted_deals WHERE channel = ?",
                        (STORY_CHANNEL,)).fetchall()
    return {r[0] for r in rows}


def main(argv: list[str] | None = None) -> int:
    from config import settings
    from deals.brands import PREFERRED_BRANDS
    from deals.card import load_fonts
    from deals.images import fetch_product_image
    from deals.video import render_reel
    from notifications.telegram import TelegramNotifier, send_video
    from storage.database import connect, init_schema, record_posted_deals

    parser = argparse.ArgumentParser(description='"Bu indirim gerçek mi?" videosu')
    parser.add_argument("--dry-run", action="store_true", help="Gönderme, sadece üret")
    args = parser.parse_args(argv)
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")

    now = datetime.now()
    conn = connect(settings.database_path)
    init_schema(conn)
    story = pick_story(conn, now, exclude_ids=_told_ids(conn), preferred_brands=PREFERRED_BRANDS)
    if story is None:
        print("Anlatılacak ürün bulunamadı (taze fiyatı ve net hükmü olan yok).")
        return 1
    out_dir = Path("data/deals") / f"gercekmi-{now:%Y%m%d-%H%M}"
    cards = render_story_cards(story, fetch_product_image(story.image_url),
                               settings.deals_page_name, out_dir, load_fonts(settings.deals_font_dir))
    video = render_reel(cards, out_dir / "reel.mp4")
    caption = story_caption(story, settings.telegram_channel_id, settings.deals_hashtags)
    print(f"{story.title}\n{story.product_url}\n{video}\n\n{caption}")
    if args.dry_run:
        return 0
    admin = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id,
                             settings.telegram_enabled)
    admin.send_text('🎬 "Bu indirim gerçek mi?" videosu hazır. Müziği ekleyip Instagram ve '
                    f"TikTok'a sen paylaşıyorsun.\nÜrün: {story.product_url}")
    if not send_video(settings.telegram_bot_token, settings.telegram_chat_id, video, caption):
        return 1
    record_posted_deals(conn, [story.product_id], STORY_CHANNEL, None, now)
    return 0


if __name__ == "__main__":
    sys.exit(main())
