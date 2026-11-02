"""Video -> room.json: SAM 3.1 tracks every concept through the whole video.

    uv run python -m app.pipeline.room ~/Downloads/IMG_1184.MOV

Full-video tracking at 10 fps (~4-5 min for 23 concepts on a 24 s clip).
We tried faster modes (keyframes as images, keyframes as a 1 fps clip) and
they got details wrong: 5 chairs instead of 4, shelves split into boards in
close-ups, small side tables missed. Seeing every frame lets SAM keep one ID
per real object, so one track = one object. Each object gets the frame where
it is seen largest and uncut, preferring keyframes; that frame is the one
Muse Image edits later.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import pickle
import re
import shutil
import time
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from app.config import DATA_DIR
from app.pipeline import preview, sam, video
from app.pipeline.concepts import CONCEPTS

FPS = 10
MIN_CONFIDENCE = 0.5
# Best view smaller than this share of the frame is a fragment, not an object
# (IMG_1184: two 0.03-0.05% "tv stands"; the smallest real item, a wall lamp, is 0.15%).
MIN_AREA_PCT = 0.1

# Coarse names so the architect can reason ("beige sofa") without hex codes.
COLOR_NAMES = {
    "black": (25, 25, 25), "dark grey": (80, 80, 80), "grey": (140, 140, 140),
    "light grey": (200, 200, 200), "white": (240, 240, 240), "beige": (215, 195, 165),
    "brown": (120, 80, 50), "light wood": (190, 150, 105), "red": (190, 40, 40),
    "pink": (230, 150, 170), "orange": (230, 130, 40), "yellow": (230, 200, 60),
    "green": (70, 140, 70), "olive": (130, 130, 60), "teal": (40, 130, 130),
    "blue": (50, 90, 180), "navy": (30, 40, 90), "purple": (120, 70, 150),
}


def dominant_color(img: np.ndarray, mask: np.ndarray) -> tuple[str, str]:
    rgb = np.median(img[mask], axis=0) if mask.any() else np.zeros(3)
    name = min(COLOR_NAMES, key=lambda n: np.sum((np.array(COLOR_NAMES[n]) - rgb) ** 2))
    return "#%02x%02x%02x" % tuple(int(c) for c in rgb), name


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def frame_name(idx: int) -> str:
    return f"frame_{idx:04d}.jpg"


def view_score(obs: sam.Observation, w: int, h: int, keyframes: set[int]) -> float:
    """How good a view of the object this frame is: big, confident, not cut
    off by the frame edge, and a keyframe if possible. Uses the box so we
    don't decode thousands of masks."""
    l, t, r, b = obs.box
    score = (r - l) * (b - t) * (obs.confidence or 0)
    if l <= 2 or t <= 2 or r >= w - 3 or b >= h - 3:
        score *= 0.5
    if obs.frame in keyframes:
        score *= 1.5
    return score


PARALLEL = 8
ATTEMPTS = 3


def pick_views(
    concepts: dict[str, str], all_tracks: list[list[sam.Track]], w: int, h: int
) -> list[tuple[int, str, str]]:
    """Frames to restyle as whole views: (frame, kind, label).

    main: the frame where uncut furniture covers the most of the picture (the
    "hero" shot; on IMG_1184 the sofa corner, not the dining nook).
    zone: for each free-space zone other than plain floor (e.g. the balcony),
    the frame where it is large, centred and low in the picture, i.e. you look
    at it rather than past it; only if it covers at least 3% of the frame.
    """
    furniture: dict[int, float] = defaultdict(float)
    zone_best: dict[str, tuple[float, int]] = {}
    for concept, tracks in zip(concepts, all_tracks):
        cat = concepts[concept]
        for track in tracks:
            for f, o in track.observations.items():
                if (o.confidence or 0) < MIN_CONFIDENCE:
                    continue
                l, t, r, b = o.box
                area = (r - l) * (b - t) / (w * h)
                if cat == "furniture" and l > 2 and r < w - 3:
                    furniture[f] += area
                elif cat == "zone" and concept != "floor" and area >= 0.03:
                    centred = 1 - abs((l + r) / 2 / w - 0.5)
                    score = area * centred * (b / h)
                    if score > zone_best.get(concept, (0, -1))[0]:
                        zone_best[concept] = (score, f)
    views = [(max(furniture, key=furniture.get), "main", "room")] if furniture else []
    views += [(f, "zone", concept) for concept, (_, f) in zone_best.items()]
    return views


async def track_concepts(
    clip: Path,
    concepts: list[str],
    cache: dict[str, list[sam.Track]],
    emit: Callable[[dict[str, Any]], None],
) -> list[str]:
    """Fill `cache` with tracks for every concept not in it yet.

    Under load the API sometimes drops a long stream mid-way (23 concepts at
    once: 9 dropped), so run at most PARALLEL at a time and resend failures.
    """
    file_id = await sam.upload_video(clip)
    emit({"type": "uploaded"})
    sem = asyncio.Semaphore(PARALLEL)
    failures: list[str] = []

    async def one(concept: str) -> None:
        async with sem:
            for attempt in range(ATTEMPTS):
                try:
                    result = await sam.segment_video(file_id, concept)
                    break
                except Exception as e:
                    if attempt == ATTEMPTS - 1:
                        failures.append(f"{concept}: {type(e).__name__}: {e}")
                        return
                    emit({"type": "retry", "concept": concept, "error": type(e).__name__})
        cache[concept] = sam.tracks_from_result(result, concept)
        emit({"type": "found", "concept": concept, "count": len(cache[concept])})

    await asyncio.gather(*(one(c) for c in concepts if c not in cache))
    return failures


