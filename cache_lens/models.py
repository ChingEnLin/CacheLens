"""Core data models for cache-lens."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Literal

Provider = Literal["anthropic", "gemini", "openai"]
LayerType = Literal["static", "semi_static", "dynamic"]


@dataclass
class RawCallMetrics:
    """Normalised per-call cache metrics extracted from a provider response."""

    call_id: str
    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    cache_miss_tokens: int
    latency_ms: int
    provider: Provider


@dataclass
class PromptSegment:
    """One ordered piece of a request prompt, in prefix order.

    The analyzer only needs segment *equality* (role + content hash) and
    *length* (char-share token estimation), so ``text`` may be empty when
    content capture is off — ``text_hash`` and ``length`` are always set.
    """

    role: str          # "system", "user", "assistant", "model", "tool", ...
    text: str = ""
    text_hash: str = ""
    length: int = 0

    def __post_init__(self) -> None:
        if self.text and not self.text_hash:
            self.text_hash = hashlib.sha256(self.text.encode("utf-8")).hexdigest()
        if self.text and not self.length:
            self.length = len(self.text)

    def without_text(self) -> "PromptSegment":
        """A copy carrying only role, hash, and length — no prompt content."""
        return PromptSegment(role=self.role, text="", text_hash=self.text_hash, length=self.length)


@dataclass
class CallCapture:
    """A single intercepted call: the request prompt plus the response metrics."""

    metrics: RawCallMetrics
    segments: List[PromptSegment] = field(default_factory=list)


@dataclass
class LayerReport:
    name: str
    layer_type: LayerType
    total_tokens: int
    cached_tokens: int
    hit_rate: float
    actual_cost_usd: float
    cold_cost_usd: float
    savings_usd: float


@dataclass
class SessionReport:
    session_id: str
    provider: str
    model: str
    started_at: datetime
    ended_at: datetime
    total_calls: int
    total_turns: int
    layers: List[LayerReport] = field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cached_tokens: int = 0
    overall_hit_rate: float = 0.0
    actual_cost_usd: float = 0.0
    cold_cost_usd: float = 0.0
    total_savings_usd: float = 0.0
    theoretical_max_savings_usd: float = 0.0
    tips: List[str] = field(default_factory=list)
    models: List[str] = field(default_factory=list)  # distinct models seen, in order
    skipped_calls: int = 0  # intercepted but not instrumentable (async/streaming)
    latency_p50_ms: int = 0
    latency_p95_ms: int = 0
