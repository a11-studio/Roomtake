"""Roomtake API.

    cd backend && uv run uvicorn app.main:app --reload --port 8000

POST /api/rooms                     upload a room video -> {id}; analysis starts
GET  /api/rooms                     rooms on disk
GET  /api/rooms/{id}                status (+ room.json when done)
GET  /api/rooms/{id}/events         progress as server-sent events
GET  /api/rooms/{id}/files/{path}   frames, masks, renders
GET  /api/products                  catalog search
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

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from app.agent.architect import make_plan, revise_plan
from app.catalog import CATEGORIES, get_product, search_products
from app.config import DATA_DIR
from app.pipeline.room import analyze_room
from app.render.visualize import visualize

ROOMS = DATA_DIR / "rooms"
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]+$")

app = FastAPI(title="Roomtake")
app.add_middleware(
    CORSMiddleware,
    # any port on this machine or the home network, so a phone on the same
    # Wi-Fi can open the dev web app (http://192.168.x.x:3000)
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+)(:\d+)?",
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


async def run_analysis(room_id: str, video: Path) -> None:
    job = jobs[room_id]
    try:
        # ffmpeg and mask decoding are blocking; keep them off the server loop
        await asyncio.to_thread(
            asyncio.run, analyze_room(video, video.parent, on_event=job.events.append)
        )
        job.status = "done"
    except Exception as e:
        job.status, job.error = "error", f"{type(e).__name__}: {e}"
    job.events.append({"type": "status", "status": job.status, "error": job.error})


@app.post("/api/rooms")
async def create_room(video: UploadFile) -> dict:
    room_id = uuid.uuid4().hex[:10]
    out = ROOMS / room_id
    out.mkdir(parents=True)
    suffix = Path(video.filename or "video.mov").suffix.lower() or ".mov"
    path = out / f"source{suffix}"
    with path.open("wb") as f:
        shutil.copyfileobj(video.file, f)
    jobs[room_id] = Job()
    jobs[room_id].task = asyncio.create_task(run_analysis(room_id, path))
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
        sent = 0
        while True:
            while sent < len(job.events):
                yield f"data: {json.dumps(job.events[sent])}\n\n"
                sent += 1
            if job.status != "processing" and sent == len(job.events):
                return
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
