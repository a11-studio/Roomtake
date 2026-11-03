"""Muse Voice Transcribe: what the user says to the stylist, as text.

The ASR endpoint takes only mono 16-bit PCM WAV (16 or 24 kHz); browsers record
WebM/Opus (Chrome) or MP4/AAC (Safari), so ffmpeg converts first.
https://dev.meta.ai/docs/speech-to-text/
"""

from __future__ import annotations

import asyncio
import json

import httpx

from app.config import META_BASE_URL, VOICE_MODEL, model_api_key

MAX_SECONDS = 60  # a change to the room is a sentence or two


async def to_wav(audio: bytes) -> bytes:
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-v", "error", "-i", "pipe:0", "-t", str(MAX_SECONDS),
        "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le", "-map_metadata", "-1", "-f", "wav", "pipe:1",
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    wav, err = await proc.communicate(audio)
    if proc.returncode != 0 or not wav:
        raise ValueError(f"could not read the recording: {err.decode()[:200]}")
    return wav


async def transcribe(audio: bytes) -> str:
    wav = await to_wav(audio)
    request = {"model": VOICE_MODEL, "audioEncoding": "WAV", "mode": "PUSH_TO_TALK"}
    async with httpx.AsyncClient(timeout=60) as http:
        r = await http.post(
            f"{META_BASE_URL}/asr/transcribe",
            headers={"Authorization": f"Bearer {model_api_key()}", "Accept": "application/json"},
            files={"request": (None, json.dumps(request), "application/json"),
                   "audio": ("speech.wav", wav, "audio/wav")},
        )
    r.raise_for_status()
    return (r.json().get("transcript") or "").strip()
