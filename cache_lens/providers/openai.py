"""Extract RawCallMetrics from an OpenAI response.

Supports both the Chat Completions API (usage.prompt_tokens / completion_tokens
/ prompt_tokens_details.cached_tokens) and the Responses API (usage.input_tokens
/ output_tokens / input_tokens_details.cached_tokens).

OpenAI prompt caching is automatic with no cache-write surcharge, so
cache_creation_tokens is always 0; cached_tokens are billed at a discount.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from ..models import PromptSegment, RawCallMetrics


def capture(args: tuple, kwargs: dict, *, model: str, client: object) -> List[PromptSegment]:
    from . import text_of

    segments: List[PromptSegment] = []
    for msg in kwargs.get("messages", []) or []:
        if isinstance(msg, dict):
            segments.append(PromptSegment(role=msg.get("role", "user"), text=text_of(msg.get("content"))))
    return segments


def extract(response: object, *, model: str, latency_ms: int) -> RawCallMetrics:
    usage = getattr(response, "usage", None)

    # Chat Completions vs Responses field names.
    input_tokens = _g(usage, "prompt_tokens") or _g(usage, "input_tokens")
    output_tokens = _g(usage, "completion_tokens") or _g(usage, "output_tokens")

    details = getattr(usage, "prompt_tokens_details", None) or getattr(
        usage, "input_tokens_details", None
    )
    cache_read = _g(details, "cached_tokens")

    miss = max(input_tokens - cache_read, 0)

    return RawCallMetrics(
        call_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        model=getattr(response, "model", model) or model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_tokens=0,
        cache_read_tokens=cache_read,
        cache_miss_tokens=miss,
        latency_ms=latency_ms,
        provider="openai",
    )


def _g(obj: object, name: str) -> int:
    if obj is None:
        return 0
    value = getattr(obj, name, 0)
    return int(value or 0)
