"""The architect: looks at the room, plans 3-5 changes, picks real catalog products.

    plan = await make_plan(room_dir, prefs)                      # Muse Wonder
    plan = await revise_plan(room_dir, plan, "keep the sofa")    # Muse Spark

The model sees the keyframes (T3: both models really see the room) and a
compact inventory, and calls search_products until every change has a
product. Code, not the model, owns the facts: product details, prices,
totals and the width check are filled in from the catalog after the loop.
"""

from __future__ import annotations

import asyncio
import base64
import json
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any

from app.catalog import all_products, get_product, search_products
from app.config import ARCHITECT_MODEL, HELPER_MODEL
from app.meta_client import async_client

MAX_ROUNDS = 8

SYSTEM = """You are Roomtake's interior architect. You redesign the user's REAL room
by swapping or adding a few specific items; the rest of the room stays as it is.
The photos are keyframes from the user's video. The inventory lists every object
detected in it, by id; zones (category "zone") are free floor where things can be added.

Rules:
- Propose {n_min}-{n_max} changes, most impactful first. Each must be grounded in
  something visible in the photos (light, colour, scale, empty space, clutter).
- action "replace": target_id is an inventory object to swap for a product.
  action "add": target_id is where the product goes (a zone, or a surface such as
  a table or shelf).
- Every change needs a real product: call search_products, then use one returned
  product_id. Never invent ids. If nothing suitable exists, choose another change.
- Respect the user's preferences: budget for the total, style, items to keep.
- Estimate max_width_cm from the photos (use doors ~80 cm, chairs ~45 cm as scale).
- Write "why" for the user: one or two short, specific sentences, no jargon.

When done, reply with JSON only:
{{"summary": str, "style": str,
  "changes": [{{"action": "replace"|"add", "target_id": str, "product_id": str,
               "why": str, "max_width_cm": int}}]}}"""

TOOLS = [{
    "type": "function",
    "function": {
        "name": "search_products",
        "description": "Search the product catalog. Returns up to 10 products, cheapest first.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "one of the categories listed below"},
                "style": {"type": "string"},
                "max_price": {"type": "number"},
                "max_width_cm": {"type": "number"},
            },
            "required": ["category"],
        },
    },
}]


def _categories_with_stock() -> str:
    counts = Counter(p.category for p in all_products())
    return ", ".join(f"{c} ({n})" for c, n in sorted(counts.items()))


def _inventory(room: dict) -> str:
    return "\n".join(
        f"- {o['id']} [{o['category']}] {o['color']['name']}, "
        f"{o['approx_size']['frame_area_pct']}% of frame, seen {o['visible_s'][0]}-{o['visible_s'][1]} s"
        for o in room["objects"]
    )


def _image(path: Path) -> dict:
    b64 = base64.b64encode(path.read_bytes()).decode()
    return {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}


def _parse_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        raise ValueError(f"no JSON in reply: {text[:200]!r}")
    return json.loads(m.group(0))


def _run_tool(name: str, args: dict) -> list[dict]:
    if name != "search_products":
        return [{"error": f"unknown tool {name}"}]
    hits = search_products(
        str(args.get("category", "")),
        args.get("style"),
        args.get("max_price"),
        args.get("max_width_cm"),
    )
    return [
        {k: v for k, v in p.to_dict().items() if k not in ("image_url", "product_url")}
        for p in hits
    ]


def _finalize(raw: dict, room: dict, model: str, prefs: dict, seconds: float, tool_calls: int) -> dict:
    """Validate the model's plan against the room and catalog; fill in facts."""
    objects = {o["id"]: o for o in room["objects"]}
    changes, dropped = [], []
    for c in raw.get("changes", []):
        obj, product = objects.get(c.get("target_id")), get_product(c.get("product_id", ""))
        if obj is None or product is None or c.get("action") not in ("replace", "add"):
            dropped.append({**c, "reason": "unknown target or product"})
            continue
        if c["target_id"] in prefs.get("keep", []) and c["action"] == "replace":
            dropped.append({**c, "reason": "user wants to keep this"})
            continue
        changes.append({
            "action": c["action"],
            "target_id": c["target_id"],
            "target_label": obj["label"],
            "best_frame": obj["best_frame"],
            "why": c.get("why", ""),
            "max_width_cm": c.get("max_width_cm"),
            "fits": product.fits(c.get("max_width_cm")),
            "product": product.to_dict(),
        })
    total = round(sum(c["product"]["price"] for c in changes), 2)
    budget = prefs.get("budget")
    return {
        "summary": raw.get("summary", ""),
        "style": raw.get("style", ""),
        "changes": changes,
        "total": total,
        "currency": changes[0]["product"]["currency"] if changes else None,
        "within_budget": budget is None or total <= budget,
        "preferences": prefs,
        "dropped": dropped,
        "meta": {"model": model, "seconds": round(seconds, 1), "tool_calls": tool_calls},
    }


