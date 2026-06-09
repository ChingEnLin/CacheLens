# CLAUDE.md — cache-lens

Context for Claude Code sessions on this repo.

## What this is

A Python library that instruments prompt caching in LLM API apps (Anthropic,
Gemini, OpenAI). You wrap a provider client; on each intercepted call it captures
both the **request prompt** (normalised to ordered `PromptSegment`s) and the
**response cache metrics**. At session end the analyzer does content-based layer
classification and produces a `SessionReport` rendered to terminal / JSON / OTEL.
Full design in [SPEC.md](SPEC.md).

The differentiator (see [docs/positioning.md](docs/positioning.md)): it doesn't
just report cached-token counts (LiteLLM/Langfuse/Helicone already do that) — it
diffs the prompt prefix across calls to name *which layer* is stable-but-uncached
and what restructuring would save.

## Layout

- `cache_lens/wrapper.py` — interception (`wrap`, `CacheLens`, `CacheLensClient`);
  stores `List[CallCapture]` (request segments + response metrics) per session
- `cache_lens/providers/{anthropic,gemini,openai}.py` — `extract()` (response →
  `RawCallMetrics`) and `capture()` (request → `List[PromptSegment]`)
- `cache_lens/analyzer.py` — longest-common-prefix layer classification, cost,
  savings, ceiling, content-aware tips
- `cache_lens/models.py` — dataclasses (`RawCallMetrics`, `PromptSegment`,
  `CallCapture`, `LayerReport`, `SessionReport`)
- `cache_lens/pricing.py` — price registry (USD per 1M tokens): bundled
  `DEFAULT_PRICING` + runtime overrides via `CACHE_LENS_PRICING` env var or
  `pricing=` arg (native or LiteLLM JSON, auto-detected, merged over defaults)
- `cache_lens/outputs/{terminal,json_export,otel}.py` — sinks
- `cache_lens/cli.py` — `cache-lens run` (scaffolded, not implemented)
- `tests/` — pytest; fixtures are JSON, loaded via `tests/conftest.py`

## Conventions

- Never let instrumentation break the wrapped caller — both `capture()` and
  `extract()` are wrapped in try/except in `wrapper._wrap_call`; capture failure
  yields empty segments (analyzer degrades to no layer diagnosis, aggregates still
  exact).
- Provider SDKs and OTEL are optional deps; import them lazily inside functions,
  not at module top level.
- Pricing/cost is per-token internally (`pricing.rate`), table is per-1M.
- Overall session aggregates (cost, savings, hit rate) are computed **exactly**
  from response metrics; per-layer token splits are **estimated** by char-share
  scaled to the real `input_tokens` (no tokenizer dep).
- Cost model: actual = miss·input + creation·cache_write + read·cache_read +
  output·output; cold = all input at full input rate.

## Run tests

```bash
pip install -e .[dev] && pytest
```
