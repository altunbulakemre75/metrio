from dataclasses import dataclass
from datetime import datetime


@dataclass
class ProductSnapshot:
    """Tek bir ürünün belirli bir andaki durumu.

    Scraper'lar bu tipte değer döndürür. Database katmanı bunu `products`
    ve `price_snapshots` tablolarına ayırır.
    """
    # Ürün kimliği
    platform: str
    platform_product_id: str
    name: str
    brand: str | None
    category: str
    product_url: str
    image_url: str | None
    # Anlık veri
    price: float
    original_price: float | None
    discount_rate: float | None
    seller_name: str | None
    seller_rating: float | None
    in_stock: bool
    captured_at: datetime
