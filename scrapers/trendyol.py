import re


_PRICE_PATTERN = re.compile(r"[\d.,]+")


def parse_price_text(text: str | None) -> float | None:
    """Türkçe formatlı fiyat metnini float'a çevirir.

    Örnekler:
        '299,90 TL'   -> 299.90
        '1.299,90 TL' -> 1299.90
        '100 TL'      -> 100.0
    """
    if not text:
        return None
    match = _PRICE_PATTERN.search(text.strip())
    if not match:
        return None
    raw = match.group()
    # Türkçe: '.' binlik ayırıcı, ',' ondalık
    normalized = raw.replace(".", "").replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return None


def parse_discount_rate(original: float | None, current: float) -> float | None:
    """İndirim oranını 0-1 arası float olarak döndürür.

    original < current veya original geçersizse None döner.
    """
    if original is None or original <= 0:
        return None
    if current > original:
        return None
    return round((original - current) / original, 4)
