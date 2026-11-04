# Roomtake

Same room. Better take.

Meta Global AI Developer Hackathon · Startup track · "Build for Your World"

**Live:** https://roomtake-meta.vercel.app (works best on a phone; "Try our demo" opens a
home that is already analyzed and restyled: living room, bedroom and balcony) ·
API: https://roomtake-api.fly.dev · **Demo video (2 min):** https://www.youtube.com/watch?v=fkr5vOcODik

Snap 1–3 photos of your room → SAM 3.1 finds what's in them → an AI stylist restyles the
whole room in the style you pick, with real products → painted into **your actual photo**,
the layout stays. Every piece in the picture is a real product with a price and a link,
so the look is something you can actually buy.

Runtime AI is **Meta models only**, via the [Meta Model API](https://dev.meta.ai/docs/):

| Model | What it does in Roomtake |
|---|---|
| **SAM 3.1** | Finds 24 kinds of things in your photos (sofa, bed, rug, floor, balcony…) and returns their masks. The masks become a colour layout map that keeps every piece in its place when the room is restyled, and SAM runs again on the result to check that it did (IoU per piece). |
| **Muse Wonder 1.0** | The stylist. Sees your photos and the inventory, picks real products from a catalog shortlist that fit the style and budget, and writes the style brief. |
| **Muse Image 1.0** | Repaints your actual photo in the new style, with the layout map and the chosen product photos as references. Pieces you want to keep are pasted back pixel-exact. |
| **Muse Spark 1.3** | The quick hands: revisions ("warmer", "keep my sofa", "Japandi instead"), a fallback when Wonder is slow, and classifying every catalog product from its photo. |
| **Muse Voice Transcribe 1.0** | Talk to the stylist: what you say is written into the revision field. |

## Built during the hackathon

Everything in this repository was written during the hackathon, from the first commit on
2 Nov 2026 to the submission on 4 Nov (see `git log`). Nothing comes from an earlier
codebase. What was built:

- **Room analysis** with SAM 3.1: first full-video tracking, then 1–3 photos in ~20 s.
- **Layout-keeping restyle**: the SAM layout map raised how well pieces keep their place
  and size from a mean IoU of 0.39 (text only) to 0.55 (`spikes/t4_restyle.py`).
- **Products-first stylist**: Muse Wonder picks real products, Muse Image draws them into
  your room, Muse Spark revises. 153 hand-picked Westwing products, classified by Spark.
- **Five styles** (Scandinavian, Japandi, Art Deco, Mid-Century, Mediterranean) plus a
  **Christmas** season that keeps your furniture and dresses the room for the holidays,
  with a lit tree placed in a free spot.
- **Voice revisions** with Muse Voice Transcribe.
- **The mobile web app** (Next.js): upload, live analysis, style picker, before/after,
  shop the look, an animated "how it works" demo and a 3D logo.
- **Public deploy** on Fly.io and Vercel, with per-visitor daily limits.
- **Go/no-go spikes** T1–T4 that decided the architecture (`spikes/`).

## Pipeline

```
photos ──1280 px, one 1-frame clip each──▶ SAM 3.1 finds each concept on each photo ──▶ room.json
                                (inventory, masks; each photo is a view: the room, or a free zone like the balcony)
room.json + views + catalog shortlist ──Muse Wonder──▶ style brief + real products that fit the style
view + SAM layout map + product photos ──Muse Image──▶ the room restyled with those products, same layout
restyled main view ──SAM 3.1──▶ layout check (IoU per piece)
"warmer" / "keep my sofa" / "Scandinavian instead" ──Muse Spark──▶ revised brief + products ──▶ new look
```

Products come first: the stylist sees a shortlist of catalog products per piece (style
matches first, within budget) and uses one only where it truly fits; everything else is
drawn freely. Muse Image gets the product photos as references and draws them into the
room, so the pieces you see are the ones you can buy. A look takes ~55-75 s.

Room analysis takes ~20 s for 2 photos and 23 concepts (`app/pipeline/photos.py`). Each
photo goes to SAM as a 1-frame clip: video requests get ~20 frames/s of throughput per
team, image requests ~1.3 images/s (`spikes/t1b_latency.py`). We started with video:
SAM 3.1 tracked the full clip at 10 fps (`app/pipeline/room.py`, still in the API), one
track per real object, but it took 4–5 min per room, needed a dedicated CPU to decode
thousands of masks, and the product only ever restyles 1–2 views. Photos give those
views directly, sharper than video frames, and the user picks them.

Model roles: **Muse Wonder** writes the style brief (and the per-item plan);
**Muse Spark** handles small, frequent calls: revisions, item descriptions.

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
      photos.py          1-3 photos -> SAM -> room.json (the app's path)
      room.py            video -> keyframes -> SAM -> room.json (full tracking, kept for later)
      preview.py         debug drawings (masks + IDs)
    agent/
      stylist.py         Wonder writes the brief and picks real products; Spark revises
      architect.py       per-item plan with catalog tools (earlier flow, API only)
    looks.py             a look: brief + products -> restyled views -> layout check
    catalog/             search_products(category, style, max_price, max_width), prices in EUR
      models.py          Product + category/style vocabulary (matches SAM concepts)
      curated.py         hand-picked Westwing products: import one page, Spark classifies
      dummyjson.py       test fallback while the curated list is empty
  catalog/curated.json   the curated products (in git)
    render/
      muse_image.py      Muse Image edit + paste back inside the SAM region
      visualize.py       catalog product -> replace/add in the room photo
      restyle.py         whole-view restyle with the SAM layout map; keep = original pixels
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

## Deploy

- **API → Fly.io** (`fly.toml`, `Dockerfile`): `fly deploy`. One machine in Frankfurt that
  never sleeps (analyses and looks finish in the background), a 10 GB volume at `/data`
  for rooms, and the demo room baked into the image and copied onto the volume on first
  boot (the SAM masks too: restyling reads them). Key: `fly secrets set MODEL_API_KEY=...`.
- **Web → Vercel** (project Root Directory `web`): every push to `main` deploys to production at https://roomtake-meta.vercel.app; `NEXT_PUBLIC_API_URL` points at the API.
- `ROOMTAKE_PUBLIC=1` on the server turns off catalog editing and guards the credits:
  videos are trimmed to 60 s, uploads capped at 300 MB, at most 2 rooms analyzed at once,
  and each visitor gets 4 rooms, 12 looks and 40 voice notes a day.

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
| `POST /api/rooms` (multipart `photos`, 1–3; or `video`) | upload, analysis starts → `{id}` |
| `GET /api/rooms/{id}/events` | server-sent progress: `keyframes`, `uploaded`, one `found` per concept, `done`, `status` |
| `GET /api/rooms/{id}` | `status` + `room` (room.json) when done |
| `GET /api/rooms/{id}/files/{path}` | frames, masks, renders |
| `GET /api/products?category=lamp&max_price=100&max_width=60` | catalog search |
| `POST /api/rooms/{id}/looks` `{style?, budget?, keep?, notes?}` | start a look → poll `GET .../looks/{look_id}` (status brief → rendering → checking → done); `products` = real pieces used |
| `POST /api/rooms/{id}/looks/{look_id}/revise` `{instruction}` | new look from a revised brief |
| `POST /api/rooms/{id}/plan` `{style?, budget?, keep?, notes?}` | Muse Wonder plan with products (~40-70 s) |
| `POST /api/rooms/{id}/plan/revise` `{instruction}` | Muse Spark follow-up, e.g. "keep the sofa", "cheaper" (~20 s) |
| `GET /api/rooms/{id}/plan` | current plan (every version kept as `plan_<n>.json`) |
| `POST /api/rooms/{id}/render` `{object_id, product_id, action: replace\|add}` | before/after paths; cached per combo |

Web app: `cd web && npm install && npm run dev` → http://localhost:3000.

`data/rooms/IMG_1184` (our living room) is a ready room for UI work: no upload needed.

## Catalog

Products are hand-picked, never crawled: open http://localhost:3000/curate, paste a
Westwing product link (westwing.sk for EUR) and save. The page's schema.org data gives
name, price, colour, material, dimensions and a clean packshot; Muse Spark looks at the
packshot and fills in our category, an English title and style tags. The list lives in
`backend/catalog/curated.json`; as soon as it has a product, the app uses it instead of
DummyJSON. Editing is off on a public deploy (`ROOMTAKE_PUBLIC=1`).

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
- `t4_restyle.py` — T4, whole-room restyle that keeps our layout: Muse Image gets the
  frame plus a layout map drawn from SAM masks; SAM on the result measures how well each
  piece kept its place and size (mean IoU 0.39 text-only -> 0.55 with the map).

## Data & licenses

- Amazon Berkeley Objects (CC BY-NC 4.0) — product metadata and images.
- Westwing products: hand-picked for the demo, every item links back to the shop.
