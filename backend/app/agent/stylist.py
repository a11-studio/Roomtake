"""Style briefs for whole-room restyles, and item descriptions for shop-the-look.

    brief = await style_brief(room_dir, room, prefs)          # Muse Wonder
    brief = await revise_brief(brief, "warmer, keep the sofa") # Muse Spark
    items = await describe_items(crops, brief)                # Muse Spark (vision)
"""

from __future__ import annotations

import base64
import io
import json
import re
from pathlib import Path

from PIL import Image

from app.catalog import CATEGORIES
from app.config import ARCHITECT_MODEL, HELPER_MODEL
from app.meta_client import async_client
from app.render.restyle import LAYOUT

KEEPABLE = ("furniture", "decor")

BRIEF_SCHEMA = """{"title": str (style name, 1-3 words, e.g. "Scandinavian calm"),
 "room_type": str (e.g. "living room"),
 "summary": str (one sentence describing the look),
 "palette": [3-5 colour names], "materials": [3-5 materials],
 "pieces": {piece: str},  // for pieces in the photos from: %s - what each becomes
 "add": [str],             // 2-4 small additions: plants, lamps, textiles, wall decor
 "zones": {zone label: str}, // for free-space zones (e.g. "balcony floor"): what to put there
 "keep": [object ids],      // furniture/decor to keep exactly as is (user's list, plus any worth keeping)
 "why": str}               // 2-3 short sentences for the user: what changes and why,
                           // grounded in what you see (light, colours, empty space)""" % ", ".join(LAYOUT)


def _image(path: Path | Image.Image) -> dict:
    if isinstance(path, Image.Image):
        buf = io.BytesIO()
        path.convert("RGB").save(buf, format="JPEG", quality=88)
        data = buf.getvalue()
    else:
        data = path.read_bytes()
    return {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(data).decode()}}


def _json(text: str | None) -> dict | list:
    m = re.search(r"[\[{].*[\]}]", text or "", re.S)
    if not m:
        raise ValueError(f"no JSON in reply: {(text or '')[:200]!r}")
    return json.loads(m.group(0))


async def _ask(model: str, content: list[dict]) -> dict | list:
    async with async_client() as api:
        r = await api.chat.completions.create(model=model, messages=[{"role": "user", "content": content}])
    return _json(r.choices[0].message.content)


def _inventory(room: dict) -> str:
    return "\n".join(
        f"- {o['id']} [{o['category']}] {o['color']['name']} {o['label']}"
        for o in room["objects"] if o["category"] != "fixture"
    )


def _with_keep(brief: dict, keep: list[str], room: dict) -> dict:
    """Keep list = things you can keep: furniture and decor. Floors and zones are
    where new pieces go (pasting a kept floor back erased the new balcony set)."""
    ids = {o["id"] for o in room["objects"] if o["category"] in KEEPABLE}
    brief["keep"] = sorted({*brief.get("keep", []), *keep} & ids)
    return brief


async def style_brief(room_dir: Path, room: dict, prefs: dict) -> dict:
    keep = prefs.get("keep") or []
    text = f"""You are Roomtake's interior stylist. The photos show the user's real room (first photo
is the main view; others are free-space zones like a balcony). We will restyle the room as a whole
with an image model that keeps every piece of furniture in place and only changes its design.
Write the style brief for that restyle. Make the transformation clearly visible, worthy of an
interior magazine: give each piece a concrete new design (shape, material, colour), not just
new cushions. Only items in the keep list stay as they are.

Style the user picked: {prefs.get('style') or 'your best suggestion for this room'}
Budget for buying the look: {prefs.get('budget') or 'not set'} USD
Keep as it is (object ids): {', '.join(keep) or 'nothing specific'}
Notes: {prefs.get('notes') or '-'}

Detected objects:
{_inventory(room)}

Reply with JSON only:
{BRIEF_SCHEMA}"""
    images = [_image(room_dir / v["file"]) for v in room["views"]]
    brief = await _ask(ARCHITECT_MODEL, [*images, {"type": "text", "text": text}])
    return _with_keep(brief, keep, room)


async def revise_brief(room: dict, brief: dict, instruction: str) -> dict:
    text = f"""You are Roomtake's interior stylist. Here is the current style brief for the user's room:
{json.dumps(brief, indent=1)}

Object ids in the room: {', '.join(o['id'] for o in room['objects'] if o['category'] != 'fixture')}

The user says: "{instruction}"
Update the brief: change only what the user asked for, keep the rest. To keep an item as it is,
add its id to "keep". Reply with the full updated brief as JSON only, same schema:
{BRIEF_SCHEMA}"""
    revised = await _ask(HELPER_MODEL, [{"type": "text", "text": text}])
    return _with_keep(revised, brief.get("keep", []), room)


async def describe_items(crops: list[Image.Image], brief: dict) -> list[dict]:
    """One Spark call for all crops: what to search the catalog for."""
    text = f"""These {len(crops)} images are crops of items in a restyled room ({brief['title']}), in order.
For each, describe the item so we can find a similar real product to buy.
Allowed categories: {', '.join(CATEGORIES)}.
Reply with a JSON array, one object per image, same order:
[{{"index": int, "category": str, "name": str (3-6 words, like a product title),
   "style": str, "color": str, "material": str}}]"""
    items = await _ask(HELPER_MODEL, [*map(_image, crops), {"type": "text", "text": text}])
    return items if isinstance(items, list) else items.get("items", [])
