"""Photos -> room.json: SAM 3.1 finds every concept on 1-3 photos of a room.

    uv run python -m app.pipeline.photos room.jpg balcony.jpg --out data/rooms/my_room

The product restyles single views, so photos are what it needs: the user
picks the views (the room from its best corner, a balcony) instead of us
picking frames from a video, the pictures are sharp, and analysis takes
about a minute instead of 4-5 (full-video tracking, room.py).

Writes the same files as the video pipeline (frames/, masks/, sam_tracks.pkl,
room.json, inventory.jpg) with photo i as frame i, so the stylist, restyle
and the layout check work unchanged. Each photo goes to SAM as a 1-frame clip:
video requests get far more throughput than image requests (T1b).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import pickle
import shutil
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

from app.pipeline import preview, sam
from app.pipeline.concepts import CONCEPTS
from app.pipeline.room import ATTEMPTS, MIN_AREA_PCT, MIN_CONFIDENCE, PARALLEL, dominant_color, frame_name, slug

register_heif_opener()  # iPhone photos (HEIC)

LONG_SIDE = 1280  # like the video frames (1280x720); Muse Image edits at this size
MAX_PHOTOS = 3
# A photo is a free-space zone (an empty balcony to furnish) when the zone covers
# a good part of it and more than the furniture does; otherwise it is the room.
ZONE_MIN_PCT = 8.0


def normalize(src: Path, dst: Path) -> tuple[int, int]:
    """Upright (EXIF), RGB, long side 1280, sides even for the H.264 clip."""
    img = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    scale = LONG_SIDE / max(img.size)
    w, h = (round(s * min(scale, 1.0) / 2) * 2 for s in img.size)
    img.resize((w, h), Image.LANCZOS).save(dst, quality=92)
    return w, h


def one_frame_clip(photo: Path, clip: Path) -> Path:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-framerate", "1", "-i", str(photo),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(clip)],
        check=True,
    )
    return clip


async def find_concepts(
    clips: list[Path], concepts: list[str], emit: Callable[[dict[str, Any]], None]
) -> tuple[dict[str, list[sam.Track]], list[str]]:
    """Tracks per concept, photo i on frame i. One request per (photo, concept)."""
    file_ids = await asyncio.gather(*(sam.upload_video(c) for c in clips))
    emit({"type": "uploaded"})
    sem = asyncio.Semaphore(PARALLEL)
    failures: list[str] = []
    found: dict[str, list[sam.Track]] = {}

    async def photo(i: int, concept: str) -> list[sam.Track]:
        async with sem:
            for attempt in range(ATTEMPTS):
                try:
                    result = await sam.segment_video(file_ids[i], concept)
                    break
                except Exception as e:
                    if attempt == ATTEMPTS - 1:
                        failures.append(f"{concept} (photo {i + 1}): {type(e).__name__}: {e}")
                        return []
                    emit({"type": "retry", "concept": concept, "error": type(e).__name__})
        tracks = sam.tracks_from_result(result, concept)
        for t in tracks:  # 1-frame clip: frame 0 is photo i
            t.object_id = f"{i}-{t.object_id}"
            t.observations = {i: o for o in t.observations.values()}
            for o in t.observations.values():
                o.frame = i
        return tracks

    async def concept(c: str) -> None:
        per_photo = await asyncio.gather(*(photo(i, c) for i in range(len(clips))))
        found[c] = [t for ts in per_photo for t in ts]
        # the same sofa can be on two photos: count the most seen on one
        count = max((sum(1 for t in ts if any((o.confidence or 0) >= MIN_CONFIDENCE
                                              for o in t.observations.values())) for ts in per_photo), default=0)
        emit({"type": "found", "concept": c, "count": count})

    await asyncio.gather(*(concept(c) for c in concepts))
    return found, failures


def view_kind(tracks: dict[str, list[sam.Track]], concepts: dict[str, str], i: int, w: int, h: int) -> tuple[str, str]:
    """("main", "room") or ("zone", "balcony floor") for photo i, from box areas."""
    area: dict[str, float] = {}
    for c, ts in tracks.items():
        for t in ts:
            o = t.observations.get(i)
            if o is not None and (o.confidence or 0) >= MIN_CONFIDENCE:
                l, tp, r, b = o.box
                area[c] = area.get(c, 0) + (r - l) * (b - tp) / (w * h) * 100
    furniture = sum(a for c, a in area.items() if concepts[c] == "furniture")
    zones = {c: a for c, a in area.items() if concepts[c] == "zone" and c != "floor"}
    if zones:
        zone, a = max(zones.items(), key=lambda kv: kv[1])
        if a >= ZONE_MIN_PCT and a > furniture:
            return "zone", zone
    return "main", "room"


async def analyze_photos(
    photos: list[Path],
    out: Path,
    concepts: dict[str, str] = CONCEPTS,
    on_event: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    emit = on_event or (lambda e: None)
    t0 = time.perf_counter()
    photos = photos[:MAX_PHOTOS]
    frame_dir, mask_dir, clip_dir = out / "frames", out / "masks", out / "clips"
    for d in (frame_dir, mask_dir, clip_dir):
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)

    sizes, clips = [], []
    for i, src in enumerate(photos):
        sizes.append(normalize(src, frame_dir / frame_name(i)))
        clips.append(one_frame_clip(frame_dir / frame_name(i), clip_dir / f"photo_{i}.mp4"))
    emit({"type": "keyframes", "count": len(photos)})
    t_prep = time.perf_counter() - t0

    t1 = time.perf_counter()
    tracks, failures = await find_concepts(clips, list(concepts), emit)
    (out / "sam_tracks.pkl").write_bytes(pickle.dumps(tracks))
    shutil.rmtree(clip_dir)
    t_sam = time.perf_counter() - t1

    objects = []
    for concept in concepts:
        views = []
        for t in tracks.get(concept, []):
            (i, o), = t.observations.items()
            if o.mask is None or (o.confidence or 0) < MIN_CONFIDENCE:
                continue
            w, h = sizes[i]
            mask = sam.full_frame_mask(o.mask, w, h)
            if mask.mean() * 100 >= MIN_AREA_PCT:
                views.append((t, i, o, mask))
        views.sort(key=lambda v: (v[1], v[2].box[0]))  # photo, then left to right
        for n, (t, i, o, mask) in enumerate(views):
            oid = f"{slug(concept)}_{n + 1}"
            w, h = sizes[i]
            Image.fromarray(mask.astype(np.uint8) * 255).save(mask_dir / f"{oid}.png")
            hex_, name = dominant_color(np.asarray(Image.open(frame_dir / frame_name(i))), mask)
            l, tp, r, b = o.box
            objects.append({
                "id": oid,
                "label": concept,
                "track_id": t.object_id,
                "category": concepts[concept],
                "best_frame": f"frames/{frame_name(i)}",
                "mask": f"masks/{oid}.png",
                "bbox": [round(l), round(tp), round(r), round(b)],
                "approx_size": {
                    "frame_area_pct": round(float(mask.mean()) * 100, 2),
                    "bbox_w_pct": round((r - l) / w * 100, 1),
                    "bbox_h_pct": round((b - tp) / h * 100, 1),
                },
                "color": {"hex": hex_, "name": name},
                "confidence": round(o.confidence or 0, 2),
                "seen_in_keyframes": [f"frames/{frame_name(i)}"],
            })

    views = []
    for i, (w, h) in enumerate(sizes):
        kind, label = view_kind(tracks, concepts, i, w, h)
        views.append({"file": f"frames/{frame_name(i)}", "frame": i, "kind": kind, "label": label})
    if views and not any(v["kind"] == "main" for v in views):
        views[0].update(kind="main", label="room")  # the stylist needs the room itself

    room = {
        "source": "photos",
        "source_video": None,
        "frame_size": list(sizes[0]),
        "keyframes": [{"file": v["file"], "time_s": 0,
                       "brightness": round(float(np.asarray(Image.open(out / v["file"]).convert("L")).mean() / 255), 2)}
                      for v in views],
        "views": views,
        "objects": objects,
        "stats": {
            "photos": len(photos),
            "concepts": len(concepts),
            "failed": failures,
            "seconds": {"prepare": round(t_prep, 1), "sam": round(t_sam, 1),
                        "total": round(time.perf_counter() - t0, 1)},
        },
    }
    (out / "room.json").write_text(json.dumps(room, indent=2, ensure_ascii=False))
    emit({"type": "done", "objects": len(objects)})
    preview.object_gallery(objects, out).save(out / "inventory.jpg", quality=85)
    return room


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("photos", type=Path, nargs="+")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    out = args.out if args.out.is_absolute() else Path.cwd() / args.out
    room = asyncio.run(analyze_photos([p.expanduser() for p in args.photos], out,
                                      on_event=lambda e: print(e, flush=True)))
    print(json.dumps(room["stats"], indent=2))
    print(f"{len(room['objects'])} objects, views {[v['kind'] + ':' + v['label'] for v in room['views']]}")


if __name__ == "__main__":
    main()
