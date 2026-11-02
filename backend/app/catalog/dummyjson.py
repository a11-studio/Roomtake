"""DummyJSON furniture + home-decoration: ~10 products to wire the flow end to end.

Dimensions in DummyJSON are placeholders, not real centimetres; replaced by
Amazon Berkeley Objects and the Westwing list later.
"""

import json
from pathlib import Path

import httpx

from app.catalog.models import Product

URL = "https://dummyjson.com/products/category/{}?limit=0"
SOURCE_CATEGORIES = ("furniture", "home-decoration")

# First keyword found in the title wins.
TITLE_TO_CATEGORY = [
    ("sofa", "sofa"), ("bed", "bed"), ("bedside table", "side table"),
    ("table lamp", "lamp"), ("lamp", "lamp"), ("chair", "chair"),
    ("photo frame", "picture frame"), ("plant", "potted plant"),
    ("mirror", "mirror"), ("swing", "decor"),
]


def _category(title: str) -> str:
    t = title.lower()
    # check longer keywords first so "bedside table" beats "bed"
    for key, cat in sorted(TITLE_TO_CATEGORY, key=lambda kv: -len(kv[0])):
        if key in t:
            return cat
    return "decor"


def load(cache: Path) -> list[Product]:
    if cache.exists():
        raw = json.loads(cache.read_text())
    else:
        raw = []
        for cat in SOURCE_CATEGORIES:
            raw += httpx.get(URL.format(cat), timeout=30).json()["products"]
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(raw))
    return [
        Product(
            id=f"dummyjson-{p['id']}",
            name=p["title"],
            category=_category(p["title"]),
            style=None,
            color=None,
            material=None,
            price=p["price"],
            currency="USD",
            width_cm=p["dimensions"]["width"],
            depth_cm=p["dimensions"]["depth"],
            height_cm=p["dimensions"]["height"],
            image_url=p["images"][0],
            product_url=f"https://dummyjson.com/products/{p['id']}",
            source="dummyjson",
        )
        for p in raw
    ]
