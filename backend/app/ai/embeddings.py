from typing import Any

import google.generativeai as genai

from app.core.config import get_settings

_MODEL = "models/gemini-embedding-2"
_OUTPUT_DIMENSIONALITY = 768

_configured = False


def _ensure_configured() -> None:
    global _configured
    if not _configured:
        genai.configure(api_key=get_settings().gemini_api_key)  # type: ignore[attr-defined]
        _configured = True


async def _embed(content: str, *, task_type: str, title: str | None = None) -> list[float]:
    _ensure_configured()
    kwargs: dict[str, Any] = {
        "model": _MODEL,
        "content": content,
        "task_type": task_type,
        "output_dimensionality": _OUTPUT_DIMENSIONALITY,
    }
    if title is not None:
        kwargs["title"] = title
    result = await genai.embed_content_async(**kwargs)  # type: ignore[attr-defined]
    return list(result["embedding"])


async def embed_document_content(title: str, body: str) -> list[float]:
    """Used at Context Library write time (create + post-version) — asymmetric
    retrieval convention: documents are embedded differently than queries."""
    return await _embed(f"{title}\n\n{body}", task_type="RETRIEVAL_DOCUMENT", title=title)


async def embed_query_text(text: str) -> list[float]:
    """Used at retrieval time in context_builder.py."""
    return await _embed(text, task_type="RETRIEVAL_QUERY")
