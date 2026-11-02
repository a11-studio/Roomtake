# Roomtake

Same room. Better take.

Meta Global AI Developer Hackathon · Startup track · "Build for Your World"

Film your room → we find what's in it → an AI architect suggests 3–5 concrete changes
with real products → we paint those products into **your actual photo**, the rest stays untouched.

Runtime AI is **Meta models only**: SAM 3.1, Muse Wonder, Muse Spark, Muse Image
(optionally Muse Voice Transcribe), via the [Meta Model API](https://dev.meta.ai/docs/).

## Pipeline

```
video ──ffmpeg 10 fps/720p──▶ 5–8 sharp, distinct keyframes ──▶ 1 fps keyframe clip
keyframe clip ──SAM 3.1, one request per concept, all in parallel──▶ tracks ──▶ room.json
room.json + keyframes ──Muse Wonder (agent + tools: searchProducts, fits)──▶ plan
plan + keyframe + SAM mask + product photo ──Muse Image edit──▶ before/after
```

Room analysis takes ~20 s for 23 concepts (SAM ~9 s). Why the keyframe clip
(measured in `spikes/t1b_latency.py`): the API serves a team at a roughly fixed
rate, ~20 video frames/s but only ~1.3 images/s. Sending the keyframes as one
tiny video is ~15x faster than separate image requests, and SAM keeps object
IDs across keyframes, so one track = one real object. Full-video tracking at
5 fps (~2 min) is kept for the pre-rendered demo shot.

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
    agent/               (Tue) architect agent on Muse Wonder
    catalog/             (Mon eve) searchProducts(category, style, maxPrice, maxWidth)
                         sources: DummyJSON -> Amazon Berkeley Objects -> Westwing JSON
    render/              (Tue) Muse Image edits
    main.py              (Mon eve) FastAPI
web/                     (Mon eve) Next.js, mobile-first
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

Writes `data/rooms/<video>/room.json`, `keyframes/`, `masks/` and `inventory.jpg`.

`room.json` objects: `id, label, category, best_frame, mask, bbox, approx_size,
color, confidence, seen_in`. `category: zone` marks free space (floor, an
empty balcony) where the architect can place new products.

## Spikes

- `t1_sam_video.py` — T1, SAM 3.1 tracking on the full video (`report.md`, `keyframes.jpg`, `overlay.mp4`). Result: GO.
- `t1b_latency.py` — SAM latency: fps vs keyframes vs parallelism.

## Data & licenses

- Amazon Berkeley Objects (CC BY-NC 4.0) — product metadata and images.
- Westwing products: demo use only, every item links back to the shop.