async def _agent(model: str, messages: list[dict], room: dict, prefs: dict) -> dict:
    t0, n_calls = time.perf_counter(), 0
    async with async_client() as api:
        for _ in range(MAX_ROUNDS):
            r = await api.chat.completions.create(model=model, messages=messages, tools=TOOLS)
            msg = r.choices[0].message
            messages.append(msg.model_dump(exclude_none=True))
            if not msg.tool_calls:
                plan = _parse_json(msg.content)
                return _finalize(plan, room, model, prefs, time.perf_counter() - t0, n_calls)
            for tc in msg.tool_calls:
                n_calls += 1
                try:
                    args = json.loads(tc.function.arguments or "{}")
                    result: Any = _run_tool(tc.function.name, args)
                except Exception as e:  # bad arguments: tell the model, let it retry
                    result = {"error": f"{type(e).__name__}: {e}"}
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)})
    raise RuntimeError(f"architect did not finish in {MAX_ROUNDS} rounds")


def _prefs_text(prefs: dict) -> str:
    parts = [f"style: {prefs['style']}" if prefs.get("style") else "style: open to suggestions",
             f"total budget: {prefs['budget']} USD" if prefs.get("budget") else "budget: not set"]
    if prefs.get("keep"):
        parts.append("keep (do not replace): " + ", ".join(prefs["keep"]))
    if prefs.get("notes"):
        parts.append("notes: " + prefs["notes"])
    return "\n".join(parts)


def _user_message(room_dir: Path, room: dict, prefs: dict, extra: str = "") -> dict:
    text = (
        f"Inventory:\n{_inventory(room)}\n\n"
        f"Catalog categories with products in stock: {_categories_with_stock()}\n\n"
        f"User preferences:\n{_prefs_text(prefs)}{extra}"
    )
    images = [_image(room_dir / k["file"]) for k in room["keyframes"]]
    return {"role": "user", "content": [*images, {"type": "text", "text": text}]}


async def make_plan(room_dir: Path, prefs: dict | None = None, n: tuple[int, int] = (3, 5)) -> dict:
    prefs = prefs or {}
    room = json.loads((room_dir / "room.json").read_text())
    messages = [
        {"role": "system", "content": SYSTEM.format(n_min=n[0], n_max=n[1])},
        _user_message(room_dir, room, prefs),
    ]
    return await _agent(ARCHITECT_MODEL, messages, room, prefs)


async def revise_plan(room_dir: Path, plan: dict, instruction: str) -> dict:
    """Small follow-ups ("cheaper", "keep the sofa", "more green") on Muse Spark."""
    room = json.loads((room_dir / "room.json").read_text())
    prefs = dict(plan.get("preferences", {}))
    current = [
        {k: c[k] for k in ("action", "target_id", "why", "max_width_cm")}
        | {"product_id": c["product"]["id"], "price": c["product"]["price"]}
        for c in plan["changes"]
    ]
    extra = (
        f"\n\nCurrent plan (total {plan['total']}):\n{json.dumps(current, indent=1)}\n\n"
        f"The user now says: \"{instruction}\"\n"
        "Return the full updated plan. Keep the changes the user did not object to. "
        "For a lower budget, first swap products for cheaper ones in the same category, "
        "then drop the least important changes; use as much of the budget as helps."
    )
    messages = [
        {"role": "system", "content": SYSTEM.format(n_min=1, n_max=5)},
        _user_message(room_dir, room, prefs, extra),
    ]
    revised = await _agent(HELPER_MODEL, messages, room, prefs)
    revised["instruction"] = instruction
    return revised


if __name__ == "__main__":
    import argparse
    import sys

    from app.config import DATA_DIR

    p = argparse.ArgumentParser()
    p.add_argument("room", nargs="?", default="IMG_1184")
    p.add_argument("--budget", type=float)
    p.add_argument("--style")
    p.add_argument("--revise", help="instruction applied to the saved plan.json")
    a = p.parse_args()
    rdir = DATA_DIR / "rooms" / a.room
    if a.revise:
        result = asyncio.run(revise_plan(rdir, json.loads((rdir / "plan.json").read_text()), a.revise))
        out = rdir / "plan_revised.json"
    else:
        result = asyncio.run(make_plan(rdir, {"budget": a.budget, "style": a.style}))
        out = rdir / "plan.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print(f"\n-> {out}")
