from dataclasses import asdict, dataclass, fields

# Our category vocabulary. Matches the SAM concepts (concepts.py) so the
# architect can go from "replace rug_1" to search_products("rug"), plus a few
# things you buy but SAM does not look for. One exception: SAM finds a
# "picture frame" on the wall, the shop sells a "painting" (PIECE_TO_CATEGORY).
CATEGORIES = [
    "sofa", "armchair", "chair", "coffee table", "side table", "dining table",
    "tv stand", "shelving unit", "wardrobe", "bed", "lamp", "rug", "cushion",
    "curtain", "potted plant", "vase", "painting", "mirror",
    "outdoor furniture", "decor",
]
PIECE_TO_CATEGORY = {"picture frame": "painting"}

STYLES = ["Scandinavian", "Japandi", "Art Deco", "Mid-Century", "Mediterranean"]

# Budgets and comparisons are in EUR; fixed rates are fine for a demo.
TO_EUR = {"EUR": 1.0, "CZK": 1 / 25.2, "USD": 0.92}


@dataclass
class Product:
    id: str
    name: str
    category: str
    style: str | None
    color: str | None
    material: str | None
    price: float
    currency: str
    width_cm: float | None
    depth_cm: float | None
    height_cm: float | None
    image_url: str
    product_url: str
    source: str
    name_en: str | None = None  # English title for matching and the UI

    @classmethod
    def from_dict(cls, d: dict) -> "Product":
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in names})

    @property
    def price_eur(self) -> float:
        return round(self.price * TO_EUR.get(self.currency, 1.0), 2)

    @property
    def image_for_model(self) -> str:
        """Packshot at a size Muse Image needs; Shopify originals are 3000 px."""
        if "cdn.shopify.com" in self.image_url:
            return self.image_url + ("&" if "?" in self.image_url else "?") + "width=1024"
        return self.image_url

    def to_dict(self) -> dict:
        return {**asdict(self), "price_eur": self.price_eur}

    def fits(self, max_width_cm: float | None) -> bool:
        return max_width_cm is None or self.width_cm is None or self.width_cm <= max_width_cm
