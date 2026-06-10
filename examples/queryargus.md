# Real-world example: QueryArgus

[QueryArgus](https://github.com/ChingEnLin/QueryArgus) is a 30+ turn agent loop (Gemini
`gemini-2.5-flash`) that investigates a database collection turn-by-turn,
maintaining a running state of schema info, findings, and progress. Wrapping
its client in cache-lens surfaced a caching problem the team didn't know they
had — and then let them measure the fix.

## Before

```
cache-lens  ·  gemini  ·  gemini-2.5-flash  ·  32 turns
┏━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ Layer        ┃  Tokens ┃ Cached ┃ Hit Rate ┃  Saved ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│ conversation │ 190,335 │      0 │      n/a │ $0.000 │
└──────────────┴─────────┴────────┴──────────┴────────┘
Total input tokens   190,335
Actual cost          $0.0157
Cold cost (est.)     $0.0159
Savings              $0.0002  (1%)
Ceiling              $0.0000  (max if fully cached)
Tips
  → No stable prompt prefix detected across calls — content differs every turn,
    so prefix caching cannot help. Ensure your system prompt and static context
    are byte-identical on each call (and placed first).
  → First call always misses the cache (expected). Pre-warm with a dummy call
    before the loop starts to eliminate the cold miss.
  → 98% of input tokens are uncached and re-sent each turn — consider
    summarising tool results instead of appending them verbatim.
```

The single `conversation` layer and 0% hit rate are the diagnosis: the agent's
system prompt and static context aren't forming a stable, byte-identical
prefix, so every one of the 190K input tokens is re-billed at full price every
turn. A hit-rate-only tool would just report "1% savings" and stop there —
cache-lens points at the *cause* (no stable prefix layer) and the *fix*
(hoist the system prompt/static context to a fixed, identical-every-call
prefix).

## After a first pass at restructuring

Acting on the third tip, QueryArgus's `summarize()` (in
`src/queryargus/agent/state.py`) was split into a stable and a volatile part:

- `_stable_prefix_lines()` — a `=== COLLECTION UNDER AUDIT (fixed context) ===`
  banner, identity + `documents_sampled`/`collection_size`, the full schema,
  and historical context. Byte-identical every turn once the schema is
  sampled.
- `_volatile_trailer_lines()` — an
  `=== INVESTIGATION PROGRESS (iteration N/budget) ===` banner, then
  everything that mutates per turn: queries run, recent actions, committed/
  dismissed findings, critique, last observation.

After this change (32 → 30 turns):

```
cache-lens  ·  gemini  ·  gemini-2.5-flash  ·  30 turns
┏━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ Layer        ┃  Tokens ┃ Cached ┃ Hit Rate ┃  Saved ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│ conversation │ 169,828 │      0 │      n/a │ $0.000 │
└──────────────┴─────────┴────────┴──────────┴────────┘
Total input tokens   169,828
Actual cost          $0.0114
Cold cost (est.)     $0.0141
Savings              $0.0027  (19%)
Ceiling              $0.0000  (max if fully cached)
Tips
  → No stable prompt prefix detected across calls — content differs every turn,
    so prefix caching cannot help. Ensure your system prompt and static context
    are byte-identical on each call (and placed first).
  → First call always misses the cache (expected). Pre-warm with a dummy call
    before the loop starts to eliminate the cold miss.
  → 72% of input tokens are uncached and re-sent each turn — consider
    summarising tool results instead of appending them verbatim.
```

| | Before | After |
|---|---|---|
| Total input tokens | 190,335 | 169,828 |
| Savings | $0.0002 (1%) | $0.0027 (19%) |
| Uncached share | 98% | 72% |
| Cache hit rate | 0% | 0% |

Trimming the per-turn payload cut total input tokens by ~11% and nearly
doubled the savings percentage — but the hit rate is still 0% and cache-lens
still reports "no stable prompt prefix detected." That's the next target:
despite the `state.py` split, the prefix the model actually receives still
isn't byte-identical turn-to-turn, so prefix caching itself hasn't kicked in
yet. The remaining win (the gap between 19% and the ceiling) is gated on
finding and removing whatever is still varying ahead of the conversation
history — e.g. timestamps, ordering, or other framing text that wraps the
stable block before it reaches the API.

This is the loop cache-lens is meant to drive: change something, rerun, read
the report, see whether the *cause* the tips named actually went away — not
just whether the headline cost number moved.
