import json
from pathlib import Path

from cache_lens import pricing

FIXTURES = Path(__file__).parent / "fixtures"


def test_defaults_present():
    p = pricing.get_pricing("openai", "gpt-4o")
    assert p["input"] == 2.50


def test_native_dict_override_merges():
    pricing.load({"openai": {"gpt-5": {"input": 1.0, "output": 8.0, "cache_read": 0.1}}})

    new = pricing.get_pricing("openai", "gpt-5")
    assert new["input"] == 1.0
    # Existing default untouched by a merge.
    assert pricing.get_pricing("openai", "gpt-4o")["input"] == 2.50


def test_override_replaces_existing_model():
    pricing.load({"anthropic": {"claude-opus-4-7": {"input": 99.0, "output": 100.0}}})
    assert pricing.get_pricing("anthropic", "claude-opus-4-7")["input"] == 99.0


def test_replace_mode_drops_defaults():
    pricing.load({"openai": {"gpt-9": {"input": 1.0}}}, merge=False)
    assert pricing.get_pricing("openai", "gpt-4o") is None
    assert pricing.get_pricing("openai", "gpt-9")["input"] == 1.0


def test_litellm_format_converts_per_token_to_per_million():
    pricing.load(str(FIXTURES / "litellm_pricing.json"))

    gpt5 = pricing.get_pricing("openai", "gpt-5")
    assert gpt5["input"] == 1.25         # 1.25e-6 * 1e6
    assert gpt5["output"] == 10.0
    assert gpt5["cache_read"] == 0.125

    # "anthropic/claude-sonnet-4-6" -> provider from litellm_provider, model stripped
    claude = pricing.get_pricing("anthropic", "claude-sonnet-4-6")
    assert claude["input"] == 4.0
    assert claude["cache_write"] == 5.0


def test_env_var_override(monkeypatch, tmp_path):
    path = tmp_path / "p.json"
    path.write_text(json.dumps({"openai": {"gpt-4o": {"input": 7.77, "output": 9.0}}}))
    monkeypatch.setenv("CACHE_LENS_PRICING", str(path))
    pricing.reset()  # force re-read of env on next lookup

    assert pricing.get_pricing("openai", "gpt-4o")["input"] == 7.77


def test_bad_env_file_falls_back_to_defaults(monkeypatch, tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{ not valid json ")
    monkeypatch.setenv("CACHE_LENS_PRICING", str(path))
    pricing.reset()

    assert pricing.get_pricing("openai", "gpt-4o")["input"] == 2.50


def test_rate_uses_overridden_registry():
    pricing.load({"openai": {"gpt-4o": {"input": 2_000_000.0}}})
    # 2_000_000 USD / 1M tokens == 2.0 USD per token
    assert pricing.rate("openai", "gpt-4o", "input") == 2.0


def test_registry_isolated_from_module():
    registry = pricing.Registry()
    registry.load({"openai": {"gpt-4o": {"input": 50.0}}})

    assert registry.get_pricing("openai", "gpt-4o")["input"] == 50.0
    # Module-level table untouched by the per-session override.
    assert pricing.get_pricing("openai", "gpt-4o")["input"] == 2.50


def test_registry_snapshots_module_overrides():
    pricing.load({"openai": {"gpt-x": {"input": 9.0}}})
    registry = pricing.Registry()
    assert registry.get_pricing("openai", "gpt-x")["input"] == 9.0


def test_registry_replace_mode():
    registry = pricing.Registry()
    registry.load({"openai": {"gpt-9": {"input": 1.0}}}, merge=False)
    assert registry.get_pricing("openai", "gpt-4o") is None
    assert registry.get_pricing("openai", "gpt-9")["input"] == 1.0


def test_registry_prefix_match():
    registry = pricing.Registry()
    assert registry.rate("openai", "gpt-4o-2026-01-01", "input") == 2.50 / 1_000_000
