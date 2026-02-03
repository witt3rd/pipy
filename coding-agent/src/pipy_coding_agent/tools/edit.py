"""Edit tool for precise file modifications."""

import difflib
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Protocol

from pipy_agent import AgentTool, AgentToolResult, AbortSignal, TextContent

from .path_utils import resolve_to_cwd


class EditToolDetails:
    """Details returned by edit tool."""

    def __init__(self, diff: str, first_changed_line: int | None = None):
        self.diff = diff
        self.first_changed_line = first_changed_line


class EditOperations(Protocol):
    """Pluggable operations for the edit tool."""

    async def read_file(self, absolute_path: str) -> bytes:
        """Read file contents as bytes."""
        ...

    async def write_file(self, absolute_path: str, content: str) -> None:
        """Write content to a file."""
        ...

    async def access(self, absolute_path: str) -> None:
        """Check if file is readable and writable (raise if not)."""
        ...


class DefaultEditOperations:
    """Default edit operations using local filesystem."""

    async def read_file(self, absolute_path: str) -> bytes:
        """Read file contents."""
        with open(absolute_path, "rb") as f:
            return f.read()

    async def write_file(self, absolute_path: str, content: str) -> None:
        """Write content to file in binary mode to preserve exact line endings."""
        with open(absolute_path, "wb") as f:
            f.write(content.encode("utf-8"))

    async def access(self, absolute_path: str) -> None:
        """Check if file is readable and writable."""
        if not os.path.exists(absolute_path):
            raise FileNotFoundError(f"File not found: {absolute_path}")
        if not os.access(absolute_path, os.R_OK | os.W_OK):
            raise PermissionError(f"Permission denied: {absolute_path}")


def detect_line_ending(content: str) -> str:
    """Detect line ending style (CRLF or LF)."""
    crlf_idx = content.find("\r\n")
    lf_idx = content.find("\n")
    if lf_idx == -1:
        return "\n"
    if crlf_idx == -1:
        return "\n"
    return "\r\n" if crlf_idx < lf_idx else "\n"


