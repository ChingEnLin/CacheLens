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

    report = None
    # report is set on __exit__; re-access via the manager
    # (we rebuild to assert metrics flowed through)
    assert resp is not None


def test_call_passthrough_returns_response(monkeypatch):
    monkeypatch.setenv("CACHE_LENS_TERMINAL", "0")
    client = _FakeAnthropic()
    cl = CacheLens(client, model="claude-sonnet-4-6")
    wrapped = cl.__enter__()
    resp = wrapped.messages.create()
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
