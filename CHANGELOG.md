# CHANGELOG


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
