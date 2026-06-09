"""Provider-specific response extraction and request capture."""

from __future__ import annotations

from typing import Optional

from . import anthropic as _anthropic
from . import gemini as _gemini
from . import openai as _openai


def text_of(value: object) -> str:
    """Flatten heterogeneous prompt content into a plain string.

    Handles the shapes providers use for message content: a bare string, a list
    of content blocks (dicts with a ``text`` field or objects with a ``.text``
    attribute), or a single such block. Best-effort and defensive — capture must
    never raise into the caller's request path.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return "".join(text_of(item) for item in value)
    if isinstance(value, dict):
        if "text" in value:
            return text_of(value["text"])
        if "parts" in value:
            return text_of(value["parts"])
        if "content" in value:
            return text_of(value["content"])
        return ""
    # Objects (e.g. genai Part / Content) exposing .text or .parts.
    for attr in ("text", "parts"):
        inner = getattr(value, attr, None)
        if inner is not None:
            return text_of(inner)
    return ""


def detect_provider(client: object) -> Optional[str]:
    """Best-effort detection of which provider a client object belongs to."""
    module = type(client).__module__ or ""
    if "anthropic" in module:
        return "anthropic"
    if "openai" in module:
        return "openai"
    if "google" in module or "genai" in module or "vertexai" in module:
        return "gemini"
    return None


def extractor_for(provider: str):
    return {"anthropic": _anthropic, "gemini": _gemini, "openai": _openai}[provider]


__all__ = ["detect_provider", "extractor_for", "text_of", "_anthropic", "_gemini", "_openai"]
