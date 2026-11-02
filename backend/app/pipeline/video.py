"""Video preprocessing: normalize for SAM, dump frames, pick sharp keyframes."""

import subprocess
from pathlib import Path

import numpy as np
from PIL import Image


def normalize(src: Path, dst: Path, fps: int = 15, height: int = 720) -> Path:
    """Re-encode to a small H.264 MP4 (no audio, faststart) that SAM accepts.

    Lower fps/resolution keeps SAM cost and latency down; furniture does not
    move, so 15 fps is plenty for tracking.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y", "-i", str(src),
            "-map", "0:v:0", "-an",
            "-vf", f"fps={fps},scale=-2:{height}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(dst),
        ],
        check=True,
    )
    return dst


def extract_frames(
    video: Path, out_dir: Path, fps: int | None = None, height: int | None = None
) -> list[Path]:
    """Dump frames as JPEG (frame index = list index), optionally resampled/scaled."""
    out_dir.mkdir(parents=True, exist_ok=True)
    filters = [f for f in (fps and f"fps={fps}", height and f"scale=-2:{height}") if f]
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(video),
         *(["-vf", ",".join(filters)] if filters else []),
         "-q:v", "2", "-start_number", "0", str(out_dir / "%05d.jpg")],
        check=True,
    )
    return sorted(out_dir.glob("*.jpg"))


def sharpness(path: Path) -> float:
    """Variance of the Laplacian on a grayscale downscale; higher = sharper."""
    img = Image.open(path).convert("L")
    img.thumbnail((640, 640))
    g = np.asarray(img, dtype=np.float32)
    lap = (
        -4 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:]
    )
    return float(lap.var())


def _thumb(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("L").resize((64, 36)), dtype=np.float32) / 255


# Mean absolute difference of 64x36 grayscale thumbnails. On IMG_1184 the same
# view a second apart scores ~0.05, a different part of the room ~0.22+.
MIN_VIEW_DIFF = 0.12


def pick_keyframes(frames: list[Path], k: int = 8) -> list[int]:
    """Up to k sharp frames that each show a different view of the room.

    The timeline is split into k equal segments and the sharpest frame in the
    middle 60% of each is taken (sharpness is only compared within a segment:
    a textured view like trees outside always scores higher than a plain wall).
    A pick that looks like an already kept one is merged, keeping the sharper,
    so a slow pan over the same spot yields fewer than k keyframes.
    """
    scores = [sharpness(f) for f in frames]
    bounds = np.linspace(0, len(frames), k + 1)
    picks: list[int] = []
    for start, end in zip(bounds[:-1], bounds[1:]):
        lo, hi = int(start + 0.2 * (end - start)), int(np.ceil(end - 0.2 * (end - start)))
        if hi <= lo:
            continue
        i = lo + int(np.argmax(scores[lo:hi]))
        thumb = _thumb(frames[i])
        dup = next(
            (j for j, p in enumerate(picks)
             if np.abs(thumb - _thumb(frames[p])).mean() < MIN_VIEW_DIFF),
            None,
        )
        if dup is None:
            picks.append(i)
        elif scores[i] > scores[picks[dup]]:
            picks[dup] = i
    return sorted(picks)
