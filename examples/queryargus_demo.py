"""End-to-end demo wrapping a QueryArgus Gemini client.

Run from a checkout where QueryArgus is importable, e.g.:
    pip install cache-lens[gemini]
    python examples/queryargus_demo.py --collection users

The only integration point is wrapping the GenerativeModel; QueryArgus runs
unchanged. See SPEC.md §9.4.
"""

import argparse

from cache_lens import CacheLens


def main() -> None:
    parser = argparse.ArgumentParser(description="cache-lens QueryArgus demo")
    parser.add_argument("--collection", default="users")
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--json", dest="json_export", default=None)
    parser.add_argument("--otel", action="store_true")
    args = parser.parse_args()

    import google.generativeai as genai

    model = genai.GenerativeModel(args.model)

    with CacheLens(model, json_export=args.json_export, otel=args.otel) as client:
        # Stand-in for the QueryArgus ReAct loop. Replace with:
        #   from queryargus.agent import ReActAgent
        #   ReActAgent(client).run(connection, args.collection)
        system = "You are QueryArgus, a Cosmos DB query agent.\n" + ("schema context " * 500)
        history = system
        for i in range(20):
            history += f"\nIteration {i}: tool result for {args.collection}"
            client.generate_content(history)


if __name__ == "__main__":
    main()
