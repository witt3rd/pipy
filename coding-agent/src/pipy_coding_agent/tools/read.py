"""Read tool for reading file contents."""

import base64
import os
from pathlib import Path
from typing import Any, Protocol

from pipy_agent import AgentTool, AgentToolResult, AbortSignal, TextContent, ImageContent

from .path_utils import resolve_read_path
from .truncate import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_LINES,
    TruncationResult,
    format_size,
    truncate_head,
)

# Supported image types and their signatures
IMAGE_SIGNATURES = {
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"RIFF": "image/webp",  # WebP starts with RIFF...WEBP
}


class ReadOperations(Protocol):
    """Pluggable operations for the read tool."""

    async def read_file(self, absolute_path: str) -> bytes:
        """Read file contents as bytes."""
        ...

    async def access(self, absolute_path: str) -> None:
        """Check if file is readable (raise if not)."""
        ...

    async def detect_image_mime_type(self, absolute_path: str) -> str | None:
        """Detect image MIME type, return None for non-images."""
        ...


class DefaultReadOperations:
    """Default read operations using local filesystem."""

    async def read_file(self, absolute_path: str) -> bytes:
        """Read file contents."""
        with open(absolute_path, "rb") as f:
            return f.read()

    async def access(self, absolute_path: str) -> None:
        """Check if file is readable."""
        if not os.path.exists(absolute_path):
            raise FileNotFoundError(f"File not found: {absolute_path}")
        if not os.access(absolute_path, os.R_OK):
            raise PermissionError(f"Permission denied: {absolute_path}")

    async def detect_image_mime_type(self, absolute_path: str) -> str | None:
        """Detect image MIME type from file signature."""
        try:
            with open(absolute_path, "rb") as f:
                header = f.read(12)  # Read enough for all signatures

            # Check for WebP specifically (RIFF....WEBP)
            if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
                return "image/webp"

            # Check other signatures
            for sig, mime_type in IMAGE_SIGNATURES.items():
                if sig == b"RIFF":
                    continue  # Already handled WebP
                if header.startswith(sig):
                    return mime_type

            return None
        except Exception:
            return None


class ReadToolDetails:
    """Details returned by read tool."""

    def __init__(self, truncation: TruncationResult | None = None):
        self.truncation = truncation


READ_PARAMETERS = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Path to the file to read (relative or absolute)",
        },
        "offset": {
            "type": "number",
            "description": "Line number to start reading from (1-indexed)",
        },
        "limit": {
            "type": "number",
            "description": "Maximum number of lines to read",
        },
    },
    "required": ["path"],
}


