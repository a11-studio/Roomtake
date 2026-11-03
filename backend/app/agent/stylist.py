"""Style briefs for whole-room restyles, with real products picked up front.

    brief = await style_brief(room_dir, room, prefs)               # Muse Wonder
    brief = await revise_brief(room_dir, room, brief, "warmer")    # Muse Spark

The stylist sees the room and a shortlist of catalog products per piece. It
uses a real product only where one truly fits the style; everything else is
described in words and drawn freely. Code checks the picks (ids, budget,
nothing replaces a kept item) before the image model sees them.
"""

from __future__ import annotations

import asyncio
import base64
import json
import re
from pathlib import Path

from app.catalog import get_product, search_products
from app.catalog.models import PIECE_TO_CATEGORY
from app.config import ARCHITECT_MODEL, HELPER_MODEL
from app.meta_client import async_client
from app.render.restyle import LAYOUT, pieces_in_view

KEEPABLE = ("furniture", "decor")
# Always on the shortlist for the main view, whatever SAM found: curtains and a
# rug finish even a basic room (DRESSING_RULES), the rest are small wins.
ADD_ONS = ["curtain", "rug", "lamp", "potted plant", "painting", "mirror", "vase", "cushion"]
ZONE_PIECES = ["outdoor furniture", "potted plant", "rug", "lamp"]
MAX_MAIN, MAX_ZONE, PER_CATEGORY = 5, 3, 5
# Wonder usually writes the brief in 20-45 s but has taken 113 s (Nov 2);
# past this, Spark writes it instead (~15-20 s, similar picks in T3).
WONDER_TIMEOUT_S = 45

BRIEF_SCHEMA = """{"title": str (style name, 1-3 words, e.g. "Scandinavian calm"),
 "room_type": str (e.g. "living room"),
 "summary": str (one sentence describing the look),
 "palette": [3-5 colour names], "materials": [3-5 materials],
 "pieces": {piece: str},  // for pieces in the photos from: %s - what each becomes
 "add": [str],             // 2-4 small additions: plants, lamps, textiles, wall decor
 "zones": {zone label: str}, // for free-space zones (e.g. "balcony floor"): what to put there
 "products": [{"product_id": str, "for": piece name or "add", "view": "main" or a zone label,
               "note": str}], // real products from the shortlist used in the design (see rules)
 "keep": [object ids],      // furniture/decor to keep exactly as is (user's list, plus any worth keeping)
 "why": str}               // 2-3 short sentences for the user: what changes and why,
                           // grounded in what you see (light, colours, empty space)""" % ", ".join(LAYOUT)

PRODUCT_RULES = f"""Real products: the shortlist below holds products the user can buy. Use one only when it
truly fits the style and the room - otherwise describe the piece in "pieces"/"zones" and it is drawn
freely. Using a real product is a bonus, never a must. At most {MAX_MAIN} in the main view and
{MAX_ZONE} per zone; "for" is the piece it becomes (e.g. "sofa") or "add" for a new item (say where
in "note"); the total price must stay within the budget. Never replace a kept item."""


# Martin, Nov 3, after a bare kindergarten room came back barely changed: windows
# and floors are what make a room look finished, so the stylist always dresses them.
DRESSING_RULES = """Dressing rules (they make even a basic room look finished):
- Windows: if the main photo shows a window, dress it with curtains in the style (soft, long
  fabric), even when it only has blinds now. Prefer a curtain from the shortlist: "for": "curtain"
  if the room already has curtains, otherwise "for": "add" with the note "curtains on the window".
- Floor: if the room has a rug, or a carpet or bare floor where one belongs, give it a better rug
  from the shortlist: "for": "rug" if a rug was detected, otherwise "for": "add" with the note
  saying where it lies (e.g. "rug on the carpet in front of the desk"). A wall-to-wall carpet stays;
  the new rug lies on top of it."""


def _image(path: Path) -> dict:
    return {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()}}


def _json(text: str | None) -> dict:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        raise ValueError(f"no JSON in reply: {(text or '')[:200]!r}")
    return json.loads(m.group(0))


async def _ask(model: str, content: list[dict]) -> dict:
    async with async_client() as api:
        r = await api.chat.completions.create(model=model, messages=[{"role": "user", "content": content}])
    return _json(r.choices[0].message.content)


def _inventory(room: dict) -> str:
    return "\n".join(
        f"- {o['id']} [{o['category']}] {o['color']['name']} {o['label']}"
        for o in room["objects"] if o["category"] != "fixture"
    )


