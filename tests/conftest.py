"""Shared test helpers: turn fixture dicts into attribute-access objects."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from cache_lens import pricing as pricing_mod

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _isolate_pricing(monkeypatch):
    """Keep the global pricing registry from leaking across tests."""
    monkeypatch.delenv("CACHE_LENS_PRICING", raising=False)
    pricing_mod.reset()
    yield
    pricing_mod.reset()


def _to_obj(value):
    if isinstance(value, dict):
        return SimpleNamespace(**{k: _to_obj(v) for k, v in value.items()})
    if isinstance(value, list):
        return [_to_obj(v) for v in value]
    return value


def load_responses(name: str):
    data = json.loads((FIXTURES / name).read_text())
    return [_to_obj(item) for item in data]
