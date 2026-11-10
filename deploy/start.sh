#!/bin/sh
# Seed the volume with the demo room, then serve the API. -n adds files the
# volume lacks (e.g. a file a later image brings) and never overwrites looks.
set -e
mkdir -p "$ROOMTAKE_DATA/rooms"
cp -rn /app/seed/rooms/IMG_1184 "$ROOMTAKE_DATA/rooms/" || true  # newer cp reports skipped files
cd /app/backend && exec /app/backend/.venv/bin/python -m app.serve  # exits 0 when idle (app/idle.py)
