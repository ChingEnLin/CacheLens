from datetime import datetime, timezone

from cache_lens.analyzer import analyze
from cache_lens.models import CallCapture, PromptSegment, RawCallMetrics


def _metric(read, created, miss, out, ts, model="claude-sonnet-4-6", provider="anthropic"):
    return RawCallMetrics(
        call_id=f"c{ts}",
        timestamp=datetime(2026, 1, 1, 0, 0, ts, tzinfo=timezone.utc),
        model=model,
        input_tokens=read + created + miss,
        output_tokens=out,
        cache_creation_tokens=created,
        cache_read_tokens=read,
        cache_miss_tokens=miss,
        latency_ms=100,
        provider=provider,
    )


def _cap(segments, *, read, created, miss, out, ts, model="claude-sonnet-4-6", provider="anthropic"):
    return CallCapture(
        metrics=_metric(read, created, miss, out, ts, model, provider),
        segments=segments,
    )


def _seg(role, text):
    return PromptSegment(role=role, text=text)


def test_empty_session():
    report = analyze([])
    assert report.total_calls == 0
    assert report.actual_cost_usd == 0.0


def test_savings_and_hit_rate_from_metrics():
    # Empty segments: aggregates still come exactly from metrics.
    captures = [
        _cap([], read=0, created=4800, miss=200, out=50, ts=1),
        _cap([], read=4800, created=0, miss=350, out=70, ts=2),
    ]
    report = analyze(captures)

    assert report.total_calls == 2
    assert report.total_cached_tokens == 4800
    assert 0.0 < report.overall_hit_rate < 1.0
    assert report.cold_cost_usd > report.actual_cost_usd
    assert report.total_savings_usd > 0


def test_layer_classification_stable_prefix_uncached():
    """System + context identical across calls, nothing cached -> the killer tip."""
    system = _seg("system", "S" * 100)
    context = _seg("user", "C" * 300)  # retrieved chunk, stable across calls
    calls = [
        _cap([system, context, _seg("user", "first question")],
             read=0, created=0, miss=4000, out=50, ts=1),
        _cap([system, context, _seg("user", "a different second question entirely")],
             read=0, created=0, miss=4200, out=60, ts=2),
    ]
    report = analyze(calls)

    by = {layer.name: layer for layer in report.layers}
    assert set(by) == {"system_prompt", "context", "conversation"}
    assert by["system_prompt"].layer_type == "static"
    assert by["context"].layer_type == "semi_static"
    assert by["conversation"].layer_type == "dynamic"

    assert by["context"].total_tokens > 0
    assert by["context"].cached_tokens == 0
    assert report.theoretical_max_savings_usd > 0
    assert any("context layer" in t for t in report.tips)


def test_layer_classification_with_cache_reads():
    system = _seg("system", "S" * 100)
    context = _seg("user", "C" * 300)
    calls = [
        _cap([system, context, _seg("user", "q1")],
             read=0, created=400, miss=100, out=50, ts=1),
        _cap([system, context, _seg("user", "a second distinct question")],
             read=400, created=0, miss=120, out=60, ts=2),
    ]
    report = analyze(calls)

    by = {layer.name: layer for layer in report.layers}
    # Cache reads are attributed to the stable prefix (system + context).
    assert by["context"].cached_tokens > 0
    assert by["context"].hit_rate > 0
    assert report.total_savings_usd > 0


def test_no_stable_prefix_tip():
    calls = [
        _cap([_seg("user", "completely unique alpha content one")],
             read=0, created=0, miss=3000, out=50, ts=1),
        _cap([_seg("user", "totally different beta content two")],
             read=0, created=0, miss=3200, out=60, ts=2),
    ]
    report = analyze(calls)
    assert any("No stable prompt prefix" in t for t in report.tips)


def test_first_call_miss_tip():
    report = analyze([_cap([], read=0, created=0, miss=5000, out=50, ts=1)])
    assert any("First call" in t for t in report.tips)


def test_gemini_no_cache_tip():
    report = analyze([
        _cap([], read=0, created=0, miss=5000, out=50, ts=1,
             model="gemini-2.5-flash", provider="gemini")
    ])
    assert any("Gemini context cache" in t for t in report.tips)


def test_latency_percentiles():
    caps = [_cap([], read=0, created=0, miss=100, out=10, ts=i) for i in range(1, 4)]
    report = analyze(caps)  # every fixture call reports latency_ms=100
    assert report.latency_p50_ms == 100
    assert report.latency_p95_ms == 100


def test_skipped_calls_reported_with_tip():
    report = analyze([], skipped_calls=3)
    assert report.skipped_calls == 3
    assert any("not instrumented" in t for t in report.tips)


def test_skipped_calls_tip_alongside_captures():
    report = analyze(
        [_cap([], read=0, created=0, miss=100, out=10, ts=1)], skipped_calls=2
    )
    assert report.skipped_calls == 2
    assert any("not instrumented" in t for t in report.tips)


def test_mixed_models_listed_and_flagged():
    caps = [
        _cap([], read=0, created=0, miss=100, out=10, ts=1, model="claude-sonnet-4-6"),
        _cap([], read=0, created=0, miss=100, out=10, ts=2, model="claude-haiku-4-5"),
    ]
    report = analyze(caps)
    assert report.models == ["claude-sonnet-4-6", "claude-haiku-4-5"]
    assert any("mixed" in t.lower() for t in report.tips)


def test_content_free_segments_classify_identically():
    """Hash+length capture must yield the same layer split as full text."""
    def calls(transform):
        system = _seg("system", "S" * 100)
        context = _seg("user", "C" * 300)
        return [
            _cap([transform(system), transform(context),
                  transform(_seg("user", "first question"))],
                 read=0, created=0, miss=4000, out=50, ts=1),
            _cap([transform(system), transform(context),
                  transform(_seg("user", "a different second question entirely"))],
                 read=0, created=0, miss=4200, out=60, ts=2),
        ]

    full = analyze(calls(lambda s: s))
    stripped = analyze(calls(lambda s: s.without_text()))

    assert [(layer.name, layer.total_tokens) for layer in full.layers] == [
        (layer.name, layer.total_tokens) for layer in stripped.layers
    ]
