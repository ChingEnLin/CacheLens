"""Minimal Anthropic example. Requires: pip install cache-lens[anthropic]"""

import anthropic

from cache_lens import wrap

client = wrap(anthropic.Anthropic())

system = [
    {
        "type": "text",
        "text": "You are a helpful assistant. " * 200,  # large enough to cache
        "cache_control": {"type": "ephemeral"},
    }
]

for question in ["What is caching?", "Give an example.", "Why does it save money?"]:
    client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=128,
        system=system,
        messages=[{"role": "user", "content": question}],
    )

# Report prints automatically on process exit.
