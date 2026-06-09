# cache-lens

> Non-invasive prompt cache instrumentation for LLM API apps.
> Wrap your client in one line. Get terminal reports, JSON exports, and OTEL metrics.

Prompt caching gives steep discounts on cached tokens — but nothing tells you
whether your app is actually getting cache hits, or why not. cache-lens wraps
your Anthropic, Gemini, or OpenAI client and reports cache hit rate, cost,
savings, and the money you're leaving on the table, broken down by prompt layer.

See [SPEC.md](SPEC.md) for the full design.

## Install

```bash
pip install cache-lens                # core + rich
pip install cache-lens[anthropic]     # + Anthropic SDK
pip install cache-lens[gemini]        # + Gemini SDK
pip install cache-lens[openai]        # + OpenAI SDK
pip install cache-lens[otel]          # + OpenTelemetry
pip install cache-lens[all]           # everything
```

## Quickstart

```python
import anthropic
from cache_lens import wrap

client = wrap(anthropic.Anthropic())
# ... use client exactly as before; report prints on exit
```

Explicit session boundary with exports:

```python
from cache_lens import CacheLens

with CacheLens(client, json_export="report.json", otel=True) as session:
    agent.run(...)        # your code, unchanged
report = session.report
```

Suppress the terminal report in CI with `CACHE_LENS_TERMINAL=0`.

## Custom pricing

cache-lens ships a default price table, but you can override or extend it without
forking — handy when a new model lands. User entries merge over the defaults:

```python
# in-memory dict (native format, USD per 1M tokens)
wrap(client, pricing={"openai": {"gpt-5": {"input": 1.25, "output": 10.0, "cache_read": 0.125}}})

# or a JSON file (native or LiteLLM model_prices_and_context_window.json format)
wrap(client, pricing="pricing.json")
```

Or point at a file process-wide with `CACHE_LENS_PRICING=/path/to/pricing.json`.
A bad pricing file falls back to defaults rather than breaking the run. See
[SPEC.md §12](SPEC.md#12-pricing-table).

## Status

v1.0. Implemented: wrapper interception with **request capture**, provider
extraction + capture (Anthropic + Gemini + OpenAI), **content-based layer
classification** (longest-common-prefix → named system_prompt / context /
conversation layers, cross-referenced against actual cache reads),
terminal/JSON/OTEL outputs, overridable pricing, tests.
Pending: `cache-lens run` CLI injection, streaming support, and cross-run
static/semi-static separation (see [docs/architecture.md](docs/architecture.md)).

## Develop

```bash
pip install -e .[dev]
pytest
```
