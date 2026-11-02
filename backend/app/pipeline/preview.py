"""Debug drawings: masks, boxes and IDs over a frame, and contact sheets."""

import colorsys
import zlib

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app.pipeline import sam
from app.pipeline.concepts import CONCEPTS


def color_for(key: str) -> tuple[int, int, int]:
    h = (zlib.crc32(key.encode()) % 360) / 360
    r, g, b = colorsys.hsv_to_rgb(h, 0.85, 1.0)
    return int(r * 255), int(g * 255), int(b * 255)


def draw_frame(img: Image.Image, tracks: list[sam.Track], idx: int) -> Image.Image:
    w, h = img.size
    base = np.asarray(img.convert("RGB"), dtype=np.float32)
    labels = []
    for t in tracks:
        obs = t.observations.get(idx)
        if obs is None:
            continue
        key = f"{t.concept}#{t.object_id}"
        color = np.array(color_for(key), dtype=np.float32)
        if obs.mask is not None:
            m = sam.full_frame_mask(obs.mask, w, h)
            alpha = 0.25 if CONCEPTS.get(t.concept) == "zone" else 0.55
            base[m] = base[m] * (1 - alpha) + color * alpha
        labels.append((key, obs, tuple(int(c) for c in color)))
    out = Image.fromarray(base.astype(np.uint8))
    d = ImageDraw.Draw(out)
    font = ImageFont.load_default(size=max(14, h // 40))
    for key, obs, color in labels:
        l, t_, r, b = obs.box
        d.rectangle([l, t_, r, b], outline=color, width=2)
        text = key if obs.confidence is None else f"{key} {obs.confidence:.2f}"
        tb = d.textbbox((l + 3, t_ + 3), text, font=font)
        d.rectangle(tb, fill=(0, 0, 0))
        d.text((l + 3, t_ + 3), text, fill=color, font=font)
    d.text((8, 8), f"frame {idx}", fill=(255, 255, 255), font=font)
    return out


def object_gallery(objects: list[dict], room_dir, tile: int = 240, cols: int = 8) -> Image.Image:
    """One padded crop per room.json object with its id, mask edge tinted."""
    font = ImageFont.load_default(size=16)
    tiles = []
    for o in objects:
        img = Image.open(room_dir / o["best_frame"]).convert("RGB")
        mask = np.asarray(Image.open(room_dir / o["mask"])) > 0
        base = np.asarray(img, dtype=np.float32)
        color = np.array(color_for(o["id"]), dtype=np.float32)
        base[~mask] *= 0.55  # dim everything outside the object
        l, t, r, b = o["bbox"]
        pad = 0.1 * max(r - l, b - t)
        box = (max(0, l - pad), max(0, t - pad), min(img.width, r + pad), min(img.height, b + pad))
        crop = Image.fromarray(base.astype(np.uint8)).crop(box)
        crop.thumbnail((tile, tile - 22))
        cell = Image.new("RGB", (tile, tile), (20, 20, 20))
        cell.paste(crop, ((tile - crop.width) // 2, 0))
        d = ImageDraw.Draw(cell)
        d.text((6, tile - 20), o["id"], fill=tuple(int(c) for c in color), font=font)
        tiles.append(cell)
    return contact_sheet(tiles, cols=cols)


def contact_sheet(tiles: list[Image.Image], cols: int = 2) -> Image.Image:
    tw, th = tiles[0].size
    sheet = Image.new("RGB", (tw * cols, th * ((len(tiles) + cols - 1) // cols)))
    for i, tile in enumerate(tiles):
        sheet.paste(tile, ((i % cols) * tw, (i // cols) * th))
    return sheet
