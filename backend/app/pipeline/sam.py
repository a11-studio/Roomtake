"""SAM 3.1 via the Meta Model API: upload a video, segment one concept, read tracks.

Stream handling follows meta-model-cookbook/07_sam/01_api_basics.
"""

from __future__ import annotations

import base64
from collections.abc import AsyncIterable, AsyncIterator
from contextlib import aclosing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from meta_sam_parser import (
    ImageSegmentationResult,
    ResponsesEventLike,
    SegmentationBoxRecord,
    SegmentationMaskRecord,
    VideoSegmentationResult,
    decode_mask_to_raster,
    parse_responses_stream,
    image_segmentation_format,
    video_segmentation_format,
)

from app.config import SAM_MODEL
from app.meta_client import async_client


# Throughput note (T1b, Nov 2): the API serves our team at a roughly fixed rate,
# ~20 video frames/s but only ~1.3 images/s, regardless of parallelism. Total
# time is about (concepts x frames) / 20 s. We still track the full video at
# 10 fps: the faster keyframe modes got details wrong (see room.py).


async def upload_video(path: Path) -> str:
    async with async_client() as api:
        uploaded = await api.files.create(
            file=(path.name, path.read_bytes(), "video/mp4"), purpose="user_data"
        )
    return uploaded.id


async def _stream_events(stream: AsyncIterable[Any]) -> AsyncIterator[ResponsesEventLike]:
    """SDK events -> plain dicts for the parser. The API sends
    `response.content_part.done` but not `response.output_text.done`, which the
    parser needs to close a lane, so synthesize it."""
    done: set[tuple[object, object, object]] = set()
    async for event in stream:
        data = event.model_dump() if hasattr(event, "model_dump") else dict(event)
        lane = (data.get("item_id"), data.get("output_index"), data.get("content_index"))
        if data.get("type") == "response.output_text.done":
            if lane not in done:
                done.add(lane)
                yield data
            continue
        yield data
        part = data.get("part")
        if (
            data.get("type") == "response.content_part.done"
            and lane not in done
            and isinstance(part, dict)
            and part.get("type") == "output_text"
            and isinstance(part.get("text"), str)
        ):
            done.add(lane)
            yield {
                "type": "response.output_text.done",
                "item_id": data.get("item_id"),
                "output_index": data.get("output_index"),
                "content_index": data.get("content_index"),
                "text": part["text"],
            }


async def _segment(media: dict[str, str], concept: str, fmt: Any):
    """One concept (short noun phrase) per request, as the API recommends."""
    async with async_client() as api:
        stream = await api.responses.create(
            model=SAM_MODEL,
            stream=True,
            metadata={"include_confidence": "true"},
            input=[{
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": concept}, media],
            }],
        )
        async with stream, aclosing(_stream_events(stream)) as events:
            parsed = parse_responses_stream(events, fmt)
            async with parsed:
                async for _ in parsed:
                    pass
                return await parsed.final_result()


async def segment_video(file_id: str, concept: str) -> VideoSegmentationResult:
    return await _segment(
        {"type": "input_video", "file_id": file_id}, concept, video_segmentation_format()
    )


async def segment_image(path: Path, concept: str) -> ImageSegmentationResult:
    url = "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()
    return await _segment(
        {"type": "input_image", "image_url": url}, concept, image_segmentation_format()
    )



@dataclass
class Observation:
    frame: int
    box: tuple[float, float, float, float]  # left, top, right, bottom (source px)
    confidence: float | None
    mask: SegmentationMaskRecord | None = None


@dataclass
class Track:
    concept: str
    object_id: str
    observations: dict[int, Observation] = field(default_factory=dict)

    @property
    def frames(self) -> list[int]:
        return sorted(self.observations)


def tracks_from_result(
    result: VideoSegmentationResult | ImageSegmentationResult, concept: str
) -> list[Track]:
    """Group records by object ID. Image results land on frame 0."""
    tracks: dict[str, Track] = {}
    for record in result.records:
        if record.kind not in ("box", "mask"):
            continue
        track = tracks.setdefault(record.object_id, Track(concept, record.object_id))
        idx = 0 if record.frame is None else record.frame.frame_index
        if isinstance(record, SegmentationBoxRecord):
            obs = track.observations.get(idx)
            box = (record.left, record.top, record.right, record.bottom)
            if obs is None:
                track.observations[idx] = Observation(idx, box, record.confidence)
            else:
                obs.box, obs.confidence = box, record.confidence
        elif isinstance(record, SegmentationMaskRecord):
            obs = track.observations.get(idx)
            if obs is None:
                b = record.bounds
                obs = track.observations[idx] = Observation(
                    idx, (b.left, b.top, b.right, b.bottom), record.confidence
                )
            obs.mask = record
    return sorted(tracks.values(), key=lambda t: int(t.object_id))


def full_frame_mask(record: SegmentationMaskRecord, width: int, height: int) -> np.ndarray:
    """Place the box-local mask raster into a full-frame boolean array."""
    m = record.mask
    local = np.frombuffer(bytes(decode_mask_to_raster(m)), dtype=np.uint8)
    local = local.reshape(m.height, m.width).astype(bool)
    out = np.zeros((height, width), dtype=bool)
    x0, y0 = int(round(record.bounds.left)), int(round(record.bounds.top))
    x1, y1 = min(width, x0 + m.width), min(height, y0 + m.height)
    cx, cy = max(0, -x0), max(0, -y0)
    out[y0 + cy : y1, x0 + cx : x1] = local[cy : y1 - y0, cx : x1 - x0]
    return out
