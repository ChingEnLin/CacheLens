# cache-lens architecture

Expanded notes complementing [SPEC.md](../SPEC.md).

## Module map

| Module | Responsibility |
|--------|----------------|
| `cache_lens/wrapper.py` | `CacheLensClient` proxy, `wrap()`, `CacheLens` context manager, flush/atexit |
| `cache_lens/providers/` | Per-provider extraction of `RawCallMetrics` from responses |
| `cache_lens/analyzer.py` | Aggregation, cost/savings, layer classification, tips |
| `cache_lens/models.py` | `RawCallMetrics`, `LayerReport`, `SessionReport` dataclasses |
| `cache_lens/pricing.py` | Static `(provider, model)` → rate table |
| `cache_lens/outputs/` | Terminal (rich), JSON export, OTEL metric sinks |
| `cache_lens/cli.py` | `cache-lens run <command>` entry point |

## Interception

`CacheLensClient.__getattr__` forwards every attribute to the wrapped client.
Two cases get special handling:

1. **Intercepted methods** (`messages.create`, `generate_content`) are wrapped so
   the response is timed and passed to the provider extractor. The original
   response is returned unchanged — instrumentation failures are swallowed so a
   wrapped client never breaks the caller.
2. **Namespace attributes** (e.g. `client.messages`) are themselves wrapped in a
   `CacheLensClient` so their methods are intercepted too.

## Layer classification (content-based)

The wrapper captures each call's **request prompt** (not just the response) and
normalises it to ordered `PromptSegment`s. The analyzer computes the longest
common prefix of segments across all calls (the cacheable region), names the
layers within it (`system_prompt` / `context` / `conversation`), and
cross-references that content-derived prefix against the `cache_read` tokens the
provider actually reported — surfacing which named layer is stable-but-uncached
and what it costs. See SPEC §6 for the full algorithm and the per-layer token
estimation method.

This is the project's differentiator (see [positioning.md](positioning.md)):
metric-only tools know *how many* tokens were cached; cache-lens knows *which
layer* should have been and wasn't.

**Deferred:** true static vs semi-static separation needs cross-run comparison
(persisted JSON reports from multiple runs), which a single in-memory session
can't do — v1 uses a role/position heuristic.

## CLI injection (not yet implemented)

`cache-lens run` will inject a `sitecustomize.py` onto `PYTHONPATH` that patches
the Anthropic/Gemini SDK at import time and registers an atexit report, so apps
can be instrumented without code changes. Scaffolded in `cli.py`.
