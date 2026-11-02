"""T3: do Muse Wonder and Muse Spark accept images, and do they really see the room?

Run from backend/ after app.pipeline.room:
    uv run python ../spikes/t3_vision.py

Per model:
  A  vision probe: one frame + questions whose answers are only in the pixels
     (we know the truth: grey L-shaped sofa, remote + glass on a white coffee
     table, yellow box on its lower shelf, warm wall sconce, light shaggy rug)
  B  architect preview: all keyframes + compact inventory from room.json ->
     JSON with style, light, and 3 changes that reference inventory ids
Writes data/t3/report.md and data/t3/<model>_{probe,architect}.txt.
"""

from __future__ import annotations

import asyncio
import base64
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import DATA_DIR, SPARK_MODEL, WONDER_MODEL  # noqa: E402
from app.meta_client import async_client  # noqa: E402

ROOM = DATA_DIR / "rooms" / "IMG_1184"
OUT = DATA_DIR / "t3"
PRICES = {WONDER_MODEL: (4.00, 20.00), SPARK_MODEL: (1.25, 4.25)}  # $ per 1M in/out

PROBE = """Look at the photo and answer briefly, one line each:
1. Colour and shape of the sofa?
2. What lies on top of the coffee table?
3. Anything on the lower shelf of the coffee table? Colour?
4. What light source is on the wall on the right, and is it on?
5. Colour and texture of the rug?
6. What is visible through the window?"""

ARCHITECT = """You are an interior architect. The photos are keyframes from a video of one
apartment (living room + balcony). The inventory below was detected automatically;
use its ids. Look at the photos for style, colours, light and empty space.

Inventory:
{inventory}

Reply with JSON only:
{{"room_type": str, "style": str, "palette": [str], "light": str,
  "changes": [{{"action": "replace"|"add"|"remove"|"restyle", "target_id": str,
               "why": str, "product_category": str, "max_width_cm": int}}]}}
Give exactly 3 changes, each grounded in something visible in the photos."""


def image_part(path: Path) -> dict:
    b64 = base64.b64encode(path.read_bytes()).decode()
    return {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}


def inventory(room: dict) -> str:
    return "\n".join(
        f"- {o['id']} ({o['category']}): {o['color']['name']}, "
        f"{o['approx_size']['frame_area_pct']}% of frame, best view {o['best_frame']}"
        for o in room["objects"]
    )


async def ask(model: str, images: list[Path], text: str) -> dict:
    t0 = time.perf_counter()
    async with async_client() as api:
        try:
            r = await api.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": [*map(image_part, images),
                                                        {"type": "text", "text": text}]}],
            )
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}", "seconds": time.perf_counter() - t0}
    u = r.usage
    pin, pout = PRICES[model]
    return {
        "text": r.choices[0].message.content,
        "seconds": time.perf_counter() - t0,
        "in": u.prompt_tokens,
        "out": u.completion_tokens,
        "cost": (u.prompt_tokens * pin + u.completion_tokens * pout) / 1e6,
    }


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    room = json.loads((ROOM / "room.json").read_text())
    probe_img = ROOM / "frames" / "frame_0110.jpg"
    keyframes = [ROOM / k["file"] for k in room["keyframes"]]
    prompt = ARCHITECT.format(inventory=inventory(room))

    jobs = {
        (m, kind): ask(m, imgs, text)
        for m in (WONDER_MODEL, SPARK_MODEL)
        for kind, imgs, text in (("probe", [probe_img], PROBE), ("architect", keyframes, prompt))
    }
    results = dict(zip(jobs, await asyncio.gather(*jobs.values())))

    lines = ["# T3 — image input on Muse Wonder / Muse Spark", "",
             f"Probe: 1 frame ({probe_img.name}). Architect: {len(keyframes)} keyframes + "
             f"{len(room['objects'])}-object inventory.", "",
             "| model | test | ok | seconds | tokens in/out | cost $ |", "|---|---|---|---|---|---|"]
    for (m, kind), r in results.items():
        if "error" in r:
            lines.append(f"| {m} | {kind} | ERROR | {r['seconds']:.1f} | | |")
            (OUT / f"{m}_{kind}.txt").write_text(r["error"])
            continue
        lines.append(f"| {m} | {kind} | yes | {r['seconds']:.1f} | {r['in']}/{r['out']} | {r['cost']:.4f} |")
        (OUT / f"{m}_{kind}.txt").write_text(r["text"])
    for (m, kind), r in results.items():
        lines += ["", f"## {m} — {kind}", "", "```", r.get("text") or r.get("error", ""), "```"]
    (OUT / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    asyncio.run(main())
