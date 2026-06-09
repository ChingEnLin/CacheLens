"""Pricing registry. USD per 1M tokens.

A bundled default table ships in code as a zero-config, offline fallback. It can
be overridden or extended at runtime — without forking the package — via:

  * the ``CACHE_LENS_PRICING`` env var (path to a JSON file), and/or
  * a ``pricing=`` argument on ``wrap()`` / ``CacheLens`` (path or dict).

Two JSON formats are accepted:

  * **native** — nested ``{provider: {model: {input, output, cache_read,
    cache_write}}}``, values in USD per 1M tokens (same units as the table here).
  * **LiteLLM** — the ``model_prices_and_context_window.json`` shape, a flat
    ``{model: {litellm_provider, input_cost_per_token, ...}}`` map in USD per
    *single* token; detected automatically and converted.

User entries are merged over defaults, so overriding or adding a single model
does not require redefining the whole table.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Mapping, Optional, Tuple, Union

Key = Tuple[str, str]
Rates = Dict[str, float]

DEFAULT_PRICING: Dict[Key, Rates] = {
    ("anthropic", "claude-sonnet-4-6"): {"input": 3.00, "output": 15.00, "cache_write": 3.75, "cache_read": 0.30},
    ("anthropic", "claude-opus-4-7"): {"input": 15.00, "output": 75.00, "cache_write": 18.75, "cache_read": 1.50},
    ("anthropic", "claude-haiku-4-5"): {"input": 0.80, "output": 4.00, "cache_write": 1.00, "cache_read": 0.08},
    ("gemini", "gemini-2.5-flash"): {"input": 0.075, "output": 0.30, "cache_read": 0.01875},
    ("gemini", "gemini-2.5-pro"): {"input": 1.25, "output": 10.00, "cache_read": 0.31},
    ("openai", "gpt-4o"): {"input": 2.50, "output": 10.00, "cache_read": 1.25},
    ("openai", "gpt-4o-mini"): {"input": 0.15, "output": 0.60, "cache_read": 0.075},
    ("openai", "gpt-4.1"): {"input": 2.00, "output": 8.00, "cache_read": 0.50},
    ("openai", "gpt-4.1-mini"): {"input": 0.40, "output": 1.60, "cache_read": 0.10},
}

# Back-compat alias; the active, possibly-overridden registry.
PRICING: Dict[Key, Rates] = dict(DEFAULT_PRICING)

_PER_TOKEN = 1_000_000.0
_env_loaded = False

# Normalise provider names from external sources to cache-lens conventions.
_PROVIDER_ALIASES = {
    "vertex_ai": "gemini",
    "vertex_ai-language-models": "gemini",
    "google": "gemini",
    "azure": "openai",
    "azure_ai": "openai",
}

# LiteLLM per-token field -> native per-1M rate kind.
_LITELLM_FIELDS = {
    "input_cost_per_token": "input",
    "output_cost_per_token": "output",
    "cache_read_input_token_cost": "cache_read",
    "cache_creation_input_token_cost": "cache_write",
}


def get_pricing(provider: str, model: str) -> Optional[Rates]:
    """Look up pricing for a (provider, model). Falls back to longest prefix match."""
    _ensure_env_loaded()
    exact = PRICING.get((provider, model))
    if exact is not None:
        return exact
    best_len = -1
    best_price = None
    for (prov, mdl), price in PRICING.items():
        if prov == provider and model.startswith(mdl) and len(mdl) > best_len:
            best_len, best_price = len(mdl), price
    return best_price


def rate(provider: str, model: str, kind: str) -> float:
    """USD per single token for a given rate kind (input/output/cache_write/cache_read)."""
    price = get_pricing(provider, model)
    if price is None:
        return 0.0
    return price.get(kind, 0.0) / _PER_TOKEN


def reset() -> None:
    """Restore the active registry to the bundled defaults."""
    global PRICING, _env_loaded
    PRICING = dict(DEFAULT_PRICING)
    _env_loaded = False


def load(source: Union[str, Mapping], *, merge: bool = True) -> None:
    """Load a pricing override (file path or in-memory mapping) into the registry.

    By default it merges over existing entries; pass ``merge=False`` to replace.
    """
    parsed = parse(source)
    global PRICING
    if not merge:
        PRICING = {}
    PRICING.update(parsed)


def parse(source: Union[str, Mapping]) -> Dict[Key, Rates]:
    """Parse a path or mapping into internal ``{(provider, model): rates}`` form."""
    if isinstance(source, str):
        with open(source, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    else:
        data = source

    if not isinstance(data, dict):
        raise ValueError("pricing source must be a JSON object")

    if _looks_like_litellm(data):
        return _parse_litellm(data)
    return _parse_native(data)


def _ensure_env_loaded() -> None:
    global _env_loaded
    if _env_loaded:
        return
    _env_loaded = True  # set first so a bad file doesn't retry every lookup
    path = os.environ.get("CACHE_LENS_PRICING")
    if not path:
        return
    try:
        PRICING.update(parse(path))
    except (OSError, ValueError, json.JSONDecodeError):
        # Never let a bad pricing file break instrumentation; defaults stand.
        pass


def _looks_like_litellm(data: Mapping) -> bool:
    for value in data.values():
        if isinstance(value, Mapping) and (
            "litellm_provider" in value
            or any(field in value for field in _LITELLM_FIELDS)
        ):
            return True
        # Native entries are themselves nested {model: rates} maps.
        if isinstance(value, Mapping) and value and all(
            isinstance(v, Mapping) for v in value.values()
        ):
            return False
    return False


def _parse_native(data: Mapping) -> Dict[Key, Rates]:
    out: Dict[Key, Rates] = {}
    for provider, models in data.items():
        if not isinstance(models, Mapping):
            continue
        prov = _PROVIDER_ALIASES.get(provider, provider)
        for model, rates in models.items():
            if not isinstance(rates, Mapping):
                continue
            out[(prov, model)] = {k: float(v) for k, v in rates.items()}
    return out


def _parse_litellm(data: Mapping) -> Dict[Key, Rates]:
    out: Dict[Key, Rates] = {}
    for raw_model, entry in data.items():
        if not isinstance(entry, Mapping):
            continue
        provider = entry.get("litellm_provider")
        if not provider:
            continue
        prov = _PROVIDER_ALIASES.get(provider, provider)
        model = raw_model.split("/")[-1]  # strip any "provider/" prefix
        rates: Rates = {}
        for field, kind in _LITELLM_FIELDS.items():
            value = entry.get(field)
            if value is not None:
                rates[kind] = float(value) * _PER_TOKEN  # per-token -> per-1M
        if rates:
            out[(prov, model)] = rates
    return out
