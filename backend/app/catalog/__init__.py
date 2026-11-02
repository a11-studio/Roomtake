"""Product catalog behind one function, so sources can change without touching the app.

    search_products(category, style=None, max_price=None, max_width=None)

Sources: the hand-picked Westwing list (backend/catalog/curated.json) once it
has products; until then DummyJSON, so the flow still runs. Prices are
compared in EUR.
"""

from functools import cache

from app.catalog import curated, dummyjson
from app.catalog.models import CATEGORIES, STYLES, Product
from app.config import DATA_DIR

__all__ = ["CATEGORIES", "STYLES", "Product", "add_product", "all_products", "get_product",
           "remove_product", "search_products"]


@cache
def _load() -> dict[str, Product]:
    products = curated.load() or dummyjson.load(DATA_DIR / "catalog" / "dummyjson.json")
    return {p.id: p for p in products}


def all_products() -> list[Product]:
    return list(_load().values())


def get_product(product_id: str) -> Product | None:
    return _load().get(product_id)


def add_product(product: Product) -> None:
    items = {p.id: p for p in curated.load()}
    items[product.id] = product
    curated.save(list(items.values()))
    _load.cache_clear()


def remove_product(product_id: str) -> None:
    curated.save([p for p in curated.load() if p.id != product_id])
    _load.cache_clear()


def search_products(
    category: str,
    style: str | None = None,
    max_price: float | None = None,
    max_width: float | None = None,
    limit: int = 10,
) -> list[Product]:
    """Cheapest first. max_price in EUR. Style is a soft filter: products without a style still match."""
    category = category.strip().lower()
    hits = [
        p for p in _load().values()
        if p.category == category
        and (style is None or p.style is None or style.lower() in p.style.lower())
        and (max_price is None or p.price_eur <= max_price)
        and p.fits(max_width)
    ]
    return sorted(hits, key=lambda p: p.price_eur)[:limit]
