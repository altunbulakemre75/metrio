"""Paylaşım metinleri: TL biçimi, Instagram açıklaması, Telegram mesajı."""
import re
from datetime import datetime

from deals.brands import TIKTOK_HANDLES, TRENDYOL_TIKTOK, brand_key
from deals.selector import Deal

_MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
           "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
PLATFORM_NAMES = {"trendyol": "Trendyol", "akakce": "Akakçe", "n11": "N11",
                  "hepsiburada": "Hepsiburada"}
# Kapakta ve açıklamada görünen sıra.
_CATEGORY_LABELS = {"kozmetik": "kozmetik", "makyaj": "makyaj", "cilt-bakimi": "bakım",
                    "sac-bakimi": "saç bakımı", "parfum": "parfüm", "vitamin": "vitamin",
                    "canta": "çanta"}
_INSTAGRAM_CAPTION_LIMIT = 2200
_MAX_NAME_IN_CAPTION = 70
# Trendyol satıcıları ada barkod (EAN, 8-14 hane) ekliyor; ml/renk kodları kısa kalır.
_BARCODE = re.compile(r"(?<!\S)\d{8,14}(?!\S)")
_TIKTOK_KEYS = {brand_key(b): h for b, h in TIKTOK_HANDLES.items()}
_MAX_BRAND_TAGS = 3


def format_tl(amount: float) -> str:
    """345 → '345 TL', 1234.5 → '1.234,50 TL'."""
    whole = round(amount, 2) == int(amount)
    text = f"{amount:,.0f}" if whole else f"{amount:,.2f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".") + " TL"


def turkish_date(when: datetime) -> str:
    return f"{when.day} {_MONTHS[when.month - 1]}"


def clean_name(name: str) -> str:
    return " ".join(_BARCODE.sub(" ", name).split())


def product_title(deal: Deal) -> str:
    name = clean_name(deal.name)
    if deal.brand and not name.casefold().startswith(deal.brand.casefold()):
        return f"{deal.brand} {name}"
    return name


def card_name(deal: Deal) -> str:
    """Kartta marka ayrı satırda yazdığı için addaki marka tekrarını atar."""
    name = clean_name(deal.name)
    if deal.brand and name.casefold().startswith(deal.brand.casefold()):
        rest = name[len(deal.brand):].strip(" -–")
        return rest or name
    return name


def _short(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def price_note(deal: Deal) -> str:
    """Fiyatın neye göre ucuz olduğunu söyler: üstü çizili fiyat ya da önceki tarama."""
    if deal.drop_rate:
        return f"önceki fiyat {format_tl(deal.previous_price)}, %{deal.drop_rate * 100:.0f} düştü"
    if deal.original_price and deal.discount_rate:
        return f"{format_tl(deal.original_price)} yerine, %{deal.discount_rate * 100:.0f} indirim"
    return ""


def telegram_caption(deal: Deal) -> str:
    lines = [product_title(deal)]
    note = price_note(deal)
    lines.append(f"💰 {format_tl(deal.price)}" + (f" ({note})" if note else ""))
    if deal.lowest_30d:
        lines.append("📉 Son 30 günün en düşük fiyatı")
    lines.append(f"🛒 {PLATFORM_NAMES.get(deal.platform, deal.platform)}: {deal.product_url}")
    return "\n".join(lines)


def category_summary(deals: list[Deal]) -> str:
    """Paylaşımdaki kategoriler, sabit sırada: 'kozmetik, parfüm, çanta'."""
    present = {d.category for d in deals}
    return ", ".join(label for cat, label in _CATEGORY_LABELS.items() if cat in present)


def _headline(deals: list[Deal], when: datetime, label: str = "") -> str:
    """label: özel gün adı (örn. "11.11"); yoksa "Günün"."""
    topic = "kozmetik ve çanta" if any(d.category == "canta" for d in deals) else "kozmetik"
    return f"{label or 'Günün'} {topic} fırsatları · {turkish_date(when)}"


def tiktok_mentions(deals: list[Deal]) -> str:
    """Videodaki markaların TikTok hesapları (en fazla 3) ve Trendyol: "@erbatab @trendyolcom".

    Etiket erişimi kendiliğinden artırmaz; marka bildirimi görüp beğenir ya da yeniden
    paylaşırsa artar. Bu yüzden sadece videoda ürünü olan markalar etiketlenir.
    """
    handles: list[str] = []
    for deal in deals:
        handle = _TIKTOK_KEYS.get(brand_key(deal.brand or ""))
        if handle and handle not in handles and len(handles) < _MAX_BRAND_TAGS:
            handles.append(handle)
    if any(d.platform == "trendyol" for d in deals):
        handles.append(TRENDYOL_TIKTOK)
    return " ".join(f"@{h}" for h in handles)


# Sayıya gelen yönelme eki: 2'ye, 3'e, 6'ya …
_DATIVE = {1: "e", 2: "ye", 3: "e", 4: "e", 5: "e", 6: "ya", 7: "ye", 8: "e", 9: "a", 10: "a"}


def _comment_question(count: int) -> str:
    """İlk satır: yorum yazdıran soru. Kartlardaki numaralarla eşleşir."""
    return f"Hangisini alırdın? 1'den {count}'{_DATIVE.get(count, 'e')} yaz 👇"


def video_caption(deals: list[Deal], when: datetime, channel: str, hashtags: str,
                  label: str = "", mentions: str = "") -> str:
    """TikTok gibi elle yüklenen video için kısa açıklama: ürün listesi yok, kanal adı var."""
    lines = [_comment_question(len(deals)), _headline(deals, when, label),
             f"Fiyatlar {turkish_date(when)} taramasına göredir, değişebilir."]
    if channel:
        lines.append(f"Ürün linkleri Telegram kanalımızda: {channel}")
    if mentions:
        lines += ["", mentions]
    if hashtags:
        lines += ["", hashtags]
    return "\n".join(lines)


def instagram_caption(deals: list[Deal], when: datetime, footer: str, hashtags: str,
                      label: str = "") -> str:
    head = _headline(deals, when, label)
    tail = [f"Fiyatlar {turkish_date(when)} taramasına göredir, değişebilir."]
    if footer:
        tail.append(footer)
    if hashtags:
        tail += ["", hashtags]
    tail_text = "\n".join(tail)

    lines = [head, ""]
    for i, deal in enumerate(deals, start=1):
        note = price_note(deal)
        line = f"{i}. {_short(product_title(deal), _MAX_NAME_IN_CAPTION)}: {format_tl(deal.price)}"
        if note:
            line += f" ({note})"
        if deal.lowest_30d:
            line += " · son 30 günün en düşüğü"
        candidate = "\n".join(lines + [line, "", tail_text])
        if len(candidate) > _INSTAGRAM_CAPTION_LIMIT:
            break
        lines.append(line)
    return "\n".join(lines + ["", tail_text])
