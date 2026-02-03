"""Grep tool for searching file contents."""

import fnmatch
import os
import re
from pathlib import Path
from typing import Any, Protocol

from pipy_agent import AgentTool, AgentToolResult, AbortSignal, TextContent

from .path_utils import resolve_to_cwd
from .truncate import (
    DEFAULT_MAX_BYTES,
    GREP_MAX_LINE_LENGTH,
    TruncationResult,
    format_size,
    truncate_head,
    truncate_line,
)

DEFAULT_LIMIT = 100


class GrepToolDetails:
    """Details returned by grep tool."""

    def __init__(
        self,
        truncation: TruncationResult | None = None,
        match_limit_reached: int | None = None,
        lines_truncated: bool = False,
    ):
        self.truncation = truncation
        self.match_limit_reached = match_limit_reached
        self.lines_truncated = lines_truncated


class GrepOperations(Protocol):
    """Pluggable operations for the grep tool."""

    async def is_directory(self, absolute_path: str) -> bool:
        """Check if path is a directory."""
        ...

    async def read_file(self, absolute_path: str) -> str:
        """Read file contents for search."""
        ...

    async def walk_files(
        self,
        absolute_path: str,
        glob_pattern: str | None = None,
    ) -> list[str]:
        """Walk directory and return file paths."""
        ...


class DefaultGrepOperations:
    """Default grep operations using local filesystem."""

    async def is_directory(self, absolute_path: str) -> bool:
        """Check if path is a directory."""
        return os.path.isdir(absolute_path)

    async def read_file(self, absolute_path: str) -> str:
        """Read file contents."""
        try:
            with open(absolute_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return ""

    async def walk_files(
        self,
        absolute_path: str,
        glob_pattern: str | None = None,
    ) -> list[str]:
        """Walk directory and return file paths."""
        files = []
        ignore_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv"}

        for root, dirs, filenames in os.walk(absolute_path):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]

            for filename in filenames:
                # Skip hidden files
                if filename.startswith("."):
                    continue

                file_path = os.path.join(root, filename)

                # Apply glob filter if specified
                if glob_pattern:
                    rel_path = os.path.relpath(file_path, absolute_path)
                    if not fnmatch.fnmatch(rel_path, glob_pattern) and not fnmatch.fnmatch(
                        filename, glob_pattern
                    ):
                        continue

                files.append(file_path)

        return files


GREP_PARAMETERS = {
    "type": "object",
    "properties": {
        "pattern": {
            "type": "string",
            "description": "Search pattern (regex or literal string)",
        },
        "path": {
            "type": "string",
            "description": "Directory or file to search (default: current directory)",
        },
        "glob": {
            "type": "string",
            "description": "Filter files by glob pattern, e.g. '*.ts' or '**/*.spec.ts'",
        },
        "ignoreCase": {
            "type": "boolean",
            "description": "Case-insensitive search (default: false)",
        },
        "literal": {
            "type": "boolean",
            "description": "Treat pattern as literal string instead of regex (default: false)",
        },
        "context": {
            "type": "number",
            "description": "Number of lines to show before and after each match (default: 0)",
        },
        "limit": {
            "type": "number",
            "description": "Maximum number of matches to return (default: 100)",
        },
    },
    "required": ["pattern"],
}


