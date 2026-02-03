"""Cut point detection for compaction."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .tokens import estimate_tokens

if TYPE_CHECKING:
    from ..session.entries import SessionEntry


@dataclass
class CutPointResult:
    """Result from finding a cut point."""

    first_kept_entry_index: int
    """Index of first entry to keep."""

    turn_start_index: int
    """Index of user message that starts the turn being split, or -1."""

    is_split_turn: bool
    """Whether this cut splits a turn (cut point is not a user message)."""


def find_valid_cut_points(
    entries: list["SessionEntry"],
    start_index: int,
    end_index: int,
) -> list[int]:
    """
    Find valid cut points: indices of user, assistant, custom messages.

    Never cut at tool results (they must follow their tool call).
    When we cut at an assistant message with tool calls, its tool results
    follow it and will be kept.
    """
    cut_points: list[int] = []

    for i in range(start_index, end_index):
        entry = entries[i]
        entry_type = entry.get("type") if isinstance(entry, dict) else getattr(entry, "type", None)

        if entry_type == "message":
            message = entry.get("message") if isinstance(entry, dict) else getattr(entry, "message", None)
            if message:
                role = message.get("role") if isinstance(message, dict) else getattr(message, "role", None)
                # Valid cut points
                if role in ("user", "assistant", "custom", "bash_execution",
                            "branch_summary", "compaction_summary"):
                    cut_points.append(i)
                # Don't cut at tool results (role == "tool" is skipped)

        elif entry_type in ("custom_message", "branch_summary"):
            # User-role messages, valid cut points
            cut_points.append(i)

    return cut_points


def find_turn_start_index(
    entries: list["SessionEntry"],
    entry_index: int,
    start_index: int,
) -> int:
    """
    Find the user message that starts the turn containing the given entry.

    Returns -1 if no turn start found.
    """
    for i in range(entry_index, start_index - 1, -1):
        entry = entries[i]
        entry_type = entry.get("type") if isinstance(entry, dict) else getattr(entry, "type", None)

        if entry_type in ("branch_summary", "custom_message"):
            return i

        if entry_type == "message":
            message = entry.get("message") if isinstance(entry, dict) else getattr(entry, "message", None)
            if message:
                role = message.get("role") if isinstance(message, dict) else getattr(message, "role", None)
                if role in ("user", "bash_execution"):
                    return i

    return -1


def find_cut_point(
    entries: list["SessionEntry"],
    start_index: int,
    end_index: int,
    keep_recent_tokens: int,
) -> CutPointResult:
    """
    Find the cut point that keeps approximately `keep_recent_tokens`.

    Algorithm: Walk backwards from newest, accumulating estimated message sizes.
    Stop when we've accumulated >= keep_recent_tokens. Cut at that point.

    Can cut at user OR assistant messages (never tool results).

    Args:
        entries: Session entries
        start_index: First entry to consider
        end_index: One past last entry to consider
        keep_recent_tokens: Target tokens to keep

    Returns:
        CutPointResult with cut point information
    """
    cut_points = find_valid_cut_points(entries, start_index, end_index)

    if not cut_points:
        return CutPointResult(
            first_kept_entry_index=start_index,
            turn_start_index=-1,
            is_split_turn=False,
        )

    # Walk backwards, accumulating message sizes
    accumulated_tokens = 0
    cut_index = cut_points[0]  # Default: keep from first message

    for i in range(end_index - 1, start_index - 1, -1):
        entry = entries[i]
        entry_type = entry.get("type") if isinstance(entry, dict) else getattr(entry, "type", None)

        if entry_type != "message":
            continue

        message = entry.get("message") if isinstance(entry, dict) else getattr(entry, "message", None)
        if not message:
            continue

        # Estimate message size
        message_tokens = estimate_tokens(message)
        accumulated_tokens += message_tokens

        # Check if we've exceeded budget
        if accumulated_tokens >= keep_recent_tokens:
            # Find closest valid cut point at or after this entry
            for c in cut_points:
                if c >= i:
                    cut_index = c
                    break
            break

    # Scan backwards to include non-message entries
    while cut_index > start_index:
        prev_entry = entries[cut_index - 1]
        prev_type = prev_entry.get("type") if isinstance(prev_entry, dict) else getattr(prev_entry, "type", None)

        # Stop at compaction boundaries
        if prev_type == "compaction":
            break

        if prev_type == "message":
            break

        # Include non-message entry
        cut_index -= 1

    # Determine if this is a split turn
    cut_entry = entries[cut_index]
    cut_type = cut_entry.get("type") if isinstance(cut_entry, dict) else getattr(cut_entry, "type", None)

    is_user_message = False
    if cut_type == "message":
        message = cut_entry.get("message") if isinstance(cut_entry, dict) else getattr(cut_entry, "message", None)
        if message:
            role = message.get("role") if isinstance(message, dict) else getattr(message, "role", None)
            is_user_message = role == "user"

    turn_start_index = -1 if is_user_message else find_turn_start_index(
        entries, cut_index, start_index
    )

    return CutPointResult(
        first_kept_entry_index=cut_index,
        turn_start_index=turn_start_index,
        is_split_turn=not is_user_message and turn_start_index != -1,
    )
