import json
import time
from typing import Any

import google.generativeai as genai

from app.core.config import get_settings

_configured = False


def _ensure_configured() -> None:
    global _configured
    if not _configured:
        genai.configure(api_key=get_settings().gemini_api_key)  # type: ignore[attr-defined]
        _configured = True


class GeminiResult:
    def __init__(self, text: str, tokens: int, latency_ms: int):
        self.text = text
        self.tokens = tokens
        self.latency_ms = latency_ms

    def as_json(self) -> Any:
        return json.loads(self.text)


async def generate(prompt: str, *, structured: bool = False, model: str = "gemini-1.5-pro") -> GeminiResult:
    """Single entry point for every Gemini call in the system — replaces the
    manual Gemini Notebook paste-and-chat loop. Callers that need
    deterministic frontend rendering (scorecards) pass structured=True to get
    JSON output instead of free text, per backend/CLAUDE.md phase 4."""
    _ensure_configured()
    generation_config = {"response_mime_type": "application/json"} if structured else None
    gemini_model = genai.GenerativeModel(model, generation_config=generation_config)  # type: ignore[attr-defined, arg-type]

    started = time.monotonic()
    response = await gemini_model.generate_content_async(prompt)
    latency_ms = int((time.monotonic() - started) * 1000)

    usage = getattr(response, "usage_metadata", None)
    tokens = usage.total_token_count if usage else 0

    return GeminiResult(text=response.text, tokens=tokens, latency_ms=latency_ms)
