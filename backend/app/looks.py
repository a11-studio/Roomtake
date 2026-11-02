"""A "look": the whole room restyled in one style, plus real products to buy it.

Pipeline (each step saved to looks/<id>/look.json so the UI can show it early):
  1. brief     Muse Wonder writes the style brief (or Muse Spark revises one)
  2. views     Muse Image restyles each hero view with the SAM layout map
  3. shop      SAM finds the new pieces in the restyled views, Muse Spark
               describes each, the catalog gives the closest real products;
               SAM also measures how well the layout was kept (IoU)
Then "make it real" puts one exact catalog product into a restyled view.
"""

from __future__ import annotations

import asyncio
import io
import json
import re
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

import httpx
import numpy as np
from PIL import Image

from app.agent.stylist import describe_items, revise_brief, style_brief
from app.catalog import Product, get_product, search_products
from app.pipeline import sam
from app.render import muse_image
from app.render.restyle import concept_masks, restyle_view

# What we look for in a restyled view to sell it. "table" catches the new
# pieces that are not exactly a coffee/side table (e.g. a balcony bistro table).
SHOP = ["sofa", "armchair", "chair", "coffee table", "side table", "table", "rug",
        "lamp", "shelving unit", "potted plant", "curtain"]
LAYOUT_CHECK = ["sofa", "armchair", "coffee table", "side table", "chair", "rug", "shelving unit", "curtain"]
MAX_ITEMS = 8
MIN_ITEM_AREA = 0.004


def look_dir(room_dir: Path, look_id: str) -> Path:
    return room_dir / "looks" / look_id


def load_look(room_dir: Path, look_id: str) -> dict:
    return json.loads((look_dir(room_dir, look_id) / "look.json").read_text())


def save_look(room_dir: Path, look: dict) -> None:
    d = look_dir(room_dir, look["id"])
    d.mkdir(parents=True, exist_ok=True)
    (d / "look.json").write_text(json.dumps(look, indent=2, ensure_ascii=False))


def new_look(room_dir: Path, room: dict, prefs: dict, parent: dict | None = None, instruction: str | None = None) -> dict:
    look = {
        "id": uuid.uuid4().hex[:8],
        "parent": parent["id"] if parent else None,
        "instruction": instruction,
        "status": "brief",
        "error": None,
        "prefs": prefs,
        "brief": None,
        "views": [{**v, "after": None, "current": None} for v in room["views"]],
        "layout_iou": None,
        "items": [],
        "seconds": {},
        "created": time.time(),
    }
    save_look(room_dir, look)
    return look


def _score(p: Product, desc: dict) -> int:
    want = set(re.findall(r"[a-z]+", " ".join(str(desc.get(k, "")) for k in ("name", "style", "color", "material")).lower()))
    have = set(re.findall(r"[a-z]+", " ".join(str(x or "") for x in (p.name, p.style, p.color, p.material)).lower()))
    return len(want & have)


def _matches(desc: dict, max_price: float | None) -> list[dict]:
    hits = search_products(str(desc.get("category", "")), max_price=max_price)
    hits.sort(key=lambda p: (-_score(p, desc), p.price))
    return [p.to_dict() for p in hits[:3]]


async def _restyle(room_dir: Path, room: dict, look: dict) -> None:
    d = look_dir(room_dir, look["id"])

    async def one(i: int, view: dict) -> None:
        out = d / f"view{i}.jpg"
        r = await restyle_view(room_dir, room, view, look["brief"], out)
        view["after"] = view["current"] = str(out.relative_to(room_dir))
        view["seconds"] = r["seconds"]
        save_look(room_dir, look)

    await asyncio.gather(*(one(i, v) for i, v in enumerate(look["views"])))


