"""T4: restyle the whole room in one style and keep OUR layout.

Run from backend/ after app.pipeline.room (uses room.json frames + SAM cache):
    uv run python ../spikes/t4_restyle.py [--style Scandinavian]

Per frame, two Muse Image variants:
  text  room photo + prompt listing where each piece stands
  map   the same + a layout map drawn from SAM masks (one colour per piece)
Layout kept is measured by running SAM on the result and comparing each
piece's mask with the original (IoU, 1.0 = same place and size).
Writes data/t4/<style>/report.md and sheet.jpg.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import DATA_DIR  # noqa: E402
from app.pipeline import sam  # noqa: E402
from app.pipeline.preview import contact_sheet  # noqa: E402
from app.render import muse_image  # noqa: E402

ROOM = DATA_DIR / "rooms" / "IMG_1184"
# Big pieces that define the layout; small decor is free to change.
LAYOUT = ["sofa", "coffee table", "side table", "chair", "shelving unit", "tv stand",
          "television", "rug", "curtain", "dining table"]
# piece -> (colour name used in the prompt, RGB on the layout map)
MAP_COLORS = {
    "sofa": ("red", (230, 60, 60)), "coffee table": ("blue", (60, 120, 230)),
    "side table": ("orange", (250, 170, 30)), "chair": ("green", (40, 170, 90)),
    "shelving unit": ("purple", (150, 80, 200)), "tv stand": ("brown", (120, 70, 40)),
    "television": ("black", (30, 30, 30)), "rug": ("pink", (240, 120, 200)),
    "curtain": ("cyan", (60, 200, 210)), "dining table": ("grey", (150, 150, 150)),
    "balcony floor": ("pink", (240, 120, 200)),
}
FRAMES = {
    "living_room": (110, LAYOUT),
    "balcony": (215, ["balcony floor"]),
}


def where(box: tuple[float, float, float, float], w: int, h: int) -> str:
    cx, by = (box[0] + box[2]) / 2 / w, box[3] / h
    horiz = "left" if cx < 0.36 else "right" if cx > 0.64 else "centre"
    depth = "foreground" if by > 0.85 else "back" if by < 0.6 else "middle"
    width = round((box[2] - box[0]) / w * 100)
    return f"{horiz}, {depth}, about {width}% of the image width"


def frame_masks(cache: dict, frame: int, concepts: list[str], w: int, h: int) -> dict[str, np.ndarray]:
    """Union mask per concept on one frame, from the cached video tracks."""
    out = {}
    for c in concepts:
        m = np.zeros((h, w), bool)
        for t in cache.get(c, []):
            o = t.observations.get(frame)
            if o is not None and o.mask is not None and (o.confidence or 0) >= 0.5:
                m |= sam.full_frame_mask(o.mask, w, h)
        if m.mean() > 0.001:
            out[c] = m
    return out


def layout_map(masks: dict[str, np.ndarray], w: int, h: int) -> Image.Image:
    img = np.full((h, w, 3), 255, np.uint8)
    for c in sorted(masks, key=lambda c: -masks[c].sum()):  # big first, small on top
        img[masks[c]] = MAP_COLORS[c][1]
    return Image.fromarray(img)


def prompt(style: str, room_type: str, pieces: dict[str, str], with_map: bool) -> str:
    layout = "; ".join(f"the {c} ({pos})" for c, pos in pieces.items())
    if room_type == "balcony":
        body = (
            f"Image 1 is a photo of my small, empty balcony. Furnish and style it as a beautiful "
            f"{style} balcony, like a photo from an interior magazine: a compact seating set, "
            f"plants, an outdoor rug, soft lighting. Put the new pieces only on the tiled floor"
            f"{' (the pink area in image 2)' if with_map else ''}, leaving a path to the door. "
        )
    else:
        body = (
            f"Image 1 is a photo of my living room. Restyle it as a beautiful {style} living room, "
            f"like a photo from an interior magazine. Keep the furniture layout exactly: every piece "
            f"stays in the same place with the same size and footprint, only its design, materials "
            f"and colours change: {layout}. Textiles, lamps, wall decor, plants and small objects "
            f"may change or be added. "
        )
        if with_map:
            legend = ", ".join(f"{MAP_COLORS[c][0]} = {c}" for c in pieces)
            body += (
                f"Image 2 is the layout map of image 1: each coloured shape is one piece of furniture "
                f"({legend}). Keep each new piece inside its shape. "
            )
    return body + (
        "Keep the room itself exactly as in image 1: same walls, windows, doors, radiator, floor area, "
        "ceiling, view outside, camera position, lens and framing. Photorealistic, natural light."
    )


async def layout_iou(result: Image.Image, original: dict[str, np.ndarray]) -> dict[str, float]:
    """SAM on the restyled image; IoU per piece against the original masks."""
    w, h = result.size
    tmp = DATA_DIR / "t4" / "_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    path = tmp / f"{id(result)}.jpg"
    result.save(path, quality=92)

    async def one(c: str) -> tuple[str, float]:
        try:
            r = await asyncio.wait_for(sam.segment_image(path, c), 90)
        except Exception:
            return c, float("nan")
        m = np.zeros((h, w), bool)
        for t in sam.tracks_from_result(r, c):
            o = t.observations[0]
            if o.mask is not None and (o.confidence or 0) >= 0.5:
                m |= sam.full_frame_mask(o.mask, w, h)
        inter, union = (m & original[c]).sum(), (m | original[c]).sum()
        return c, round(float(inter / union), 2) if union else float("nan")

    return dict(await asyncio.gather(*(one(c) for c in original)))


def label(img: Image.Image, text: str) -> Image.Image:
    img = img.copy()
    d = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=26)
    tb = d.textbbox((12, 12), text, font=font)
    d.rectangle((tb[0] - 6, tb[1] - 6, tb[2] + 6, tb[3] + 6), fill=(0, 0, 0))
    d.text((12, 12), text, fill=(255, 255, 255), font=font)
    return img


async def run(style: str) -> None:
    out = DATA_DIR / "t4" / style.lower()
    out.mkdir(parents=True, exist_ok=True)
    cache = pickle.loads((ROOM / "sam_tracks.pkl").read_bytes())

    async def variant(room_type: str, frame_idx: int, concepts: list[str], with_map: bool):
        frame = Image.open(ROOM / "frames" / f"frame_{frame_idx:04d}.jpg").convert("RGB")
        w, h = frame.size
        masks = frame_masks(cache, frame_idx, concepts, w, h)
        pieces = {}
        for c, m in masks.items():
            ys, xs = np.nonzero(m)
            pieces[c] = where((xs.min(), ys.min(), xs.max(), ys.max()), w, h)
        lmap = layout_map(masks, w, h)
        inputs = [frame, lmap] if with_map else [frame]
        p = prompt(style, room_type, pieces, with_map)
        t0 = time.perf_counter()
        img, _ = await muse_image.edit(inputs, p, size=f"{w}x{h}")
        dt = time.perf_counter() - t0
        img = img.resize((w, h), Image.LANCZOS)
        name = f"{room_type}_{'map' if with_map else 'text'}"
        img.save(out / f"{name}.jpg", quality=92)
        lmap.save(out / f"{room_type}_layout_map.png")
        iou = await layout_iou(img, masks) if room_type != "balcony" else {}
        print(f"{name}: {dt:.1f}s iou={iou}", flush=True)
        return {"name": name, "seconds": round(dt, 1), "iou": iou, "prompt": p,
                "tiles": (frame, lmap, img)}

    jobs = [variant(rt, f, cs, m) for rt, (f, cs) in FRAMES.items() for m in (False, True)]
    results = await asyncio.gather(*jobs)

    lines = [f"# T4 restyle — {style}", "",
             "IoU = overlap of each piece before vs after (SAM on both); 1.0 = same place and size.", "",
             "| variant | seconds | mean IoU | per piece |", "|---|---|---|---|"]
    tiles = []
    for r in results:
        vals = [v for v in r["iou"].values() if v == v]
        mean = f"{np.mean(vals):.2f}" if vals else "–"
        per = ", ".join(f"{k} {v}" for k, v in r["iou"].items())
        lines.append(f"| {r['name']} | {r['seconds']} | {mean} | {per} |")
        frame, lmap, img = r.pop("tiles")
        if r["name"].endswith("text"):
            tiles += [label(frame, "original"), label(lmap, "SAM layout map")]
        tiles.append(label(img, r["name"]))
    (out / "report.md").write_text("\n".join(lines) + "\n")
    (out / "results.json").write_text(json.dumps(results, indent=2))
    contact_sheet(tiles, cols=4).save(out / "sheet.jpg", quality=85)
    print("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", default="Scandinavian")
    asyncio.run(run(ap.parse_args().style))
