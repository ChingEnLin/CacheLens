"""cache-lens CLI: `cache-lens run <command>` for zero-code instrumentation."""

from __future__ import annotations

import sys
from typing import List, Optional


def main(argv: Optional[List[str]] = None) -> int:
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


def _run(command: List[str]) -> int:
    if not command:
        sys.stderr.write("cache-lens run: no command given\n")
        return 2
    # Planned: sitecustomize injection that patches the SDK at import time and
    # registers an atexit report. Design tracked in docs/architecture.md.
    sys.stderr.write(
        "cache-lens run is not implemented yet — wrap your client in code instead:\n"
        "  from cache_lens import wrap; client = wrap(client)\n"
        "Track progress: https://github.com/ChingEnLin/CacheLens/issues\n"
    )
    return 2


def _print_usage() -> None:
    sys.stdout.write(
        "cache-lens — prompt cache instrumentation\n\n"
        "Usage:\n"
        "  cache-lens run <command> [args...]   Instrument a subprocess (experimental,\n"
        "                                       not yet implemented)\n"
    )


if __name__ == "__main__":
    raise SystemExit(main())
