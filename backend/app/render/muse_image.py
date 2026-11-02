"""Muse Image edits + compositing back into the real photo.

Muse Image has no mask/inpainting parameter (`mask` -> 400 unsupported), so
it may redraw more than we asked. We therefore paste only the edited region
(SAM mask, grown and feathered) back onto the original frame: outside that
region the user's room stays pixel-identical.
"""

from __future__ import annotations

import base64
import io

import httpx
import numpy as np
from PIL import Image
from scipy import ndimage

from app.config import IMAGE_MODEL, META_BASE_URL, model_api_key


def data_url(img: Image.Image, fmt: str = "PNG") -> str:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format=fmt)
    mime = "png" if fmt == "PNG" else "jpeg"
    return f"data:image/{mime};base64," + base64.b64encode(buf.getvalue()).decode()


async def edit(
    images: list[Image.Image],
    prompt: str,
    size: str | None = None,
    extra: dict | None = None,
) -> tuple[Image.Image, dict]:
    """POST /v1/images/edits with 1-10 input images; returns (image, raw response meta)."""
    body = {
        "model": IMAGE_MODEL,
        "prompt": prompt,
        "images": [{"image_url": data_url(im)} for im in images],
        "n": 1,
        "output_format": "png",
        **({"size": size} if size else {}),
        **(extra or {}),
    }
    async with httpx.AsyncClient(timeout=300) as http:
        r = await http.post(
            f"{META_BASE_URL}/images/edits",
            headers={"Authorization": f"Bearer {model_api_key()}"},
            json=body,
        )
    if r.status_code >= 400:
        raise RuntimeError(f"images/edits {r.status_code}: {r.text[:500]}")
    data = r.json()
    b64 = data["data"][0]["b64_json"]
    meta = {k: v for k, v in data.items() if k != "data"}
    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB"), meta


def edit_region(mask: np.ndarray, grow_pct: float = 0.15, grow_up: float = 0.0) -> np.ndarray:
    """Where the new product may land: the object's mask plus its bbox grown
    by grow_pct (a replacement can be a bit bigger or a different shape).
    grow_up extends the box upwards by that share of its height, for items
    placed on a surface (a lamp on a table, a plant on the balcony floor)."""
    h, w = mask.shape
    ys, xs = np.nonzero(mask)
    region = mask.copy()
    if len(xs):
        l, r, t, b = xs.min(), xs.max(), ys.min(), ys.max()
        gx, gy = int((r - l) * grow_pct), int((b - t) * grow_pct)
        up = int((b - t) * grow_up)
        region[max(0, t - gy - up) : min(h, b + gy), max(0, l - gx) : min(w, r + gx)] = True
    return region


def composite(
    original: Image.Image, edited: Image.Image, region: np.ndarray, feather_px: int = 12
) -> Image.Image:
    """Paste `edited` into `original` inside `region` with a soft edge."""
    edited = edited.resize(original.size, Image.LANCZOS)
    alpha = ndimage.gaussian_filter(region.astype(np.float32), feather_px / 2)
    alpha = np.clip(alpha * 1.5, 0, 1)[..., None]  # keep the inside fully opaque
    o = np.asarray(original.convert("RGB"), dtype=np.float32)
    e = np.asarray(edited, dtype=np.float32)
    return Image.fromarray((o * (1 - alpha) + e * alpha).astype(np.uint8))


def preservation(original: Image.Image, edited: Image.Image, region: np.ndarray) -> dict:
    """How much did the edit change outside the region we asked to change?"""
    e = np.asarray(edited.resize(original.size, Image.LANCZOS), dtype=np.float32)
    o = np.asarray(original.convert("RGB"), dtype=np.float32)
    diff = np.abs(e - o).mean(axis=2)
    outside = ~ndimage.binary_dilation(region, iterations=8)
    return {
        "mae_outside": round(float(diff[outside].mean()), 1),
        "changed_outside_pct": round(float((diff[outside] > 30).mean() * 100), 1),
        "mae_inside": round(float(diff[region].mean()), 1),
    }
