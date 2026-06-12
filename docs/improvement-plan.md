# Improvement Plan

Derived from the 2026-06-10 deep-dive audit of the published `cachelens` 1.0.5
package (artifact integrity, correctness, security, efficacy). Items are ordered
by priority; each has a concrete change, acceptance criteria, and a suggested
conventional-commit type so semantic-release versions it correctly.

Audit scores at baseline: Reliability 7/10 · Security 8.5/10 · Utility 7.5/10.

## Status (2026-06-10)

Implemented in the `feat/improvement-plan` PR:

- **P0:** item 1 (OTEL ≥1.23 floor, per-sink failure isolation, min-versions CI
  job) and item 2 stage 1 (skipped-call counting + report surfacing). Item 2
  stage 2 landed **partially**: async clients (`AsyncAnthropic`/`AsyncOpenAI`/
  `generate_content_async`) are now fully instrumented; streaming usage
  extraction is still pending and streaming calls are counted as skipped.
- **P1:** item 3 (content-free hash+length capture by default,
  `capture_content=True` opt-in; no ring buffer — retention is now O(KB)),
  item 4 (per-session `pricing.Registry`, private OTEL `MeterProvider`),
  item 5 (latency p50/p95, `models` list + mixed-model tip, `skipped_calls`).
- **P2:** items 6–10 (release gated on test matrix, `__version__` from package
  metadata, changelog `mode = "update"` + insertion flag, graceful CLI exit +
  Beta classifier, ruff/mypy/min-versions CI jobs). macOS/Windows CI legs not
  added.
