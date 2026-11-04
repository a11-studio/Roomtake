import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(REPO_ROOT / ".env")

# Rooms, frames and renders; a deploy points this at its volume (ROOMTAKE_DATA=/data).
DATA_DIR = Path(os.environ.get("ROOMTAKE_DATA") or REPO_ROOT / "data")

META_BASE_URL = "https://api.meta.ai/v1"

# Runtime AI is Meta-only: these are the only models the product calls.
SAM_MODEL = "sam-3.1"
WONDER_MODEL = "muse-wonder-1.0"
SPARK_MODEL = "muse-spark-1.3"
IMAGE_MODEL = "muse-image-1.0"
VOICE_MODEL = "muse-voice-transcribe-1.0"

# Roles (decided after T3, Nov 2): Wonder writes the room plan once per room
# (~27 s, ~$0.09); Spark does everything small and frequent: iterations
# ("cheaper", "keep the sofa"), UI copy, captions (~15 s, ~$0.02).
ARCHITECT_MODEL = WONDER_MODEL
HELPER_MODEL = SPARK_MODEL


def model_api_key() -> str:
    key = os.environ.get("MODEL_API_KEY")
    if not key:
        raise RuntimeError("Set MODEL_API_KEY in .env (see .env.example).")
    return key

# Editing the curated catalog is for us, locally; a public deploy sets ROOMTAKE_PUBLIC=1.
PUBLIC = bool(os.environ.get("ROOMTAKE_PUBLIC"))
CURATE_ENABLED = not PUBLIC

# Guards on the public server, so a stranger's upload can't drain the credits:
# SAM bills per video frame, so uploads are capped in size and length, and only
# a couple of rooms are analyzed at once.
MAX_UPLOAD_MB = 300
MAX_VIDEO_S = 60
MAX_ANALYSES = 2
# ...and each visitor (by IP) gets a day's worth of model work, then a polite 429
VISITOR_LIMITS = {"room": 4, "look": 12, "voice": 40}
