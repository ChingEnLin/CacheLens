import json
from datetime import datetime, timezone

import pytest

from cache_lens.models import SessionReport
from cache_lens.outputs import json_export


def _report(**over):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    base = dict(
        session_id="sid",
        provider="anthropic",
        model="claude-sonnet-4-6",
        started_at=now,
        ended_at=now,
        total_calls=1,
        total_turns=1,
    )
    base.update(over)
    return SessionReport(**base)


def test_export_renders_documented_tokens(tmp_path):
    json_export.export(_report(), str(tmp_path / "{model}-{session_id}.json"))

    written = tmp_path / "claude-sonnet-4-6-sid.json"
    assert written.exists()
    assert json.loads(written.read_text())["provider"] == "anthropic"


def test_export_rejects_attribute_access_tokens(tmp_path):
    with pytest.raises(ValueError):
        json_export.export(_report(), str(tmp_path / "{model.__class__}.json"))


def test_export_rejects_unknown_tokens(tmp_path):
    with pytest.raises(ValueError):
        json_export.export(_report(), str(tmp_path / "{whatever}.json"))


def test_export_sanitises_path_separators_in_model(tmp_path):
    json_export.export(_report(model="org/model\\v1"), str(tmp_path / "{model}.json"))
    assert (tmp_path / "org_model_v1.json").exists()


def test_terminal_render_smoke(capsys):
    from cache_lens.outputs import terminal

    terminal.render(
        _report(models=["m1", "m2"], skipped_calls=2, latency_p50_ms=10, latency_p95_ms=20)
    )
    out = capsys.readouterr().out
    assert "Skipped" in out
    assert "Latency" in out


def test_otel_emit_smoke(capsys):
    """Exercises Meter.create_gauge — fails on opentelemetry-sdk < 1.23.

    Skipped when the optional OTEL extra isn't installed; the min-versions CI
    job installs the declared floor and runs it.
    """
    pytest.importorskip("opentelemetry.sdk")
    from cache_lens.outputs import otel

    otel.emit(_report())  # console exporter; must not raise
