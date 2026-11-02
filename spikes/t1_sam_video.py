"""T1: does SAM 3.1 find our furniture from text prompts and keep object IDs?

Run from backend/:
    uv run python ../spikes/t1_sam_video.py ~/Downloads/IMG_1184.MOV

Writes to data/t1/<video-stem>/:
    report.md        per-concept tracks, frame coverage, fragmentation, confidence
    tracks.json      raw per-frame boxes for every track
    keyframes.jpg    sharpest keyframes with masks + IDs drawn
    overlay.mp4      the whole clip with masks + IDs (check ID stability by eye)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import DATA_DIR  # noqa: E402
from app.pipeline import sam, video  # noqa: E402
from app.pipeline.concepts import CONCEPTS  # noqa: E402
from app.pipeline.preview import contact_sheet, draw_frame  # noqa: E402


def fragments(frames: list[int]) -> int:
    """Number of contiguous runs; 1 means the ID was held without a gap."""
    return 1 + sum(1 for a, b in zip(frames, frames[1:]) if b - a > 1) if frames else 0



async def run(args: argparse.Namespace) -> None:
    out = DATA_DIR / "t1" / f"{args.video.stem}_{args.fps}fps"
    out.mkdir(parents=True, exist_ok=True)

    small = out / "normalized.mp4"
    if not small.exists():
        print(f"Normalizing to {args.fps} fps / {args.height}p ...")
        video.normalize(args.video, small, fps=args.fps, height=args.height)
    frames = video.extract_frames(small, out / "frames")
    fw, fh = Image.open(frames[0]).size
    print(f"{len(frames)} frames at {fw}x{fh}")

    id_file = out / "file_id.txt"
    if id_file.exists():
        file_id = id_file.read_text().strip()
    else:
        print("Uploading ...")
        file_id = await sam.upload_video(small)
        id_file.write_text(file_id)
    print(f"file_id={file_id}")

    sem = asyncio.Semaphore(args.parallel)

    async def one(concept: str):
        async with sem:
            t0 = time.perf_counter()
            try:
                result = await sam.segment_video(file_id, concept)
            except Exception as e:  # report and keep going with other concepts
                print(f"  {concept:15s} ERROR {e}")
                return concept, None, time.perf_counter() - t0
            dt = time.perf_counter() - t0
            tr = sam.tracks_from_result(result, concept)
            print(f"  {concept:15s} {len(tr)} track(s) in {dt:.1f}s")
            return concept, tr, dt

    print(f"Segmenting {len(args.concepts)} concepts ({args.parallel} in parallel) ...")
    t_all = time.perf_counter()
    results = await asyncio.gather(*(one(c) for c in args.concepts))
    wall = time.perf_counter() - t_all

    all_tracks = [t for _, tr, _ in results if tr for t in tr]
    keyframes = video.pick_keyframes(frames, k=8)

    # report
    n = len(frames)
    lines = [
        f"# T1 SAM 3.1 — {args.video.name}",
        "",
        f"{n} frames @ {args.fps} fps, {fw}x{fh}. Keyframes: {keyframes}",
        f"{len(args.concepts)} concepts, {args.parallel} in parallel, wall time {wall:.0f} s, "
        f"~${len(args.concepts) * max(n, 50) * 0.0002:.2f}",
        "",
        "| concept | category | tracks | time s | track | frames visible | coverage | runs | mean conf | in keyframes |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    dump = {}
    for concept, tr, dt in results:
        cat = CONCEPTS.get(concept, "")
        if tr is None:
            lines.append(f"| {concept} | {cat} | ERROR | {dt:.1f} | | | | | | |")
            continue
        if not tr:
            lines.append(f"| {concept} | {cat} | 0 | {dt:.1f} | | | | | | |")
        for i, t in enumerate(tr):
            fr = t.frames
            confs = [o.confidence for o in t.observations.values() if o.confidence is not None]
            conf = f"{np.mean(confs):.2f}" if confs else "–"
            kf = [k for k in keyframes if k in t.observations]
            head = f"| {concept} | {cat} | {len(tr)} | {dt:.1f} |" if i == 0 else "| | | | |"
            lines.append(
                f"{head} #{t.object_id} | {fr[0]}–{fr[-1]} ({len(fr)}) | "
                f"{len(fr) / n:.0%} | {fragments(fr)} | {conf} | {kf} |"
            )
            dump[f"{concept}#{t.object_id}"] = {
                str(f): {"box": o.box, "conf": o.confidence} for f, o in sorted(t.observations.items())
            }
    lines += [
        "",
        "`runs` = number of contiguous visibility runs for one ID (1 = held with no gap).",
        "",
    ]
    (out / "report.md").write_text("\n".join(lines))
    (out / "tracks.json").write_text(json.dumps(dump))

    # keyframe contact sheet
    tiles = [draw_frame(Image.open(frames[k]), all_tracks, k) for k in keyframes]
    contact_sheet(tiles).save(out / "keyframes.jpg", quality=85)

    # overlay video
    if not args.no_video:
        print("Rendering overlay video ...")
        ov_dir = out / "overlay"
        ov_dir.mkdir(exist_ok=True)
        for i, f in enumerate(frames):
            draw_frame(Image.open(f), all_tracks, i).save(ov_dir / f"{i:05d}.jpg", quality=80)
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-framerate", str(args.fps), "-i",
             str(ov_dir / "%05d.jpg"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-movflags", "+faststart", str(out / "overlay.mp4")],
            check=True,
        )

    print("\n".join(lines))
    print(f"\nOutputs in {out}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("video", type=Path)
    p.add_argument("--concept", dest="concepts", action="append", help="repeatable; default: furniture list")
    p.add_argument("--fps", type=int, default=10)
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--parallel", type=int, default=12)
    p.add_argument("--no-video", action="store_true", help="skip overlay.mp4")
    args = p.parse_args()
    args.concepts = args.concepts or list(CONCEPTS)
    args.video = args.video.expanduser()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
