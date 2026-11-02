"""Put one catalog product into the real room photo (prompts proven in T2)."""

from __future__ import annotations

import io
import time
from pathlib import Path
from typing import Literal

import httpx
import numpy as np
from PIL import Image

from app.catalog import Product
from app.render import muse_image

Action = Literal["replace", "add"]

KEEP = (
    "Keep everything else in image 1 exactly as it is: same walls, floor, "
    "windows, furniture, objects, lighting, camera angle and framing. "
    "Return the full room photo, not a close-up."
)


def prompt(action: Action, obj: dict, product: Product) -> str:
    thing = f"{obj['color']['name']} {obj['label']}"
    size = (
        f" It is about {product.width_cm:.0f} cm wide." if product.width_cm and product.source != "dummyjson" else ""
    )
    if action == "replace":
        return (
            f"Image 1 is a photo of my room. Image 2 is a product photo of a {product.category}. "
            f"Replace the {thing} in image 1 with the {product.category} from image 2: same design, "
            f"colour and material as in image 2, standing where the old one stands, at a realistic "
            f"size for this room, with matching perspective, lighting and shadows.{size} " + KEEP
        )
    where = "on the " + obj["label"] + (" in image 1" if obj["category"] == "zone" else " in image 1, on top of it")
    return (
        f"Image 1 is a photo of my room. Image 2 is a product photo of a {product.category}. "
        f"Place the {product.category} from image 2 {where}: same design and colours as in image 2, "
        f"at a realistic size, with matching perspective, lighting and a soft shadow.{size} " + KEEP
    )


def region_for(action: Action, obj: dict, mask: np.ndarray) -> np.ndarray:
    if action == "replace":
        return muse_image.edit_region(mask, grow_pct=0.15)
    if obj["category"] == "zone":  # free floor: new item stands on it and rises above
        return muse_image.edit_region(mask, grow_pct=0.05, grow_up=0.6)
    return muse_image.edit_region(mask, grow_pct=0.15, grow_up=1.6)  # on top of furniture


async def visualize(room_dir: Path, obj: dict, product: Product, action: Action) -> dict:
    """Returns paths (relative to room_dir) of the before frame and the after image.
    Cached per (object, product, action), so repeated demo clicks are instant."""
    renders = room_dir / "renders"
    renders.mkdir(exist_ok=True)
    stem = f"{obj['id']}__{product.id}__{action}"
    after = renders / f"{stem}.jpg"
    result = {"before": obj["best_frame"], "after": f"renders/{after.name}", "cached": after.exists()}
    if after.exists():
        return result

    frame = Image.open(room_dir / obj["best_frame"]).convert("RGB")
    mask = np.asarray(Image.open(room_dir / obj["mask"])) > 0
    async with httpx.AsyncClient(timeout=60) as http:
        product_img = Image.open(io.BytesIO((await http.get(product.image_url)).content)).convert("RGB")

    t0 = time.perf_counter()
    raw, _ = await muse_image.edit(
        [frame, product_img], prompt(action, obj, product), size=f"{frame.width}x{frame.height}"
    )
    raw.save(renders / f"{stem}.raw.png")
    muse_image.composite(frame, raw, region_for(action, obj, mask)).save(after, quality=92)
    return {**result, "seconds": round(time.perf_counter() - t0, 1)}
