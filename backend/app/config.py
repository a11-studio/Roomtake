import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"

load_dotenv(REPO_ROOT / ".env")

META_BASE_URL = "https://api.meta.ai/v1"

# Runtime AI is Meta-only: these are the only models the product calls.
SAM_MODEL = "sam-3.1"
WONDER_MODEL = "muse-wonder-1.0"
SPARK_MODEL = "muse-spark-1.3"
IMAGE_MODEL = "muse-image-1.0"
VOICE_MODEL = "muse-voice-transcribe-1.0"


def model_api_key() -> str:
    key = os.environ.get("MODEL_API_KEY")
    if not key:
        raise RuntimeError("Set MODEL_API_KEY in .env (see .env.example).")
    return key
