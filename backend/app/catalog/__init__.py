"""Product catalog behind one function, so sources can change without touching the app.

    search_products(category, style=None, max_price=None, max_width=None)

Sources, in order of the plan: DummyJSON (now) -> Amazon Berkeley Objects ->
hand-made Westwing JSON. Add a loader returning list[Product] and list it in
_load().
"""

from functools import cache

from app.catalog import dummyjson
from app.catalog.models import CATEGORIES, Product
from app.config import DATA_DIR

__all__ = ["CATEGORIES", "Product", "get_product", "search_products"]


@cache
def _load() -> dict[str, Product]:
    products = dummyjson.load(DATA_DIR / "catalog" / "dummyjson.json")
    return {p.id: p for p in products}


def get_product(product_id: str) -> Product | None:
    return _load().get(product_id)


def search_products(
    category: str,
    style: str | None = None,
    max_price: float | None = None,
    max_width: float | None = None,
    limit: int = 10,
) -> list[Product]:
    """Cheapest first. Style is a soft filter: products without a style still match."""
    category = category.strip().lower()
    hits = [
        p for p in _load().values()
        if p.category == category
        and (style is None or p.style is None or style.lower() in p.style.lower())
        and (max_price is None or p.price <= max_price)
        and p.fits(max_width)
    ]
    return sorted(hits, key=lambda p: p.price)[:limit]
