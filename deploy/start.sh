#!/bin/sh
# Seed the volume with the demo room on first boot, then serve the API.
set -e
mkdir -p "$ROOMTAKE_DATA/rooms"
[ -d "$ROOMTAKE_DATA/rooms/IMG_1184" ] || cp -r /app/seed/rooms/IMG_1184 "$ROOMTAKE_DATA/rooms/"
exec /app/backend/.venv/bin/uvicorn app.main:app --app-dir /app/backend --host 0.0.0.0 --port 8080 --proxy-headers
