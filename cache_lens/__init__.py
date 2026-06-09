"""cache-lens — non-invasive prompt cache instrumentation for LLM API apps."""

from __future__ import annotations

from .models import LayerReport, RawCallMetrics, SessionReport
from .wrapper import CacheLens, CacheLensClient, wrap

__version__ = "1.0.0"

__all__ = [
    "wrap",
    "CacheLens",
    "CacheLensClient",
    "RawCallMetrics",
    "LayerReport",
    "SessionReport",
    "__version__",
]
