"""Restyle a whole view of the room in one style while keeping OUR layout (T4).

Muse Image gets the real frame plus a layout map drawn from the SAM masks of
that frame (one flat colour per piece) and a style brief. With the map, each
piece keeps its place and size far better (T4: mean IoU 0.39 -> 0.55).
Items the user wants to keep are pasted back from the original photo, so
they stay pixel-exact.
"""

from __future__ import annotations

import asyncio
import io
import pickle
import time
from functools import cache
from pathlib import Path

import httpx
import numpy as np
from PIL import Image
from scipy import ndimage

from app.catalog.models import Product
from app.pipeline import sam
from app.render import muse_image

# Big pieces that define the layout; small decor is free to change.
LAYOUT = ["sofa", "armchair", "coffee table", "side table", "chair", "dining table",
          "shelving unit", "tv stand", "television", "rug", "curtain", "wardrobe"]
# piece -> (colour name for the prompt, RGB on the map)
MAP_COLORS = {
    "sofa": ("red", (230, 60, 60)), "armchair": ("yellow", (240, 220, 40)),
    "coffee table": ("blue", (60, 120, 230)), "side table": ("orange", (250, 170, 30)),
    "chair": ("green", (40, 170, 90)), "dining table": ("grey", (150, 150, 150)),
    "shelving unit": ("purple", (150, 80, 200)), "tv stand": ("brown", (120, 70, 40)),
    "television": ("black", (30, 30, 30)), "rug": ("pink", (240, 120, 200)),
    "curtain": ("cyan", (60, 200, 210)), "wardrobe": ("navy", (30, 40, 120)),
}
ZONE_COLOR = ("pink", (240, 120, 200))

ROOM_KEEP = (
    "Keep the room itself exactly as in image 1: same walls, windows, doors, radiator, "
    "floor area, ceiling, view outside, camera position, lens and framing. "
    "Photorealistic, natural light, like a photo from an interior design magazine."
)


@cache
def _tracks(cache_file: Path) -> dict[str, list[sam.Track]]:
    return pickle.loads(cache_file.read_bytes())


def concept_masks(room_dir: Path, frame: int, concepts: list[str], w: int, h: int) -> dict[str, np.ndarray]:
    """Union mask per concept on one frame, from the cached video tracks."""
    tracks = _tracks(room_dir / "sam_tracks.pkl")
    out = {}
    for c in concepts:
        m = np.zeros((h, w), bool)
        for t in tracks.get(c, []):
            o = t.observations.get(frame)
            if o is not None and o.mask is not None and (o.confidence or 0) >= 0.5:
                m |= sam.full_frame_mask(o.mask, w, h)
        if m.mean() > 0.001:
            out[c] = m
    return out


def object_mask(room_dir: Path, obj: dict, frame: int, w: int, h: int) -> np.ndarray | None:
    """One room.json object's mask on another frame (via its SAM track)."""
    for t in _tracks(room_dir / "sam_tracks.pkl").get(obj["label"], []):
        if t.object_id == obj.get("track_id"):
            o = t.observations.get(frame)
            return None if o is None or o.mask is None else sam.full_frame_mask(o.mask, w, h)
    return None


def layout_map(masks: dict[str, np.ndarray], w: int, h: int, zone: bool = False) -> Image.Image:
    img = np.full((h, w, 3), 255, np.uint8)
    for c in sorted(masks, key=lambda c: -masks[c].sum()):  # big first, small on top
        img[masks[c]] = ZONE_COLOR[1] if zone else MAP_COLORS[c][1]
    return Image.fromarray(img)


def position(mask: np.ndarray) -> str:
    h, w = mask.shape
    ys, xs = np.nonzero(mask)
    cx, bottom = (xs.min() + xs.max()) / 2 / w, ys.max() / h
    horiz = "left" if cx < 0.36 else "right" if cx > 0.64 else "centre"
    depth = "foreground" if bottom > 0.85 else "back" if bottom < 0.6 else "middle"
    return f"{horiz}, {depth}, about {round((xs.max() - xs.min()) / w * 100)}% of the image width"


def pieces_in_view(room_dir: Path, frame: int) -> list[str]:
    """Layout pieces SAM saw on this frame (cheap: no mask decoding)."""
    tracks = _tracks(room_dir / "sam_tracks.pkl")
    return [c for c in LAYOUT if any(
        (o := t.observations.get(frame)) is not None and (o.confidence or 0) >= 0.5 for t in tracks.get(c, []))]


def _product_line(n: int, use: dict) -> str:
    p = use["product"]
    size = f", {p['width_cm']:.0f} cm wide" if p.get("width_cm") else ""
    return f"image {n} is a real product, the {p['name_en'] or p['category']}{size}"


