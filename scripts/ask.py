#!/usr/bin/env python3
"""Ask a question with optional file context, streamed to stdout.

Usage:
    uv run scripts/ask.py "Summarize this code" --ctx src/main.py --ctx src/utils.py
    uv run scripts/ask.py "Explain the bug" --ctx error.log --model ollama/qwen2.5
"""

import argparse
import sys
from pathlib import Path

from pipy_ai import StreamOptions, ctx, stream, user


def main():
    parser = argparse.ArgumentParser(description="Ask an LLM with optional file context")
    parser.add_argument("prompt", help="User prompt")
    parser.add_argument(
        "--ctx",
        dest="ctx_files",
        action="append",
        default=[],
        metavar="FILE",
        help="File to include as context (repeatable)",
    )
    parser.add_argument("--system", metavar="FILE", help="File to use as system prompt")
    parser.add_argument("--model", default="ollama/llama3.1", help="Model (default: ollama/llama3.1)")
    parser.add_argument("--max-tokens", type=int, default=None, help="Max output tokens")
    args = parser.parse_args()

    # Read system prompt file
    system_prompt = None
    if args.system:
        p = Path(args.system)
        if not p.is_file():
            print(f"Error: {args.system} not found", file=sys.stderr)
            sys.exit(1)
        system_prompt = p.read_text(encoding="utf-8")

    # Read and concatenate context files
    parts = []
    for path_str in args.ctx_files:
        p = Path(path_str)
        if not p.is_file():
            print(f"Error: {path_str} not found", file=sys.stderr)
            sys.exit(1)
        content = p.read_text(encoding="utf-8")
        parts.append(f"--- {p.name} ---\n{content}")

    # Build user message: context files then prompt
    if parts:
        message = "\n\n".join(parts) + f"\n\n{args.prompt}"
    else:
        message = args.prompt

    options = StreamOptions(max_tokens=args.max_tokens) if args.max_tokens else None

    for event in stream(args.model, ctx(user(message), system=system_prompt), options):
        if event.type == "text_delta":
            print(event.delta, end="", flush=True)
        elif event.type == "error":
            print(f"\nError: {event.error.error_message}", file=sys.stderr)
            sys.exit(1)
    print()


if __name__ == "__main__":
    main()
