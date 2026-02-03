"""File operation tracking for compaction context."""

from dataclasses import dataclass, field
from typing import Any


def _get_attr(obj: Any, key: str, default: Any = None) -> Any:
    """Get attribute from dict or object."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


@dataclass
class FileOperations:
    """Tracked file operations."""

    read: set[str] = field(default_factory=set)
    """Files that were read."""

    written: set[str] = field(default_factory=set)
    """Files that were written (created/overwritten)."""

    edited: set[str] = field(default_factory=set)
    """Files that were edited."""


def create_file_ops() -> FileOperations:
    """Create empty file operations tracker."""
    return FileOperations()


def extract_file_ops_from_message(message: Any, file_ops: FileOperations) -> None:
    """
    Extract file operations from tool calls in an assistant message.

    Modifies file_ops in place.
    Handles both dict-style and Pydantic messages.
    """
    role = _get_attr(message, "role", "")
    if role != "assistant":
        return

    content = _get_attr(message, "content")
    if not isinstance(content, list):
        return

    for block in content:
        block_type = _get_attr(block, "type", "")

        # Accept both "toolCall" (pipy) and "tool_use" (Anthropic)
        if block_type not in ("toolCall", "tool_use"):
            continue

        name = _get_attr(block, "name", "")
        # Accept both "arguments" (pipy) and "input" (Anthropic)
        args = _get_attr(block, "arguments") or _get_attr(block, "input", {})

        if not isinstance(args, dict):
            continue

        path = args.get("path")
        if not isinstance(path, str):
            continue

        if name == "Read":
            file_ops.read.add(path)
        elif name == "Write":
            file_ops.written.add(path)
        elif name == "Edit":
            file_ops.edited.add(path)


def compute_file_lists(file_ops: FileOperations) -> tuple[list[str], list[str]]:
    """
    Compute final file lists from file operations.

    Returns:
        Tuple of (read_files, modified_files) where read_files
        contains files only read (not modified) and modified_files
        contains all written/edited files.
    """
    modified = file_ops.edited | file_ops.written
    read_only = sorted(f for f in file_ops.read if f not in modified)
    modified_files = sorted(modified)
    return read_only, modified_files


def format_file_operations(read_files: list[str], modified_files: list[str]) -> str:
    """
    Format file operations as XML tags for summary.

    Returns empty string if no files.
    """
    sections: list[str] = []

    if read_files:
        sections.append(f"<read-files>\n{chr(10).join(read_files)}\n</read-files>")

    if modified_files:
        sections.append(f"<modified-files>\n{chr(10).join(modified_files)}\n</modified-files>")

    if not sections:
        return ""

    return "\n\n" + "\n\n".join(sections)
