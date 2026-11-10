"""Türkiye'de tanınan markalar: seçimde küçük bir öncelik alırlar (deals/selector.py).

Bilinen marka gönderide daha çok kaydediliyor ve tıklanıyor; adı bilinmeyen bir markanın
%45 indirimi, tanınan markanın %35 indiriminin önüne geçmesin diye. Liste elle tutulur,
yazım farkı (büyük harf, Türkçe İ, aksan) önemli değil.
"""
import unicodedata

PREFERRED_BRANDS = (
    # Cilt bakımı, dermokozmetik
    "La Roche-Posay", "Bioderma", "CeraVe", "Vichy", "Avène", "Eucerin", "The Ordinary",
    "The Purest Solutions", "COSRX", "Sinoz", "Dermoskin", "Procsin", "Nivea", "Garnier",
    "Neutrogena", "Bee Beauty",
    # Makyaj
    "L'Oréal Paris", "Maybelline", "Maybelline New York", "Flormar", "Golden Rose", "Pastel",
    "Note", "Essence", "Catrice", "NYX Professional Makeup", "MAC", "Kiko Milano", "Clinique",
    "Estée Lauder",
    # Saç ve kişisel bakım
    "Elidor", "Pantene", "Head & Shoulders", "Wella", "Schwarzkopf", "Gillette Venus", "Braun",
    "Philips",
    # Parfüm
    "Dior", "Chanel", "Yves Saint Laurent", "Lancôme", "Giorgio Armani", "Versace",
    "Carolina Herrera", "Paco Rabanne", "Rabanne", "Victoria's Secret", "Calvin Klein",
    "Hugo Boss", "Lacoste", "Davidoff",
    # Vitamin ve takviye
    "Solgar", "Nutraxin", "Ocean", "Orzax", "Voonka", "Venatura", "Supradyn", "Centrum",
    # Çanta
    "Guess", "Michael Kors", "Pierre Cardin", "U.S. Polo Assn.", "Beverly Hills Polo Club",
    "Mango", "Nine West", "Tommy Hilfiger", "DeFacto", "Koton", "Derimod", "Desa", "Vakko",
)


# TikTok'ta etiketlenecek marka hesapları (2026-11-10'da TikTok aramasıyla tek tek doğrulandı).
# Yalnızca videoda ürünü olan marka etiketlenir; hesabı emin olunmayan marka buraya yazılmaz.
TIKTOK_HANDLES = {
    "Dr. Ümit Aktaş": "umitaktasofficial",
    "Erbatab": "erbatab",
    "Wella": "wellaturkiye",
    "The Ceel": "theceelcom",
    "INO Beauty": "inobeautytr",
    "ICON Care": "iconcaretr",
    "The NewLab": "thenewlab",
    "DeFacto": "defacto",
    "Gillette Venus": "gillettevenus",
}
TRENDYOL_TIKTOK = "trendyolcom"  # Türkiye hesabı; @trendyol uluslararası moda hesabı


def brand_key(brand: str) -> str:
    """"L'ORÉAL PARIS", "L'Oreal Paris" ve "CALLİEL"/"Calliel" aynı anahtara iner."""
    decomposed = unicodedata.normalize("NFKD", brand.casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).strip()
