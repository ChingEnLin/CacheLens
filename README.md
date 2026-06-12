# CacheLens

> Non-invasive prompt cache instrumentation for LLM API apps.
> Wrap your client in one line. Get terminal reports, JSON exports, and OTEL metrics.

Prompt caching gives steep discounts on cached tokens — but nothing tells you
whether your app is actually getting cache hits, or why not. CacheLens wraps
your Anthropic, Gemini, or OpenAI client and reports cache hit rate, cost,
savings, and the money you're leaving on the table, broken down by prompt layer.

See [docs/architecture.md](docs/architecture.md) for the full design.

## Install

```bash
pip install cachelens                # core + rich
pip install cachelens[anthropic]     # + Anthropic SDK
pip install cachelens[gemini]        # + Gemini SDK
pip install cachelens[openai]        # + OpenAI SDK
pip install cachelens[otel]          # + OpenTelemetry
pip install cachelens[all]           # everything
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

CacheLens ships a default price table, but you can override or extend it without
forking — handy when a new model lands. User entries merge over the defaults:

```python
# in-memory dict (native format, USD per 1M tokens)
wrap(client, pricing={"openai": {"gpt-5": {"input": 1.25, "output": 10.0, "cache_read": 0.125}}})

# or a JSON file (native or LiteLLM model_prices_and_context_window.json format)
wrap(client, pricing="pricing.json")
```

Or point at a file process-wide with `CACHE_LENS_PRICING=/path/to/pricing.json`.
A bad pricing file falls back to defaults rather than breaking the run. See
[docs/architecture.md](docs/architecture.md) for the full design.

A `pricing=` argument applies to that wrapped client's session only — two
clients with different overrides don't leak into each other. For a
process-wide override use the env var or `cache_lens.pricing.load(...)`.

## Privacy & what gets captured

CacheLens never sends your prompts anywhere. By default it doesn't even keep
them: each request segment is reduced to *(role, SHA-256 hash, length)* at
capture time — enough for prefix diffing and layer attribution — so memory
stays bounded and no prompt content lingers in the process heap. Reports
(terminal, JSON, OTEL) contain only aggregates: token counts, costs, hit
rates, and tips. Pass `capture_content=True` to `wrap()` / `CacheLens` to
retain full text for your own inspection.

Async clients (`AsyncAnthropic`, `AsyncOpenAI`, `generate_content_async`) are
instrumented like sync ones. Streaming calls (`stream=True`,
`messages.stream`) are **not** instrumented yet — they are counted and shown
as "skipped" in the report, so missing tokens are visible rather than silently
under-counted.

The wrapper is a proxy: `isinstance(wrapped, anthropic.Anthropic)` is False.
Call `wrapped.unwrap()` to reach the original client where identity matters.

## How this helps you develop LLM applications

Prompt caching only pays off if your prompt's prefix is stable and
byte-identical across calls — but most agent loops accumulate per-turn state
(timestamps, counters, mutating progress trackers) that silently breaks the
prefix without anyone noticing. The API still works fine, the bill just stays
high. CacheLens turns that invisible problem into a concrete, iterable
workflow during development:

1. **Wrap your client once** and run your normal dev/test loop — no changes
   to your app logic required.
2. **Read the layer table** to see whether your prompt is actually splitting
   into stable layers (system prompt, schema/context, conversation) or
   collapsing into one big `conversation` blob — the latter is a strong
   signal that something near the top of your prompt changes every turn.
3. **Use the tips as a diagnosis, not just a metric.** "No stable prompt
   prefix detected" tells you *why* your hit rate is 0% and what to fix
   (move static content first, make it byte-identical); "X% of input tokens
   are uncached" tells you how much headroom restructuring is worth before
   you spend time on it.
4. **Re-run after each change** and compare `Savings`, `Cached`/`Hit Rate`,
   and whether the tips changed — this is the feedback loop that tells you
   whether a refactor (e.g. splitting prompt-building into a stable prefix
   and a volatile trailer) actually moved the needle, before you ever look at
   a billing dashboard.

See [examples/queryargus.md](examples/queryargus.md) for a real before/after
walkthrough of this loop on a 30-turn Gemini agent.

## Status

v1.1. Implemented: wrapper interception (sync **and async**) with **request
capture** (content-free by default — hash + length only), provider extraction
+ capture (Anthropic + Gemini + OpenAI), **content-based layer
classification** (longest-common-prefix → named system_prompt / context /
conversation layers, cross-referenced against actual cache reads),
terminal/JSON/OTEL outputs, per-session overridable pricing, latency
percentiles, skipped-call accounting, tests.
Pending: streaming usage extraction (currently counted as skipped),
`cache-lens run` CLI injection, and cross-run static/semi-static separation
(see [docs/architecture.md](docs/architecture.md) and
[docs/improvement-plan.md](docs/improvement-plan.md)).

## Develop

```bash
pip install -e .[dev]
pytest
```