def create_read_tool(
    cwd: str | Path,
    auto_resize_images: bool = True,
    operations: ReadOperations | None = None,
) -> AgentTool:
    """
    Create a read tool for the given working directory.

    Args:
        cwd: Working directory for relative paths
        auto_resize_images: Whether to auto-resize large images (not yet implemented)
        operations: Custom operations for file reading (default: local filesystem)
    """
    cwd_str = str(cwd)
    ops = operations or DefaultReadOperations()

    class ReadTool(AgentTool):
        name: str = "read"
        label: str = "read"
        description: str = (
            f"Read the contents of a file. Supports text files and images (jpg, png, gif, webp). "
            f"Images are sent as attachments. For text files, output is truncated to {DEFAULT_MAX_LINES} lines "
            f"or {DEFAULT_MAX_BYTES // 1024}KB (whichever is hit first). Use offset/limit for large files. "
            f"When you need the full file, continue with offset until complete."
        )
        parameters: dict[str, Any] = READ_PARAMETERS

        async def execute(
            self,
            tool_call_id: str,
            params: dict[str, Any],
            signal: AbortSignal | None = None,
            on_update=None,
        ) -> AgentToolResult[ReadToolDetails]:
            path = params.get("path", "")
            offset = params.get("offset")
            limit = params.get("limit")

            # Resolve path
            absolute_path = resolve_read_path(path, cwd_str)

            # Check abort
            if signal and signal.aborted:
                raise RuntimeError("Operation aborted")

            # Check file access
            await ops.access(absolute_path)

            # Check abort
            if signal and signal.aborted:
                raise RuntimeError("Operation aborted")

            # Detect if image
            mime_type = await ops.detect_image_mime_type(absolute_path)

            content: list[TextContent | ImageContent]
            details: ReadToolDetails | None = None

            if mime_type:
                # Read as image
                buffer = await ops.read_file(absolute_path)
                data = base64.b64encode(buffer).decode("ascii")

                # TODO: Implement image resizing if auto_resize_images is True
                text_note = f"Read image file [{mime_type}]"
                content = [
                    TextContent(type="text", text=text_note),
                    ImageContent(type="image", data=data, mimeType=mime_type),
                ]
            else:
                # Read as text
                buffer = await ops.read_file(absolute_path)
                text_content = buffer.decode("utf-8")
                all_lines = text_content.split("\n")
                total_file_lines = len(all_lines)

                # Apply offset if specified (1-indexed to 0-indexed)
                start_line = max(0, (offset or 1) - 1)
                start_line_display = start_line + 1  # For display (1-indexed)

                # Check if offset is out of bounds
                if start_line >= len(all_lines):
                    raise ValueError(
                        f"Offset {offset} is beyond end of file ({len(all_lines)} lines total)"
                    )

                # If limit is specified by user, use it
                if limit is not None:
                    end_line = min(start_line + int(limit), len(all_lines))
                    selected_content = "\n".join(all_lines[start_line:end_line])
                    user_limited_lines = end_line - start_line
                else:
                    selected_content = "\n".join(all_lines[start_line:])
                    user_limited_lines = None

                # Apply truncation
                truncation = truncate_head(selected_content)

                if truncation.first_line_exceeds_limit:
                    # First line at offset exceeds limit
                    first_line_size = format_size(len(all_lines[start_line].encode("utf-8")))
                    output_text = (
                        f"[Line {start_line_display} is {first_line_size}, exceeds "
                        f"{format_size(DEFAULT_MAX_BYTES)} limit. Use bash: "
                        f"sed -n '{start_line_display}p' {path} | head -c {DEFAULT_MAX_BYTES}]"
                    )
                    details = ReadToolDetails(truncation=truncation)
                elif truncation.truncated:
                    # Truncation occurred
                    end_line_display = start_line_display + truncation.output_lines - 1
                    next_offset = end_line_display + 1

                    output_text = truncation.content

                    if truncation.truncated_by == "lines":
                        output_text += (
                            f"\n\n[Showing lines {start_line_display}-{end_line_display} "
                            f"of {total_file_lines}. Use offset={next_offset} to continue.]"
                        )
                    else:
                        output_text += (
                            f"\n\n[Showing lines {start_line_display}-{end_line_display} "
                            f"of {total_file_lines} ({format_size(DEFAULT_MAX_BYTES)} limit). "
                            f"Use offset={next_offset} to continue.]"
                        )
                    details = ReadToolDetails(truncation=truncation)
                elif user_limited_lines is not None and start_line + user_limited_lines < len(all_lines):
                    # User specified limit, there's more content
                    remaining = len(all_lines) - (start_line + user_limited_lines)
                    next_offset = start_line + user_limited_lines + 1

                    output_text = truncation.content
                    output_text += f"\n\n[{remaining} more lines in file. Use offset={next_offset} to continue.]"
                else:
                    # No truncation
                    output_text = truncation.content

                content = [TextContent(type="text", text=output_text)]

            # Check abort
            if signal and signal.aborted:
                raise RuntimeError("Operation aborted")

            return AgentToolResult(content=content, details=details)

    return ReadTool()


# Default read tool using current directory
def _get_default_cwd() -> str:
    return os.getcwd()


read_tool = create_read_tool(_get_default_cwd())
