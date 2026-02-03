"""Bash tool for executing shell commands."""

import asyncio
import os
import sys
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

from pipy_agent import AgentTool, AgentToolResult, AbortSignal, TextContent

from .truncate import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_LINES,
    TruncationResult,
    format_size,
    truncate_tail,
)


@dataclass
class BashSpawnContext:
    """Context for bash spawn hook."""

    command: str
    """The command to execute."""

    cwd: str
    """Working directory for execution."""

    env: dict[str, str] = field(default_factory=lambda: dict(os.environ))
    """Environment variables for execution."""


# Type alias for spawn hook
BashSpawnHook = Callable[[BashSpawnContext], BashSpawnContext]


def _get_temp_file_path() -> str:
    """Generate a unique temp file path for bash output."""
    return os.path.join(tempfile.gettempdir(), f"pipy-bash-{uuid.uuid4().hex[:16]}.log")


class BashToolDetails:
    """Details returned by bash tool."""

    def __init__(
        self,
        truncation: TruncationResult | None = None,
        full_output_path: str | None = None,
    ):
        self.truncation = truncation
        self.full_output_path = full_output_path


class BashOperations(Protocol):
    """Pluggable operations for the bash tool."""

    async def exec(
        self,
        command: str,
        cwd: str,
        on_data: Any,
        signal: AbortSignal | None = None,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
    ) -> dict[str, int | None]:
        """Execute a command and stream output."""
        ...


class DefaultBashOperations:
    """Default bash operations using local shell."""

    async def exec(
        self,
        command: str,
        cwd: str,
        on_data,
        signal: AbortSignal | None = None,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
    ) -> dict[str, int | None]:
        """Execute command using asyncio subprocess."""
        if not os.path.exists(cwd):
            raise RuntimeError(f"Working directory does not exist: {cwd}\nCannot execute bash commands.")

        # Determine shell based on platform
        if sys.platform == "win32":
            # On Windows, use cmd.exe or PowerShell
            shell_cmd = ["cmd.exe", "/c", command]
        else:
            # On Unix, use bash
            shell_cmd = ["/bin/bash", "-c", command]

        # Use provided env or default to current environment
        exec_env = env if env is not None else dict(os.environ)

        process = await asyncio.create_subprocess_exec(
            *shell_cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=exec_env,
        )

        try:
            # Handle timeout and abort
            async def read_output():
                while True:
                    if signal and signal.aborted:
                        process.kill()
                        raise RuntimeError("aborted")

                    try:
                        chunk = await asyncio.wait_for(
                            process.stdout.read(4096),
                            timeout=0.1,  # Check abort frequently
                        )
                        if not chunk:
                            break
                        on_data(chunk)
                    except asyncio.TimeoutError:
                        continue

            if timeout:
                try:
                    await asyncio.wait_for(read_output(), timeout=timeout)
                except asyncio.TimeoutError:
                    process.kill()
                    raise RuntimeError(f"timeout:{timeout}")
            else:
                await read_output()

            await process.wait()
            return {"exitCode": process.returncode}

        except Exception as e:
            try:
                process.kill()
            except Exception:
                pass
            raise e


BASH_PARAMETERS = {
    "type": "object",
    "properties": {
        "command": {
            "type": "string",
            "description": "Bash command to execute",
        },
        "timeout": {
            "type": "number",
            "description": "Timeout in seconds (optional, no default timeout)",
        },
    },
    "required": ["command"],
}


def _resolve_spawn_context(
    command: str,
    cwd: str,
    spawn_hook: BashSpawnHook | None = None,
) -> BashSpawnContext:
    """Resolve spawn context, applying hook if provided."""
    base_context = BashSpawnContext(
        command=command,
        cwd=cwd,
        env=dict(os.environ),
    )
    return spawn_hook(base_context) if spawn_hook else base_context


