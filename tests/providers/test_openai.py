from types import SimpleNamespace

from conftest import load_responses

from cache_lens.providers import openai as openai_provider


def test_extract_chat_completions_no_cache():
    responses = load_responses("openai_responses.json")
    m = openai_provider.extract(responses[0], model="gpt-4o", latency_ms=150)

    assert m.provider == "openai"
    assert m.cache_read_tokens == 0
    assert m.cache_creation_tokens == 0
    assert m.input_tokens == 5000
    assert m.output_tokens == 50
    assert m.cache_miss_tokens == 5000


def test_extract_chat_completions_with_cache():
    responses = load_responses("openai_responses.json")
    m = openai_provider.extract(responses[1], model="gpt-4o", latency_ms=120)

    assert m.cache_read_tokens == 4800
    assert m.input_tokens == 5350
    assert m.cache_miss_tokens == 550


def test_extract_responses_api():
    """Responses API uses input_tokens / input_tokens_details.cached_tokens."""
    resp = SimpleNamespace(
        model="gpt-4.1",
        usage=SimpleNamespace(
            input_tokens=3000,
            output_tokens=40,
            input_tokens_details=SimpleNamespace(cached_tokens=2000),
        ),
    )
    m = openai_provider.extract(resp, model="gpt-4.1", latency_ms=100)

    assert m.input_tokens == 3000
    assert m.output_tokens == 40
    assert m.cache_read_tokens == 2000
    assert m.cache_miss_tokens == 1000
