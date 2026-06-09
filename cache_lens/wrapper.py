"""CacheLensClient — non-invasive interception of provider calls."""

from __future__ import annotations

import atexit
import time
from typing import Callable, List, Mapping, Optional, Union

from . import analyzer, pricing as pricing_mod, providers
from .models import CallCapture, SessionReport
from .outputs import json_export as json_output, otel as otel_output, terminal

# Method names per provider that produce a cacheable usage response.
_INTERCEPT = {
    "anthropic": {"create"},          # client.messages.create
    "gemini": {"generate_content"},   # model.generate_content
    "openai": {"create"},             # client.chat.completions.create / responses.create
}


class _Session:
    """Holds the in-memory call log for one wrapped client."""

    def __init__(self) -> None:
        self.captures: List[CallCapture] = []
        self.reported = False

    def record(self, capture: CallCapture) -> None:
        self.captures.append(capture)

    def build_report(self) -> SessionReport:
        return analyzer.analyze(self.captures)


class CacheLensClient:
    """Transparent proxy that records cache metrics on intercepted calls."""

    def __init__(self, client: object, provider: Optional[str], session: _Session, model: str):
        object.__setattr__(self, "_cl_client", client)
        object.__setattr__(self, "_cl_provider", provider)
        object.__setattr__(self, "_cl_session", session)
        object.__setattr__(self, "_cl_model", model)

    def __getattr__(self, name: str):
        target = getattr(object.__getattribute__(self, "_cl_client"), name)
        provider = object.__getattribute__(self, "_cl_provider")
        session = object.__getattribute__(self, "_cl_session")
        model = object.__getattribute__(self, "_cl_model")

        if callable(target) and provider and name in _INTERCEPT.get(provider, set()):
            client = object.__getattribute__(self, "_cl_client")
            return _wrap_call(target, provider, session, model, client)

        # Wrap nested attribute holders (e.g. client.messages) so their methods
        # are also intercepted.
        if _is_namespace(target):
            return CacheLensClient(target, provider, session, model)
        return target

    def __setattr__(self, name: str, value: object) -> None:
        setattr(object.__getattribute__(self, "_cl_client"), name, value)


def _wrap_call(
    func: Callable, provider: str, session: _Session, model: str, client: object
) -> Callable:
    extractor = providers.extractor_for(provider)

    def wrapped(*args, **kwargs):
        call_model = kwargs.get("model", model)
        # Capture the request prompt before the call (never break the caller).
        try:
            segments = extractor.capture(args, kwargs, model=call_model, client=client)
        except Exception:
            segments = []

        start = time.perf_counter()
        response = func(*args, **kwargs)
        latency_ms = int((time.perf_counter() - start) * 1000)

        try:
            metrics = extractor.extract(response, model=call_model, latency_ms=latency_ms)
            session.record(CallCapture(metrics=metrics, segments=segments))
        except Exception:
            # Never let instrumentation break the caller's request.
            pass
        return response

    return wrapped


def _is_namespace(obj: object) -> bool:
    module = getattr(type(obj), "__module__", "") or ""
    return (
        module.startswith("anthropic")
        or module.startswith("openai")
        or "genai" in module
        or "google" in module
    )


def wrap(
    client: object,
    *,
    json_export: Optional[str] = None,
    otel: bool = False,
    terminal_report: Optional[bool] = None,
    model: str = "",
    pricing: Optional[Union[str, Mapping]] = None,
) -> CacheLensClient:
    """Wrap a provider client. Report prints on process exit via atexit."""
    if pricing is not None:
        pricing_mod.load(pricing)
    provider = providers.detect_provider(client)
    model = model or _guess_model(client)
    session = _Session()
    wrapped = CacheLensClient(client, provider, session, model)

    atexit.register(
        _flush, session, json_export=json_export, otel=otel, terminal_report=terminal_report
    )
    return wrapped


class CacheLens:
    """Context manager establishing an explicit session boundary."""

    def __init__(
        self,
        client: object,
        *,
        json_export: Optional[str] = None,
        otel: bool = False,
        terminal_report: Optional[bool] = None,
        model: str = "",
        pricing: Optional[Union[str, Mapping]] = None,
    ):
        if pricing is not None:
            pricing_mod.load(pricing)
        self._provider = providers.detect_provider(client)
        self._model = model or _guess_model(client)
        self._session = _Session()
        self._wrapped = CacheLensClient(client, self._provider, self._session, self._model)
        self._json_export = json_export
        self._otel = otel
        self._terminal_report = terminal_report
        self.report: Optional[SessionReport] = None

    def __enter__(self) -> CacheLensClient:
        return self._wrapped

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.report = _flush(
            self._session,
            json_export=self._json_export,
            otel=self._otel,
            terminal_report=self._terminal_report,
        )
        return False


def _flush(
    session: _Session,
    *,
    json_export: Optional[str],
    otel: bool,
    terminal_report: Optional[bool],
) -> Optional[SessionReport]:
    if session.reported or not session.captures:
        return None
    session.reported = True

    report = session.build_report()

    import os

    show_terminal = terminal_report
    if show_terminal is None:
        show_terminal = os.environ.get("CACHE_LENS_TERMINAL", "1") != "0"
    if show_terminal:
        terminal.render(report)
    if json_export:
        json_output.export(report, json_export)
    if otel:
        otel_output.emit(report)

    return report


def _guess_model(client: object) -> str:
    for attr in ("model_name", "model", "_model_name"):
        value = getattr(client, attr, None)
        if isinstance(value, str):
            return value
    return ""
