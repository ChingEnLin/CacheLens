"""Extract RawCallMetrics and capture request prompts for Anthropic."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from ..models import PromptSegment, RawCallMetrics


def capture(args: tuple, kwargs: dict, *, model: str, client: object) -> List[PromptSegment]:
    from . import text_of

    segments: List[PromptSegment] = []
    system = kwargs.get("system")
    if system:
        segments.append(PromptSegment(role="system", text=text_of(system)))
    for msg in kwargs.get("messages", []) or []:
        if isinstance(msg, dict):
            segments.append(PromptSegment(role=msg.get("role", "user"), text=text_of(msg.get("content"))))
    return segments


def extract(response: object, *, model: str, latency_ms: int) -> RawCallMetrics:
    usage = getattr(response, "usage", None)
    input_tokens = _g(usage, "input_tokens")
    output_tokens = _g(usage, "output_tokens")
    cache_creation = _g(usage, "cache_creation_input_tokens")
    cache_read = _g(usage, "cache_read_input_tokens")

    # Anthropic's input_tokens excludes cached/created tokens; total input is the sum.
    total_input = input_tokens + cache_creation + cache_read
    miss = input_tokens

    return RawCallMetrics(
        call_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        model=getattr(response, "model", model) or model,
        input_tokens=total_input,
        output_tokens=output_tokens,
        cache_creation_tokens=cache_creation,
        cache_read_tokens=cache_read,
        cache_miss_tokens=miss,
        latency_ms=latency_ms,
        provider="anthropic",
    )


def _g(obj: object, name: str) -> int:
    if obj is None:
        return 0
    value = getattr(obj, name, 0)
    return int(value or 0)
