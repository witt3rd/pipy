"""Session context building from entries.

Handles walking the session tree from leaf to root, applying compaction
summaries, and building the message list for LLM context.
"""

from dataclasses import dataclass, field
from typing import Any

from pipy_agent import AgentMessage, UserMessage, TextContent

from .entries import (
    BRANCH_SUMMARY_PREFIX,
    BRANCH_SUMMARY_SUFFIX,
    COMPACTION_SUMMARY_PREFIX,
    COMPACTION_SUMMARY_SUFFIX,
    CompactionEntry,
    SessionEntry,
    SessionMessageEntry,
)


@dataclass
class SessionContext:
    """Context for LLM from session entries."""

    messages: list[AgentMessage] = field(default_factory=list)
    thinking_level: str = "off"
    model: dict[str, str] | None = None  # {"provider": ..., "modelId": ...}


@dataclass
class ModelInfo:
    """Model information from session."""

    provider: str
    model_id: str


def create_compaction_summary_message(
    summary: str,
    tokens_before: int,
    timestamp: str,
) -> UserMessage:
    """Create a user message containing compaction summary."""
    text = f"{COMPACTION_SUMMARY_PREFIX}{summary}{COMPACTION_SUMMARY_SUFFIX}"
    return UserMessage(
        role="user",
        content=[TextContent(type="text", text=text)],
    )


def create_branch_summary_message(
    summary: str,
    from_id: str,
    timestamp: str,
) -> UserMessage:
    """Create a user message containing branch summary."""
    text = f"{BRANCH_SUMMARY_PREFIX}{summary}{BRANCH_SUMMARY_SUFFIX}"
    return UserMessage(
        role="user",
        content=[TextContent(type="text", text=text)],
    )


def create_custom_message(
    custom_type: str,
    content: str | list[dict],
    display: bool,
    details: Any,
    timestamp: str,
) -> UserMessage:
    """Create a user message from custom message entry."""
    if isinstance(content, str):
        msg_content = [TextContent(type="text", text=content)]
    else:
        msg_content = content
    return UserMessage(
        role="user",
        content=msg_content,
    )


def build_session_context(
    entries: list[SessionEntry],
    leaf_id: str | None = None,
    by_id: dict[str, SessionEntry] | None = None,
) -> SessionContext:
    """
    Build the session context from entries using tree traversal.

    If leaf_id is provided, walks from that entry to root.
    Handles compaction and branch summaries along the path.

    Args:
        entries: All session entries
        leaf_id: ID of the leaf entry to start from (None = last entry)
        by_id: Pre-built index of entries by ID

    Returns:
        SessionContext with messages, thinking level, and model info
    """
    # Build ID index if not provided
    if by_id is None:
        by_id = {e["id"]: e for e in entries}

    # Handle explicitly null leaf (navigated before first entry)
    if leaf_id is None and len(entries) == 0:
        return SessionContext()

    # Find leaf entry
    if leaf_id:
        leaf = by_id.get(leaf_id)
    else:
        # Default to last entry
        leaf = entries[-1] if entries else None

    if leaf is None:
        return SessionContext()

    # Walk from leaf to root, collecting path
    path: list[SessionEntry] = []
    current: SessionEntry | None = leaf
    while current:
        path.insert(0, current)
        parent_id = current.get("parentId")
        current = by_id.get(parent_id) if parent_id else None

    # Extract settings and find compaction
    thinking_level = "off"
    model: dict[str, str] | None = None
    compaction: CompactionEntry | None = None

    for entry in path:
        entry_type = entry["type"]
        if entry_type == "thinking_level_change":
            thinking_level = entry["thinkingLevel"]
        elif entry_type == "model_change":
            model = {"provider": entry["provider"], "modelId": entry["modelId"]}
        elif entry_type == "message":
            msg = entry["message"]
            if msg.get("role") == "assistant":
                # Extract model from assistant message
                if "provider" in msg and "model" in msg:
                    model = {"provider": msg["provider"], "modelId": msg["model"]}
        elif entry_type == "compaction":
            compaction = entry

    # Build messages
    messages: list[AgentMessage] = []

    def append_message(entry: SessionEntry) -> None:
        """Append message from entry if applicable."""
        entry_type = entry["type"]
        if entry_type == "message":
            messages.append(entry["message"])
        elif entry_type == "custom_message":
            msg = create_custom_message(
                entry["customType"],
                entry["content"],
                entry["display"],
                entry.get("details"),
                entry["timestamp"],
            )
            messages.append(msg)
        elif entry_type == "branch_summary" and entry.get("summary"):
            msg = create_branch_summary_message(
                entry["summary"],
                entry["fromId"],
                entry["timestamp"],
            )
            messages.append(msg)

    if compaction:
        # Emit summary first
        summary_msg = create_compaction_summary_message(
            compaction["summary"],
            compaction["tokensBefore"],
            compaction["timestamp"],
        )
        messages.append(summary_msg)

        # Find compaction index in path
        compaction_idx = -1
        for i, e in enumerate(path):
            if e["type"] == "compaction" and e["id"] == compaction["id"]:
                compaction_idx = i
                break

        # Emit kept messages (before compaction, starting from firstKeptEntryId)
        found_first_kept = False
        first_kept_id = compaction["firstKeptEntryId"]
        for i in range(compaction_idx):
            entry = path[i]
            if entry["id"] == first_kept_id:
                found_first_kept = True
            if found_first_kept:
                append_message(entry)

        # Emit messages after compaction
        for i in range(compaction_idx + 1, len(path)):
            append_message(path[i])
    else:
        # No compaction - emit all messages
        for entry in path:
            append_message(entry)

    return SessionContext(
        messages=messages,
        thinking_level=thinking_level,
        model=model,
    )
