"""Unified API - sync-first with async variants."""

import time
from collections.abc import AsyncIterator, Iterator

from .provider import LiteLLMProvider
from .stream import AssistantMessageEvent
from .types import (
    AssistantMessage,
    Context,
    SimpleStreamOptions,
    StreamOptions,
    ThinkingLevel,
    UserMessage,
)

# Default provider singleton
_provider: LiteLLMProvider | None = None


def _get_provider() -> LiteLLMProvider:
    global _provider
    if _provider is None:
        _provider = LiteLLMProvider()
    return _provider


# === Completion (sync-first) ===


def complete(
    model: str,
    context: Context,
    options: StreamOptions | None = None,
) -> AssistantMessage:
    """Complete a request (sync, blocking).

    Args:
        model: Model identifier (e.g., "anthropic/claude-sonnet-4-5")
        context: System prompt, messages, and optional tools
        options: Temperature, max_tokens, cache settings, etc.

    Returns:
        AssistantMessage with response text, usage, etc.

    Example:
        from pipy_ai import complete, Context, UserMessage

        context = Context(
            system_prompt="You are a helpful assistant.",
            messages=[UserMessage(content="Hello!")]
        )

        result = complete("anthropic/claude-sonnet-4-5", context)
        print(result.text)
    """
    return _get_provider().complete(model, context, options)


async def acomplete(
    model: str,
    context: Context,
    options: StreamOptions | None = None,
) -> AssistantMessage:
    """Complete a request (async variant).

    Example:
        result = await acomplete("anthropic/claude-sonnet-4-5", context)
        print(result.text)
    """
    return await _get_provider().acomplete(model, context, options)


# === Streaming (sync-first) ===


def stream(
    model: str,
    context: Context,
    options: StreamOptions | None = None,
) -> Iterator[AssistantMessageEvent]:
    """Stream a response (sync, blocking iterator).

    Example:
        from pipy_ai import stream, Context, UserMessage

        context = Context(messages=[UserMessage(content="Write a poem.")])

        for event in stream("anthropic/claude-sonnet-4-5", context):
            if event.type == "text_delta":
                print(event.delta, end="", flush=True)
        print()  # newline at end
    """
    return _get_provider().stream(model, context, options)


async def astream(
    model: str,
    context: Context,
    options: StreamOptions | None = None,
) -> AsyncIterator[AssistantMessageEvent]:
    """Stream a response (async variant).

    Example:
        async for event in astream("anthropic/claude-sonnet-4-5", context):
            if event.type == "text_delta":
                print(event.delta, end="", flush=True)
    """
    async for event in _get_provider().astream(model, context, options):
        yield event


# === Simple variants (with reasoning) ===


def complete_simple(
    model: str,
    context: Context,
    options: SimpleStreamOptions | None = None,
) -> AssistantMessage:
    """Complete with reasoning support (sync).

    Example:
        from pipy_ai import complete_simple, SimpleStreamOptions, ThinkingLevel

        options = SimpleStreamOptions(reasoning=ThinkingLevel.HIGH)
        result = complete_simple("anthropic/claude-sonnet-4-5", context, options)
        print(result.thinking_text)  # The reasoning
        print(result.text)           # The answer
    """
    return _get_provider().complete_simple(model, context, options)


async def acomplete_simple(
    model: str,
    context: Context,
    options: SimpleStreamOptions | None = None,
) -> AssistantMessage:
    """Complete with reasoning support (async)."""
    return await _get_provider().acomplete_simple(model, context, options)


def stream_simple(
    model: str,
    context: Context,
    options: SimpleStreamOptions | None = None,
) -> Iterator[AssistantMessageEvent]:
    """Stream with reasoning support (sync).

    Example:
        options = SimpleStreamOptions(reasoning=ThinkingLevel.HIGH)
        for event in stream_simple(model, context, options):
            match event.type:
                case "thinking_delta":
                    print(f"[thinking] {event.delta}")
                case "text_delta":
                    print(event.delta, end="")
    """
    return _get_provider().stream_simple(model, context, options)


async def astream_simple(
    model: str,
    context: Context,
    options: SimpleStreamOptions | None = None,
) -> AsyncIterator[AssistantMessageEvent]:
    """Stream with reasoning support (async)."""
    async for event in _get_provider().astream_simple(model, context, options):
        yield event


# === Convenience Functions ===


def quick(
    prompt: str,
    model: str = "anthropic/claude-sonnet-4-5",
    system: str | None = None,
    temperature: float | None = None,
    max_tokens: int = 4096,
    reasoning: ThinkingLevel | None = None,
) -> AssistantMessage:
    """Quick one-liner completion.

    Example:
        from pipy_ai import quick

        result = quick("What is 2+2?")
        print(result.text)  # "4"

        # With reasoning
        result = quick("Solve step by step: 127 * 843", reasoning=ThinkingLevel.HIGH)
        print(result.thinking_text)
        print(result.text)
    """
    context = Context(
        system_prompt=system,
        messages=[UserMessage(content=prompt, timestamp=int(time.time() * 1000))],
    )
    options = SimpleStreamOptions(
        temperature=temperature,
        max_tokens=max_tokens,
        reasoning=reasoning,
    )
    return complete_simple(model, context, options)


# === Context Builders ===


def user(content: str) -> UserMessage:
    """Create a user message.

    Example:
        from pipy_ai import Context, user, complete

        ctx = Context(messages=[user("What's the weather?")])
        result = complete("anthropic/claude-sonnet-4-5", ctx)
    """
    return UserMessage(content=content, timestamp=int(time.time() * 1000))


def ctx(
    *messages: UserMessage | AssistantMessage,
    system: str | None = None,
) -> Context:
    """Build a context from messages.

    Example:
        from pipy_ai import ctx, user, complete

        result = complete("anthropic/claude-sonnet-4-5", ctx(
            user("Hello!"),
            system="You are helpful."
        ))
    """
    return Context(
        system_prompt=system,
        messages=list(messages),
    )
