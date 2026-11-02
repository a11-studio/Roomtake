"""T1b: where does SAM time go, and what is the fastest usable mode?

Run from backend/ after t1_sam_video.py (reuses its frames and keyframes):
    uv run python ../spikes/t1b_latency.py ~/Downloads/IMG_1184.MOV

Experiments:
  A  one concept alone on the video at 10 / 5 / 2 fps   -> does latency scale with frames?
  B  all concepts on the 5 fps video, in parallel       -> realistic wall time for video mode
  C  all concepts x 8 keyframes as images, in parallel  -> wall time for keyframe mode
Writes data/t1b/<video>/report.md and keyframes_image_mode.jpg.
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import DATA_DIR  # noqa: E402
from app.pipeline import sam, video  # noqa: E402
from app.pipeline.concepts import CONCEPTS  # noqa: E402
from app.pipeline.preview import contact_sheet, draw_frame  # noqa: E402


async def timed(coro):
    t0 = time.perf_counter()
    try:
        return await coro, time.perf_counter() - t0
    except Exception as e:
        print(f"    ERROR {e}")
        return None, time.perf_counter() - t0


async def prepare(src: Path, out: Path, fps: int) -> tuple[str, int]:
    """Normalize + upload once per fps; returns (file_id, frame count)."""
    d = out / f"{fps}fps"
    mp4 = d / "normalized.mp4"
    if not mp4.exists():
        video.normalize(src, mp4, fps=fps)
    id_file = d / "file_id.txt"
    if not id_file.exists():
        id_file.write_text(await sam.upload_video(mp4))
    frames = int(
        subprocess.run(
            ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
             "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(mp4)],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    )
    return id_file.read_text().strip(), frames


async def run(args: argparse.Namespace) -> None:
    out = DATA_DIR / "t1b" / args.video.stem
    out.mkdir(parents=True, exist_ok=True)
    concepts = list(CONCEPTS)
    lines = [f"# T1b SAM latency — {args.video.name}", ""]

    # A: single concept, no contention
    lines += ["## A. One concept alone (`sofa`)", "", "| fps | frames | latency s | tracks |", "|---|---|---|---|"]
    for fps in (10, 5, 2):
        file_id, n = await prepare(args.video, out, fps)
        res, dt = await timed(sam.segment_video(file_id, "sofa"))
        tr = sam.tracks_from_result(res, "sofa") if res else []
        print(f"A  {fps:>2} fps {n:>3} frames  {dt:6.1f}s  {len(tr)} track(s)")
        lines.append(f"| {fps} | {n} | {dt:.1f} | {len(tr)} |")

    # B: all concepts on 5 fps video
    file_id, n = await prepare(args.video, out, 5)
    sem = asyncio.Semaphore(args.parallel)

    async def vid(c):
        async with sem:
            return c, *(await timed(sam.segment_video(file_id, c)))

    t0 = time.perf_counter()
    b = await asyncio.gather(*(vid(c) for c in concepts))
    wall_b = time.perf_counter() - t0
    lat_b = [dt for _, r, dt in b if r]
    print(f"B  {len(concepts)} concepts @5fps: wall {wall_b:.0f}s, median req {statistics.median(lat_b):.0f}s")
    lines += [
        "", f"## B. {len(concepts)} concepts on 5 fps video ({n} frames), {args.parallel} parallel", "",
        f"wall **{wall_b:.0f} s**, request median {statistics.median(lat_b):.0f} s, max {max(lat_b):.0f} s, "
        f"~${len(concepts) * max(n, 50) * 0.0002:.2f}",
    ]

    # C: all concepts x keyframes as images (reuse t1 frames)
    frames = sorted((DATA_DIR / "t1" / f"{args.video.stem}_10fps" / "frames").glob("*.jpg"))
    keyframes = video.pick_keyframes(frames, k=8)

    async def img(c, k):
        async with sem:
            return c, k, *(await timed(sam.segment_image(frames[k], c)))

    t0 = time.perf_counter()
    c_res = await asyncio.gather(*(img(c, k) for c in concepts for k in keyframes))
    wall_c = time.perf_counter() - t0
    lat_c = [dt for *_, r, dt in c_res if r]
    errors = sum(1 for *_, r, _ in c_res if r is None)
    print(f"C  {len(c_res)} image requests: wall {wall_c:.0f}s, median req {statistics.median(lat_c):.1f}s, errors {errors}")
    lines += [
        "", f"## C. {len(concepts)} concepts x {len(keyframes)} keyframes as images, {args.parallel} parallel", "",
        f"wall **{wall_c:.0f} s**, request median {statistics.median(lat_c):.1f} s, max {max(lat_c):.1f} s, "
        f"errors {errors}, ~${len(c_res) * 0.0025:.2f}", "",
        "| keyframe | objects found |", "|---|---|",
    ]

    # contact sheet for image mode (object IDs are per image, not shared across keyframes)
    tiles = []
    for k in keyframes:
        tracks = [
            t for c, kk, r, _ in c_res if kk == k and r
            for t in sam.tracks_from_result(r, c)
        ]
        found = sorted({f"{t.concept}" for t in tracks})
        lines.append(f"| {k} | {len(tracks)}: {', '.join(found)} |")
        tiles.append(draw_frame(Image.open(frames[k]), tracks, 0))
    contact_sheet(tiles).save(out / "keyframes_image_mode.jpg", quality=85)

    (out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nOutputs in {out}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("video", type=Path)
    p.add_argument("--parallel", type=int, default=12)
    args = p.parse_args()
    args.video = args.video.expanduser()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
