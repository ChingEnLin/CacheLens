import asyncio
from types import SimpleNamespace

from cache_lens.wrapper import CacheLens


class _FakeMessages:
    """Mimics anthropic.Anthropic().messages with a create() method."""

    __module__ = "anthropic.resources.messages"

    def create(self, **kwargs):
        return SimpleNamespace(
            model="claude-sonnet-4-6",
            usage=SimpleNamespace(
                input_tokens=200,
                output_tokens=50,
                cache_creation_input_tokens=4800,
                cache_read_input_tokens=0,
            ),
        )


class _FakeAnthropic:
    __module__ = "anthropic"

    def __init__(self):
        self.messages = _FakeMessages()


def test_context_manager_records_and_reports(monkeypatch):
    monkeypatch.setenv("CACHE_LENS_TERMINAL", "0")
    client = _FakeAnthropic()

    with CacheLens(client, model="claude-sonnet-4-6") as wrapped:
        resp = wrapped.messages.create(messages=[{"role": "user", "content": "hi"}])
        assert resp.usage.output_tokens == 50

    assert resp is not None


def test_call_passthrough_returns_response(monkeypatch):
    monkeypatch.setenv("CACHE_LENS_TERMINAL", "0")
    client = _FakeAnthropic()
    cl = CacheLens(client, model="claude-sonnet-4-6")
    wrapped = cl.__enter__()
    wrapped.messages.create()
    cl.__exit__(None, None, None)

    assert cl.report is not None
    assert cl.report.total_calls == 1
    assert cl.report.total_cached_tokens == 0
    assert cl.report.provider == "anthropic"


class _FakeCompletions:
    __module__ = "openai.resources.chat.completions"

    def create(self, **kwargs):
        return SimpleNamespace(
            model="gpt-4o",
            usage=SimpleNamespace(
                prompt_tokens=5350,
                completion_tokens=70,
                prompt_tokens_details=SimpleNamespace(cached_tokens=4800),
            ),
        )


class _FakeChat:
    __module__ = "openai.resources.chat"

    def __init__(self):
        self.completions = _FakeCompletions()


class _FakeOpenAI:
    __module__ = "openai"

    def __init__(self):
        self.chat = _FakeChat()


def test_openai_nested_namespace_interception(monkeypatch):
    monkeypatch.setenv("CACHE_LENS_TERMINAL", "0")
    cl = CacheLens(_FakeOpenAI(), model="gpt-4o")
    wrapped = cl.__enter__()
    resp = wrapped.chat.completions.create(model="gpt-4o")
    cl.__exit__(None, None, None)

    assert resp.usage.completion_tokens == 70
    assert cl.report is not None
    assert cl.report.provider == "openai"
    assert cl.report.total_calls == 1
    assert cl.report.total_cached_tokens == 4800


class _FakeAsyncMessages:
    __module__ = "anthropic.resources.messages"

    async def create(self, **kwargs):
        return SimpleNamespace(
            model="claude-sonnet-4-6",
            usage=SimpleNamespace(
                input_tokens=100,
                output_tokens=10,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=400,
            ),
        )


class _FakeAsyncAnthropic:
    __module__ = "anthropic"

    def __init__(self):
        self.messages = _FakeAsyncMessages()


def test_async_client_interception(monkeypatch):
    monkeypatch.setenv("CACHE_LENS_TERMINAL", "0")
    cl = CacheLens(_FakeAsyncAnthropic(), model="claude-sonnet-4-6")
    wrapped = cl.__enter__()
    resp = asyncio.run(wrapped.messages.create(messages=[{"role": "user", "content": "hi"}]))
    cl.__exit__(None, None, None)

    assert resp.usage.output_tokens == 10
    assert cl.report is not None
    assert cl.report.total_calls == 1
    assert cl.report.total_cached_tokens == 400


def test_stream_kwarg_counted_as_skipped(monkeypatch):
    monkeypatch.setenv("CACHE_LENS_TERMINAL", "0")
    cl = CacheLens(_FakeAnthropic(), model="claude-sonnet-4-6")
    wrapped = cl.__enter__()
    wrapped.messages.create(stream=True, messages=[{"role": "user", "content": "hi"}])
    cl.__exit__(None, None, None)

    assert cl.report is not None
    assert cl.report.total_calls == 0
    assert cl.report.skipped_calls == 1
    assert any("not instrumented" in t for t in cl.report.tips)


