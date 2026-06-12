# CHANGELOG

<!-- version list -->

## v1.1.0 (2026-06-12)

### Build System

- **deps**: Bump actions/checkout from 4 to 6
  ([`1752f8f`](https://github.com/ChingEnLin/CacheLens/commit/1752f8f64d6c3e0ebdec57a83c4c920a992783ce))

Bumps [actions/checkout](https://github.com/actions/checkout) from 4 to 6. - [Release
  notes](https://github.com/actions/checkout/releases) -
  [Changelog](https://github.com/actions/checkout/blob/main/CHANGELOG.md) -
  [Commits](https://github.com/actions/checkout/compare/v4...v6)

--- updated-dependencies: - dependency-name: actions/checkout dependency-version: '6'

dependency-type: direct:production

update-type: version-update:semver-major ...

Signed-off-by: dependabot[bot] <support@github.com>

- **deps**: Bump actions/setup-python from 5 to 6
  ([`75be19d`](https://github.com/ChingEnLin/CacheLens/commit/75be19db449e4b9fee69b9dddf757abff52b9336))

Bumps [actions/setup-python](https://github.com/actions/setup-python) from 5 to 6. - [Release
  notes](https://github.com/actions/setup-python/releases) -
  [Commits](https://github.com/actions/setup-python/compare/v5...v6)

--- updated-dependencies: - dependency-name: actions/setup-python dependency-version: '6'

dependency-type: direct:production

update-type: version-update:semver-major ...

Signed-off-by: dependabot[bot] <support@github.com>

- **deps**: Bump python-semantic-release/python-semantic-release
  ([`a73316b`](https://github.com/ChingEnLin/CacheLens/commit/a73316b4c9e1e32d60863f59ba4f62689a3bf2d4))

Bumps
  [python-semantic-release/python-semantic-release](https://github.com/python-semantic-release/python-semantic-release)
  from 0b9bc98db4143ecf7df57025ad69056fa4f1b2c1 to 0dc72ac9058a62054a45f6344c83a423d7f906a8. -
  [Release notes](https://github.com/python-semantic-release/python-semantic-release/releases) -
  [Changelog](https://github.com/python-semantic-release/python-semantic-release/blob/master/CHANGELOG.rst)
  -
  [Commits](https://github.com/python-semantic-release/python-semantic-release/compare/0b9bc98db4143ecf7df57025ad69056fa4f1b2c1...0dc72ac9058a62054a45f6344c83a423d7f906a8)

--- updated-dependencies: - dependency-name: python-semantic-release/python-semantic-release
  dependency-version: 0dc72ac9058a62054a45f6344c83a423d7f906a8

dependency-type: direct:production ...

Signed-off-by: dependabot[bot] <support@github.com>

### Continuous Integration

- Gate release on tests; add lint, type-check, and min-versions jobs
  ([`2a42482`](https://github.com/ChingEnLin/CacheLens/commit/2a42482d05aafc7cf8e454bf0491c9e0430693c9))

The release workflow previously published whenever semantic-release cut a version, regardless of
  test status. It now needs a green matrix first. CI gains ruff + mypy and a job that installs every
  extra at its declared minimum version so dependency-floor drift fails in CI instead of on users.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

- Push releases via deploy key to satisfy branch ruleset
  ([`3568b4a`](https://github.com/ChingEnLin/CacheLens/commit/3568b4a51b4cc54ac2c03e85ee6c1f1ad581071d))

The main ruleset (PRs required, no direct pushes) rejects semantic-release's version-bump push with
  GITHUB_TOKEN, and the GitHub Actions app cannot be a ruleset bypass actor on a personal repo.
  Check out the release job with the RELEASE_DEPLOY_KEY secret instead: pushes go over SSH using a
  write deploy key, which is on the ruleset bypass list — automated releases work again while humans
  still go through pull requests.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

- Run semantic-release CLI on runner and push via SSH remote
  ([`c2f51cd`](https://github.com/ChingEnLin/CacheLens/commit/c2f51cd0f3282c19d9af8b6099a69b59d6d5257e))

The PSR docker action rewrites the push URL with GITHUB_TOKEN, so the deploy-key SSH remote from
  checkout was never used and the main ruleset kept rejecting the version-bump push (GH013). Run the
  PSR CLI directly on the runner (where checkout's SSH config is visible) and set
  remote.ignore_token_for_push so the push goes through the deploy-key bypass; the token is still
  used for the GitHub Release API.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

### Documentation

- Add improvement plan, privacy section, and capture semantics
  ([`95c219e`](https://github.com/ChingEnLin/CacheLens/commit/95c219e073703ad8e88206cf7bde8a973a2bf75c))

README documents what is captured/retained/exported (content-free by default), session-scoped
  pricing, async/streaming status, and unwrap(); architecture.md describes hash+length capture;
  docs/improvement-plan.md records the audit-derived roadmap and what this PR implements.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

### Features

- Harden instrumentation per audit improvement plan
  ([`e17dca6`](https://github.com/ChingEnLin/CacheLens/commit/e17dca6beb8908432600d6886fac57a38543d086))

Implements the P0-P1 (and P3 hardening) items from docs/improvement-plan.md:

- otel: require opentelemetry-sdk>=1.23 (Meter.create_gauge did not exist on the previously declared
  1.20 floor and crashed emit()); use a private MeterProvider instead of hijacking the
  process-global one - wrapper: isolate every output sink in _flush so a sink failure can never
  reach the caller; async clients (AsyncAnthropic/AsyncOpenAI/ generate_content_async) are now
  instrumented; streaming calls are counted and surfaced as skipped instead of silently dropped or
  zero-recorded - capture: content-free by default — segments keep (role, sha256, length) only,
  bounding memory and keeping prompt text out of the heap; capture_content=True opts back into full
  text - pricing: per-session Registry so pricing= overrides no longer mutate the process-global
  table; module-level API unchanged - report: latency p50/p95, distinct-models list with mixed-model
  tip, skipped_calls accounting - json export: whitelisted path-template substitution (rejects
  {model.__class__}-style traversal), backslash sanitised in model names - proxy: functools.wraps on
  intercepted methods, unwrap() escape hatch - __version__ now derived from package metadata (was
  frozen at 1.0.0) - cli: cache-lens run exits 2 with guidance instead of raising
  NotImplementedError; classifier moved to Beta - semantic-release changelog switched to update mode
  with insertion flag so released sections stop being regenerated/dropped

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>


## v1.0.5 (2026-06-10)

### Bug Fixes

- Drop Python 3.8 support
  ([`e500d31`](https://github.com/ChingEnLin/CacheLens/commit/e500d31439d8e575c24d47bf1f9310a15be4e063))

google-generativeai (the gemini extra) has no distribution for Python 3.8, so
  cachelens[gemini]/[all] was already broken there. Python 3.8 is also EOL. Raise requires-python to
  >=3.9 and update the CI matrix accordingly.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Documentation

- Restore v1.0.0 changelog details and tidy pyproject.toml
  ([`6a7fa3b`](https://github.com/ChingEnLin/CacheLens/commit/6a7fa3bb43c0b78d09e61e0a2038e955f1ebc856))

The semantic-release version_toml writer drops the v1.0.0 changelog section and accumulates blank
  lines in pyproject.toml on each run.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v1.0.4 (2026-06-10)

### Bug Fixes

- Enable verbose output for PyPI publish step
  ([`ce84b90`](https://github.com/ChingEnLin/CacheLens/commit/ce84b90150133aa8e3e947d10dfaaa34319613b7))

Restore v1.0.0 changelog details dropped by the earlier release misfires, and turn on verbose
  logging in the PyPI publish step for easier troubleshooting.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v1.0.3 (2026-06-10)

### Bug Fixes

- Stop semantic-release from pre-building dist/ before CI build
  ([`46a9a87`](https://github.com/ChingEnLin/CacheLens/commit/46a9a874e2292432790cd975dc90bc1b2ca59514))

semantic-release's build_command ran inside its container and wrote dist/*.tar.gz as root, causing a
  permission error when the workflow's own build step tried to overwrite it. The workflow already
  builds and publishes the package itself, so this command is unnecessary. Also restore v1.0.0
  changelog details dropped by the earlier release.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v1.0.2 (2026-06-10)

### Bug Fixes

- Publish to PyPI in the same job that creates the release
  ([`0a64e39`](https://github.com/ChingEnLin/CacheLens/commit/0a64e391bf57c9a580b7d108747564cb47782bb7))

The separate publish.yml never ran because GitHub Actions doesn't trigger workflows from events
  created by the default GITHUB_TOKEN (release.yml created v1.0.1 but it was never published to
  PyPI). Build and publish to PyPI directly in release.yml when semantic-release creates a new
  release. Drop the deprecated/broken upload-to-gh-release step. Restore v1.0.0 changelog details
  lost by the earlier release misfire.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v1.0.1 (2026-06-10)

### Bug Fixes

- Pin third-party GitHub Actions to commit SHAs
  ([`9e0058b`](https://github.com/ChingEnLin/CacheLens/commit/9e0058bb4c041330781d535feac6d6e158a6393c))

Pin python-semantic-release, upload-to-gh-release, and gh-action-pypi-publish to immutable commit
  SHAs to mitigate supply-chain risk from mutable tags. Add Dependabot config to keep the pins
  updated.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v1.0.0 (2026-06-10)