def create_bash_tool(
    cwd: str | Path,
    operations: BashOperations | None = None,
    command_prefix: str | None = None,
    spawn_hook: BashSpawnHook | None = None,
) -> AgentTool:
    """
    Create a bash tool for the given working directory.

    Args:
        cwd: Working directory for command execution
        operations: Custom operations for command execution (default: local shell)
        command_prefix: Command prefix prepended to every command
        spawn_hook: Hook to adjust command, cwd, or env before execution
    """
    cwd_str = str(cwd)
    ops = operations or DefaultBashOperations()

    class BashTool(AgentTool):
        name: str = "bash"
        label: str = "bash"
        description: str = (
            f"Execute a bash command in the current working directory. Returns stdout and stderr. "
            f"Output is truncated to last {DEFAULT_MAX_LINES} lines or {DEFAULT_MAX_BYTES // 1024}KB "
            f"(whichever is hit first). If truncated, full output is saved to a temp file. "
            f"Optionally provide a timeout in seconds."
        )
        parameters: dict[str, Any] = BASH_PARAMETERS

        async def execute(
            self,
            tool_call_id: str,
            params: dict[str, Any],
            signal: AbortSignal | None = None,
            on_update=None,
        ) -> AgentToolResult[BashToolDetails]:
            command = params.get("command", "")
            timeout = params.get("timeout")

            # Apply command prefix if configured
            prefixed_command = f"{command_prefix}\n{command}" if command_prefix else command

            # Apply spawn hook if configured
            spawn_context = _resolve_spawn_context(prefixed_command, cwd_str, spawn_hook)
            resolved_command = spawn_context.command
            resolved_cwd = spawn_context.cwd
            resolved_env = spawn_context.env

            # Track output
            temp_file_path: str | None = None
            temp_file = None
            total_bytes = 0
            chunks: list[bytes] = []
            chunks_bytes = 0
            max_chunks_bytes = DEFAULT_MAX_BYTES * 2

            def handle_data(data: bytes):
                nonlocal temp_file_path, temp_file, total_bytes, chunks_bytes

                total_bytes += len(data)

                # Start writing to temp file once we exceed the threshold
                if total_bytes > DEFAULT_MAX_BYTES and temp_file_path is None:
                    temp_file_path = _get_temp_file_path()
                    temp_file = open(temp_file_path, "wb")
                    # Write all buffered chunks to the file
                    for chunk in chunks:
                        temp_file.write(chunk)

                # Write to temp file if we have one
                if temp_file:
                    temp_file.write(data)

                # Keep rolling buffer of recent data
                chunks.append(data)
                chunks_bytes += len(data)

                # Trim old chunks if buffer is too large
                while chunks_bytes > max_chunks_bytes and len(chunks) > 1:
                    removed = chunks.pop(0)
                    chunks_bytes -= len(removed)

                # Stream partial output to callback
                if on_update:
                    full_buffer = b"".join(chunks)
                    full_text = full_buffer.decode("utf-8", errors="replace")
                    truncation = truncate_tail(full_text)
                    on_update(
                        AgentToolResult(
                            content=[TextContent(type="text", text=truncation.content or "")],
                            details=BashToolDetails(
                                truncation=truncation if truncation.truncated else None,
                                full_output_path=temp_file_path,
                            ),
                        )
                    )

            try:
                result = await ops.exec(
                    resolved_command,
                    resolved_cwd,
                    handle_data,
                    signal,
                    timeout,
                    resolved_env,
                )
                exit_code = result.get("exitCode")

                # Close temp file
                if temp_file:
                    temp_file.close()

                # Combine all buffered chunks
                full_buffer = b"".join(chunks)
                full_output = full_buffer.decode("utf-8", errors="replace")

                # Apply tail truncation
                truncation = truncate_tail(full_output)
                output_text = truncation.content or "(no output)"

                details: BashToolDetails | None = None

                if truncation.truncated:
                    details = BashToolDetails(
                        truncation=truncation,
                        full_output_path=temp_file_path,
                    )

                    # Build actionable notice
                    start_line = truncation.total_lines - truncation.output_lines + 1
                    end_line = truncation.total_lines

                    if truncation.last_line_partial:
                        last_line = full_output.split("\n")[-1] if full_output else ""
                        last_line_size = format_size(len(last_line.encode("utf-8")))
                        output_text += (
                            f"\n\n[Showing last {format_size(truncation.output_bytes)} of line {end_line} "
                            f"(line is {last_line_size}). Full output: {temp_file_path}]"
                        )
                    elif truncation.truncated_by == "lines":
                        output_text += (
                            f"\n\n[Showing lines {start_line}-{end_line} of {truncation.total_lines}. "
                            f"Full output: {temp_file_path}]"
                        )
                    else:
                        output_text += (
                            f"\n\n[Showing lines {start_line}-{end_line} of {truncation.total_lines} "
                            f"({format_size(DEFAULT_MAX_BYTES)} limit). Full output: {temp_file_path}]"
                        )

                if exit_code is not None and exit_code != 0:
                    output_text += f"\n\nCommand exited with code {exit_code}"
                    raise RuntimeError(output_text)

                return AgentToolResult(content=[TextContent(type="text", text=output_text)], details=details)

            except RuntimeError as e:
                # Close temp file
                if temp_file:
                    temp_file.close()

                error_msg = str(e)

                # Combine all buffered chunks for error output
                full_buffer = b"".join(chunks)
                output = full_buffer.decode("utf-8", errors="replace")

                if error_msg == "aborted":
                    if output:
                        output += "\n\n"
                    output += "Command aborted"
                    raise RuntimeError(output)
                elif error_msg.startswith("timeout:"):
                    timeout_secs = error_msg.split(":")[1]
                    if output:
                        output += "\n\n"
                    output += f"Command timed out after {timeout_secs} seconds"
                    raise RuntimeError(output)
                else:
                    raise

    return BashTool()


# Default bash tool using current directory
def _get_default_cwd() -> str:
    return os.getcwd()


bash_tool = create_bash_tool(_get_default_cwd())