class _FakeStreamingMessages(_FakeMessages):
    __module__ = "anthropic.resources.messages"

    def stream(self, **kwargs):
        return "stream-handle"


class _FakeStreamingAnthropic:
    __module__ = "anthropic"

    def __init__(self):
        self.messages = _FakeStreamingMessages()


def test_messages_stream_counted_as_skipped(monkeypatch):
    monkeypatch.setenv("CACHE_LENS_TERMINAL", "0")
    cl = CacheLens(_FakeStreamingAnthropic(), model="claude-sonnet-4-6")
    wrapped = cl.__enter__()
    handle = wrapped.messages.stream(messages=[{"role": "user", "content": "hi"}])
    cl.__exit__(None, None, None)

    assert handle == "stream-handle"
    assert cl.report is not None
    assert cl.report.skipped_calls == 1


def test_capture_is_content_free_by_default(monkeypatch):
    monkeypatch.setenv("CACHE_LENS_TERMINAL", "0")
    cl = CacheLens(_FakeAnthropic(), model="claude-sonnet-4-6")
    wrapped = cl.__enter__()
    wrapped.messages.create(
        system="sys prompt", messages=[{"role": "user", "content": "secret data"}]
    )
    segments = cl._session.captures[0].segments
    cl.__exit__(None, None, None)

    user_seg = segments[1]
    assert user_seg.text == ""
    assert user_seg.length == len("secret data")
    assert user_seg.text_hash


def test_capture_content_opt_in(monkeypatch):
    monkeypatch.setenv("CACHE_LENS_TERMINAL", "0")
    cl = CacheLens(_FakeAnthropic(), model="claude-sonnet-4-6", capture_content=True)
    wrapped = cl.__enter__()
    wrapped.messages.create(messages=[{"role": "user", "content": "secret data"}])
    segments = cl._session.captures[0].segments
    cl.__exit__(None, None, None)

    assert segments[0].text == "secret data"


def test_unwrap_returns_original_client(monkeypatch):
    monkeypatch.setenv("CACHE_LENS_TERMINAL", "0")
    client = _FakeAnthropic()
    cl = CacheLens(client, model="claude-sonnet-4-6")
    assert cl.__enter__().unwrap() is client
    cl.__exit__(None, None, None)


def test_sink_failure_never_reaches_caller(monkeypatch, tmp_path):
    monkeypatch.setenv("CACHE_LENS_TERMINAL", "1")
    from cache_lens.outputs import terminal

    def boom(report):
        raise RuntimeError("sink exploded")

    monkeypatch.setattr(terminal, "render", boom)

    out = tmp_path / "report.json"
    cl = CacheLens(_FakeAnthropic(), model="claude-sonnet-4-6", json_export=str(out))
    wrapped = cl.__enter__()
    wrapped.messages.create(messages=[{"role": "user", "content": "hi"}])
    cl.__exit__(None, None, None)  # must not raise despite terminal sink failing

    assert cl.report is not None
    assert out.exists()  # remaining sinks still ran


def test_pricing_override_is_session_scoped(monkeypatch):
    monkeypatch.setenv("CACHE_LENS_TERMINAL", "0")
    from cache_lens import pricing

    override = {
        "anthropic": {
            "claude-sonnet-4-6": {
                "input": 300.0, "output": 15.0, "cache_write": 375.0, "cache_read": 30.0,
            }
        }
    }
    cl = CacheLens(_FakeAnthropic(), model="claude-sonnet-4-6", pricing=override)
    wrapped = cl.__enter__()
    wrapped.messages.create()
    cl.__exit__(None, None, None)

    base = CacheLens(_FakeAnthropic(), model="claude-sonnet-4-6")
    w2 = base.__enter__()
    w2.messages.create()
    base.__exit__(None, None, None)

    # 100x input rate in the overridden session only.
    assert cl.report.cold_cost_usd > base.report.cold_cost_usd * 50
    # The module-level registry is untouched.
    assert pricing.get_pricing("anthropic", "claude-sonnet-4-6")["input"] == 3.00
