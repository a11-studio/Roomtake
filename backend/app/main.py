"""Roomtake API.

    cd backend && uv run uvicorn app.main:app --reload --port 8000

POST /api/rooms                     upload 1-3 room photos (or a video) -> {id}; analysis starts
GET  /api/rooms                     rooms on disk
GET  /api/rooms/{id}                status (+ room.json when done)
GET  /api/rooms/{id}/events         progress as server-sent events
GET  /api/rooms/{id}/files/{path}   frames, masks, renders
GET  /api/products                  catalog search
POST /api/transcribe                speech to text for the stylist (Muse Voice Transcribe)
POST /api/rooms/{id}/render         product into the room photo (Muse Image)
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from app import looks
from app.agent.architect import make_plan, revise_plan
from app.catalog import CATEGORIES, STYLES, Product, add_product, all_products, get_product, remove_product, search_products
from app.catalog.curated import import_url
from app.config import CURATE_ENABLED, DATA_DIR, MAX_ANALYSES, MAX_UPLOAD_MB, PUBLIC
from app.pipeline.photos import MAX_PHOTOS, analyze_photos
from app.pipeline.room import analyze_room
from app.render.visualize import visualize
from app.voice import transcribe

ROOMS = DATA_DIR / "rooms"
ROOMS.mkdir(parents=True, exist_ok=True)
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]+$")

app = FastAPI(title="Roomtake")
app.add_middleware(
    CORSMiddleware,
    # any port on this machine or the home network, so a phone on the same
    # Wi-Fi can open the dev web app (http://192.168.x.x:3000); and the
    # deployed web app on Vercel, production and previews
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+)(:\d+)?"
    r"|https://roomtake[a-z0-9-]*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)


@dataclass
class Job:
    status: Literal["processing", "done", "error"] = "processing"
    events: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    task: asyncio.Task | None = None  # keep a reference so it is not garbage-collected


# In-memory progress of analyses started by this process. Finished rooms are
# also found on disk (room.json), so a restart only loses live progress.
jobs: dict[str, Job] = {}


def room_dir(room_id: str) -> Path:
    if not SAFE_ID.match(room_id) or not (ROOMS / room_id).is_dir():
        raise HTTPException(404, "room not found")
    return ROOMS / room_id


def load_room(room_id: str) -> dict:
    path = room_dir(room_id) / "room.json"
    if not path.exists():
        raise HTTPException(409, "room is still being analyzed")
    return json.loads(path.read_text())


def status(room_id: str) -> str:
    if room_id in jobs:
        return jobs[room_id].status
    return "done" if (room_dir(room_id) / "room.json").exists() else "error"


async def run_analysis(room_id: str, sources: list[Path], kind: Literal["photos", "video"]) -> None:
    job = jobs[room_id]
    out = sources[0].parent
    work = (analyze_photos(sources, out, on_event=job.events.append) if kind == "photos"
            else analyze_room(sources[0], out, on_event=job.events.append))
    try:
        # ffmpeg and mask decoding are blocking; keep them off the server loop
        await asyncio.to_thread(asyncio.run, work)
        job.status = "done"
    except Exception as e:
        job.status, job.error = "error", f"{type(e).__name__}: {e}"
    job.events.append({"type": "status", "status": job.status, "error": job.error})


@app.post("/api/rooms")
async def create_room(photos: list[UploadFile] = File(default=[]), video: UploadFile | None = None) -> dict:
    """1-3 photos of a room (the main way, ~20 s) or a video (full tracking, ~5 min)."""
    files = photos[:MAX_PHOTOS] or ([video] if video else [])
    if not files:
        raise HTTPException(400, "Add a photo of your room.")
    if PUBLIC and sum(j.status == "processing" for j in jobs.values()) >= MAX_ANALYSES:
        raise HTTPException(429, "Roomtake is analyzing other rooms right now. Try again in a few minutes.")
    if any(f.size and f.size > MAX_UPLOAD_MB * 2**20 for f in files):
        raise HTTPException(413, f"That file is over {MAX_UPLOAD_MB} MB.")
    room_id = uuid.uuid4().hex[:10]
    out = ROOMS / room_id
    out.mkdir(parents=True)
    paths = []
    for i, f in enumerate(files):
        suffix = Path(f.filename or "").suffix.lower() or (".jpg" if photos else ".mov")
        path = out / f"source{i}{suffix}"
        with path.open("wb") as dst:
            shutil.copyfileobj(f.file, dst)
        paths.append(path)
    jobs[room_id] = Job()
    jobs[room_id].task = asyncio.create_task(run_analysis(room_id, paths, "photos" if photos else "video"))
    return {"id": room_id, "status": "processing"}


@app.get("/api/rooms")
def list_rooms() -> list[dict]:
    return [
        {"id": d.name, "status": status(d.name)}
        for d in sorted(ROOMS.iterdir(), key=lambda d: d.stat().st_mtime, reverse=True)
        if d.is_dir() and SAFE_ID.match(d.name)
    ]


@app.get("/api/rooms/{room_id}")
def get_room(room_id: str) -> dict:
    st = status(room_id)
    body: dict[str, Any] = {"id": room_id, "status": st}
    if st == "done":
        body["room"] = load_room(room_id)
    if room_id in jobs:
        body["error"] = jobs[room_id].error
    return body


@app.get("/api/rooms/{room_id}/events")
async def room_events(room_id: str) -> StreamingResponse:
    """Progress for the analysis screen: keyframes, uploaded, one `found` per
    concept ({"concept": "sofa", "count": 1}), retry, done, status."""
    room_dir(room_id)

    async def stream():
        job = jobs.get(room_id)
        if job is None:  # finished before this process started
            yield f"data: {json.dumps({'type': 'status', 'status': status(room_id)})}\n\n"
            return
        sent = idle = 0
        while True:
            while sent < len(job.events):
                yield f"data: {json.dumps(job.events[sent])}\n\n"
                sent += 1
            if job.status != "processing" and sent == len(job.events):
                return
            idle += 1
            if idle % 30 == 0:  # a comment every ~15 s keeps proxies from closing a quiet stream
                yield ": ping\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/rooms/{room_id}/files/{path:path}")
def room_file(room_id: str, path: str) -> FileResponse:
    base = room_dir(room_id).resolve()
    target = (base / path).resolve()
    if not target.is_relative_to(base) or not target.is_file() or target.name.startswith("source"):
        raise HTTPException(404, "file not found")
    return FileResponse(target)


@app.get("/api/products")
def products(
    category: str,
    style: str | None = None,
    max_price: float | None = None,
    max_width: float | None = None,
) -> dict:
    hits = search_products(category, style, max_price, max_width)
    return {"categories": CATEGORIES, "products": [p.to_dict() for p in hits]}


def curate_only() -> None:
    if not CURATE_ENABLED:
        raise HTTPException(403, "catalog editing is disabled on this server")


@app.get("/api/catalog")
def catalog() -> dict:
    products = [p.to_dict() for p in all_products()]
    counts = {c: sum(p["category"] == c for p in products) for c in CATEGORIES}
    return {"categories": CATEGORIES, "styles": STYLES, "counts": counts, "products": products,
            "source": products[0]["source"] if products else None, "editable": CURATE_ENABLED}


class ImportRequest(BaseModel):
    url: str


@app.post("/api/catalog/import")
async def catalog_import(req: ImportRequest) -> dict:
    """Read one Westwing product page; returns its variants to review (~6 s)."""
    curate_only()
    try:
        return {"variants": await import_url(req.url)}
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(502, f"{type(e).__name__}: {e}") from e


@app.post("/api/catalog/products")
def catalog_add(product: dict) -> dict:
    curate_only()
    try:
        p = Product.from_dict(product)
    except TypeError as e:
        raise HTTPException(400, f"invalid product: {e}") from e
    if p.category not in CATEGORIES or not p.product_url.startswith("https://"):
        raise HTTPException(400, "unknown category or bad product URL")
    add_product(p)
    return p.to_dict()


@app.delete("/api/catalog/products/{product_id}")
def catalog_remove(product_id: str) -> dict:
    curate_only()
    remove_product(product_id)
    return {"removed": product_id}


class PlanRequest(BaseModel):
    style: str | None = None
    budget: float | None = None
    keep: list[str] = []
    notes: str | None = None


class ReviseRequest(BaseModel):
    instruction: str


def save_plan(room_id: str, plan: dict) -> dict:
    """plan.json is the current plan; every version is kept as plan_<n>.json."""
    d = room_dir(room_id)
    n = len(list(d.glob("plan_*.json"))) + 1
    plan = {**plan, "version": n}
    for name in ("plan.json", f"plan_{n}.json"):
        (d / name).write_text(json.dumps(plan, indent=2, ensure_ascii=False))
    return plan


@app.post("/api/rooms/{room_id}/plan")
async def plan(room_id: str, req: PlanRequest) -> dict:
    """Muse Wonder looks at the room and proposes 3-5 changes with products (~30-40 s)."""
    load_room(room_id)
    try:
        result = await make_plan(room_dir(room_id), req.model_dump())
    except Exception as e:
        raise HTTPException(502, f"{type(e).__name__}: {e}") from e
    return save_plan(room_id, result)


@app.get("/api/rooms/{room_id}/plan")
def get_plan(room_id: str) -> dict:
    path = room_dir(room_id) / "plan.json"
    if not path.exists():
        raise HTTPException(404, "no plan yet")
    return json.loads(path.read_text())


@app.post("/api/rooms/{room_id}/plan/revise")
async def revise(room_id: str, req: ReviseRequest) -> dict:
    """Muse Spark applies a follow-up like "keep the sofa" or "cheaper" (~15 s)."""
    current = get_plan(room_id)
    try:
        result = await revise_plan(room_dir(room_id), current, req.instruction)
    except Exception as e:
        raise HTTPException(502, f"{type(e).__name__}: {e}") from e
    return save_plan(room_id, result)


class LookRequest(BaseModel):
    style: str | None = None
    budget: float | None = None
    keep: list[str] = []
    notes: str | None = None


background: set[asyncio.Task] = set()  # keep references so tasks are not garbage-collected


def start_look(room_id: str, look: dict, parent_brief: dict | None = None) -> None:
    d, room = room_dir(room_id), load_room(room_id)
    # image work is partly blocking (masks, compositing); keep it off the server loop
    task = asyncio.create_task(asyncio.to_thread(asyncio.run, looks.run_look(d, room, look, parent_brief)))
    background.add(task)
    task.add_done_callback(background.discard)


def look_body(room_id: str, look_id: str) -> dict:
    if not SAFE_ID.match(look_id) or not (looks.look_dir(room_dir(room_id), look_id) / "look.json").exists():
        raise HTTPException(404, "look not found")
    look = looks.load_look(room_dir(room_id), look_id)
    return {**look, "shop": looks.summary(look)}


@app.post("/api/rooms/{room_id}/looks")
async def create_look(room_id: str, req: LookRequest) -> dict:
    """Whole-room restyle in one style, using real catalog products where they fit.
    Poll GET .../looks/{id}; status goes brief -> rendering -> checking -> done (~1 min)."""
    look = looks.new_look(room_dir(room_id), load_room(room_id), req.model_dump())
    start_look(room_id, look)
    return look


@app.get("/api/rooms/{room_id}/looks")
def list_looks(room_id: str) -> list[dict]:
    base = room_dir(room_id) / "looks"
    out = []
    for f in base.glob("*/look.json") if base.exists() else []:
        look = json.loads(f.read_text())
        out.append({"id": look["id"], "status": look["status"], "created": look["created"],
                    "title": (look.get("brief") or {}).get("title"), "instruction": look.get("instruction")})
    return sorted(out, key=lambda x: -x["created"])


@app.get("/api/rooms/{room_id}/looks/{look_id}")
def get_look(room_id: str, look_id: str) -> dict:
    return look_body(room_id, look_id)


class ReviseLookRequest(BaseModel):
    instruction: str


@app.post("/api/rooms/{room_id}/looks/{look_id}/revise")
async def revise_look(room_id: str, look_id: str, req: ReviseLookRequest) -> dict:
    """Muse Spark edits the brief ("warmer", "keep the sofa", "Japandi instead"),
    then the views are restyled again. Returns the new look to poll."""
    parent = look_body(room_id, look_id)
    if not parent.get("brief"):
        raise HTTPException(409, "look has no brief yet")
    look = looks.new_look(room_dir(room_id), load_room(room_id), parent["prefs"], parent, req.instruction)
    start_look(room_id, look, looks.parent_brief(parent))
    return look


class RenderRequest(BaseModel):
    object_id: str
    product_id: str
    action: Literal["replace", "add"] = "replace"


@app.post("/api/rooms/{room_id}/render")
async def render(room_id: str, req: RenderRequest) -> dict:
    room = load_room(room_id)
    obj = next((o for o in room["objects"] if o["id"] == req.object_id), None)
    product = get_product(req.product_id)
    if obj is None or product is None:
        raise HTTPException(404, "object or product not found")
    try:
        result = await visualize(room_dir(room_id), obj, product, req.action)
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from e
    return {**result, "product": product.to_dict()}


@app.post("/api/transcribe")
async def transcribe_speech(audio: UploadFile) -> dict:
    """What the user said to the stylist, as text (Muse Voice Transcribe, ~1-3 s)."""
    data = await audio.read()
    if not data or len(data) > 10 * 2**20:
        raise HTTPException(413, "That recording is empty or too long.")
    try:
        return {"text": await transcribe(data)}
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(502, f"{type(e).__name__}: {e}") from e
