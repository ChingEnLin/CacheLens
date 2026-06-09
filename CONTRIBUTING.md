# Contributing to cachelens

Thanks for your interest in contributing!

## Setup

```bash
git clone https://github.com/ChingEnLin/CacheLens.git
cd CacheLens
pip install -e .[dev]
```

## Running tests

```bash
pytest
```

All tests must pass before opening a PR.

## Adding a provider

1. Create `cache_lens/providers/<name>.py` with `extract(response) -> RawCallMetrics` and `capture(request, client) -> List[PromptSegment]`
2. Register it in `cache_lens/wrapper.py` (`_detect_provider`)
3. Add tests in `tests/providers/test_<name>.py`

## Pull requests

- Keep PRs focused — one feature or fix per PR
- Include tests for new behavior
- Update `CHANGELOG.md` under `[Unreleased]`

## Reporting issues

Open an issue at https://github.com/ChingEnLin/CacheLens/issues with:
- Python version and OS
- Provider SDK version
- Minimal reproducer