def prompt(view: dict, brief: dict, masks: dict[str, np.ndarray], kept: list[str], uses: list[dict]) -> str:
    """uses: real catalog products for this view, shown to the model as images 3, 4, ..."""
    style = f"{brief['title']}: {brief['summary']} Palette: {', '.join(brief.get('palette', []))}. " \
            f"Materials: {', '.join(brief.get('materials', []))}."
    real = {u["for"]: (n, u) for n, u in enumerate(uses, start=3) if u["for"] != "add"}
    added = [(n, u) for n, u in enumerate(uses, start=3) if u["for"] == "add"]
    copy = "copy its exact design, shape, colour and material"
    products = ""
    if uses:
        products = (
            "Images " + ", ".join(str(n) for n in range(3, 3 + len(uses))) + " are real products to use: "
            + "; ".join(_product_line(n, u) for n, u in enumerate(uses, start=3)) + ". "
        )
    if view["kind"] == "zone":
        place = view["label"].replace(" floor", "")
        zones = brief.get("zones", {})
        what = next((v for k, v in zones.items() if place in k.lower()), None) or \
            "a compact seating set, plants in pots, an outdoor rug and soft lighting"
        use = "".join(f" Include the product from image {n} ({copy}){': ' + u['note'] if u.get('note') else ''}."
                      for n, u in enumerate(uses, start=3))
        return (
            f"Image 1 is a photo of my {place}. It is empty now; turn it into a cosy, fully furnished "
            f"spot in this style — {style} Furnish it with: {what}.{use} Place the new pieces on the floor "
            "(the pink area in image 2), clearly visible and filling the space, leaving a path to the door. "
            + products + ROOM_KEEP
        )
    pieces = brief.get("pieces", {})

    def becomes(c: str) -> str:
        if c in real:
            return f" becomes the product in image {real[c][0]} ({copy})"
        return f" becomes: {pieces[c]}" if c in pieces else ""

    layout = "; ".join(f"the {c} ({position(m)}){becomes(c)}" for c, m in masks.items() if c not in kept)
    legend = ", ".join(f"{MAP_COLORS[c][0]} = {c}" for c in masks)
    text = (
        f"Image 1 is a photo of my {brief.get('room_type', 'living room')}. Restyle it in this style — {style} "
        f"Keep the furniture layout exactly: every piece stays in the same place with the same size and "
        f"footprint, only its design, materials and colours change: {layout}. "
    )
    if kept:
        text += f"Keep these exactly as they are, unchanged: {', '.join('the ' + k for k in kept)}. "
    for n, u in added:
        text += f"Add the product from image {n} ({copy}){', ' + u['note'] if u.get('note') else ''}. "
    if brief.get("add"):
        text += f"You may also add: {', '.join(brief['add'])}. "
    text += (
        f"Image 2 is the layout map of image 1: each coloured shape is one piece of furniture ({legend}). "
        "Keep each new piece inside its shape. " + products
    )
    return text + ROOM_KEEP


async def _photo(url: str) -> Image.Image:
    async with httpx.AsyncClient(timeout=60) as http:
        return Image.open(io.BytesIO((await http.get(url)).content)).convert("RGB")


async def restyle_view(room_dir: Path, room: dict, view: dict, brief: dict, out: Path,
                       uses: list[dict] | None = None) -> dict:
    """uses: [{"product": product dict, "for": piece or "add", "note": str}] for this view."""
    uses = uses or []
    frame = Image.open(room_dir / view["file"]).convert("RGB")
    w, h = frame.size
    zone = view["kind"] == "zone"
    masks = concept_masks(room_dir, view["frame"], [view["label"]] if zone else LAYOUT, w, h)
    objects = {o["id"]: o for o in room["objects"]}
    # only real pieces are pasted back; never floors/zones that new pieces stand on
    keep = [objects[i] for i in brief.get("keep", [])
            if i in objects and objects[i]["category"] in ("furniture", "decor")]
    keep_masks = [(o, object_mask(room_dir, o, view["frame"], w, h)) for o in keep]
    keep_masks = [(o, m) for o, m in keep_masks if m is not None]
    photos = await asyncio.gather(*(_photo(Product.from_dict(u["product"]).image_for_model) for u in uses))

    t0 = time.perf_counter()
    img, _ = await muse_image.edit(
        [frame, layout_map(masks, w, h, zone), *photos],
        prompt(view, brief, masks, [o["label"] for o, _ in keep_masks], uses),
        size=f"{w}x{h}",
    )
    img = img.resize((w, h), Image.LANCZOS)
    img.save(out.with_suffix(".raw.jpg"), quality=92)
    for _, m in keep_masks:  # kept items: the real pixels, not a redraw
        img = muse_image.composite(img, frame, ndimage.binary_dilation(m, iterations=4), feather_px=6)
    img.save(out, quality=92)
    return {"seconds": round(time.perf_counter() - t0, 1), "kept": [o["id"] for o, _ in keep_masks]}
