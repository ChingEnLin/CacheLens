"""Aggregate intercepted calls into a SessionReport.

Layer classification is content-based: the analyzer reconstructs each call's
prompt as an ordered list of segments, finds the longest prefix that is byte
-identical across every call in the session (the cacheable region), and names
the layers within it. It then cross-references that content-derived prefix
against the cache-read tokens the provider actually reported — surfacing which
named layer is stable-but-uncached and what it costs.

Token attribution per layer is estimated by character share, then scaled so each
call's layer tokens sum to the *real* input_tokens the provider returned. Overall
session aggregates (cost, savings, hit rate) are computed exactly from the
response metrics; only the per-layer split is an estimate.

Static vs semi-static is a single-run heuristic (a system-role prefix segment is
static; other stable-prefix content is semi-static). True static/semi-static
separation needs cross-run comparison, which a single in-memory session can't see.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List

from . import pricing
from .models import CallCapture, LayerReport, RawCallMetrics, SessionReport


def analyze(captures: List[CallCapture], session_id: str = "") -> SessionReport:
    session_id = session_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    if not captures:
        return SessionReport(
            session_id=session_id,
            provider="",
            model="",
            started_at=now,
            ended_at=now,
            total_calls=0,
            total_turns=0,
        )

    metrics = [c.metrics for c in captures]
    provider = metrics[0].provider
    model = metrics[0].model

    total_input = sum(m.input_tokens for m in metrics)
    total_output = sum(m.output_tokens for m in metrics)
    total_cached = sum(m.cache_read_tokens for m in metrics)
    total_miss = sum(m.cache_miss_tokens for m in metrics)

    actual_cost = _actual_cost(metrics)
    cold_cost = _cold_cost(metrics)
    savings = max(cold_cost - actual_cost, 0.0)
    overall_hit_rate = (total_cached / total_input) if total_input else 0.0

    layers, prefix_len, prefix_per_call_tokens = _classify_layers(captures, provider, model)

    input_rate = pricing.rate(provider, model, "input")
    read_rate = pricing.rate(provider, model, "cache_read")
    theoretical_max = max(
        prefix_per_call_tokens * (len(captures) - 1) * (input_rate - read_rate), 0.0
    )

    report = SessionReport(
        session_id=session_id,
        provider=provider,
        model=model,
        started_at=metrics[0].timestamp,
        ended_at=metrics[-1].timestamp,
        total_calls=len(metrics),
        total_turns=len(metrics),
        layers=layers,
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        total_cached_tokens=total_cached,
        overall_hit_rate=overall_hit_rate,
        actual_cost_usd=round(actual_cost, 6),
        cold_cost_usd=round(cold_cost, 6),
        total_savings_usd=round(savings, 6),
        theoretical_max_savings_usd=round(theoretical_max, 6),
    )
    report.tips = _build_tips(report, captures, layers, prefix_len, total_miss)
    return report


def _actual_cost(metrics: List[RawCallMetrics]) -> float:
    cost = 0.0
    for m in metrics:
        cost += m.cache_miss_tokens * pricing.rate(m.provider, m.model, "input")
        cost += m.cache_creation_tokens * pricing.rate(m.provider, m.model, "cache_write")
        cost += m.cache_read_tokens * pricing.rate(m.provider, m.model, "cache_read")
        cost += m.output_tokens * pricing.rate(m.provider, m.model, "output")
    return cost


def _cold_cost(metrics: List[RawCallMetrics]) -> float:
    """Cost if every input token were billed at the full input rate."""
    cost = 0.0
    for m in metrics:
        cost += m.input_tokens * pricing.rate(m.provider, m.model, "input")
        cost += m.output_tokens * pricing.rate(m.provider, m.model, "output")
    return cost


def _common_prefix_len(captures: List[CallCapture]) -> int:
    """Number of leading segments identical (role + text) across all calls."""
    seq_lists = [c.segments for c in captures]
    if not seq_lists or any(not s for s in seq_lists):
        return 0
    shortest = min(len(s) for s in seq_lists)
    n = 0
    for i in range(shortest):
        first = seq_lists[0][i]
        if all(
            s[i].role == first.role and s[i].text == first.text for s in seq_lists
        ):
            n += 1
        else:
            break
    return n


def _classify_layers(captures: List[CallCapture], provider: str, model: str):
    """Return (layers, prefix_len, prefix_tokens_per_call)."""
    prefix_len = _common_prefix_len(captures)

    sys_tok = ctx_tok = conv_tok = 0.0
    for cap in captures:
        segs = cap.segments
        total_chars = sum(len(s.text) for s in segs)
        if total_chars <= 0:
            # No capturable content — attribute everything to the dynamic layer.
            conv_tok += cap.metrics.input_tokens
            continue
        for i, seg in enumerate(segs):
            tok = cap.metrics.input_tokens * (len(seg.text) / total_chars)
            if i < prefix_len:
                if seg.role == "system":
                    sys_tok += tok
                else:
                    ctx_tok += tok
            else:
                conv_tok += tok

    # The stable prefix is sent on every call; cache reads (prefix-based) are
    # attributed to it, split across system_prompt and context by token share.
    prefix_tok = sys_tok + ctx_tok
    cached_total = sum(c.metrics.cache_read_tokens for c in captures)
    cached_in_prefix = min(cached_total, prefix_tok)
    sys_cached = cached_in_prefix * (sys_tok / prefix_tok) if prefix_tok else 0.0
    ctx_cached = cached_in_prefix - sys_cached

    input_rate = pricing.rate(provider, model, "input")
    read_rate = pricing.rate(provider, model, "cache_read")

    def make(name: str, layer_type: str, total: float, cached: float) -> LayerReport:
        cached = min(cached, total)
        cold = total * input_rate
        actual = cached * read_rate + (total - cached) * input_rate
        return LayerReport(
            name=name,
            layer_type=layer_type,
            total_tokens=int(round(total)),
            cached_tokens=int(round(cached)),
            hit_rate=(cached / total) if total else 0.0,
            actual_cost_usd=round(actual, 6),
            cold_cost_usd=round(cold, 6),
            savings_usd=round(max(cold - actual, 0.0), 6),
        )

    layers: List[LayerReport] = []
    if sys_tok > 0:
        layers.append(make("system_prompt", "static", sys_tok, sys_cached))
    if ctx_tok > 0:
        layers.append(make("context", "semi_static", ctx_tok, ctx_cached))
    if conv_tok > 0:
        layers.append(make("conversation", "dynamic", conv_tok, 0.0))

    prefix_tokens_per_call = _prefix_tokens_per_call(captures, prefix_len)
    return layers, prefix_len, prefix_tokens_per_call


def _prefix_tokens_per_call(captures: List[CallCapture], prefix_len: int) -> float:
    """Estimated token size of the stable prefix as sent on a single call."""
    if not captures or prefix_len <= 0:
        return 0.0
    cap = captures[0]
    total_chars = sum(len(s.text) for s in cap.segments)
    if total_chars <= 0:
        return 0.0
    return sum(
        cap.metrics.input_tokens * (len(cap.segments[i].text) / total_chars)
        for i in range(prefix_len)
    )


def _build_tips(
    report: SessionReport,
    captures: List[CallCapture],
    layers: List[LayerReport],
    prefix_len: int,
    total_miss: int,
) -> List[str]:
    tips: List[str] = []
    by_name: Dict[str, LayerReport] = {layer.name: layer for layer in layers}
    multi_call = report.total_calls > 1
    have_content = any(c.segments for c in captures)

    if report.provider == "gemini" and report.total_cached_tokens == 0:
        tips.append(
            "No Gemini context cache detected — create a cacheContent object for "
            "stable context (system prompt, schema) to enable cache reads."
        )

    context = by_name.get("context")
    if context and multi_call and context.hit_rate < 0.5:
        tips.append(
            f"context layer (~{context.total_tokens:,} tokens) is identical across "
            f"all {report.total_calls} calls but only {context.hit_rate:.0%} cached — "
            f"move it behind a cache_control breakpoint before the conversation "
            f"history (est. ${report.theoretical_max_savings_usd:.3f} recoverable)."
        )

    system = by_name.get("system_prompt")
    if system and multi_call and system.hit_rate < 0.9:
        tips.append(
            f"system_prompt cache hit rate is {system.hit_rate:.0%} — check the "
            "prefix isn't being prepended with dynamic content that breaks the cache."
        )

    if have_content and multi_call and prefix_len == 0:
        tips.append(
            "No stable prompt prefix detected across calls — content differs every "
            "turn, so prefix caching cannot help. Ensure your system prompt and "
            "static context are byte-identical on each call (and placed first)."
        )

    if captures and captures[0].metrics.cache_read_tokens == 0:
        tips.append(
            "First call always misses the cache (expected). Pre-warm with a dummy "
            "call before the loop starts to eliminate the cold miss."
        )

    if report.total_input_tokens and total_miss / report.total_input_tokens > 0.3:
        tips.append(
            f"{total_miss / report.total_input_tokens:.0%} of input tokens are "
            "uncached and re-sent each turn — consider summarising tool results "
            "instead of appending them verbatim."
        )

    return tips
