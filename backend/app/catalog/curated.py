"""Hand-picked products (Westwing), kept in the repo as backend/catalog/curated.json.

Products are added one at a time from a pasted product URL (import_url),
never by crawling the shop: the page's schema.org data gives name, price,
colour, material, dimensions and a clean packshot; Muse Spark looks at the
packshot to fill in our category, an English title and style tags. Every
product links back to the shop.
"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.catalog.models import CATEGORIES, STYLES, Product
from app.config import HELPER_MODEL, REPO_ROOT
from app.meta_client import async_client

FILE = REPO_ROOT / "backend" / "catalog" / "curated.json"
ALLOWED_HOST = re.compile(r"(^|\.)westwing\.[a-z]{2,3}$")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def load(path: Path = FILE) -> list[Product]:
    if not path.exists():
        return []
    return [Product.from_dict(p) for p in json.loads(path.read_text())]


def save(products: list[Product], path: Path = FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = sorted((p.to_dict() for p in products), key=lambda p: (p["category"], p["price_eur"]))
    for p in data:
        p.pop("price_eur")
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def _ld_products(html: str) -> list[dict]:
    """schema.org Product entries (variants of a ProductGroup, or a single Product)."""
    out = []
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        nodes = data.get("@graph", [data]) if isinstance(data, dict) else data
        for node in nodes:
            if node.get("@type") == "ProductGroup":
                out += [v | {"_group": node} for v in node.get("hasVariant", [])]
            elif node.get("@type") == "Product":
                out.append(node)
    return out


CURRENCY_SIGNS = {"€": "EUR", "Kč": "CZK", "zł": "PLN", "Ft": "HUF", "CHF": "CHF"}


def _html_product(html: str, url: str) -> dict | None:
    """The shown variant from the page itself, for shop pages without schema.org
    data (Westwing's newer Shopify storefront): name and packshot from the Open
    Graph tags, the price as rendered, dimensions from the page's filter data.
    Returned in the schema.org shape that import_url reads."""
    def meta(prop: str) -> str | None:
        m = re.search(rf'<meta property="{prop}" content="([^"]+)"', html)
        return m and m.group(1)

    name, image = meta("og:title"), meta("og:image:secure_url") or meta("og:image")
    # the current price: "product-price", or "product-sale-price" next to a struck-out one
    price = re.search(r'data-testid="product-(?:sale-)?price">([^<]+)<', html)
    if not (name and image and price):
        return None
    # "2 299 €", "2.299,00 €", "1,299.00 €": drop thousands separators, keep the decimal
    digits = re.sub(r"[^\d,.]", "", price.group(1))
    amount = re.sub(r"[.,](?=\d{3}\b)", "", digits).replace(",", ".")
    sign = next((c for s, c in CURRENCY_SIGNS.items() if s in price.group(1)), "EUR")
    sku = re.search(r"[?&]simple=([A-Za-z0-9-]+)", url) or re.search(r"/files/([A-Za-z0-9-]+)_", image)
    size = dict(re.findall(r'filter(Width|Height|Depth)\\",\{[^}]*\},\\"([\d.]+)\\"', html))
    return {
        "name": re.split(r"\s*[❘|]\s*Westwing", name)[0].strip(),
        "sku": sku.group(1) if sku else name,
        "image": image.replace("&amp;", "&"),
        "offers": {"price": amount, "priceCurrency": sign},
        **{k.lower(): {"value": v} for k, v in size.items()},
    }


def _image(node: dict) -> str | None:
    """schema.org image: a URL, an ImageObject, or a list of either."""
    img = node.get("image")
    img = img[0] if isinstance(img, list) and img else img
    if isinstance(img, dict):
        img = img.get("url") or img.get("contentUrl")
    return img if isinstance(img, str) else None


def _offer(node: dict) -> dict:
    offer = node.get("offers") or {}
    return (offer[0] if offer else {}) if isinstance(offer, list) else offer


def _cm(v: dict | None) -> float | None:
    return float(v["value"]) if isinstance(v, dict) and v.get("value") is not None else None


async def _classify(name: str, color: str, material: str, image_url: str) -> dict:
    """Muse Spark: category, English title, colour, material, styles from the packshot."""
    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": UA}) as http:
        img = (await http.get(image_url + ("&" if "?" in image_url else "?") + "width=600")).content
    text = f"""This is a product from a furniture shop: "{name}" (colour: {color}, material: {material}).
Reply with JSON only:
{{"category": one of {CATEGORIES},
  "name_en": short English product title (3-6 words, keep the model name),
  "color": colour in English, "material": material in English,
  "styles": the 1-3 best fitting of {STYLES}}}"""
    async with async_client() as api:
        r = await api.chat.completions.create(model=HELPER_MODEL, messages=[{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(img).decode()}},
            {"type": "text", "text": text},
        ]}])
    m = re.search(r"\{.*\}", r.choices[0].message.content or "", re.S)
    return json.loads(m.group(0)) if m else {}


async def import_url(url: str) -> list[dict]:
    """All variants on one product page, ready to review and save."""
    host = urlparse(url).hostname or ""
    if not ALLOWED_HOST.search(host):
        raise ValueError("Only Westwing product pages can be imported.")
    async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers={"User-Agent": UA}) as http:
        r = await http.get(url)
    r.raise_for_status()
    variants = _ld_products(r.text)
    if not variants and (shown := _html_product(r.text, str(r.url))):
        variants = [shown]
    if not variants:
        raise ValueError("No product data found on that page.")

    first = variants[0]
    image = _image(first) or _image(first.get("_group", {}))
    if not image:
        raise ValueError("The product has no image.")
    group_name = first.get("_group", {}).get("name") or first["name"]
    ai = await _classify(group_name, first.get("color", ""), first.get("material", ""), image)

    out, seen = [], set()
    for v in variants:
        sku = v.get("mpn") or v.get("sku") or v["name"]
        if sku in seen:
            continue
        seen.add(sku)
        offer = _offer(v)
        img = _image(v) or image
        out.append(Product(
            id="westwing-" + re.sub(r"[^A-Za-z0-9-]", "", sku),
            name=v["name"],
            category=ai.get("category") if ai.get("category") in CATEGORIES else "decor",
            style=", ".join(s for s in ai.get("styles", []) if s in STYLES) or None,
            color=ai.get("color") or v.get("color") or None,
            material=ai.get("material") or v.get("material") or None,
            price=float(offer.get("price", 0)),
            currency=offer.get("priceCurrency", "EUR"),
            width_cm=_cm(v.get("width")),
            depth_cm=_cm(v.get("depth")),
            height_cm=_cm(v.get("height")),
            image_url=img,
            product_url=url.split("?")[0],
            source="westwing",
            name_en=ai.get("name_en"),
        ).to_dict())
    return out
