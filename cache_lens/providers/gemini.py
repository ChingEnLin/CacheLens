"""Extract RawCallMetrics from a Gemini generate_content response."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from ..models import PromptSegment, RawCallMetrics


def capture(args: tuple, kwargs: dict, *, model: str, client: object) -> List[PromptSegment]:
    from . import text_of

    segments: List[PromptSegment] = []

    # New google-genai SDK passes the system prompt in the per-call config;
    # the legacy google-generativeai SDK stores it on the model object.
    config = kwargs.get("config")
    if isinstance(config, dict):
        si = config.get("system_instruction")
    else:
        si = getattr(config, "system_instruction", None)
    si = (
        si
        or getattr(client, "_system_instruction", None)
        or getattr(client, "system_instruction", None)
    )
    if si:
        text = text_of(si)
        if text:
            segments.append(PromptSegment(role="system", text=text))

    contents = kwargs.get("contents")
    if contents is None and args:
        contents = args[0]

    items = contents if isinstance(contents, (list, tuple)) else [contents]
    for item in items:
        if item is None:
            continue
        role = "user"
        if isinstance(item, dict):
            role = item.get("role", "user")
        else:
            role = getattr(item, "role", "user") or "user"
        segments.append(PromptSegment(role=role, text=text_of(item)))
    return segments


def extract(response: object, *, model: str, latency_ms: int) -> RawCallMetrics:
    meta = getattr(response, "usage_metadata", None)
    total = _g(meta, "total_token_count")
    output_tokens = _g(meta, "candidates_token_count")
    cache_read = _g(meta, "cached_content_token_count")

    input_tokens = max(total - output_tokens, 0)
    # Gemini has no creation-token field; uncached input is the miss portion.
    miss = max(input_tokens - cache_read, 0)

    return RawCallMetrics(
        call_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_tokens=0,
        cache_read_tokens=cache_read,
        cache_miss_tokens=miss,
        latency_ms=latency_ms,
        provider="gemini",
    )


def _g(obj: object, name: str) -> int:
    if obj is None:
        return 0
    value = getattr(obj, name, 0)
    return int(value or 0)
