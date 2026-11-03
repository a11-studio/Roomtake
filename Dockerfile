# Roomtake API for Fly.io (fly.toml). The web app deploys separately to Vercel.
FROM python:3.13-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /usr/local/bin/uv

WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock backend/
RUN uv sync --directory backend --frozen --no-dev --no-install-project
COPY backend backend

# The demo living room, analyzed and styled ahead of time; copied onto the
# volume on first boot so "Try our demo living room" opens instantly.
COPY data/rooms/IMG_1184 seed/rooms/IMG_1184
COPY deploy/start.sh start.sh

ENV ROOMTAKE_DATA=/data ROOMTAKE_PUBLIC=1
EXPOSE 8080
CMD ["/app/start.sh"]
