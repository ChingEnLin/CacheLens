"""Minimal OpenAI example. Requires: pip install cache-lens[openai]

OpenAI caches prompt prefixes automatically (no cache_control needed) once the
prefix exceeds ~1024 tokens. cache-lens reports the resulting cached_tokens.
"""

from openai import OpenAI

from cache_lens import wrap

client = wrap(OpenAI())

system = {"role": "system", "content": "You are a helpful assistant. " * 200}

for question in ["What is caching?", "Give an example.", "Why does it save money?"]:
    client.chat.completions.create(
        model="gpt-4o",
        max_tokens=128,
        messages=[system, {"role": "user", "content": question}],
    )

# Report prints automatically on process exit.