def normalize_to_lf(text: str) -> str:
    """Normalize all line endings to LF."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def restore_line_endings(text: str, ending: str) -> str:
    """Restore line endings to original style."""
    return text.replace("\n", ending) if ending == "\r\n" else text


def strip_bom(content: str) -> tuple[str, str]:
    """Strip UTF-8 BOM if present. Returns (bom, text)."""
    if content.startswith("\ufeff"):
        return "\ufeff", content[1:]
    return "", content


def normalize_for_fuzzy_match(text: str) -> str:
    """
    Normalize text for fuzzy matching.
    - Strip trailing whitespace from each line
    - Normalize smart quotes to ASCII
    - Normalize Unicode dashes to ASCII hyphen
    - Normalize special spaces to regular space
    """
    # Strip trailing whitespace per line
    lines = [line.rstrip() for line in text.split("\n")]
    result = "\n".join(lines)

    # Smart single quotes → '
    result = re.sub(r"[\u2018\u2019\u201a\u201b]", "'", result)

    # Smart double quotes → "
    result = re.sub(r"[\u201c\u201d\u201e\u201f]", '"', result)

    # Various dashes → -
    result = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]", "-", result)

    # Special spaces → regular space
    result = re.sub(r"[\u00a0\u2002-\u200a\u202f\u205f\u3000]", " ", result)

    return result


def fuzzy_find_text(content: str, old_text: str) -> dict:
    """
    Find old_text in content, trying exact match first, then fuzzy match.
    """
    # Try exact match first
    exact_index = content.find(old_text)
    if exact_index != -1:
        return {
            "found": True,
            "index": exact_index,
            "match_length": len(old_text),
            "used_fuzzy_match": False,
            "content_for_replacement": content,
        }

    # Try fuzzy match
    fuzzy_content = normalize_for_fuzzy_match(content)
    fuzzy_old_text = normalize_for_fuzzy_match(old_text)
    fuzzy_index = fuzzy_content.find(fuzzy_old_text)

    if fuzzy_index == -1:
        return {
            "found": False,
            "index": -1,
            "match_length": 0,
            "used_fuzzy_match": False,
            "content_for_replacement": content,
        }

    return {
        "found": True,
        "index": fuzzy_index,
        "match_length": len(fuzzy_old_text),
        "used_fuzzy_match": True,
        "content_for_replacement": fuzzy_content,
    }


def generate_diff_string(old_content: str, new_content: str, context_lines: int = 4) -> tuple[str, int | None]:
    """
    Generate a unified diff string with line numbers.
    Returns (diff_string, first_changed_line).
    """
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile="original",
        tofile="modified",
        lineterm="",
        n=context_lines,
    )

    diff_lines = list(diff)
    diff_str = "".join(diff_lines)

    # Find first changed line
    first_changed_line = None
    new_line_num = 0
    for line in diff_lines:
        if line.startswith("@@"):
            # Parse hunk header like @@ -1,3 +1,4 @@
            match = re.search(r"\+(\d+)", line)
            if match:
                new_line_num = int(match.group(1)) - 1
        elif line.startswith("+") and not line.startswith("+++"):
            if first_changed_line is None:
                first_changed_line = new_line_num + 1
            new_line_num += 1
        elif line.startswith("-") and not line.startswith("---"):
            pass  # Deleted line
        elif not line.startswith("@@"):
            new_line_num += 1

    return diff_str, first_changed_line


EDIT_PARAMETERS = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Path to the file to edit (relative or absolute)",
        },
        "oldText": {
            "type": "string",
            "description": "Exact text to find and replace (must match exactly)",
        },
        "newText": {
            "type": "string",
            "description": "New text to replace the old text with",
        },
    },
    "required": ["path", "oldText", "newText"],
}


def create_edit_tool(
    cwd: str | Path,
    operations: EditOperations | None = None,
) -> AgentTool:
    """
    Create an edit tool for the given working directory.

    Args:
        cwd: Working directory for relative paths
        operations: Custom operations for file editing (default: local filesystem)
    """
    cwd_str = str(cwd)
    ops = operations or DefaultEditOperations()

    class EditTool(AgentTool):
        name: str = "edit"
        label: str = "edit"
        description: str = (
            "Edit a file by replacing exact text. The oldText must match exactly "
            "(including whitespace). Use this for precise, surgical edits."
        )
        parameters: dict[str, Any] = EDIT_PARAMETERS

        async def execute(
            self,
            tool_call_id: str,
            params: dict[str, Any],
            signal: AbortSignal | None = None,
            on_update=None,
        ) -> AgentToolResult[EditToolDetails]:
            path = params.get("path", "")
            old_text = params.get("oldText", "")
            new_text = params.get("newText", "")

            # Resolve path
            absolute_path = resolve_to_cwd(path, cwd_str)

            # Check abort
            if signal and signal.aborted:
                raise RuntimeError("Operation aborted")

            # Check file access
            try:
                await ops.access(absolute_path)
            except FileNotFoundError:
                raise RuntimeError(f"File not found: {path}")

            # Check abort
            if signal and signal.aborted:
                raise RuntimeError("Operation aborted")

            # Read the file
            buffer = await ops.read_file(absolute_path)
            raw_content = buffer.decode("utf-8")

            # Check abort
            if signal and signal.aborted:
                raise RuntimeError("Operation aborted")

            # Strip BOM before matching
            bom, content = strip_bom(raw_content)

            original_ending = detect_line_ending(content)
            normalized_content = normalize_to_lf(content)
            normalized_old_text = normalize_to_lf(old_text)
            normalized_new_text = normalize_to_lf(new_text)

            # Find the old text using fuzzy matching
            match_result = fuzzy_find_text(normalized_content, normalized_old_text)

            if not match_result["found"]:
                raise RuntimeError(
                    f"Could not find the exact text in {path}. "
                    f"The old text must match exactly including all whitespace and newlines."
                )

            # Count occurrences for uniqueness check
            fuzzy_content = normalize_for_fuzzy_match(normalized_content)
            fuzzy_old_text = normalize_for_fuzzy_match(normalized_old_text)
            occurrences = fuzzy_content.count(fuzzy_old_text)

            if occurrences > 1:
                raise RuntimeError(
                    f"Found {occurrences} occurrences of the text in {path}. "
                    f"The text must be unique. Please provide more context to make it unique."
                )

            # Check abort
            if signal and signal.aborted:
                raise RuntimeError("Operation aborted")

            # Perform replacement
            base_content = match_result["content_for_replacement"]
            idx = match_result["index"]
            match_len = match_result["match_length"]

            new_content = base_content[:idx] + normalized_new_text + base_content[idx + match_len:]

            # Verify replacement changed something
            if base_content == new_content:
                raise RuntimeError(
                    f"No changes made to {path}. "
                    f"The replacement produced identical content."
                )

            final_content = bom + restore_line_endings(new_content, original_ending)
            await ops.write_file(absolute_path, final_content)

            # Check abort
            if signal and signal.aborted:
                raise RuntimeError("Operation aborted")

            # Generate diff
            diff_str, first_changed_line = generate_diff_string(base_content, new_content)

            return AgentToolResult(
                content=[TextContent(type="text", text=f"Successfully replaced text in {path}.")],
                details=EditToolDetails(diff=diff_str, first_changed_line=first_changed_line),
            )

    return EditTool()


# Default edit tool using current directory
def _get_default_cwd() -> str:
    return os.getcwd()


edit_tool = create_edit_tool(_get_default_cwd())