def shortlist(room_dir: Path, room: dict, style: str | None, budget: float | None) -> str:
    """Catalog products per piece the design can use, style matches first."""
    main = next((v for v in room["views"] if v["kind"] == "main"), None)
    groups: dict[str, list[str]] = {}
    if main:
        groups["main"] = [c for c in pieces_in_view(room_dir, main["frame"]) if c != "television"] + ADD_ONS
    for v in room["views"]:
        if v["kind"] == "zone":
            groups[v["label"]] = ZONE_PIECES
    lines = []
    for view, cats in groups.items():
        lines.append(f"[view: {view}]")
        # one list per catalog category, under the room's own name for the piece
        # (a "picture frame" on the wall gets the paintings; the add-on is skipped)
        by_category = {}
        for cat in cats:
            by_category.setdefault(PIECE_TO_CATEGORY.get(cat, cat), cat)
        for category, cat in by_category.items():
            hits = search_products(category, max_price=budget)
            hits.sort(key=lambda p: (not (style and p.style and style.lower() in p.style.lower()), p.price_eur))
            for p in hits[:PER_CATEGORY]:
                size = f"{p.width_cm:.0f}x{p.depth_cm or 0:.0f}x{p.height_cm or 0:.0f} cm" if p.width_cm else "size n/a"
                lines.append(f"- {p.id} | {cat} | {p.name_en or p.name} | {p.color}, {p.material} | "
                             f"{size} | {p.price_eur:.0f} EUR | styles: {p.style or '-'}")
    return "\n".join(lines)


def _check(brief: dict, keep: list[str], room: dict, budget: float | None) -> dict:
    """Keep list: only furniture/decor (pasting a kept floor back once erased the
    new balcony set). Products: real ids, not replacing kept items, capped, in budget."""
    objects = {o["id"]: o for o in room["objects"]}
    brief["keep"] = sorted({*brief.get("keep", []), *keep} & {i for i, o in objects.items() if o["category"] in KEEPABLE})
    kept_labels = {objects[i]["label"] for i in brief["keep"]}
    zones = {v["label"] for v in room["views"] if v["kind"] == "zone"}
    out, per_view, total = [], {}, 0.0
    for u in brief.get("products", []):
        p = get_product(str(u.get("product_id", "")))
        view = u.get("view") if u.get("view") in zones else "main"
        target = u.get("for") or "add"
        if p is None or target in kept_labels or any(x["product"]["id"] == p.id for x in out):
            continue
        if per_view.get(view, 0) >= (MAX_MAIN if view == "main" else MAX_ZONE):
            continue
        if budget and total + p.price_eur > budget:
            continue
        per_view[view] = per_view.get(view, 0) + 1
        total += p.price_eur
        out.append({"product": p.to_dict(), "for": target if view == "main" else "add",
                    "view": view, "note": u.get("note", "")})
    brief["products"] = out
    return brief


def _picks(brief: dict) -> list[dict]:
    return [{"product_id": u["product"]["id"], "for": u["for"], "view": u["view"], "note": u["note"]}
            for u in brief.get("products", [])]


async def style_brief(room_dir: Path, room: dict, prefs: dict) -> dict:
    keep, budget = prefs.get("keep") or [], prefs.get("budget")
    text = f"""You are Roomtake's interior stylist. The photos show the user's real room (first photo
is the main view; others are free-space zones like a balcony). We will restyle the room as a whole
with an image model that keeps every piece of furniture in place and only changes its design.
Write the style brief for that restyle. Make the transformation clearly visible, worthy of an
interior magazine: give each piece a concrete new design (shape, material, colour), not just
new cushions. Only items in the keep list stay as they are.

Style the user picked: {prefs.get('style') or 'your best suggestion for this room'}
Budget for buying the look: {budget or 'not set'} EUR
Keep as it is (object ids): {', '.join(keep) or 'nothing specific'}
Notes: {prefs.get('notes') or '-'}

Detected objects:
{_inventory(room)}

{PRODUCT_RULES}

{DRESSING_RULES}

Shortlist (id | piece | name | colour, material | W x D x H | price | styles):
{shortlist(room_dir, room, prefs.get('style'), budget)}

Reply with JSON only:
{BRIEF_SCHEMA}"""
    images = [_image(room_dir / v["file"]) for v in room["views"]]
    content = [*images, {"type": "text", "text": text}]
    try:
        brief = await asyncio.wait_for(_ask(ARCHITECT_MODEL, content), WONDER_TIMEOUT_S)
        brief["model"] = ARCHITECT_MODEL
    except asyncio.TimeoutError:
        brief = await _ask(HELPER_MODEL, content)
        brief["model"] = f"{HELPER_MODEL} (fallback: {ARCHITECT_MODEL} over {WONDER_TIMEOUT_S} s)"
    return _check(brief, keep, room, budget)


async def revise_brief(room_dir: Path, room: dict, brief: dict, instruction: str, prefs: dict) -> dict:
    current = {k: v for k, v in brief.items() if k != "products"} | {"products": _picks(brief)}
    text = f"""You are Roomtake's interior stylist. Here is the current style brief for the user's room:
{json.dumps(current, indent=1)}

Object ids in the room: {', '.join(o['id'] for o in room['objects'] if o['category'] != 'fixture')}

The user says: "{instruction}"
Update the brief: change only what the user asked for, keep the rest (including products that
still fit). To keep an item as it is, add its id to "keep". If the style changes, pick products
that fit the new style.

{PRODUCT_RULES}

Shortlist (id | piece | name | colour, material | W x D x H | price | styles):
{shortlist(room_dir, room, None, prefs.get('budget'))}

Reply with the full updated brief as JSON only, same schema:
{BRIEF_SCHEMA}"""
    revised = await _ask(HELPER_MODEL, [{"type": "text", "text": text}])
    revised["model"] = HELPER_MODEL
    return _check(revised, brief.get("keep", []), room, prefs.get("budget"))
