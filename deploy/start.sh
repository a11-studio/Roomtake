#!/bin/sh
# Seed the volume with the demo room, then serve the API. -n adds files the
# volume lacks (e.g. a file a later image brings) and never overwrites looks.
set -e
mkdir -p "$ROOMTAKE_DATA/rooms"
cp -rn /app/seed/rooms/IMG_1184 "$ROOMTAKE_DATA/rooms/" || true  # newer cp reports skipped files
exec /app/backend/.venv/bin/uvicorn app.main:app --app-dir /app/backend --host 0.0.0.0 --port 8080 --proxy-headers