def create_grep_tool(
    cwd: str | Path,
    operations: GrepOperations | None = None,
) -> AgentTool:
    """
    Create a grep tool for the given working directory.

    Args:
        cwd: Working directory for relative paths
        operations: Custom operations for grep (default: local filesystem)
    """
    cwd_str = str(cwd)
    ops = operations or DefaultGrepOperations()

    class GrepTool(AgentTool):
        name: str = "grep"
        label: str = "grep"
        description: str = (
            f"Search file contents for a pattern. Returns matching lines with file paths and line numbers. "
            f"Respects .gitignore. Output is truncated to {DEFAULT_LIMIT} matches or "
            f"{DEFAULT_MAX_BYTES // 1024}KB (whichever is hit first). "
            f"Long lines are truncated to {GREP_MAX_LINE_LENGTH} chars."
        )
        parameters: dict[str, Any] = GREP_PARAMETERS

        async def execute(
            self,
            tool_call_id: str,
            params: dict[str, Any],
            signal: AbortSignal | None = None,
            on_update=None,
        ) -> AgentToolResult[GrepToolDetails]:
            pattern = params.get("pattern", "")
            search_dir = params.get("path", ".")
            glob_pattern = params.get("glob")
            ignore_case = params.get("ignoreCase", False)
            literal = params.get("literal", False)
            context = params.get("context", 0)
            limit = params.get("limit", DEFAULT_LIMIT)

            # Check abort
            if signal and signal.aborted:
                raise RuntimeError("Operation aborted")

            # Resolve search path
            search_path = resolve_to_cwd(search_dir, cwd_str)

            if not os.path.exists(search_path):
                raise RuntimeError(f"Path not found: {search_path}")

            is_directory = await ops.is_directory(search_path)

            # Compile regex
            flags = re.IGNORECASE if ignore_case else 0
            if literal:
                regex = re.compile(re.escape(pattern), flags)
            else:
                try:
                    regex = re.compile(pattern, flags)
                except re.error as e:
                    raise RuntimeError(f"Invalid regex pattern: {e}")

            # Get files to search
            if is_directory:
                files = await ops.walk_files(search_path, glob_pattern)
            else:
                files = [search_path]

            # Search files
            results: list[str] = []
            match_count = 0
            match_limit_reached = False
            lines_truncated = False

            for file_path in files:
                if signal and signal.aborted:
                    raise RuntimeError("Operation aborted")

                if match_count >= limit:
                    match_limit_reached = True
                    break

                try:
                    content = await ops.read_file(file_path)
                except Exception:
                    continue

                lines = content.split("\n")

                # Format relative path
                if is_directory:
                    rel_path = os.path.relpath(file_path, search_path)
                    display_path = rel_path.replace("\\", "/")
                else:
                    display_path = os.path.basename(file_path)

                for line_num, line in enumerate(lines, 1):
                    if match_count >= limit:
                        match_limit_reached = True
                        break

                    if regex.search(line):
                        match_count += 1

                        # Truncate long lines
                        display_line, was_truncated = truncate_line(line)
                        if was_truncated:
                            lines_truncated = True

                        # Add context lines if requested
                        if context > 0:
                            context_lines = []
                            # Before context
                            start = max(0, line_num - 1 - context)
                            for i in range(start, line_num - 1):
                                ctx_line, _ = truncate_line(lines[i])
                                context_lines.append(f"{display_path}:{i+1}- {ctx_line}")

                            # Match line
                            context_lines.append(f"{display_path}:{line_num}: {display_line}")

                            # After context
                            end = min(len(lines), line_num + context)
                            for i in range(line_num, end):
                                ctx_line, _ = truncate_line(lines[i])
                                context_lines.append(f"{display_path}:{i+1}- {ctx_line}")

                            results.append("\n".join(context_lines))
                            results.append("")  # Separator
                        else:
                            results.append(f"{display_path}:{line_num}: {display_line}")

            if not results:
                return AgentToolResult(
                    content=[TextContent(type="text", text="No matches found")],
                    details=GrepToolDetails(),
                )

            # Join results
            output = "\n".join(results)

            # Apply truncation
            truncation = truncate_head(output)
            output_text = truncation.content

            details = GrepToolDetails(
                truncation=truncation if truncation.truncated else None,
                match_limit_reached=limit if match_limit_reached else None,
                lines_truncated=lines_truncated,
            )

            if truncation.truncated:
                output_text += f"\n\n[Output truncated. Showing {truncation.output_lines} lines of {truncation.total_lines}.]"
            elif match_limit_reached:
                output_text += f"\n\n[Showing first {limit} matches. Use limit parameter to see more.]"

            return AgentToolResult(
                content=[TextContent(type="text", text=output_text)],
                details=details,
            )

    return GrepTool()


# Default grep tool using current directory
def _get_default_cwd() -> str:
    return os.getcwd()


grep_tool = create_grep_tool(_get_default_cwd())
