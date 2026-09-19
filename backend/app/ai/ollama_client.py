import time

import httpx

from app.ai.gemini_client import GeminiResult
from app.core.config import get_settings


async def generate(prompt: str, *, structured: bool = False, model: str | None = None) -> GeminiResult:
    """Self-hosted equivalent of app/ai/gemini_client.py's generate() — same
    return shape so post_session.py / draft_generator.py can swap the
    import without other changes. structured=True asks Ollama's JSON mode for
    the same prompt-driven JSON contract Gemini's response_mime_type gave us;
    unlike Gemini there's no SDK-level schema enforcement, so a malformed
    response still raises on json.loads() in the caller rather than here."""
    settings = get_settings()
    payload: dict[str, object] = {
        "model": model or settings.ollama_model,
        "prompt": prompt,
        "stream": False,
    }
    if structured:
        payload["format"] = "json"

    started = time.monotonic()
    async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=120.0) as client:
        response = await client.post("/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
    latency_ms = int((time.monotonic() - started) * 1000)

    tokens = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)

    return GeminiResult(text=data["response"], tokens=tokens, latency_ms=latency_ms)
