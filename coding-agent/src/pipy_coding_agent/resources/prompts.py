"""Prompt template loading and expansion.

Prompt templates are markdown files with optional frontmatter that can be
invoked with /template-name [args].
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .skills import parse_frontmatter


@dataclass
class PromptTemplate:
    """A loaded prompt template."""

    name: str
    description: str
    content: str
    file_path: str
    source: str


@dataclass
class PromptDiagnostic:
    """Diagnostic message from prompt loading."""

    path: str
    message: str
    level: str = "warning"


@dataclass
class LoadPromptsResult:
    """Result from loading prompts."""

    prompts: list[PromptTemplate] = field(default_factory=list)
    diagnostics: list[PromptDiagnostic] = field(default_factory=list)


def parse_command_args(args_string: str) -> list[str]:
    """
    Parse command arguments respecting quoted strings (bash-style).

    Examples:
        'hello world' -> ['hello', 'world']
        '"hello world"' -> ['hello world']
        'foo "bar baz" qux' -> ['foo', 'bar baz', 'qux']
    """
    args: list[str] = []
    current = ""
    in_quote: str | None = None

    for char in args_string:
        if in_quote:
            if char == in_quote:
                in_quote = None
            else:
                current += char
        elif char in ('"', "'"):
            in_quote = char
        elif char in (" ", "\t"):
            if current:
                args.append(current)
                current = ""
        else:
            current += char

    if current:
        args.append(current)

    return args


def substitute_args(content: str, args: list[str]) -> str:
    """
    Substitute argument placeholders in template content.

    Supports:
    - $1, $2, ... for positional args
    - $@ and $ARGUMENTS for all args joined
    - ${@:N} for args from Nth onwards (bash-style slicing, 1-indexed)
    - ${@:N:L} for L args starting from Nth
    """
    result = content

    # Replace $1, $2, etc. with positional args FIRST (before wildcards)
    def replace_positional(match: re.Match) -> str:
        num = int(match.group(1))
        index = num - 1  # Convert to 0-indexed
        return args[index] if 0 <= index < len(args) else ""

    result = re.sub(r"\$(\d+)", replace_positional, result)

    # Replace ${@:start} or ${@:start:length} with sliced args
    def replace_slice(match: re.Match) -> str:
        start = int(match.group(1)) - 1  # Convert to 0-indexed
        if start < 0:
            start = 0

        if match.group(2):
            length = int(match.group(2))
            return " ".join(args[start : start + length])
        return " ".join(args[start:])

    result = re.sub(r"\$\{@:(\d+)(?::(\d+))?\}", replace_slice, result)

    # Pre-compute all args joined
    all_args = " ".join(args)

    # Replace $ARGUMENTS with all args joined
    result = result.replace("$ARGUMENTS", all_args)

    # Replace $@ with all args joined
    result = result.replace("$@", all_args)

    return result


def load_prompt_from_file(
    file_path: Path,
    source: str,
) -> tuple[PromptTemplate | None, list[PromptDiagnostic]]:
    """Load a single prompt template from a markdown file."""
    diagnostics: list[PromptDiagnostic] = []

    try:
        content = file_path.read_text(encoding="utf-8")
    except IOError as e:
        diagnostics.append(PromptDiagnostic(
            path=str(file_path),
            message=f"Could not read file: {e}",
            level="error",
        ))
        return None, diagnostics

    frontmatter, body = parse_frontmatter(content)

    # Get name from frontmatter or filename
    name = frontmatter.get("name", file_path.stem)
    description = frontmatter.get("description", f"Prompt template: {name}")

    if not body.strip():
        diagnostics.append(PromptDiagnostic(
            path=str(file_path),
            message="Prompt template has no content",
            level="warning",
        ))
        return None, diagnostics

    template = PromptTemplate(
        name=name,
        description=description,
        content=body,
        file_path=str(file_path),
        source=source,
    )

    return template, diagnostics


def load_prompts_from_dir(
    directory: str | Path,
    source: str = "user",
) -> LoadPromptsResult:
    """Load prompt templates from a directory."""
    directory = Path(directory)
    result = LoadPromptsResult()

    if not directory.exists():
        return result

    # Load .md files
    for file_path in directory.glob("*.md"):
        if file_path.name.startswith("."):
            continue

        template, diagnostics = load_prompt_from_file(file_path, source)
        result.diagnostics.extend(diagnostics)
        if template:
            result.prompts.append(template)

    return result


def load_prompts(
    paths: list[str | Path],
    source: str = "user",
) -> LoadPromptsResult:
    """Load prompt templates from multiple paths (files or directories)."""
    result = LoadPromptsResult()

    for path in paths:
        path = Path(path)

        if path.is_file() and path.suffix == ".md":
            template, diagnostics = load_prompt_from_file(path, source)
            result.diagnostics.extend(diagnostics)
            if template:
                result.prompts.append(template)
        elif path.is_dir():
            dir_result = load_prompts_from_dir(path, source)
            result.prompts.extend(dir_result.prompts)
            result.diagnostics.extend(dir_result.diagnostics)

    return result


def expand_prompt_template(template: PromptTemplate, args_string: str = "") -> str:
    """Expand a prompt template with the given arguments."""
    args = parse_command_args(args_string) if args_string else []
    return substitute_args(template.content, args)
