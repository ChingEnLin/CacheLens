from types import SimpleNamespace

from cache_lens.providers import _anthropic, _gemini, _openai


def test_anthropic_capture_system_and_messages():
    segs = _anthropic.capture(
        (),
        {
            "system": "you are helpful",
            "messages": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": [{"type": "text", "text": "hi"}]},
            ],
        },
        model="claude-sonnet-4-6",
        client=object(),
    )
    assert [s.role for s in segs] == ["system", "user", "assistant"]
    assert segs[0].text == "you are helpful"
    assert segs[2].text == "hi"  # flattened from content blocks


def test_openai_capture_messages():
    segs = _openai.capture(
        (),
        {"messages": [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "q"},
        ]},
        model="gpt-4o",
        client=object(),
    )
    assert [s.role for s in segs] == ["system", "user"]


def test_gemini_capture_system_instruction_and_contents():
    model_obj = SimpleNamespace(_system_instruction="be terse")
    segs = _gemini.capture(
        ("just a string prompt",),
        {},
        model="gemini-2.5-flash",
        client=model_obj,
    )
    assert segs[0].role == "system"
    assert segs[0].text == "be terse"
    assert segs[1].text == "just a string prompt"


def test_gemini_capture_contents_list_of_dicts():
    segs = _gemini.capture(
        (),
        {"contents": [
            {"role": "user", "parts": [{"text": "hello"}]},
            {"role": "model", "parts": [{"text": "hi there"}]},
        ]},
        model="gemini-2.5-flash",
        client=SimpleNamespace(),
    )
    assert [s.role for s in segs] == ["user", "model"]
    assert segs[0].text == "hello"
