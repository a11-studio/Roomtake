"""Per-visitor limits on the public server: what one person can ask of the
models in a day. In memory, so a restart forgets; enough to stop one visitor
from draining the credits, not a billing system."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.config import PUBLIC, VISITOR_LIMITS

WINDOW_S = 24 * 3600

MESSAGES = {
    "room": "You've designed {n} rooms today, the most we can do per visitor. Come back tomorrow, or try our demo living room.",
    "look": "You've made {n} new looks today, the most we can do per visitor. Come back tomorrow.",
    "voice": "That's all the talking we can transcribe today. Type your change instead.",
}

_hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)


def visitor(request: Request) -> str:
    # Fly's proxy puts the visitor's address in Fly-Client-IP; locally it's the socket's
    forwarded = request.headers.get("fly-client-ip") or request.headers.get("x-forwarded-for", "").split(",")[0]
    return forwarded.strip() or (request.client.host if request.client else "unknown")


def take(request: Request, kind: str) -> None:
    """Count one `kind` for this visitor, or refuse with 429 once they're at the limit."""
    if not PUBLIC:
        return
    limit, now = VISITOR_LIMITS[kind], time.time()
    hits = _hits[(visitor(request), kind)]
    while hits and hits[0] < now - WINDOW_S:
        hits.popleft()
    if len(hits) >= limit:
        raise HTTPException(429, MESSAGES[kind].format(n=limit))
    hits.append(now)
