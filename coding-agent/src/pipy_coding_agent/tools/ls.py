"""Ls tool for listing directory contents."""

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

DEFAULT_LIMIT = 500


class LsToolDetails:
    """Details returned by ls tool."""

    def __init__(
        self,
        truncation: TruncationResult | None = None,
        entry_limit_reached: int | None = None,
    ):
        self.truncation = truncation
        self.entry_limit_reached = entry_limit_reached


class LsOperations(Protocol):
    """Pluggable operations for the ls tool."""

    async def exists(self, absolute_path: str) -> bool:
        """Check if path exists."""
        ...

    async def stat(self, absolute_path: str) -> dict:
        """Get file/directory stats."""
        ...

    async def readdir(self, absolute_path: str) -> list[str]:
        """Read directory entries."""
        ...


class DefaultLsOperations:
    """Default ls operations using local filesystem."""

    async def exists(self, absolute_path: str) -> bool:
        """Check if path exists."""
        return os.path.exists(absolute_path)

    async def stat(self, absolute_path: str) -> dict:
        """Get file/directory stats."""
        st = os.stat(absolute_path)
        return {"is_directory": os.path.isdir(absolute_path)}

    async def readdir(self, absolute_path: str) -> list[str]:
        """Read directory entries."""
        return os.listdir(absolute_path)


LS_PARAMETERS = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Directory to list (default: current directory)",
        },
        "limit": {
            "type": "number",
            "description": "Maximum number of entries to return (default: 500)",
        },
    },
    "required": [],
}


def create_ls_tool(
    cwd: str | Path,
    operations: LsOperations | None = None,
) -> AgentTool:
    """
    Create an ls tool for the given working directory.

    Args:
        cwd: Working directory for relative paths
        operations: Custom operations for ls (default: local filesystem)
    """
    cwd_str = str(cwd)
    ops = operations or DefaultLsOperations()

    class LsTool(AgentTool):
        name: str = "ls"
        label: str = "ls"
        description: str = (
            f"List directory contents. Returns entries sorted alphabetically, with '/' suffix for directories. "
            f"Includes dotfiles. Output is truncated to {DEFAULT_LIMIT} entries or "
            f"{DEFAULT_MAX_BYTES // 1024}KB (whichever is hit first)."
        )
        parameters: dict[str, Any] = LS_PARAMETERS

        async def execute(
            self,
            tool_call_id: str,
            params: dict[str, Any],
            signal: AbortSignal | None = None,
            on_update=None,
        ) -> AgentToolResult[LsToolDetails]:
            dir_path_param = params.get("path", ".")
            limit = params.get("limit", DEFAULT_LIMIT)

            # Check abort
            if signal and signal.aborted:
                raise RuntimeError("Operation aborted")

            # Resolve path
            dir_path = resolve_to_cwd(dir_path_param, cwd_str)

            if not await ops.exists(dir_path):
                raise RuntimeError(f"Path not found: {dir_path}")

            stat = await ops.stat(dir_path)
            if not stat["is_directory"]:
                raise RuntimeError(f"Not a directory: {dir_path}")

            # Read directory entries
            try:
                entries = await ops.readdir(dir_path)
            except Exception as e:
                raise RuntimeError(f"Cannot read directory: {e}")

            # Sort alphabetically (case-insensitive)
            entries.sort(key=lambda x: x.lower())

            # Format entries with directory indicators
            results: list[str] = []
            entry_limit_reached = False

            for entry in entries:
                if len(results) >= limit:
                    entry_limit_reached = True
                    break

                entry_path = os.path.join(dir_path, entry)
                try:
                    entry_stat = await ops.stat(entry_path)
                    if entry_stat["is_directory"]:
                        results.append(f"{entry}/")
                    else:
                        results.append(entry)
                except Exception:
                    # If we can't stat, just show the name
                    results.append(entry)

            if not results:
                return AgentToolResult(
                    content=[TextContent(type="text", text="(empty directory)")],
                    details=LsToolDetails(),
                )

            # Join results
            output = "\n".join(results)

            # Apply truncation
            truncation = truncate_head(output)
            output_text = truncation.content

            details = LsToolDetails(
                truncation=truncation if truncation.truncated else None,
                entry_limit_reached=limit if entry_limit_reached else None,
            )

            if truncation.truncated:
                output_text += (
                    f"\n\n[Output truncated. Showing {truncation.output_lines} of {truncation.total_lines} entries.]"
                )
            elif entry_limit_reached:
                output_text += f"\n\n[Showing first {limit} entries. Use limit parameter to see more.]"

            return AgentToolResult(
                content=[TextContent(type="text", text=output_text)],
                details=details,
            )

    return LsTool()


# Default ls tool using current directory
def _get_default_cwd() -> str:
    return os.getcwd()


ls_tool = create_ls_tool(_get_default_cwd())
