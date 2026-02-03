"""CLI for pipy-coding-agent."""

import argparse
import asyncio
import sys
from pathlib import Path

from .agent import AgentSession, AgentSessionConfig


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="pipy",
        description="AI coding assistant",
    )

    # Model options
    parser.add_argument(
        "-m", "--model",
        default="sonnet",
        help="Model to use (default: sonnet)",
    )
    parser.add_argument(
        "--thinking",
        choices=["none", "low", "medium", "high"],
        default="medium",
        help="Thinking level (default: medium)",
    )

    # Session options
    parser.add_argument(
        "--no-session",
        action="store_true",
        help="Don't persist session",
    )
    parser.add_argument(
        "--cwd",
        type=str,
        help="Working directory",
    )

    # Prompt options
    parser.add_argument(
        "-p", "--prompt",
        type=str,
        help="Run with a single prompt and exit",
    )
    parser.add_argument(
        "--system",
        type=str,
        help="Custom system prompt",
    )

    # Output options
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version",
    )

    return parser


def print_version() -> None:
    """Print version information."""
    from . import __version__
    print(f"pipy-coding-agent v{__version__}")


async def run_interactive_async(session: AgentSession) -> None:
    """Run interactive mode (async)."""
    print(f"pipy-coding-agent (model: {session.model.model_id})")
    print("Type 'quit' or 'exit' to exit, '/help' for commands")
    print()

    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        # Commands
        if user_input.lower() in ("quit", "exit", "/quit", "/exit"):
            print("Goodbye!")
            break

        if user_input.lower() == "/help":
            print_help()
            continue

        if user_input.lower() == "/clear":
            session.clear()
            print("Conversation cleared.")
            continue

        if user_input.lower().startswith("/model "):
            model = user_input[7:].strip()
            session.set_model(model)
            print(f"Model changed to: {session.model.model_id}")
            continue

        if user_input.lower().startswith("/thinking "):
            level = user_input[10:].strip()
            session.set_thinking_level(level)
            print(f"Thinking level: {level}")
            continue

        # Send prompt
        try:
            result = await session.aprompt(user_input)
            print()
            print(result.response)
            print()
        except Exception as e:
            print(f"Error: {e}")


def run_interactive(session: AgentSession) -> None:
    """Run interactive mode."""
    asyncio.run(run_interactive_async(session))


def print_help() -> None:
    """Print help message."""
    print("""
Commands:
  /help              Show this help
  /clear             Clear conversation history
  /model <name>      Change model (e.g., /model opus)
  /thinking <level>  Set thinking level (none, low, medium, high)
  /quit, /exit       Exit

Aliases:
  sonnet   -> claude-sonnet-4
  opus     -> claude-3-opus
  haiku    -> claude-3.5-haiku
  gpt4o    -> gpt-4o
  gemini   -> gemini-2.0-flash
""")


async def run_single_prompt_async(session: AgentSession, prompt: str, verbose: bool = False) -> int:
    """Run a single prompt and exit (async)."""
    try:
        if verbose:
            print(f"Model: {session.model.model_id}")
            print(f"Prompt: {prompt}")
            print()

        result = await session.aprompt(prompt)
        print(result.response)

        if verbose:
            print()
            print(f"Tool calls: {result.tool_calls}")
            print(f"Tokens: {result.tokens_used}")

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def run_single_prompt(session: AgentSession, prompt: str, verbose: bool = False) -> int:
    """Run a single prompt and exit."""
    return asyncio.run(run_single_prompt_async(session, prompt, verbose))


def main(args: list[str] | None = None) -> int:
    """Main entry point."""
    parser = create_parser()
    parsed = parser.parse_args(args)

    if parsed.version:
        print_version()
        return 0

    # Create session config
    config = AgentSessionConfig(
        model=parsed.model,
        thinking_level=parsed.thinking,
        cwd=parsed.cwd,
        system_prompt=parsed.system,
        persist_session=not parsed.no_session,
    )

    # Create session
    try:
        session = AgentSession(config)
    except Exception as e:
        print(f"Failed to create session: {e}", file=sys.stderr)
        return 1

    # Run mode
    if parsed.prompt:
        return run_single_prompt(session, parsed.prompt, parsed.verbose)
    else:
        run_interactive(session)
        return 0


if __name__ == "__main__":
    sys.exit(main())
