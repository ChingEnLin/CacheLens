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

## Commit messages and versioning

This project uses [Conventional Commits](https://www.conventionalcommits.org/)
and [python-semantic-release](https://python-semantic-release.readthedocs.io/)
to automate versioning, the changelog, and PyPI releases. Every commit to
`main` is parsed, so PR titles/commits should follow:

- `fix: ...` → patch release (1.0.0 → 1.0.1)
- `feat: ...` → minor release (1.0.0 → 1.1.0)
- `feat!: ...` or a `BREAKING CHANGE:` footer → major release (1.0.0 → 2.0.0)
- `docs:`, `chore:`, `refactor:`, `test:`, etc. → no release

`CHANGELOG.md` is generated automatically from these messages — don't edit it
by hand.

## Reporting issues

Open an issue at https://github.com/ChingEnLin/CacheLens/issues with:
- Python version and OS
- Provider SDK version
- Minimal reproducer
