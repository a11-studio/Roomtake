# Roomtake

Same room. Better take.

Meta Global AI Developer Hackathon · Startup track · "Build for Your World"

Film your room → we find what's in it → an AI architect suggests 3–5 concrete changes
with real products → we paint those products into **your actual photo**, the rest stays untouched.

Runtime AI is **Meta models only**: SAM 3.1, Muse Wonder, Muse Spark, Muse Image
(optionally Muse Voice Transcribe), via the [Meta Model API](https://dev.meta.ai/docs/).

## Pipeline

```
video ──ffmpeg 10 fps/720p──▶ SAM 3.1 tracks each concept through the whole clip ──▶ room.json
      └─sharpness──▶ 5–8 keyframes (preferred "best frame" per object)
room.json + frames ──Muse Wonder (agent + tools: searchProducts, fits)──▶ plan
plan + best frame + SAM mask + product photo ──Muse Image edit──▶ before/after
"cheaper" / "keep the sofa" ──Muse Spark──▶ updated plan
```

Model roles: **Muse Wonder** writes the room plan once per room (~27 s, ~$0.09);
**Muse Spark** handles small, frequent calls: iterations, UI copy, captions
(~15 s, ~$0.02). Both read images (T3).

Room analysis tracks the full video at 10 fps: ~4–5 min for 23 concepts on a
24 s clip. Faster modes (keyframes as images, keyframes as a 1 fps clip, ~20 s)
got details wrong: 5 chairs instead of 4, shelves split into boards in
close-ups, small side tables missed. One track = one real object. The API
serves a team at ~20 video frames/s total (`spikes/t1b_latency.py`), so the UI
shows progress per concept, and demo videos are pre-processed.

## Repo layout

```
backend/                 Python 3.12+, uv
  app/
    config.py            model IDs, API key, paths
    meta_client.py       OpenAI-SDK client pointed at api.meta.ai
    pipeline/
      video.py           normalize, frame dump, keyframe picking
      sam.py             SAM 3.1 upload / segment / tracks / masks
      concepts.py        what SAM looks for: furniture, decor, fixture, zone
      room.py            video -> keyframes -> SAM -> room.json
      preview.py         debug drawings (masks + IDs)
    agent/
      architect.py       Wonder plans 3-5 changes with catalog tools; Spark revises
    catalog/             search_products(category, style, max_price, max_width)
      models.py          Product + category vocabulary (matches SAM concepts)
      dummyjson.py       source 1 of 3: DummyJSON -> ABO -> Westwing JSON
    render/
      muse_image.py      Muse Image edit + paste back inside the SAM region
      visualize.py       catalog product -> replace/add in the room photo
    main.py              FastAPI
web/                     Next.js, mobile-first (see web/README.md)
spikes/                  go/no-go tests T1–T3
data/                    local videos/outputs (gitignored)
```

## Setup

```bash
cp .env.example .env        # put MODEL_API_KEY in it
cd backend && uv sync
```

## Analyze a room

```bash
cd backend
uv run python -m app.pipeline.room ~/path/to/room.mov
```

Writes `data/rooms/<video>/room.json`, `frames/`, `masks/` and `inventory.jpg`.
Add `--reuse-sam` to rebuild `room.json` from cached SAM tracks without API calls.

`room.json` objects: `id, label, category, best_frame, mask, bbox, approx_size,
color, confidence, visible_s, seen_in_keyframes`. `category: zone` marks free space (floor, an
empty balcony) where the architect can place new products.

## API

```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

| | |
|---|---|
| `POST /api/rooms` (multipart `video`) | upload, analysis starts → `{id}` |
| `GET /api/rooms/{id}/events` | server-sent progress: `keyframes`, `uploaded`, one `found` per concept, `done`, `status` |
| `GET /api/rooms/{id}` | `status` + `room` (room.json) when done |
| `GET /api/rooms/{id}/files/{path}` | frames, masks, renders |
| `GET /api/products?category=lamp&max_price=100&max_width=60` | catalog search |
| `POST /api/rooms/{id}/plan` `{style?, budget?, keep?, notes?}` | Muse Wonder plan with products (~40-70 s) |
| `POST /api/rooms/{id}/plan/revise` `{instruction}` | Muse Spark follow-up, e.g. "keep the sofa", "cheaper" (~20 s) |
| `GET /api/rooms/{id}/plan` | current plan (every version kept as `plan_<n>.json`) |
| `POST /api/rooms/{id}/render` `{object_id, product_id, action: replace\|add}` | before/after paths; cached per combo |

Web app: `cd web && npm install && npm run dev` → http://localhost:3000.

`data/rooms/IMG_1184` (our living room) is a ready room for UI work: no upload needed.

## Spikes

- `t1_sam_video.py` — T1, SAM 3.1 tracking on the full video (`report.md`, `keyframes.jpg`, `overlay.mp4`). Result: GO.
- `t1b_latency.py` — SAM latency: fps vs keyframes vs parallelism.
- `t2_muse_image.py` — T2, Muse Image swaps/adds a catalog product in our real frame
  (`/v1/images/edits` with [room frame, product photo]), then the edit is pasted back
  only inside the SAM region so the rest of the room stays pixel-identical. Result: GO.
- `t3_vision.py` — T3, image input on Muse Wonder and Muse Spark: a vision probe with
  answers only in the pixels, and an architect pass over keyframes + inventory. Both
  models see the room (6/6 probe answers right) and return grounded changes by id.
  Wonder ~27 s / $0.09 per plan, Spark ~15 s / $0.02. Result: GO.

## Data & licenses

- Amazon Berkeley Objects (CC BY-NC 4.0) — product metadata and images.
- Westwing products: demo use only, every item links back to the shop.
