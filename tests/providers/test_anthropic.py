from conftest import load_responses

from cache_lens.providers import anthropic as anthropic_provider


def test_extract_creation_call():
    responses = load_responses("anthropic_responses.json")
    m = anthropic_provider.extract(responses[0], model="claude-sonnet-4-6", latency_ms=120)

    assert m.provider == "anthropic"
    assert m.cache_creation_tokens == 4800
    assert m.cache_read_tokens == 0
    assert m.cache_miss_tokens == 200
    assert m.input_tokens == 5000  # 200 miss + 4800 created
    assert m.output_tokens == 50


def test_extract_read_call():
    responses = load_responses("anthropic_responses.json")
    m = anthropic_provider.extract(responses[1], model="claude-sonnet-4-6", latency_ms=90)

    assert m.cache_read_tokens == 4800
    assert m.cache_miss_tokens == 350
    assert m.input_tokens == 5150
