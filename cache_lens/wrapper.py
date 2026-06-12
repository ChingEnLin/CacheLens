"""CacheLensClient — non-invasive interception of provider calls."""

from __future__ import annotations

import atexit
import functools
import inspect
import sys
import time
from typing import Callable, List, Mapping, Optional, Union

from . import analyzer, pricing as pricing_mod, providers
from .models import CallCapture, PromptSegment, SessionReport

# Method names per provider that produce a cacheable usage response.
_INTERCEPT = {
    "anthropic": {"create"},          # client.messages.create
    "gemini": {"generate_content", "generate_content_async"},
    "openai": {"create"},             # client.chat.completions.create / responses.create
}

# Methods we can't instrument yet (streaming); calls are counted as skipped so
# the report can say why they're missing instead of silently under-reporting.
_SKIP_COUNT = {
    "anthropic": {"stream"},          # client.messages.stream
}


class _Session:
    """Holds the in-memory call log and per-session config for one wrapped client."""

    def __init__(
        self,
        registry: Optional[pricing_mod.Registry] = None,
        capture_content: bool = False,
    ) -> None:
        self.captures: List[CallCapture] = []
        self.reported = False
        self.skipped = 0
        self.registry = registry if registry is not None else pricing_mod.Registry()
        self.capture_content = capture_content

    def record(self, capture: CallCapture) -> None:
        self.captures.append(capture)

    def build_report(self) -> SessionReport:
        return analyzer.analyze(
            self.captures, registry=self.registry, skipped_calls=self.skipped
        )


class CacheLensClient:
    """Transparent proxy that records cache metrics on intercepted calls."""

    def __init__(self, client: object, provider: Optional[str], session: _Session, model: str):
        object.__setattr__(self, "_cl_client", client)
        object.__setattr__(self, "_cl_provider", provider)
        object.__setattr__(self, "_cl_session", session)
        object.__setattr__(self, "_cl_model", model)

    def unwrap(self) -> object:
        """Return the original, unwrapped provider client.

        Use this where identity matters — e.g. ``isinstance`` checks, which are
        False on the proxy itself.
        """
        return object.__getattribute__(self, "_cl_client")

    def __getattr__(self, name: str):
        target = getattr(object.__getattribute__(self, "_cl_client"), name)
        provider = object.__getattribute__(self, "_cl_provider")
        session = object.__getattribute__(self, "_cl_session")
        model = object.__getattribute__(self, "_cl_model")

        if callable(target) and provider:
            if name in _INTERCEPT.get(provider, set()):
                client = object.__getattribute__(self, "_cl_client")
                return _wrap_call(target, provider, session, model, client)
            if name in _SKIP_COUNT.get(provider, set()):
                return _count_skip(target, session)

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

    def _capture(args: tuple, kwargs: dict, call_model: str) -> List[PromptSegment]:
        # Capture the request prompt before the call (never break the caller).
        try:
            segments = extractor.capture(args, kwargs, model=call_model, client=client)
        except Exception:
            return []
        if not session.capture_content:
            # Default: keep only role + hash + length, never the prompt text,
            # so memory stays bounded and no content lingers in the heap.
            segments = [s.without_text() for s in segments]
        return segments

    def _record(
        response: object, call_model: str, segments: List[PromptSegment], latency_ms: int
    ) -> None:
        try:
            metrics = extractor.extract(response, model=call_model, latency_ms=latency_ms)
            session.record(CallCapture(metrics=metrics, segments=segments))
        except Exception:
            # Never let instrumentation break the caller's request.
            pass

    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapped(*args, **kwargs):
            if kwargs.get("stream"):
                session.skipped += 1
                return await func(*args, **kwargs)
            call_model = kwargs.get("model", model)
            segments = _capture(args, kwargs, call_model)
            start = time.perf_counter()
            response = await func(*args, **kwargs)
            latency_ms = int((time.perf_counter() - start) * 1000)
            _record(response, call_model, segments, latency_ms)
            return response

        return async_wrapped

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        if kwargs.get("stream"):
            # Streaming responses carry usage on terminal events we don't
            # consume; count the call so the report can say it's missing.
            session.skipped += 1
            return func(*args, **kwargs)
        call_model = kwargs.get("model", model)
        segments = _capture(args, kwargs, call_model)
        start = time.perf_counter()
        response = func(*args, **kwargs)
        latency_ms = int((time.perf_counter() - start) * 1000)
        if inspect.iscoroutine(response):
            # Async method that slipped past iscoroutinefunction (e.g. a
            # wrapped/partial coroutine factory) — pass it through untouched.
            session.skipped += 1
            return response
        _record(response, call_model, segments, latency_ms)
        return response

    return wrapped


def _count_skip(func: Callable, session: _Session) -> Callable:
    @functools.wraps(func)
    def counted(*args, **kwargs):
        session.skipped += 1
        return func(*args, **kwargs)

    return counted


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
    capture_content: bool = False,
) -> CacheLensClient:
    """Wrap a provider client. Report prints on process exit via atexit."""
    registry = pricing_mod.Registry()
    if pricing is not None:
        registry.load(pricing)
    provider = providers.detect_provider(client)
    model = model or _guess_model(client)
    session = _Session(registry=registry, capture_content=capture_content)
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
        capture_content: bool = False,
    ):
        registry = pricing_mod.Registry()
        if pricing is not None:
            registry.load(pricing)
        self._provider = providers.detect_provider(client)
        self._model = model or _guess_model(client)
        self._session = _Session(registry=registry, capture_content=capture_content)
        self._wrapped = CacheLensClient(client, self._provider, self._session, self._model)
        self._json_export = json_export
        self._otel = otel
        self._terminal_report = terminal_report
        self.report: Optional[SessionReport] = None

    def __enter__(self) -> CacheLensClient:
        return self._wrapped

    def __exit__(self, exc_type, exc, tb) -> None:
        self.report = _flush(
            self._session,
            json_export=self._json_export,
            otel=self._otel,
            terminal_report=self._terminal_report,
        )


def _flush(
    session: _Session,
    *,
    json_export: Optional[str],
    otel: bool,
    terminal_report: Optional[bool],
) -> Optional[SessionReport]:
    if session.reported or (not session.captures and not session.skipped):
        return None
    session.reported = True

    report = session.build_report()

    import os

    from .outputs import json_export as json_output, otel as otel_output, terminal

    show_terminal = terminal_report
    if show_terminal is None:
        show_terminal = os.environ.get("CACHE_LENS_TERMINAL", "1") != "0"
    if show_terminal:
        _emit("terminal", terminal.render, report)
    if json_export:
        _emit("json", json_output.export, report, json_export)
    if otel:
        _emit("otel", otel_output.emit, report)

    return report


def _emit(sink: str, fn: Callable, *args: object) -> None:
    """Run one output sink; a sink failure must never reach the caller."""
    try:
        fn(*args)
    except Exception as exc:
        sys.stderr.write(f"cache-lens: {sink} output failed ({type(exc).__name__}: {exc})\n")


def _guess_model(client: object) -> str:
    for attr in ("model_name", "model", "_model_name"):
        value = getattr(client, attr, None)
        if isinstance(value, str):
            return value
    return ""
