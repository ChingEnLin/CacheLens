"""cache-lens CLI: `cache-lens run <command>` for zero-code instrumentation."""

from __future__ import annotations

import sys


def main(argv: list = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        _print_usage()
        return 0

    cmd, rest = argv[0], argv[1:]
    if cmd == "run":
        return _run(rest)

    sys.stderr.write(f"cache-lens: unknown command '{cmd}'\n")
    _print_usage()
    return 2


def _run(command: list) -> int:
    if not command:
        sys.stderr.write("cache-lens run: no command given\n")
        return 2
    # v1.0: sitecustomize injection that patches the SDK at import time and
    # registers an atexit report. Implementation tracked in docs/architecture.md.
    raise NotImplementedError(
        "cache-lens run is scaffolded; sitecustomize injection not yet implemented"
    )


def _print_usage() -> None:
    sys.stdout.write(
        "cache-lens — prompt cache instrumentation\n\n"
        "Usage:\n"
        "  cache-lens run <command> [args...]   Instrument a subprocess\n"
    )


if __name__ == "__main__":
    raise SystemExit(main())
