from dataclasses import asdict, dataclass

# Our category vocabulary. Matches the SAM concepts (concepts.py) so the
# architect can go from "replace rug_1" to search_products("rug"), plus a few
# things you buy but SAM does not look for.
CATEGORIES = [
    "sofa", "armchair", "chair", "coffee table", "side table", "dining table",
    "tv stand", "shelving unit", "wardrobe", "bed", "lamp", "rug", "cushion",
    "curtain", "potted plant", "vase", "picture frame", "mirror",
    "outdoor furniture", "decor",
]


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

    def to_dict(self) -> dict:
        return asdict(self)

    def fits(self, max_width_cm: float | None) -> bool:
        return max_width_cm is None or self.width_cm is None or self.width_cm <= max_width_cm
