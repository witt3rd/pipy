"""Coding tools for file operations and command execution."""

from pipy_agent import AgentTool

from .bash import bash_tool, create_bash_tool, BashOperations, BashToolDetails
from .edit import edit_tool, create_edit_tool, EditOperations, EditToolDetails
from .find import find_tool, create_find_tool, FindOperations, FindToolDetails
from .grep import grep_tool, create_grep_tool, GrepOperations, GrepToolDetails
from .ls import ls_tool, create_ls_tool, LsOperations, LsToolDetails
from .read import read_tool, create_read_tool, ReadOperations, ReadToolDetails
from .write import write_tool, create_write_tool, WriteOperations
from .truncate import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_LINES,
    GREP_MAX_LINE_LENGTH,
    TruncationResult,
    format_size,
    truncate_head,
    truncate_tail,
    truncate_line,
)
from .path_utils import expand_path, resolve_to_cwd, resolve_read_path


# Default tool collections
coding_tools: list[AgentTool] = [read_tool, bash_tool, edit_tool, write_tool]
"""Default tools for full access mode: read, bash, edit, write"""

read_only_tools: list[AgentTool] = [read_tool, grep_tool, find_tool, ls_tool]
"""Read-only tools for exploration: read, grep, find, ls"""


def create_coding_tools(cwd: str) -> list[AgentTool]:
    """Create coding tools configured for a specific working directory."""
    return [
        create_read_tool(cwd),
        create_bash_tool(cwd),
        create_edit_tool(cwd),
        create_write_tool(cwd),
    ]


def create_read_only_tools(cwd: str) -> list[AgentTool]:
    """Create read-only tools configured for a specific working directory."""
    return [
        create_read_tool(cwd),
        create_grep_tool(cwd),
        create_find_tool(cwd),
        create_ls_tool(cwd),
    ]


__all__ = [
    # Tool instances (using process.cwd())
    "read_tool",
    "bash_tool",
    "edit_tool",
    "write_tool",
    "grep_tool",
    "find_tool",
    "ls_tool",
    # Tool collections
    "coding_tools",
    "read_only_tools",
    # Tool factories
    "create_read_tool",
    "create_bash_tool",
    "create_edit_tool",
    "create_write_tool",
    "create_grep_tool",
    "create_find_tool",
    "create_ls_tool",
    "create_coding_tools",
    "create_read_only_tools",
    # Operations protocols
    "ReadOperations",
    "BashOperations",
    "EditOperations",
    "WriteOperations",
    "GrepOperations",
    "FindOperations",
    "LsOperations",
    # Details types
    "ReadToolDetails",
    "BashToolDetails",
    "EditToolDetails",
    "GrepToolDetails",
    "FindToolDetails",
    "LsToolDetails",
    # Truncation utilities
    "DEFAULT_MAX_BYTES",
    "DEFAULT_MAX_LINES",
    "GREP_MAX_LINE_LENGTH",
    "TruncationResult",
    "format_size",
    "truncate_head",
    "truncate_tail",
    "truncate_line",
    # Path utilities
    "expand_path",
    "resolve_to_cwd",
    "resolve_read_path",
]