async def _shop(room_dir: Path, look: dict) -> None:
    d = look_dir(room_dir, look["id"])
    views = look["views"]
    # restyled views as a 1 fps clip: one SAM request per concept covers all views
    for i, v in enumerate(views):
        Image.open(room_dir / v["after"]).save(d / f"clip_{i}.jpg", quality=95)
    clip = d / "views.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-framerate", "1", "-i", str(d / "clip_%d.jpg"),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(clip)],
        check=True,
    )
    file_id = await sam.upload_video(clip)
    results = await asyncio.gather(*(sam.segment_video(file_id, c) for c in SHOP), return_exceptions=True)

    w, h = Image.open(room_dir / views[0]["after"]).size
    found: list[tuple[int, str, sam.Observation, np.ndarray]] = []
    union: dict[str, np.ndarray] = {}
    for concept, res in zip(SHOP, results):
        if isinstance(res, BaseException):
            continue
        for track in sam.tracks_from_result(res, concept):
            for f, o in track.observations.items():
                if o.mask is None or (o.confidence or 0) < 0.6:
                    continue
                m = sam.full_frame_mask(o.mask, w, h)
                if f == 0:
                    union[concept] = union.get(concept, np.zeros((h, w), bool)) | m
                l, t, r, b = o.box
                edges = (l <= 2) + (t <= 2) + (r >= w - 3) + (b >= h - 3)
                # cut off by the frame: not a thing you can show and sell
                if m.mean() >= MIN_ITEM_AREA and edges < 2 and not (edges and m.mean() < 0.03):
                    found.append((f, concept, o, m))

    # layout kept? compare the main view's pieces with the original frame
    main = next((i for i, v in enumerate(views) if v["kind"] == "main"), None)
    if main is not None:
        before = concept_masks(room_dir, views[main]["frame"], LAYOUT_CHECK, w, h)
        ious = {c: float((union[c] & m).sum() / (union[c] | m).sum()) for c, m in before.items() if c in union}
        missing = [c for c in before if c not in union]
        look["layout_iou"] = {
            "mean": round(float(np.mean(list(ious.values()) + [0.0] * len(missing))), 2) if before else None,
            "pieces": {c: round(v, 2) for c, v in ious.items()} | {c: 0.0 for c in missing},
        }

    # one item per physical thing: drop overlaps between concepts ("table" vs "coffee table")
    found.sort(key=lambda x: -x[3].sum())
    items: list[tuple[int, str, sam.Observation, np.ndarray]] = []
    for f, c, o, m in found:
        if all(f != f2 or (m & m2).sum() / min(m.sum(), m2.sum()) < 0.5 for f2, _, _, m2 in items):
            items.append((f, c, o, m))
    items = items[:MAX_ITEMS]

    crops = []
    for n, (f, c, o, m) in enumerate(items):
        img = Image.open(room_dir / views[f]["after"]).convert("RGB")
        l, t, r, b = o.box
        pad = 0.12 * max(r - l, b - t)
        crop = img.crop((max(0, l - pad), max(0, t - pad), min(w, r + pad), min(h, b + pad)))
        crop.save(d / f"item{n}.jpg", quality=90)
        Image.fromarray(m.astype(np.uint8) * 255).save(d / f"item{n}_mask.png")
        crops.append(crop)
    descs = await describe_items(crops, look["brief"]) if crops else []
    # Spark numbers the images from 1 or 0 depending on the day; order is reliable
    by_index = dict(enumerate(descs)) if len(descs) == len(crops) else {
        int(x.get("index", i)) - min(int(y.get("index", 0)) for y in descs): x for i, x in enumerate(descs)
    }

    budget = (look.get("prefs") or {}).get("budget")
    look["items"] = []
    for n, (f, c, o, m) in enumerate(items):
        desc = by_index.get(n, {"category": c, "name": c})
        look["items"].append({
            "id": f"item{n}",
            "view": f,
            "concept": c,
            "bbox": [round(v) for v in o.box],
            "crop": str((d / f"item{n}.jpg").relative_to(room_dir)),
            "mask": str((d / f"item{n}_mask.png").relative_to(room_dir)),
            "description": desc,
            "matches": _matches(desc, budget),
            "real": None,
        })


async def run_look(room_dir: Path, room: dict, look: dict, parent_brief: dict | None = None) -> dict:
    """Fill a look created by new_look: brief -> views -> shop. Saves after each step."""
    t0 = time.perf_counter()
    try:
        if parent_brief is None:
            look["brief"] = await style_brief(room_dir, room, look["prefs"])
        else:
            look["brief"] = await revise_brief(room, parent_brief, look["instruction"])
        look["seconds"]["brief"] = round(time.perf_counter() - t0, 1)
        look["status"] = "rendering"
        save_look(room_dir, look)

        t1 = time.perf_counter()
        await _restyle(room_dir, room, look)
        look["seconds"]["views"] = round(time.perf_counter() - t1, 1)
        look["status"] = "shopping"
        save_look(room_dir, look)

        t2 = time.perf_counter()
        await _shop(room_dir, look)
        look["seconds"]["shop"] = round(time.perf_counter() - t2, 1)
        look["status"] = "done"
    except Exception as e:
        look["status"], look["error"] = "error", f"{type(e).__name__}: {e}"
    look["seconds"]["total"] = round(time.perf_counter() - t0, 1)
    save_look(room_dir, look)
    return look


async def make_real(room_dir: Path, look: dict, item_id: str, product_id: str) -> dict:
    """Put one exact catalog product where a restyled item stands, on the
    view's current image, so several products can stack up."""
    item = next(i for i in look["items"] if i["id"] == item_id)
    product = get_product(product_id)
    if product is None:
        raise KeyError(product_id)
    view = look["views"][item["view"]]
    base = Image.open(room_dir / view["current"]).convert("RGB")
    mask = np.asarray(Image.open(room_dir / item["mask"])) > 0
    async with httpx.AsyncClient(timeout=60) as http:
        photo = Image.open(io.BytesIO((await http.get(product.image_url)).content)).convert("RGB")
    name = item["description"].get("name", item["concept"])
    prompt = (
        f"Image 1 is a photo of a room. Image 2 is a product photo of a {product.category}. "
        f"Replace the {name} in image 1 with the {product.category} from image 2: same design, colour and "
        f"material as in image 2, in the same place, at a realistic size, with matching perspective, "
        f"lighting and shadows. Keep everything else in image 1 exactly as it is. Return the full photo."
    )
    raw, _ = await muse_image.edit([base, photo], prompt, size=f"{base.width}x{base.height}")
    out = look_dir(room_dir, look["id"]) / f"view{item['view']}_{item_id}_{product.id}.jpg"
    muse_image.composite(base, raw, muse_image.edit_region(mask, grow_pct=0.15)).save(out, quality=92)
    view["current"] = str(out.relative_to(room_dir))
    item["real"] = product.to_dict()
    save_look(room_dir, look)
    return look


def summary(look: dict) -> dict[str, Any]:
    """Shopping total: the product made real, else the best match, per item."""
    picks = [i["real"] or (i["matches"][0] if i["matches"] else None) for i in look["items"]]
    picks = [p for p in picks if p]
    return {"count": len(picks), "total": round(sum(p["price"] for p in picks), 2),
            "currency": picks[0]["currency"] if picks else None}
