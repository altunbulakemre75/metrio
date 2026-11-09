"""Paylaşım metinleri: TL biçimi, Instagram açıklaması, Telegram mesajı."""
from datetime import datetime

from deals.selector import Deal

_MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
           "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
PLATFORM_NAMES = {"trendyol": "Trendyol", "akakce": "Akakçe", "n11": "N11",
                  "hepsiburada": "Hepsiburada"}
_INSTAGRAM_CAPTION_LIMIT = 2200
_MAX_NAME_IN_CAPTION = 70


def format_tl(amount: float) -> str:
    """345 → '345 TL', 1234.5 → '1.234,50 TL'."""
    whole = round(amount, 2) == int(amount)
    text = f"{amount:,.0f}" if whole else f"{amount:,.2f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".") + " TL"


def turkish_date(when: datetime) -> str:
    return f"{when.day} {_MONTHS[when.month - 1]}"


def product_title(deal: Deal) -> str:
    if deal.brand and not deal.name.casefold().startswith(deal.brand.casefold()):
        return f"{deal.brand} {deal.name}"
    return deal.name


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


def instagram_caption(deals: list[Deal], when: datetime, footer: str, hashtags: str) -> str:
    head = f"Günün kozmetik fırsatları · {turkish_date(when)}"
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
