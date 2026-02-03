"""Summarization for compaction."""

from typing import Any


def _get_attr(obj: Any, key: str, default: Any = None) -> Any:
    """Get attribute from dict or object."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


SUMMARIZATION_SYSTEM_PROMPT = """You are a context summarization assistant. Your task is to read a conversation between a user and an AI coding assistant, then produce a structured summary following the exact format specified.

Do NOT continue the conversation. Do NOT respond to any questions in the conversation. ONLY output the structured summary."""


SUMMARIZATION_PROMPT = """The messages above are a conversation to summarize. Create a structured context checkpoint summary that another LLM will use to continue the work.

Use this EXACT format:

## Goal
[What is the user trying to accomplish? Can be multiple items if the session covers different tasks.]

## Constraints & Preferences
- [Any constraints, preferences, or requirements mentioned by user]
- [Or "(none)" if none were mentioned]

## Progress
### Done
- [x] [Completed tasks/changes]

### In Progress
- [ ] [Current work]

### Blocked
- [Issues preventing progress, if any]

## Key Decisions
- **[Decision]**: [Brief rationale]

## Next Steps
1. [Ordered list of what should happen next]

## Critical Context
- [Any data, examples, or references needed to continue]
- [Or "(none)" if not applicable]

Keep each section concise. Preserve exact file paths, function names, and error messages."""


UPDATE_SUMMARIZATION_PROMPT = """The messages above are NEW conversation messages to incorporate into the existing summary provided in <previous-summary> tags.

Update the existing structured summary with new information. RULES:
- PRESERVE all existing information from the previous summary
- ADD new progress, decisions, and context from the new messages
- UPDATE the Progress section: move items from "In Progress" to "Done" when completed
- UPDATE "Next Steps" based on what was accomplished
- PRESERVE exact file paths, function names, and error messages
- If something is no longer relevant, you may remove it

Use this EXACT format:

## Goal
[Preserve existing goals, add new ones if the task expanded]

## Constraints & Preferences
- [Preserve existing, add new ones discovered]

## Progress
### Done
- [x] [Include previously done items AND newly completed items]

### In Progress
- [ ] [Current work - update based on progress]

### Blocked
- [Current blockers - remove if resolved]

## Key Decisions
- **[Decision]**: [Brief rationale] (preserve all previous, add new)

## Next Steps
1. [Update based on current state]

## Critical Context
- [Preserve important context, add new if needed]

Keep each section concise. Preserve exact file paths, function names, and error messages."""


TURN_PREFIX_SUMMARIZATION_PROMPT = """This is the PREFIX of a turn that was too large to keep. The SUFFIX (recent work) is retained.

Summarize the prefix to provide context for the retained suffix:

## Original Request
[What did the user ask for in this turn?]

## Early Progress
- [Key decisions and work done in the prefix]

## Context for Suffix
- [Information needed to understand the retained recent work]

Be concise. Focus on what's needed to understand the kept suffix."""


def serialize_conversation(messages: list[Any]) -> str:
    """
    Serialize messages to text for summarization.

    This prevents the model from treating it as a conversation to continue.
    Handles both dict-style and Pydantic messages.
    """
    parts: list[str] = []

    for msg in messages:
        role = _get_attr(msg, "role", "")

        if role == "user":
            content = _get_attr(msg, "content", "")
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                text_parts = []
                for block in content:
                    block_type = _get_attr(block, "type", "")
                    if block_type == "text":
                        text_parts.append(_get_attr(block, "text", ""))
                text = "".join(text_parts)
            else:
                text = str(content)
            if text:
                parts.append(f"[User]: {text}")

        elif role == "assistant":
            text_parts: list[str] = []
            thinking_parts: list[str] = []
            tool_calls: list[str] = []

            content = _get_attr(msg, "content", [])
            if isinstance(content, list):
                for block in content:
                    block_type = _get_attr(block, "type", "")
                    if block_type == "text":
                        text_parts.append(_get_attr(block, "text", ""))
                    elif block_type == "thinking":
                        thinking_parts.append(_get_attr(block, "thinking", ""))
                    elif block_type in ("toolCall", "tool_use"):
                        name = _get_attr(block, "name", "")
                        args = _get_attr(block, "arguments") or _get_attr(block, "input", {})
                        args_str = ", ".join(
                            f"{k}={repr(v)}" for k, v in args.items()
                        )
                        tool_calls.append(f"{name}({args_str})")

            if thinking_parts:
                parts.append(f"[Assistant thinking]: {chr(10).join(thinking_parts)}")
            if text_parts:
                parts.append(f"[Assistant]: {chr(10).join(text_parts)}")
            if tool_calls:
                parts.append(f"[Assistant tool calls]: {'; '.join(tool_calls)}")

        elif role in ("tool", "toolResult"):
            content = _get_attr(msg, "content", "")
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                text_parts = []
                for block in content:
                    block_type = _get_attr(block, "type", "")
                    if block_type == "text":
                        text_parts.append(_get_attr(block, "text", ""))
                text = "".join(text_parts)
            else:
                text = str(content)
            if text:
                parts.append(f"[Tool result]: {text}")

    return "\n\n".join(parts)


