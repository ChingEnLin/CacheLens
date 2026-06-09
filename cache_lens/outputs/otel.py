"""OpenTelemetry metric emission for a SessionReport."""

from __future__ import annotations

import os

from ..models import SessionReport


def emit(report: SessionReport) -> None:
    """Emit cache-lens instruments via the OTEL SDK.

    Falls back to the console exporter if no OTLP endpoint is configured.
    Silently no-ops if the OTEL SDK is not installed.
    """
    try:
        from opentelemetry import metrics
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import (
            ConsoleMetricExporter,
            PeriodicExportingMetricReader,
        )
    except ImportError:
        return

    exporter = _build_exporter(ConsoleMetricExporter)
    reader = PeriodicExportingMetricReader(exporter)
    provider = MeterProvider(metric_readers=[reader])
    metrics.set_meter_provider(provider)
    meter = metrics.get_meter("cache_lens")

    attrs = {"provider": report.provider, "model": report.model}

    hit_rate = meter.create_gauge("cachelens.cache_hit_rate", unit="ratio")
    cost_actual = meter.create_gauge("cachelens.cost_actual", unit="USD")
    cost_saved = meter.create_gauge("cachelens.cost_saved", unit="USD")
    cost_ceiling = meter.create_gauge("cachelens.cost_ceiling", unit="USD")
    tokens_cached = meter.create_counter("cachelens.tokens_cached", unit="tokens")
    tokens_missed = meter.create_counter("cachelens.tokens_missed", unit="tokens")

    hit_rate.set(report.overall_hit_rate, attrs)
    cost_actual.set(report.actual_cost_usd, attrs)
    cost_saved.set(report.total_savings_usd, attrs)
    cost_ceiling.set(report.actual_cost_usd - report.theoretical_max_savings_usd, attrs)
    tokens_cached.add(report.total_cached_tokens, attrs)
    missed = report.total_input_tokens - report.total_cached_tokens
    tokens_missed.add(max(missed, 0), attrs)

    for layer in report.layers:
        layer_attrs = dict(attrs, layer=layer.name)
        hit_rate.set(layer.hit_rate, layer_attrs)
        tokens_cached.add(layer.cached_tokens, layer_attrs)

    provider.force_flush()


def _build_exporter(console_cls):
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return console_cls()
    try:
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
            OTLPMetricExporter,
        )

        return OTLPMetricExporter()
    except ImportError:
        return console_cls()
