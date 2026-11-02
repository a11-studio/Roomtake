"""A "look": the whole room restyled in one style, with real products in it.

Pipeline (each step saved to looks/<id>/look.json so the UI can show it early):
  1. brief     Muse Wonder writes the style brief and picks real catalog
               products where they fit the style (or Muse Spark revises it)
  2. views     Muse Image restyles each hero view from the photo, the SAM
               layout map and the picked products' photos
  3. check     SAM finds the pieces in the restyled main view and measures
               how well the layout was kept (IoU per piece)
The products used are the shopping list: what you see is what you can buy.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from app.agent.stylist import revise_brief, style_brief
from app.pipeline import sam
from app.render.restyle import concept_masks, restyle_view

LAYOUT_CHECK = ["sofa", "armchair", "coffee table", "side table", "chair", "rug", "shelving unit", "curtain"]


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
        "products": [],
        "layout_iou": None,
        "seconds": {},
        "created": time.time(),
    }
    save_look(room_dir, look)
    return look


def _uses_for(view: dict, look: dict) -> list[dict]:
    key = "main" if view["kind"] == "main" else view["label"]
    return [u for u in look["products"] if u["view"] == key]


async def _restyle(room_dir: Path, room: dict, look: dict) -> None:
    d = look_dir(room_dir, look["id"])

    async def one(i: int, view: dict) -> None:
        out = d / f"view{i}.jpg"
        r = await restyle_view(room_dir, room, view, look["brief"], out, _uses_for(view, look))
        view["after"] = view["current"] = str(out.relative_to(room_dir))
        view["seconds"] = r["seconds"]
        save_look(room_dir, look)

    await asyncio.gather(*(one(i, v) for i, v in enumerate(look["views"])))


async def _layout_check(room_dir: Path, look: dict) -> None:
    """SAM on the restyled main view vs the original frame: did pieces keep place and size?"""
    i = next((i for i, v in enumerate(look["views"]) if v["kind"] == "main"), None)
    if i is None:
        return
    view, d = look["views"][i], look_dir(room_dir, look["id"])
    after = Image.open(room_dir / view["after"])
    w, h = after.size
    before = concept_masks(room_dir, view["frame"], LAYOUT_CHECK, w, h)
    # a 1-frame clip: video requests are far cheaper in throughput than images (T1b)
    after.save(d / "check_0.jpg", quality=95)
    clip = d / "check.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-framerate", "1", "-i", str(d / "check_%d.jpg"),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(clip)],
        check=True,
    )
    file_id = await sam.upload_video(clip)
    results = await asyncio.gather(*(sam.segment_video(file_id, c) for c in before), return_exceptions=True)
    ious = {}
    for c, res in zip(before, results):
        m = np.zeros((h, w), bool)
        if not isinstance(res, BaseException):
            for t in sam.tracks_from_result(res, c):
                for o in t.observations.values():
                    if o.mask is not None and (o.confidence or 0) >= 0.6:
                        m |= sam.full_frame_mask(o.mask, w, h)
        ious[c] = round(float((m & before[c]).sum() / (m | before[c]).sum()), 2)
    look["layout_iou"] = {"mean": round(float(np.mean(list(ious.values()))), 2) if ious else None, "pieces": ious}


async def run_look(room_dir: Path, room: dict, look: dict, parent_brief: dict | None = None) -> dict:
    """Fill a look created by new_look: brief -> views -> layout check. Saves after each step."""
    t0 = time.perf_counter()
    try:
        if parent_brief is None:
            look["brief"] = await style_brief(room_dir, room, look["prefs"])
        else:
            look["brief"] = await revise_brief(room_dir, room, parent_brief, look["instruction"], look["prefs"])
        look["products"] = look["brief"].pop("products", [])
        look["seconds"]["brief"] = round(time.perf_counter() - t0, 1)
        look["status"] = "rendering"
        save_look(room_dir, look)

        t1 = time.perf_counter()
        await _restyle(room_dir, room, look)
        look["seconds"]["views"] = round(time.perf_counter() - t1, 1)
        look["status"] = "checking"
        save_look(room_dir, look)

        t2 = time.perf_counter()
        try:
            await _layout_check(room_dir, look)
        except Exception as e:  # the check is a bonus; the look is already usable
            look["layout_iou"] = {"mean": None, "error": f"{type(e).__name__}: {e}"}
        look["seconds"]["check"] = round(time.perf_counter() - t2, 1)
        look["status"] = "done"
    except Exception as e:
        look["status"], look["error"] = "error", f"{type(e).__name__}: {e}"
    look["seconds"]["total"] = round(time.perf_counter() - t0, 1)
    save_look(room_dir, look)
    return look


def parent_brief(look: dict) -> dict:
    """The brief as the stylist wrote it, with its products put back in."""
    return {**look["brief"], "products": look.get("products", [])}


def summary(look: dict) -> dict[str, Any]:
    """Shopping list total: the real products used in the design."""
    prices = [u["product"].get("price_eur", u["product"]["price"]) for u in look.get("products", [])]
    return {"count": len(prices), "total": round(sum(prices), 2), "currency": "EUR"}
