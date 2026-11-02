"""Video -> room.json: keyframes, SAM 3.1 tracks across them, one inventory.

    uv run python -m app.pipeline.room ~/Downloads/IMG_1184.MOV

The 5-8 keyframes are packed into a tiny 1 fps video and SAM runs once per
concept on it (all concepts in parallel, ~9 s in total on IMG_1184). Video
mode keeps object IDs across keyframes, so one track = one real object, and
each object gets the keyframe where it is seen largest and clearest. Those
keyframes are also the frames Muse Image edits later.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import shutil
import subprocess
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

MIN_CONFIDENCE = 0.5

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


def keyframes_video(keyframes: list[Path], dst: Path) -> Path:
    """One keyframe per second; SAM sees them as consecutive video frames."""
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-framerate", "1",
         "-i", str(keyframes[0].parent / "kf%d.jpg"),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dst)],
        check=True,
    )
    return dst


async def analyze_room(
    src: Path,
    out: Path,
    concepts: dict[str, str] = CONCEPTS,
    k: int = 8,
    on_event: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    emit = on_event or (lambda e: None)
    t0 = time.perf_counter()

    frames = video.extract_frames(src, out / "frames", fps=10, height=720)
    picks = video.pick_keyframes(frames, k=k)
    kf_dir = out / "keyframes"
    shutil.rmtree(kf_dir, ignore_errors=True)
    kf_dir.mkdir(parents=True)
    keyframes = []
    for i, f in enumerate(picks):
        path = kf_dir / f"kf{i}.jpg"
        shutil.copy(frames[f], path)
        keyframes.append(path)
    shutil.rmtree(out / "frames")
    emit({"type": "keyframes", "count": len(keyframes)})

    file_id = await sam.upload_video(keyframes_video(keyframes, out / "keyframes.mp4"))
    t_prep = time.perf_counter() - t0

    imgs = [np.asarray(Image.open(p).convert("RGB")) for p in keyframes]
    h, w = imgs[0].shape[:2]
    failures: list[str] = []

    async def one(concept: str) -> list[sam.Track]:
        try:
            result = await sam.segment_video(file_id, concept)
        except Exception as e:
            failures.append(f"{concept}: {type(e).__name__}: {e}")
            return []
        tracks = sam.tracks_from_result(result, concept)
        if tracks:
            emit({"type": "found", "concept": concept, "count": len(tracks)})
        return tracks

    t1 = time.perf_counter()
    all_tracks = await asyncio.gather(*(one(c) for c in concepts))
    t_sam = time.perf_counter() - t1

    mask_dir = out / "masks"
    shutil.rmtree(mask_dir, ignore_errors=True)
    mask_dir.mkdir()
    objects = []
    drawn: dict[int, list[sam.Track]] = defaultdict(list)  # for the debug sheet
    for concept, tracks in zip(concepts, all_tracks):
        views = []
        for track in tracks:
            obs = [o for o in track.observations.values()
                   if o.mask is not None and (o.confidence or 0) >= MIN_CONFIDENCE]
            if not obs:
                continue
            masks = {o.frame: sam.full_frame_mask(o.mask, w, h) for o in obs}
            best = max(obs, key=lambda o: masks[o.frame].mean() * (o.confidence or 0))
            views.append((track, best, masks[best.frame]))
        views.sort(key=lambda v: (v[1].frame, v[1].box[0]))
        for n, (track, best, mask) in enumerate(views):
            oid = f"{slug(concept)}_{n + 1}"
            Image.fromarray(mask.astype(np.uint8) * 255).save(mask_dir / f"{oid}.png")
            hex_, name = dominant_color(imgs[best.frame], mask)
            l, t, r, b = best.box
            objects.append({
                "id": oid,
                "label": concept,
                "category": concepts[concept],
                "best_frame": keyframes[best.frame].name,
                "mask": f"masks/{oid}.png",
                "bbox": [round(l), round(t), round(r), round(b)],
                "approx_size": {
                    "frame_area_pct": round(float(mask.mean()) * 100, 2),
                    "bbox_w_pct": round((r - l) / w * 100, 1),
                    "bbox_h_pct": round((b - t) / h * 100, 1),
                },
                "color": {"hex": hex_, "name": name},
                "confidence": round(best.confidence or 0, 2),
                "seen_in": [keyframes[f].name for f in track.frames],
            })
            shown = sam.Track(concept, str(n + 1))
            shown.observations[best.frame] = best
            drawn[best.frame].append(shown)

    room = {
        "source_video": src.name,
        "frame_size": [w, h],
        "keyframes": [
            {"file": p.name, "frame_10fps": f, "time_s": round(f / 10, 1),
             "brightness": round(float(img.mean() / 255), 2)}
            for p, f, img in zip(keyframes, picks, imgs)
        ],
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

    # debug sheet: each inventory object drawn on its best keyframe
    tiles = [
        preview.draw_frame(Image.open(path), drawn[ki], ki) for ki, path in enumerate(keyframes)
    ]
    preview.contact_sheet(tiles).save(out / "inventory.jpg", quality=85)
    return room


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("video", type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    src = args.video.expanduser()
    out = args.out or DATA_DIR / "rooms" / src.stem
    room = asyncio.run(analyze_room(src, out, on_event=lambda e: print(e, flush=True)))
    print(json.dumps(room["stats"], indent=2))
    print(f"{len(room['objects'])} objects -> {out / 'room.json'}")


if __name__ == "__main__":
    main()
