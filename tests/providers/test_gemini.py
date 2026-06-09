from conftest import load_responses

from cache_lens.providers import gemini as gemini_provider


def test_extract_no_cache():
    responses = load_responses("gemini_responses.json")
    m = gemini_provider.extract(responses[0], model="gemini-2.5-flash", latency_ms=200)

    assert m.provider == "gemini"
    assert m.cache_read_tokens == 0
    assert m.cache_creation_tokens == 0
    assert m.output_tokens == 50
    assert m.input_tokens == 5000  # total 5050 - 50 output
    assert m.cache_miss_tokens == 5000


def test_extract_with_cache():
    responses = load_responses("gemini_responses.json")
    m = gemini_provider.extract(responses[1], model="gemini-2.5-flash", latency_ms=180)

    assert m.cache_read_tokens == 4800
    assert m.input_tokens == 5330  # 5400 - 70
    assert m.cache_miss_tokens == 530
