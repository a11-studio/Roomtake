"""T2: can Muse Image swap/add one product in our real frame and keep the rest?

Run from backend/ after app.pipeline.room (uses its room.json, frames, masks):
    uv run python ../spikes/t2_muse_image.py

Cases (products from DummyJSON):
  swap_sofa      sofa_1 -> "Annibale Colombo Sofa"
  add_lamp       "Table Lamp" on top of side_table_1
  balcony_plant  "Plant Pot" on the empty balcony_floor_1
Each case: Muse Image edit with [room frame, product photo], then the edit is
pasted back only inside the SAM region. Writes data/t2/<case>/ and
data/t2/report.md + sheet.jpg (original | Muse Image raw | composited).
"""

from __future__ import annotations

import asyncio
import io
import json
import sys
import time
from pathlib import Path

import httpx
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import DATA_DIR  # noqa: E402
from app.pipeline.preview import contact_sheet  # noqa: E402
from app.render import muse_image  # noqa: E402

ROOM = DATA_DIR / "rooms" / "IMG_1184"
OUT = DATA_DIR / "t2"
CDN = "https://cdn.dummyjson.com/product-images"

KEEP = (
    "Keep everything else in image 1 exactly as it is: same walls, floor, "
    "windows, furniture, objects, lighting, camera angle and framing. "
    "Return the full room photo, not a close-up."
)

CASES = [
    {
        "name": "swap_sofa",
        "object": "sofa_1",
        "product": ("Annibale Colombo Sofa", f"{CDN}/furniture/annibale-colombo-sofa/1.webp"),
        "region": {"grow_pct": 0.15},
        "prompt": (
            "Image 1 is a photo of my living room. Image 2 is a product photo of a sofa. "
            "Replace the light grey corner sofa in image 1 (and the cushions on it) with "
            "the sofa from image 2: same design, colour and material as in image 2, "
            "standing where the old sofa stands, at a realistic size for this room, "
            "with matching perspective, lighting and floor shadows. " + KEEP
        ),
    },
    {
        "name": "add_lamp",
        "object": "side_table_1",
        "product": ("Table Lamp", f"{CDN}/home-decoration/table-lamp/1.webp"),
        "region": {"grow_pct": 0.15, "grow_up": 1.6},
        "prompt": (
            "Image 1 is a photo of my living room. Image 2 is a product photo of a table "
            "lamp. Place the lamp from image 2 on top of the small round side table on "
            "the right of image 1, same design and colours as in image 2, at a realistic "
            "size for that table, with matching perspective and lighting. " + KEEP
        ),
    },
    {
        "name": "balcony_plant",
        "object": "balcony_floor_1",
        "product": ("Plant Pot", f"{CDN}/home-decoration/plant-pot/1.webp"),
        "region": {"grow_pct": 0.05, "grow_up": 0.6},
        "prompt": (
            "Image 1 is a photo of my empty balcony. Image 2 is a product photo of a "
            "plant pot with a plant. Place the plant pot from image 2 on the tiled "
            "balcony floor, against the wall on the right, same design as in image 2, "
            "at a realistic size, with matching perspective, daylight and a soft shadow. "
            + KEEP
        ),
    },
]


def label(img: Image.Image, text: str) -> Image.Image:
    img = img.copy()
    d = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=28)
    tb = d.textbbox((12, 12), text, font=font)
    d.rectangle((tb[0] - 6, tb[1] - 6, tb[2] + 6, tb[3] + 6), fill=(0, 0, 0))
    d.text((12, 12), text, fill=(255, 255, 255), font=font)
    return img


async def run_case(case: dict, objects: dict) -> dict:
    out = OUT / case["name"]
    out.mkdir(parents=True, exist_ok=True)
    obj = objects[case["object"]]
    frame = Image.open(ROOM / obj["best_frame"]).convert("RGB")
    mask = np.asarray(Image.open(ROOM / obj["mask"])) > 0
    region = muse_image.edit_region(mask, **case["region"])

    title, url = case["product"]
    async with httpx.AsyncClient(timeout=60) as http:
        product = Image.open(io.BytesIO((await http.get(url)).content)).convert("RGB")
    product.save(out / "product.png")
    frame.save(out / "original.png")
    Image.fromarray(region.astype(np.uint8) * 255).save(out / "region.png")

    t0 = time.perf_counter()
    try:
        raw, meta = await muse_image.edit([frame, product], case["prompt"], size="1280x720")
    except Exception as e:
        return {"case": case["name"], "error": str(e), "seconds": round(time.perf_counter() - t0, 1)}
    dt = time.perf_counter() - t0
    raw.save(out / "raw.png")
    comp = muse_image.composite(frame, raw, region)
    comp.save(out / "composite.png")
    print(f"{case['name']}: {dt:.1f}s, output {raw.size}", flush=True)

    thumb = product.copy()
    thumb.thumbnail((frame.width // 4, frame.height // 3))
    orig = frame.copy()
    orig.paste(thumb, (frame.width - thumb.width, frame.height - thumb.height))
    return {
        "case": case["name"],
        "product": title,
        "seconds": round(dt, 1),
        "output_size": list(raw.size),
        "raw": muse_image.preservation(frame, raw, region),
        "composite": muse_image.preservation(frame, comp, region),
        "meta": meta,
        "tiles": [
            label(orig, f"{case['name']}: original + product"),
            label(raw.resize(frame.size), "Muse Image raw"),
            label(comp, "composited into SAM region"),
        ],
    }


async def main() -> None:
    room = json.loads((ROOM / "room.json").read_text())
    objects = {o["id"]: o for o in room["objects"]}
    results = await asyncio.gather(*(run_case(c, objects) for c in CASES))

    lines = [
        "# T2 Muse Image — swap / add a product in our real frame", "",
        "Preservation outside the edited region (0–255 per pixel): `mae_outside` = mean change, "
        "`changed_outside_pct` = share of pixels changed by more than 30.", "",
        "| case | product | seconds | output | raw mae_outside | raw changed_outside | composite mae_outside |",
        "|---|---|---|---|---|---|---|",
    ]
    tiles = []
    for r in results:
        if "error" in r:
            lines.append(f"| {r['case']} | ERROR {r['error'][:120]} | {r['seconds']} | | | | |")
            continue
        lines.append(
            f"| {r['case']} | {r['product']} | {r['seconds']} | {r['output_size'][0]}x{r['output_size'][1]} | "
            f"{r['raw']['mae_outside']} | {r['raw']['changed_outside_pct']}% | {r['composite']['mae_outside']} |"
        )
        tiles += r.pop("tiles")
    (OUT / "report.md").write_text("\n".join(lines) + "\n")
    (OUT / "results.json").write_text(json.dumps(results, indent=2, default=str))
    if tiles:
        contact_sheet(tiles, cols=3).save(OUT / "sheet.jpg", quality=85)
    print("\n".join(lines))


if __name__ == "__main__":
    asyncio.run(main())