async def analyze_room(
    src: Path,
    out: Path,
    concepts: dict[str, str] = CONCEPTS,
    k: int = 8,
    reuse_sam: bool = False,
    on_event: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    emit = on_event or (lambda e: None)
    t0 = time.perf_counter()
    out.mkdir(parents=True, exist_ok=True)

    clip = out / "video.mp4"
    if not (reuse_sam and clip.exists()):
        video.normalize(src, clip, fps=FPS, height=720)
    all_frames = out / "all_frames"
    frames = video.extract_frames(clip, all_frames)
    picks = video.pick_keyframes(frames, k=k)
    emit({"type": "keyframes", "count": len(picks)})
    t_prep = time.perf_counter() - t0

    # SAM is the slow, paid part; cache tracks per concept so room.json can be
    # rebuilt offline and a rerun only asks for concepts that failed before.
    cache_file = out / "sam_tracks.pkl"
    cache: dict[str, list[sam.Track]] = (
        pickle.loads(cache_file.read_bytes()) if reuse_sam and cache_file.exists() else {}
    )
    t1 = time.perf_counter()
    failures = []
    if any(c not in cache for c in concepts):
        failures = await track_concepts(clip, list(concepts), cache, emit)
        cache_file.write_bytes(pickle.dumps(cache))
    all_tracks = [cache.get(c, []) for c in concepts]
    t_sam = time.perf_counter() - t1

    w, h = Image.open(frames[0]).size
    keyset = set(picks)
    frame_dir = out / "frames"
    mask_dir = out / "masks"
    for d in (frame_dir, mask_dir):
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir()

    used: set[int] = set(picks)
    objects = []
    for concept, tracks in zip(concepts, all_tracks):
        views = []
        for track in tracks:
            obs = [o for o in track.observations.values()
                   if o.mask is not None and (o.confidence or 0) >= MIN_CONFIDENCE]
            if not obs:
                continue
            best = max(obs, key=lambda o: view_score(o, w, h, keyset))
            mask = sam.full_frame_mask(best.mask, w, h)
            if mask.mean() * 100 >= MIN_AREA_PCT:
                views.append((track, best, mask))
        views.sort(key=lambda v: (v[0].frames[0], v[1].box[0]))
        for n, (track, best, mask) in enumerate(views):
            oid = f"{slug(concept)}_{n + 1}"
            Image.fromarray(mask.astype(np.uint8) * 255).save(mask_dir / f"{oid}.png")
            img = np.asarray(Image.open(frames[best.frame]).convert("RGB"))
            hex_, name = dominant_color(img, mask)
            used.add(best.frame)
            l, t, r, b = best.box
            visible = track.frames
            objects.append({
                "id": oid,
                "label": concept,
                "track_id": track.object_id,
                "category": concepts[concept],
                "best_frame": f"frames/{frame_name(best.frame)}",
                "mask": f"masks/{oid}.png",
                "bbox": [round(l), round(t), round(r), round(b)],
                "approx_size": {
                    "frame_area_pct": round(float(mask.mean()) * 100, 2),
                    "bbox_w_pct": round((r - l) / w * 100, 1),
                    "bbox_h_pct": round((b - t) / h * 100, 1),
                },
                "color": {"hex": hex_, "name": name},
                "confidence": round(best.confidence or 0, 2),
                "visible_s": [round(visible[0] / FPS, 1), round(visible[-1] / FPS, 1)],
                "seen_in_keyframes": [f"frames/{frame_name(p)}" for p in picks if p in track.observations],
            })

    views = pick_views(concepts, all_tracks, w, h)
    used.update(f for f, _, _ in views)

    # keep only frames something points at
    for idx in sorted(used):
        shutil.copy(frames[idx], frame_dir / frame_name(idx))
    shutil.rmtree(all_frames)

    room = {
        "source_video": src.name,
        "frame_size": [w, h],
        "fps": FPS,
        "keyframes": [
            {"file": f"frames/{frame_name(p)}", "time_s": round(p / FPS, 1),
             "brightness": round(float(np.asarray(Image.open(frame_dir / frame_name(p)).convert("L")).mean() / 255), 2)}
            for p in picks
        ],
        "views": [{"file": f"frames/{frame_name(f)}", "frame": f, "kind": k, "label": lbl}
                  for f, k, lbl in views],
        "objects": objects,
        "stats": {
            "concepts": len(concepts),
            "failed": failures,
            "seconds": {"prepare": round(t_prep, 1), "sam": round(t_sam, 1),
                        "total": round(time.perf_counter() - t0, 1)},
        },
    }
    (out / "room.json").write_text(json.dumps(room, indent=2, ensure_ascii=False))
    emit({"type": "done", "objects": len(objects)})

    # debug/UI sheet: one crop per object
    preview.object_gallery(objects, out).save(out / "inventory.jpg", quality=85)
    return room


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("video", type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--reuse-sam", action="store_true", help="reuse cached SAM tracks; only missing concepts hit the API")
    args = p.parse_args()
    src = args.video.expanduser()
    out = args.out or DATA_DIR / "rooms" / src.stem
    room = asyncio.run(
        analyze_room(src, out, reuse_sam=args.reuse_sam, on_event=lambda e: print(e, flush=True))
    )
    print(json.dumps(room["stats"], indent=2))
    print(f"{len(room['objects'])} objects -> {out / 'room.json'}")


if __name__ == "__main__":
    main()
