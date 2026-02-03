"""Find tool for searching files by pattern."""

import fnmatch
import os
from pathlib import Path
from typing import Any, Protocol

from pipy_agent import AgentTool, AgentToolResult, AbortSignal, TextContent

from .path_utils import resolve_to_cwd
from .truncate import (
    DEFAULT_MAX_BYTES,
    TruncationResult,
    format_size,
    truncate_head,
)

DEFAULT_LIMIT = 1000


class FindToolDetails:
    """Details returned by find tool."""

    def __init__(
        self,
        truncation: TruncationResult | None = None,
        result_limit_reached: int | None = None,
    ):
        self.truncation = truncation
        self.result_limit_reached = result_limit_reached


class FindOperations(Protocol):
    """Pluggable operations for the find tool."""

    async def exists(self, absolute_path: str) -> bool:
        """Check if path exists."""
        ...

    async def glob(
        self,
        pattern: str,
        search_cwd: str,
        ignore: list[str],
        limit: int,
    ) -> list[str]:
        """Find files matching glob pattern. Returns relative paths."""
        ...


class DefaultFindOperations:
    """Default find operations using local filesystem."""

    async def exists(self, absolute_path: str) -> bool:
        """Check if path exists."""
        return os.path.exists(absolute_path)

    async def glob(
        self,
        pattern: str,
        search_cwd: str,
        ignore: list[str],
        limit: int,
    ) -> list[str]:
        """Find files matching glob pattern."""
        results = []
        ignore_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv"}

        for root, dirs, files in os.walk(search_cwd):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]

            for filename in files:
                if len(results) >= limit:
                    return results

                # Skip hidden files
                if filename.startswith("."):
                    continue

                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, search_cwd)

                # Check pattern match
                if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(filename, pattern):
                    # Check ignore patterns
                    should_ignore = False
                    for ignore_pattern in ignore:
                        if fnmatch.fnmatch(rel_path, ignore_pattern):
                            should_ignore = True
                            break
                    if not should_ignore:
                        results.append(rel_path.replace("\\", "/"))

        return results


FIND_PARAMETERS = {
    "type": "object",
    "properties": {
        "pattern": {
            "type": "string",
            "description": "Glob pattern to match files, e.g. '*.ts', '**/*.json', or 'src/**/*.spec.ts'",
        },
        "path": {
            "type": "string",
            "description": "Directory to search in (default: current directory)",
        },
        "limit": {
            "type": "number",
            "description": "Maximum number of results (default: 1000)",
        },
    },
    "required": ["pattern"],
}


def create_find_tool(
    cwd: str | Path,
    operations: FindOperations | None = None,
) -> AgentTool:
    """
    Create a find tool for the given working directory.

    Args:
        cwd: Working directory for relative paths
        operations: Custom operations for find (default: local filesystem)
    """
    cwd_str = str(cwd)
    ops = operations or DefaultFindOperations()

    class FindTool(AgentTool):
        name: str = "find"
        label: str = "find"
        description: str = (
            f"Search for files by glob pattern. Returns matching file paths relative to the search directory. "
            f"Respects .gitignore. Output is truncated to {DEFAULT_LIMIT} results or "
            f"{DEFAULT_MAX_BYTES // 1024}KB (whichever is hit first)."
        )
        parameters: dict[str, Any] = FIND_PARAMETERS

        async def execute(
            self,
            tool_call_id: str,
            params: dict[str, Any],
            signal: AbortSignal | None = None,
            on_update=None,
        ) -> AgentToolResult[FindToolDetails]:
            pattern = params.get("pattern", "")
            search_dir = params.get("path", ".")
            limit = params.get("limit", DEFAULT_LIMIT)

            # Check abort
            if signal and signal.aborted:
                raise RuntimeError("Operation aborted")

            # Resolve search path
            search_path = resolve_to_cwd(search_dir, cwd_str)

            if not await ops.exists(search_path):
                raise RuntimeError(f"Path not found: {search_path}")

            # Find files
            results = await ops.glob(
                pattern,
                search_path,
                ignore=["**/node_modules/**", "**/.git/**"],
                limit=limit,
            )

            # Check abort
            if signal and signal.aborted:
                raise RuntimeError("Operation aborted")

            if not results:
                return AgentToolResult(
                    content=[TextContent(type="text", text="No files found matching pattern")],
                    details=FindToolDetails(),
                )

            # Sort results
            results.sort(key=lambda x: x.lower())

            # Check if limit was reached
            result_limit_reached = len(results) >= limit

            # Join results
            output = "\n".join(results)

            # Apply truncation
            truncation = truncate_head(output)
            output_text = truncation.content

            details = FindToolDetails(
                truncation=truncation if truncation.truncated else None,
                result_limit_reached=limit if result_limit_reached else None,
            )

            if truncation.truncated:
                output_text += (
                    f"\n\n[Output truncated. Showing {truncation.output_lines} of {truncation.total_lines} files.]"
                )
            elif result_limit_reached:
                output_text += f"\n\n[Showing first {limit} results. Use limit parameter to see more.]"

            return AgentToolResult(
                content=[TextContent(type="text", text=output_text)],
                details=details,
            )

    return FindTool()


# Default find tool using current directory
def _get_default_cwd() -> str:
    return os.getcwd()


find_tool = create_find_tool(_get_default_cwd())