async def generate_summary(
    messages: list[Any],
    model: str,
    reserve_tokens: int,
    api_key: str | None = None,
    custom_instructions: str | None = None,
    previous_summary: str | None = None,
) -> str:
    """
    Generate a summary of the conversation using the LLM.

    If previous_summary is provided, uses the update prompt to merge.

    Args:
        messages: Messages to summarize
        model: Model identifier (e.g., "anthropic/claude-3-5-sonnet")
        reserve_tokens: Token budget for summary
        api_key: API key (optional, uses env var if not provided)
        custom_instructions: Additional focus for the summary
        previous_summary: Previous compaction summary for iterative update

    Returns:
        Generated summary text
    """
    from pipy_ai import UserMessage, complete

    max_tokens = int(0.8 * reserve_tokens)

    # Choose prompt based on whether we have a previous summary
    base_prompt = UPDATE_SUMMARIZATION_PROMPT if previous_summary else SUMMARIZATION_PROMPT
    if custom_instructions:
        base_prompt = f"{base_prompt}\n\nAdditional focus: {custom_instructions}"

    # Serialize conversation
    conversation_text = serialize_conversation(messages)

    # Build prompt
    prompt_text = f"<conversation>\n{conversation_text}\n</conversation>\n\n"
    if previous_summary:
        prompt_text += f"<previous-summary>\n{previous_summary}\n</previous-summary>\n\n"
    prompt_text += base_prompt

    # Create summarization request
    summarization_messages = [
        UserMessage(role="user", content=prompt_text),
    ]

    # Call LLM
    response = complete(
        model=model,
        messages=summarization_messages,
        system=SUMMARIZATION_SYSTEM_PROMPT,
        max_tokens=max_tokens,
    )

    if response.stop_reason == "error":
        error_msg = _get_attr(response, "error_message", "Unknown error")
        raise RuntimeError(f"Summarization failed: {error_msg}")

    # Extract text content
    text_content = []
    for block in response.content:
        block_type = _get_attr(block, "type", "")
        if block_type == "text":
            text_content.append(_get_attr(block, "text", ""))

    return "\n".join(text_content)


async def generate_turn_prefix_summary(
    messages: list[Any],
    model: str,
    reserve_tokens: int,
    api_key: str | None = None,
) -> str:
    """
    Generate a summary for a turn prefix (when splitting a turn).

    Args:
        messages: Turn prefix messages to summarize
        model: Model identifier
        reserve_tokens: Token budget
        api_key: API key

    Returns:
        Generated summary text
    """
    from pipy_ai import UserMessage, complete

    max_tokens = int(0.5 * reserve_tokens)

    conversation_text = serialize_conversation(messages)
    prompt_text = f"<conversation>\n{conversation_text}\n</conversation>\n\n{TURN_PREFIX_SUMMARIZATION_PROMPT}"

    summarization_messages = [
        UserMessage(role="user", content=prompt_text),
    ]

    response = complete(
        model=model,
        messages=summarization_messages,
        system=SUMMARIZATION_SYSTEM_PROMPT,
        max_tokens=max_tokens,
    )

    if response.stop_reason == "error":
        error_msg = _get_attr(response, "error_message", "Unknown error")
        raise RuntimeError(f"Turn prefix summarization failed: {error_msg}")

    text_content = []
    for block in response.content:
        block_type = _get_attr(block, "type", "")
        if block_type == "text":
            text_content.append(_get_attr(block, "text", ""))

    return "\n".join(text_content)
