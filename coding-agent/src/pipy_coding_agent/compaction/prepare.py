"""Compaction preparation."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pipy_ai import Message

from ..settings import CompactionSettings
from .cut_point import find_cut_point
from .file_ops import FileOperations, create_file_ops, extract_file_ops_from_message
from .tokens import estimate_context_tokens

if TYPE_CHECKING:
    from ..session.entries import SessionEntry


@dataclass
class CompactionDetails:
    """Details stored in CompactionEntry.details for file tracking."""

    read_files: list[str] = field(default_factory=list)
    modified_files: list[str] = field(default_factory=list)


@dataclass
class CompactionPreparation:
    """Prepared data for compaction."""

    first_kept_entry_id: str
    """UUID of first entry to keep."""

    messages_to_summarize: list[Message]
    """Messages that will be summarized and discarded."""

    turn_prefix_messages: list[Message]
    """Messages for turn prefix summary (if splitting)."""

    is_split_turn: bool
    """Whether this is a split turn."""

    tokens_before: int
    """Total tokens before compaction."""

    previous_summary: str | None
    """Summary from previous compaction, for iterative update."""

    file_ops: FileOperations
    """File operations extracted from messages."""

    settings: CompactionSettings
    """Compaction settings."""


def _get_message_from_entry(entry: "SessionEntry") -> Message | None:
    """Extract Message from an entry if it produces one."""
    entry_type = entry.get("type") if isinstance(entry, dict) else getattr(entry, "type", None)

    if entry_type == "message":
        message = entry.get("message") if isinstance(entry, dict) else getattr(entry, "message", None)
        if message:
            # Convert dict to Message if needed
            if isinstance(message, dict):
                return Message(**message)
            return message

    if entry_type == "custom_message":
        content = entry.get("content") if isinstance(entry, dict) else getattr(entry, "content", "")
        return Message(role="user", content=content)

    if entry_type == "branch_summary":
        from_id = entry.get("fromId") if isinstance(entry, dict) else getattr(entry, "fromId", "")
        summary = entry.get("summary") if isinstance(entry, dict) else getattr(entry, "summary", "")
        return Message(
            role="user",
            content=f"[Branch Summary from {from_id}]\n\n{summary}",
        )

    if entry_type == "compaction":
        tokens_before = entry.get("tokensBefore") if isinstance(entry, dict) else getattr(entry, "tokensBefore", 0)
        summary = entry.get("summary") if isinstance(entry, dict) else getattr(entry, "summary", "")
        return Message(
            role="user",
            content=f"[Context Checkpoint - {tokens_before} tokens compacted]\n\n{summary}",
        )

    return None


def _extract_file_operations(
    messages: list[Message],
    entries: list["SessionEntry"],
    prev_compaction_index: int,
) -> FileOperations:
    """Extract file operations from messages and previous compaction."""
    file_ops = create_file_ops()

    # Collect from previous compaction's details
    if prev_compaction_index >= 0:
        prev_compaction = entries[prev_compaction_index]
        entry_type = prev_compaction.get("type") if isinstance(prev_compaction, dict) else getattr(prev_compaction, "type", None)
        if entry_type == "compaction":
            details = prev_compaction.get("details") if isinstance(prev_compaction, dict) else getattr(prev_compaction, "details", None)
            if details and isinstance(details, dict):
                read_files = details.get("read_files", [])
                modified_files = details.get("modified_files", [])
                if isinstance(read_files, list):
                    for f in read_files:
                        if isinstance(f, str):
                            file_ops.read.add(f)
                if isinstance(modified_files, list):
                    for f in modified_files:
                        if isinstance(f, str):
                            file_ops.edited.add(f)

    # Extract from tool calls in messages
    for msg in messages:
        extract_file_ops_from_message(msg, file_ops)

    return file_ops


def prepare_compaction(
    path_entries: list["SessionEntry"],
    settings: CompactionSettings,
) -> CompactionPreparation | None:
    """
    Prepare data for compaction.

    Args:
        path_entries: Session entries in the current path
        settings: Compaction settings

    Returns:
        CompactionPreparation if compaction is needed, None otherwise
    """
    def get_entry_type(entry: "SessionEntry") -> str | None:
        return entry.get("type") if isinstance(entry, dict) else getattr(entry, "type", None)

    def get_entry_id(entry: "SessionEntry") -> str | None:
        return entry.get("id") if isinstance(entry, dict) else getattr(entry, "id", None)

    # Don't compact if last entry is already a compaction
    if path_entries and get_entry_type(path_entries[-1]) == "compaction":
        return None

    # Find previous compaction
    prev_compaction_index = -1
    for i in range(len(path_entries) - 1, -1, -1):
        if get_entry_type(path_entries[i]) == "compaction":
            prev_compaction_index = i
            break

    boundary_start = prev_compaction_index + 1
    boundary_end = len(path_entries)

    # Calculate current tokens
    usage_start = prev_compaction_index if prev_compaction_index >= 0 else 0
    usage_messages: list[Message] = []
    for i in range(usage_start, boundary_end):
        msg = _get_message_from_entry(path_entries[i])
        if msg:
            usage_messages.append(msg)

    tokens_before = estimate_context_tokens(usage_messages).tokens

    # Find cut point
    cut_point = find_cut_point(
        path_entries,
        boundary_start,
        boundary_end,
        settings.keep_recent_tokens,
    )

    # Get UUID of first kept entry
    first_kept_entry = path_entries[cut_point.first_kept_entry_index]
    first_kept_entry_id = get_entry_id(first_kept_entry)
    if not first_kept_entry_id:
        return None  # Session needs migration

    history_end = (
        cut_point.turn_start_index
        if cut_point.is_split_turn
        else cut_point.first_kept_entry_index
    )

    # Messages to summarize
    messages_to_summarize: list[Message] = []
    for i in range(boundary_start, history_end):
        msg = _get_message_from_entry(path_entries[i])
        if msg:
            messages_to_summarize.append(msg)

    # Turn prefix messages (if splitting)
    turn_prefix_messages: list[Message] = []
    if cut_point.is_split_turn:
        for i in range(cut_point.turn_start_index, cut_point.first_kept_entry_index):
            msg = _get_message_from_entry(path_entries[i])
            if msg:
                turn_prefix_messages.append(msg)

    # Get previous summary
    previous_summary: str | None = None
    if prev_compaction_index >= 0:
        prev = path_entries[prev_compaction_index]
        if get_entry_type(prev) == "compaction":
            previous_summary = prev.get("summary") if isinstance(prev, dict) else getattr(prev, "summary", None)

    # Extract file operations
    file_ops = _extract_file_operations(
        messages_to_summarize,
        path_entries,
        prev_compaction_index,
    )

    # Also extract from turn prefix
    if cut_point.is_split_turn:
        for msg in turn_prefix_messages:
            extract_file_ops_from_message(msg, file_ops)

    return CompactionPreparation(
        first_kept_entry_id=first_kept_entry_id,
        messages_to_summarize=messages_to_summarize,
        turn_prefix_messages=turn_prefix_messages,
        is_split_turn=cut_point.is_split_turn,
        tokens_before=tokens_before,
        previous_summary=previous_summary,
        file_ops=file_ops,
        settings=settings,
    )