- **P3:** items 11–14 (`functools.wraps` + `.unwrap()`, whitelisted export
  path templating + `\` sanitisation, README privacy section, limitations
  documented).

Remaining: streaming usage extraction (item 2 stage 2), `cache-lens run`
injection, cross-run static/semi-static separation.

---

## P0 — Bugs that break the core promise (target: v1.1.x, `fix:`)

### 1. OTEL sink crashes on the declared minimum dependency

**Problem (verified).** `outputs/otel.py` calls `meter.create_gauge`, which the
OTEL SDK only gained in 1.23, while the `otel` extra declares `>=1.20`. On
1.20–1.22 `emit()` raises `AttributeError`. Because `_flush` has no exception
handling, in `CacheLens(..., otel=True)` context-manager mode the error
propagates into the caller's `with` block — violating the "never break the
wrapped caller" convention.

**Change.**
- Bump `otel` and `all` extras to `opentelemetry-sdk>=1.23` and matching exporter floor.
- Wrap each sink call in `_flush` (terminal, json, otel) in its own try/except
  so no sink failure ever reaches the caller; log a one-line warning instead.

**Accept when:** a test installs a mock sink that raises and asserts the
context manager exits cleanly and the other sinks still run; CI adds one job
that installs the *minimum* declared versions of all extras and imports/exercises
every sink (catches future floor drift).

**Effort:** S

### 2. Silent no-op on async and streaming clients

**Problem.** `AsyncAnthropic`/`AsyncOpenAI` calls and `stream=True` /
`messages.stream` pass through uninstrumented: extraction fails, the exception
is swallowed, and the user gets an empty or partial report with no explanation.
Most modern agent stacks are async — this is the largest silent coverage hole.

**Change (two stages).**
- *Stage 1 (fix:, v1.1.x):* detect the case and fail loudly-but-safely — count
  unparseable/skipped calls in the session and surface a report line + tip:
  "N calls were not instrumented (async/streaming not yet supported)". Never
  return an empty report without saying why.
- *Stage 2 (feat:, v1.2):* real support. If the intercepted attribute is a
  coroutine function, return an `async def` wrapper (same capture/extract
  logic). For streaming, read final usage from the terminal event
  (Anthropic `message_delta`/`MessageStream.get_final_message`, OpenAI
  `stream_options={"include_usage": True}`).

**Accept when:** async fixture tests for both SDK shapes pass; a streaming call
produces metrics identical to its non-streaming twin; stage-1 warning appears
whenever a call is skipped.

**Effort:** Stage 1 S · Stage 2 L

---

## P1 — Production-safety gaps (target: v1.2, `feat:`)

### 3. Unbounded in-memory prompt retention

**Problem (measured).** Every call's full prompt text is held until process
exit: 1,000 calls × 100 KB prompt = 100 MB retained. Disqualifying for
long-lived processes; also widens the sensitive-data surface (prompts sit in
the heap for the process lifetime).

**Change.** The analyzer only needs *equality* and *length* per segment, not
content: store `(role, sha256(text), len(text))` instead of the text itself.
Prefix diffing compares hashes; char-share estimation uses lengths. Make
content-free capture the default; keep `capture_content=True` opt-in for future
content-aware tips. Optionally add a `max_calls` ring buffer as a hard cap.

**Accept when:** the benchmark retains O(KB) instead of O(prompt volume) for
1,000 calls; all 31 existing tests still pass with hashed capture; README
documents what is captured, retained, and exported.

**Effort:** M

### 4. Global state: pricing registry and OTEL meter provider

**Problem.** `pricing.load()` mutates a process-global table (two wrapped
clients with different `pricing=` args silently merge), and `otel.emit` calls
`metrics.set_meter_provider(...)`, racing with the host app's own OTEL setup —
one of the two silently loses its pipeline.

**Change.**
- Pricing: resolve a per-session registry (defaults → env file → `pricing=`
  arg) carried on `_Session`; keep module-level `load()` as a documented
  process-wide override.
- OTEL: build a private `MeterProvider` and flush it directly; never touch the
  global. If the app already has a provider, optionally emit through it via
  `metrics.get_meter_provider()` without setting anything.

**Accept when:** two concurrent sessions with different pricing produce
independent costs; `emit()` works in a process that already called
`set_meter_provider` (test with a pre-set provider).

**Effort:** M

### 5. Report blind spots

**Problem.** `latency_ms` is captured but never rendered; the analyzer assumes
one provider/model per session (`metrics[0]`); capture/extract failures are
invisible.

**Change.** Add latency summary (p50/p95) to the terminal/JSON report; group
layer/cost computation by model when a session mixes models (or at minimum
label the report "mixed models" instead of misattributing); add the
skipped-call counter from item 2 to `SessionReport`.

**Accept when:** mixed-model fixture produces per-model cost lines; latency
appears in terminal + JSON output.

**Effort:** M

---

## P2 — Release & packaging hygiene (target: next releases, `fix:`/`chore:`)

### 6. Releases are not gated on CI

**Problem.** `release.yml` triggers on every push to `main` and publishes
whenever semantic-release cuts a version — a red test matrix and a published
release can coexist.

**Change.** Run the test matrix as a job inside `release.yml` (or convert
`ci.yml` to a reusable workflow and `needs:` it) so semantic-release only runs
after green tests.

**Accept when:** a deliberately failing test on a branch merged to main blocks
publication.

**Effort:** S

### 7. Version skew in `__init__.py`

**Problem.** `cache_lens.__version__` is frozen at "1.0.0" while PyPI is at
1.0.5 — semantic-release only bumps `pyproject.toml`.

**Change.** Either add `version_variables = ["cache_lens/__init__.py:__version__"]`
to `[tool.semantic_release]`, or (cleaner) derive it at runtime:
`__version__ = importlib.metadata.version("cachelens")` with a fallback.

**Accept when:** released wheel's `cache_lens.__version__` equals the PyPI version.

**Effort:** S

### 8. semantic-release changelog corruption

**Problem (recurring).** Each release drops the v1.0.0 "Added" section and
accumulates blank lines in `pyproject.toml`; it has been manually restored
three times already.

**Change.** Switch `[tool.semantic_release.changelog]` to `mode = "update"`
with an insertion flag comment in `CHANGELOG.md`, so prior sections are
preserved verbatim; if the blank-line accumulation persists, stop letting
semantic-release rewrite `pyproject.toml` formatting (template or post-step).

**Accept when:** two consecutive releases leave the v1.0.0 section and file
formatting untouched.

**Effort:** S

### 9. Honest CLI and classifier

**Problem.** `cache-lens run` is advertised in `--help` but raises
`NotImplementedError`; the `Development Status :: 5 - Production/Stable`
classifier overstates a day-old package.

**Change.** Make `run` exit 2 with "not yet implemented — track at <issue
link>" (no traceback) and mark it experimental in usage text, or remove it
from usage until the sitecustomize injection lands. Move classifier to
`4 - Beta` until P0/P1 are done.

**Effort:** S

### 10. CI depth

**Change.** Add `ruff check` + `mypy cache_lens` jobs; add the minimum-versions
job from item 1; (optional) add a macOS/Windows leg since path handling differs.

**Effort:** S

---

## P3 — Hardening & polish (opportunistic)

11. **Proxy transparency** — apply `functools.wraps` to intercepted methods;
    document that `isinstance(wrapped, anthropic.Anthropic)` is False and offer
    `.unwrap()` to reach the inner client. (S)
12. **Export path hardening** — replace `str.format` on the user template with a
    whitelisted `string.Formatter` (reject attribute/index access like
    `{model.__class__}`); sanitize `\` as well as `/` in model names for
    Windows paths. (S)
13. **Privacy note in README** — one explicit paragraph: prompts are captured
    in memory only (hashed by default after item 3), never written to disk,
    terminal, or OTEL; reports contain aggregates only. (S)
14. **Streaming/async docs** — until item 2 stage 2 lands, document the
    limitation prominently in README "Status". (S)

---

## Suggested sequencing

| Release | Contents | Outcome |
|---|---|---|
| v1.1.x | Items 1, 2-stage-1, 6, 7, 8, 9 | No crash paths, no silent no-ops, trustworthy releases |
| v1.2 | Items 3, 4, 5 | Safe to leave enabled in long-lived dev/staging processes |
| v1.3 | Item 2-stage-2 + 10–14 | Async/streaming coverage; revisit Production/Stable classifier |

Re-audit expectation after v1.2: Reliability ~8.5, Security ~9, Utility ~8.5
(async support in v1.3 is the biggest remaining utility unlock).
