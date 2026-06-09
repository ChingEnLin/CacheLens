# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-06-09

### Added
- Wrapper interception for Anthropic, Gemini, and OpenAI clients (`wrap`, `CacheLens`, `CacheLensClient`)
- Request capture: normalises prompt to ordered `PromptSegment` list per call
- Content-based layer classification via longest-common-prefix analysis (system_prompt / context / conversation layers)
- Terminal report with cache hit rate, cost, savings, and per-layer breakdown
- JSON export (`json_export=` arg or `CACHE_LENS_JSON` env var)
- OpenTelemetry metrics output (`otel=True`)
- Overridable pricing table (native dict, JSON file, or `CACHE_LENS_PRICING` env var; LiteLLM format auto-detected)
- Gemini support for modern `google-genai` SDK (`config` kwarg pattern)
