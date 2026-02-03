"""Write tool for creating and writing files."""

import os
from pathlib import Path
from typing import Any, Protocol

from pipy_agent import AgentTool, AgentToolResult, AbortSignal, TextContent

from .path_utils import resolve_to_cwd


class WriteOperations(Protocol):
    """Pluggable operations for the write tool."""

    async def write_file(self, absolute_path: str, content: str) -> None:
        """Write content to a file."""
        ...

    async def mkdir(self, directory: str) -> None:
        """Create directory (recursively)."""
        ...


class DefaultWriteOperations:
    """Default write operations using local filesystem."""

    async def write_file(self, absolute_path: str, content: str) -> None:
        """Write content to file."""
        with open(absolute_path, "w", encoding="utf-8") as f:
            f.write(content)

    async def mkdir(self, directory: str) -> None:
        """Create directory recursively."""
        os.makedirs(directory, exist_ok=True)


WRITE_PARAMETERS = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Path to the file to write (relative or absolute)",
        },
        "content": {
            "type": "string",
            "description": "Content to write to the file",
        },
    },
    "required": ["path", "content"],
}


def create_write_tool(
    cwd: str | Path,
    operations: WriteOperations | None = None,
) -> AgentTool:
    """
    Create a write tool for the given working directory.

    Args:
        cwd: Working directory for relative paths
        operations: Custom operations for file writing (default: local filesystem)
    """
    cwd_str = str(cwd)
    ops = operations or DefaultWriteOperations()

    class WriteTool(AgentTool):
        name: str = "write"
        label: str = "write"
        description: str = (
            "Write content to a file. Creates the file if it doesn't exist, overwrites if it does. "
            "Automatically creates parent directories."
        )
        parameters: dict[str, Any] = WRITE_PARAMETERS

        async def execute(
            self,
            tool_call_id: str,
            params: dict[str, Any],
            signal: AbortSignal | None = None,
            on_update=None,
        ) -> AgentToolResult:
            path = params.get("path", "")
            content = params.get("content", "")

            # Resolve path
            absolute_path = resolve_to_cwd(path, cwd_str)
            directory = os.path.dirname(absolute_path)

            # Check abort
            if signal and signal.aborted:
                raise RuntimeError("Operation aborted")

            # Create parent directories if needed
            if directory:
                await ops.mkdir(directory)

            # Check abort
            if signal and signal.aborted:
                raise RuntimeError("Operation aborted")

            # Write the file
            await ops.write_file(absolute_path, content)

            # Check abort
            if signal and signal.aborted:
                raise RuntimeError("Operation aborted")

            return AgentToolResult(
                content=[TextContent(type="text", text=f"Successfully wrote {len(content)} bytes to {path}")]
            )

    return WriteTool()


# Default write tool using current directory
def _get_default_cwd() -> str:
    return os.getcwd()


write_tool = create_write_tool(_get_default_cwd())
