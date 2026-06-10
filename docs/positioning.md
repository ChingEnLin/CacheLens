# CacheLens — positioning & competitive analysis

> Why CacheLens exists alongside the existing prompt-caching tooling, and where
> the genuine whitespace is. Last reviewed 2026-06-09.

## One-line thesis

Every existing tool surfaces the cached-token *number*. None do the
**architectural diagnostic** — cross-call prefix-stability analysis that tells
you *which layer of your prompt is cacheable but isn't*, what it's costing you,
and how to restructure. That diagnostic is CacheLens's identity and it is
currently unoccupied.

## The landscape

| Tool | What it does for caching | What it does NOT do |
|------|--------------------------|---------------------|
| **LiteLLM** (proxy + SDK) | Per-call cached-token metrics (`litellm_input_cached_tokens_metric`, `litellm_input_cache_creation_tokens_metric`); PromQL hit-rate recipe; cache-aware `completion_cost()`; auto-inject of `cache_control` markers | No cross-call session aggregation for cache *analysis*; no layer classification; no "money left on the table" ceiling; no restructuring tips |
| **Langfuse** (OSS observability) | Captures `cache_read_input_tokens` alongside latency/cost | Surfaces the metric; no architectural diagnosis |
| **Helicone** (proxy observability) | Same — captures cache tokens per call | Same |
| **Datadog LLM Observability** | Surfaces cache metrics (commercial) | Same |
| **messkan/prompt-cache** (Go) | *Semantic response cache* — returns a cached answer for similar prompts | Different mechanism entirely (response caching, not KV/prefix); not a competitor |
| **token-dashboard** | Reads Claude Code session JSONL | Local Claude Code sessions only, not API apps you write |

Takeaway: surfacing the cached-token count is a solved, commoditised feature.
The *diagnostic interpretation* of that count is not.

## LiteLLM in depth (the closest overlap)

LiteLLM is the most important neighbour because it touches two adjacent jobs.

### 1. Cache hit rate — already solved by LiteLLM

LiteLLM ships per-call cached-token counters and a documented PromQL ratio
(`rate(litellm_input_cached_tokens_metric_total) / rate(litellm_input_tokens_metric_total)`),
plus cache-aware cost math in `completion_cost()`. CacheLens doesn't try to
re-do this — a "cache hit rate" metric would be redundant with what LiteLLM
already provides.

### 2. Auto-inject checkpoints — the "fix", but blind

`litellm/integrations/anthropic_cache_control_hook.py` (`AnthropicCacheControlHook`)
auto-inserts `cache_control` markers. Reading the implementation, it is a thin,
mechanical message mutator with **zero analysis**:

- It does nothing unless the user supplies `cache_control_injection_points`
  (`if not injection_points: return ... unchanged`).
- Each point is `{location: "message", index: N}` or `{..., role: "system"}`.
  It targets by index (bounds-checked) or by role (every matching message), then
  stamps `cache_control` on the message — on the *last* content block if content
  is a list (per Anthropic's spec).
- It self-describes as **not** intelligent: `should_run_prompt_management`
  always returns `False`; `_compile_prompt_helper` is a no-op ("only modifies
  messages, doesn't fetch prompts").

Three things it categorically **cannot** do:

1. **No cross-call state** — operates on a single request's `messages` list, so
   it physically cannot detect what is stable across a conversation.
2. **No discovery** — the human supplies "which messages are static"; there is
   no diffing or stability inference.
3. **No measurement** — it stamps a marker and does not read back whether hits
   actually occurred or what was saved.

Concrete footgun it will happily commit: `index: -1` caches the *last* message,
which moves every turn in a growing conversation — almost always the wrong target
for a static prefix. (See also bug #15696: it once stamped all content blocks
instead of the last — mechanically young.)

## Where that leaves CacheLens

CacheLens is the **eyes**; LiteLLM's auto-inject is the **hands**. The exact
output CacheLens produces —

> "system_prompt + schema_context are static across 18 turns, uncached, costing
> $0.14 — move them to a cache_control block before the conversation history"

— is *literally the input a user needs* to configure
`cache_control_injection_points` correctly (or to add `cache_control` by hand).
Without a diagnostic layer, configuring their injector is guesswork.

CacheLens already consumes LiteLLM's `model_prices_and_context_window.json`
pricing format (see `cache_lens/pricing.py`), so it is an ecosystem citizen,
not a competitor.

## Where each idea belongs

| Idea | Where it belongs |
|------|---------|
| Cache hit rate metric | LiteLLM — already exists, no need to duplicate |
| Diagnostics inside the auto-inject hook | Not a fit — it's a thin mutator by design, not an analysis layer |
| Pricing-data fixes | Upstream to LiteLLM's JSON — clean, welcome contribution |
| Layer classification / ceiling / tips | CacheLens — no other tool does this |

## In short

LiteLLM will stamp a cache marker wherever you point it — but pointing
correctly requires knowing your prompt's layer structure, and nothing tells
you that. CacheLens is the missing eyes.

## Sources

- LiteLLM Prometheus metrics — https://docs.litellm.ai/docs/proxy/prometheus
- LiteLLM auto-inject tutorial — https://docs.litellm.ai/docs/tutorials/prompt_caching
- LiteLLM prompt caching (completion) — https://docs.litellm.ai/docs/completion/prompt_caching
- `anthropic_cache_control_hook.py` — https://github.com/BerriAI/litellm/blob/main/litellm/integrations/anthropic_cache_control_hook.py
- PR #9996 (cache_control_injection_points) — https://github.com/BerriAI/litellm/pull/9996
- Bug #15696 (cache_control on all blocks) — https://github.com/BerriAI/litellm/issues/15696
- Cache-hit-rate landscape (Langfuse/Helicone/Datadog) — https://tianpan.co/blog/2026-04-20-prompt-cache-hit-rate-production-metric
- messkan/prompt-cache — https://github.com/messkan/prompt-cache
