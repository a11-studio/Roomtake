"""Stop the server when nobody has used it for a while (public deploy only).

The machine costs money every minute it runs, and most of the day nobody opens
the site. Fly's own auto-stop would cut analyses and looks that run in the
background after their request returned, so the app decides instead: after
IDLE_STOP_MIN minutes with no request, no open connection (the progress
stream) and no work in flight, it shuts down cleanly. The process exits with
code 0, the machine stops (restart policy on-failure), and Fly's proxy starts
it again on the next request. The clean exit needs app.serve, which hands us
its server; a signal would make uvicorn exit with 143 and Fly restart it.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import time
from collections.abc import Callable

log = logging.getLogger("uvicorn.error")

# requests that are not people: Fly's health check
QUIET_PATHS = {"/api/health"}

# set by app.serve: ends the server with exit code 0
stop: Callable[[], None] | None = None


class Activity:
    def __init__(self) -> None:
        self.last = time.monotonic()
        self.open = 0  # requests in flight, the progress stream included


class Track:
    """ASGI middleware: counts open requests, remembers the last one, and starts
    the watcher when the server starts (the lifespan event passes through here)."""

    def __init__(self, app, activity: Activity, after_s: float, busy: Callable[[], bool]):
        self.app, self.activity, self.after_s, self.busy = app, activity, after_s, busy
        self.watcher: asyncio.Task | None = None  # kept so it is not garbage-collected

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan" and self.watcher is None:
            self.watcher = asyncio.create_task(watch(self.activity, self.after_s, self.busy))
        if scope["type"] != "http" or scope["path"] in QUIET_PATHS:
            return await self.app(scope, receive, send)
        a = self.activity
        a.open += 1
        try:
            await self.app(scope, receive, send)
        finally:
            a.open -= 1
            a.last = time.monotonic()


async def watch(activity: Activity, after_s: float, busy: Callable[[], bool]) -> None:
    while True:
        await asyncio.sleep(min(30, after_s))
        quiet = time.monotonic() - activity.last
        if quiet >= after_s and not activity.open and not busy():
            log.info("idle for %d s, stopping; the next request starts the machine again", quiet)
            if stop:
                stop()
            else:  # plain `uvicorn app.main:app`: exits 143, fine locally
                os.kill(os.getpid(), signal.SIGTERM)
            return


def install(app, busy: Callable[[], bool]) -> None:
    """Off unless IDLE_STOP_MIN is set (the Fly deploy sets it)."""
    minutes = float(os.environ.get("IDLE_STOP_MIN") or 0)
    if minutes <= 0:
        return
    app.add_middleware(Track, activity=Activity(), after_s=minutes * 60, busy=busy)
