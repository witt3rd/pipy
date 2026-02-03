"""Token estimation for compaction."""

import json
from dataclasses import dataclass
from typing import Any, Union

from pipy_ai import UserMessage, AssistantMessage, ToolResultMessage, Usage, Message


@dataclass
class ContextUsageEstimate:
    """Estimated context usage."""

    tokens: int
    """Total estimated tokens."""

    usage_tokens: int
    """Tokens from actual usage data."""

    trailing_tokens: int
    """Estimated tokens for messages after last usage."""

    last_usage_index: int | None
    """Index of message with last valid usage."""


def calculate_context_tokens(usage: Usage) -> int:
    """
    Calculate total context tokens from usage.

    Uses the native total_tokens field when available,
    falls back to computing from components.
    """
    if usage.total_tokens:
        return usage.total_tokens
    return (
        usage.input
        + usage.output
        + usage.cache_read
        + usage.cache_write
    )


def _get_attr(obj: Any, key: str, default: Any = None) -> Any:
    """Get attribute from dict or object."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def estimate_tokens(message: Any) -> int:
    """
    Estimate token count for a message using chars/4 heuristic.

    This is conservative (tends to overestimate tokens).
    Handles both dict-style messages and Pydantic models.
    """
    chars = 0
    role = _get_attr(message, "role", "")

    if role == "user":
        content = _get_attr(message, "content", "")
        if isinstance(content, str):
            chars = len(content)
        elif isinstance(content, list):
            for block in content:
                block_type = _get_attr(block, "type", "")
                if block_type == "text":
                    chars += len(_get_attr(block, "text", ""))
        return (chars + 3) // 4  # Ceiling division

    elif role == "assistant":
        content = _get_attr(message, "content", [])
        if isinstance(content, list):
            for block in content:
                block_type = _get_attr(block, "type", "")
                if block_type == "text":
                    chars += len(_get_attr(block, "text", ""))
                elif block_type == "thinking":
                    chars += len(_get_attr(block, "thinking", ""))
                elif block_type in ("toolCall", "tool_use"):
                    chars += len(_get_attr(block, "name", ""))
                    # Handle both 'arguments' (pipy) and 'input' (Anthropic)
                    args = _get_attr(block, "arguments") or _get_attr(block, "input", {})
                    chars += len(json.dumps(args))
        return (chars + 3) // 4

    elif role in ("tool", "toolResult"):
        content = _get_attr(message, "content", "")
        if isinstance(content, str):
            chars = len(content)
        elif isinstance(content, list):
            for block in content:
                block_type = _get_attr(block, "type", "")
                if block_type == "text":
                    chars += len(_get_attr(block, "text", ""))
                elif block_type == "image":
                    chars += 4800  # Estimate images as ~1200 tokens
        return (chars + 3) // 4

    # Custom message types
    if role == "bash_execution":
        chars = len(_get_attr(message, "command", ""))
        chars += len(_get_attr(message, "output", ""))
        return (chars + 3) // 4

    if role in ("branch_summary", "compaction_summary"):
        chars = len(_get_attr(message, "summary", ""))
        return (chars + 3) // 4

    if role == "custom":
        content = _get_attr(message, "content", "")
        if isinstance(content, str):
            chars = len(content)
        return (chars + 3) // 4

    return 0


def _get_assistant_usage(msg: Any) -> Usage | None:
    """Get usage from an assistant message if available."""
    role = _get_attr(msg, "role", "")
    if role != "assistant":
        return None

    # Skip aborted and error messages
    stop_reason = _get_attr(msg, "stop_reason", "")
    if stop_reason in ("aborted", "error"):
        return None

    usage = _get_attr(msg, "usage")
    return usage


def estimate_context_tokens(messages: list[Any]) -> ContextUsageEstimate:
    """
    Estimate context tokens from messages.

    Uses the last assistant message's usage when available.
    For messages after the last usage, estimates with chars/4.
    """
    # Find last assistant message with valid usage
    last_usage: Usage | None = None
    last_usage_index: int | None = None

    for i in range(len(messages) - 1, -1, -1):
        usage = _get_assistant_usage(messages[i])
        if usage:
            last_usage = usage
            last_usage_index = i
            break

    if last_usage is None:
        # No usage data - estimate everything
        estimated = sum(estimate_tokens(msg) for msg in messages)
        return ContextUsageEstimate(
            tokens=estimated,
            usage_tokens=0,
            trailing_tokens=estimated,
            last_usage_index=None,
        )

    usage_tokens = calculate_context_tokens(last_usage)

    # Estimate tokens for messages after last usage
    trailing_tokens = 0
    for i in range(last_usage_index + 1, len(messages)):
        trailing_tokens += estimate_tokens(messages[i])

    return ContextUsageEstimate(
        tokens=usage_tokens + trailing_tokens,
        usage_tokens=usage_tokens,
        trailing_tokens=trailing_tokens,
        last_usage_index=last_usage_index,
    )
