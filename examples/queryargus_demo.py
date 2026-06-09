"""End-to-end demo wrapping a QueryArgus-style google-genai client.

Run:
    pip install cache-lens[gemini]
    GEMINI_API_KEY=... python examples/queryargus_demo.py --collection users

The only integration point is wrapping genai.Client; in QueryArgus itself
this is one line in GeminiClient.__init__:
    self._client = wrap(genai.Client(api_key=api_key))
"""

import argparse
import os

from cache_lens import CacheLens


def main() -> None:
    parser = argparse.ArgumentParser(description="cache-lens QueryArgus demo")
    parser.add_argument("--collection", default="users")
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--json", dest="json_export", default=None)
    parser.add_argument("--otel", action="store_true")
    args = parser.parse_args()

    from google import genai
    from google.genai import types as genai_types

    raw_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    with CacheLens(raw_client, json_export=args.json_export, otel=args.otel) as client:
        # Stand-in for the QueryArgus ReAct loop.
        system = "You are QueryArgus, a Cosmos DB query agent.\n" + ("schema context " * 500)
        config = genai_types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
        )
        history = ""
        for i in range(20):
            history += f"\nIteration {i}: tool result for {args.collection}"
            client.models.generate_content(
                model=args.model,
                contents=history,
                config=config,
            )


if __name__ == "__main__":
    main()
