"""cache-lens — non-invasive prompt cache instrumentation for LLM API apps."""

from __future__ import annotations

from .models import LayerReport, RawCallMetrics, SessionReport
from .wrapper import CacheLens, CacheLensClient, wrap

try:
    from importlib.metadata import PackageNotFoundError, version as _pkg_version

    __version__ = _pkg_version("cachelens")
except PackageNotFoundError:  # running from a source tree without install
    __version__ = "0.0.0+unknown"

__all__ = [
    "wrap",
    "CacheLens",
    "CacheLensClient",
    "RawCallMetrics",
    "LayerReport",
    "SessionReport",
    "__version__",
]
