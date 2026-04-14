from abc import ABC, abstractmethod
from storage.models import ProductSnapshot


class BaseScraper(ABC):
    """Tüm platform scraper'larının uyması gereken arayüz."""

    @abstractmethod
    def fetch_category(
        self,
        category_url: str,
        max_products: int = 500,
    ) -> list[ProductSnapshot]:
        """Kategori sayfasından en fazla max_products adet ürünü çeker."""

    @abstractmethod
    def close(self) -> None:
        """Kaynakları serbest bırakır (browser, bağlantı vb.)."""
