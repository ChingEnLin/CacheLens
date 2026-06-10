# CHANGELOG


## v1.0.1 (2026-06-10)

### Bug Fixes

- Pin third-party GitHub Actions to commit SHAs
  ([`9e0058b`](https://github.com/ChingEnLin/CacheLens/commit/9e0058bb4c041330781d535feac6d6e158a6393c))

Pin python-semantic-release, upload-to-gh-release, and gh-action-pypi-publish to immutable commit
  SHAs to mitigate supply-chain risk from mutable tags. Add Dependabot config to keep the pins
  updated.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v1.0.0 (2026-06-09)

### Added

- Wrapper interception for Anthropic, Gemini, and OpenAI clients (`wrap`, `CacheLens`, `CacheLensClient`)
- Request capture: normalises prompt to ordered `PromptSegment` list per call
- Content-based layer classification via longest-common-prefix analysis (system_prompt / context / conversation layers)
- Terminal report with cache hit rate, cost, savings, and per-layer breakdown
- JSON export (`json_export=` arg or `CACHE_LENS_JSON` env var)
- OpenTelemetry metrics output (`otel=True`)
- Overridable pricing table (native dict, JSON file, or `CACHE_LENS_PRICING` env var; LiteLLM format auto-detected)
- Gemini support for modern `google-genai` SDK (`config` kwarg pattern)
