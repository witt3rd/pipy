"""System prompt construction and project context loading."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from ..resources import Skill, ContextFile, format_skills_for_prompt


# Tool descriptions for system prompt
TOOL_DESCRIPTIONS: dict[str, str] = {
    "Read": "Read file contents",
    "Bash": "Execute bash commands (ls, grep, find, etc.)",
    "Edit": "Make surgical edits to files (find exact text and replace)",
    "Write": "Create or overwrite files",
    "Grep": "Search file contents for patterns",
    "Find": "Find files by glob pattern",
    "Ls": "List directory contents",
}


@dataclass
class BuildSystemPromptOptions:
    """Options for building system prompt."""

    custom_prompt: str | None = None
    """Custom system prompt (replaces default)."""

    selected_tools: list[str] | None = None
    """Tools to include in prompt. Default: [Read, Bash, Edit, Write]"""

    append_system_prompt: str | None = None
    """Text to append to system prompt."""

    cwd: str | Path | None = None
    """Working directory. Default: current directory"""

    context_files: list[ContextFile] = field(default_factory=list)
    """Pre-loaded context files."""

    skills: list[Skill] = field(default_factory=list)
    """Pre-loaded skills."""

    docs_path: str | None = None
    """Path to documentation."""

    examples_path: str | None = None
    """Path to examples."""


def _get_datetime_string() -> str:
    """Get formatted current date/time string."""
    now = datetime.now()
    return now.strftime("%A, %B %d, %Y at %I:%M:%S %p %Z").strip()


def _build_tools_section(tools: list[str]) -> str:
    """Build the tools list section."""
    if not tools:
        return "(none)"

    lines = []
    for tool in tools:
        desc = TOOL_DESCRIPTIONS.get(tool, f"{tool} tool")
        lines.append(f"- {tool.lower()}: {desc}")
    return "\n".join(lines)


def _build_guidelines(tools: list[str]) -> str:
    """Build guidelines based on available tools."""
    guidelines: list[str] = []

    has_bash = "Bash" in tools
    has_edit = "Edit" in tools
    has_write = "Write" in tools
    has_grep = "Grep" in tools
    has_find = "Find" in tools
    has_ls = "Ls" in tools
    has_read = "Read" in tools

    # File exploration guidelines
    if has_bash and not has_grep and not has_find and not has_ls:
        guidelines.append("Use bash for file operations like ls, rg, find")
    elif has_bash and (has_grep or has_find or has_ls):
        guidelines.append("Prefer grep/find/ls tools over bash for file exploration")

    # Read before edit
    if has_read and has_edit:
        guidelines.append("Use read to examine files before editing. You must use this tool instead of cat or sed.")

    # Edit guideline
    if has_edit:
        guidelines.append("Use edit for precise changes (old text must match exactly)")

    # Write guideline
    if has_write:
        guidelines.append("Use write only for new files or complete rewrites")

    # Output guideline
    if has_edit or has_write:
        guidelines.append(
            "When summarizing your actions, output plain text directly - do NOT use cat or bash to display what you did"
        )

    # Always include
    guidelines.append("Be concise in your responses")
    guidelines.append("Show file paths clearly when working with files")

    return "\n".join(f"- {g}" for g in guidelines)


def _build_context_section(context_files: list[ContextFile]) -> str:
    """Build the project context section."""
    if not context_files:
        return ""

    parts = ["\n\n# Project Context\n", "Project-specific instructions and guidelines:\n"]
    for ctx in context_files:
        parts.append(f"\n## {ctx.path}\n\n{ctx.content}\n")

    return "".join(parts)


def build_system_prompt(options: BuildSystemPromptOptions | None = None) -> str:
    """
    Build the system prompt with tools, guidelines, and context.

    Args:
        options: Build options

    Returns:
        Complete system prompt string
    """
    if options is None:
        options = BuildSystemPromptOptions()

    cwd = Path(options.cwd) if options.cwd else Path.cwd()
    date_time = _get_datetime_string()
    append_section = f"\n\n{options.append_system_prompt}" if options.append_system_prompt else ""

    # Handle custom prompt
    if options.custom_prompt:
        prompt = options.custom_prompt

        if append_section:
            prompt += append_section

        # Append context files
        prompt += _build_context_section(options.context_files)

        # Append skills (if read tool available)
        tools = options.selected_tools or ["Read", "Bash", "Edit", "Write"]
        if "Read" in tools and options.skills:
            prompt += "\n" + format_skills_for_prompt(options.skills)

        # Add date/time and cwd
        prompt += f"\n\nCurrent date and time: {date_time}"
        prompt += f"\nCurrent working directory: {cwd}"

        return prompt

    # Build default prompt
    tools = options.selected_tools or ["Read", "Bash", "Edit", "Write"]
    tools_list = _build_tools_section(tools)
    guidelines = _build_guidelines(tools)

    # Documentation paths
    docs_path = options.docs_path or "~/.pipy/docs"
    examples_path = options.examples_path or "~/.pipy/examples"

    prompt = f"""You are an expert coding assistant operating inside pipy, a coding agent. You help users by reading files, executing commands, editing code, and writing new files.

Available tools:
{tools_list}

In addition to the tools above, you may have access to other custom tools depending on the project.

Guidelines:
{guidelines}

Documentation (read only when asked about pipy itself):
- Main docs: {docs_path}
- Examples: {examples_path}"""

    if append_section:
        prompt += append_section

    # Append context files
    prompt += _build_context_section(options.context_files)

    # Append skills (if read tool available)
    if "Read" in tools and options.skills:
        prompt += "\n" + format_skills_for_prompt(options.skills)

    # Add date/time and cwd
    prompt += f"\n\nCurrent date and time: {date_time}"
    prompt += f"\nCurrent working directory: {cwd}"

    return prompt
