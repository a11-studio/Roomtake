"""Meta Model API clients. The API is OpenAI-SDK compatible."""

from openai import AsyncOpenAI, OpenAI

from app.config import META_BASE_URL, model_api_key


def async_client() -> AsyncOpenAI:
    return AsyncOpenAI(base_url=META_BASE_URL, api_key=model_api_key(), timeout=600)


def sync_client() -> OpenAI:
    return OpenAI(base_url=META_BASE_URL, api_key=model_api_key(), timeout=600)
