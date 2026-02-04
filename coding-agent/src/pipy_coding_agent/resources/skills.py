"""Skill loading from markdown files.

Skills are markdown files with YAML frontmatter that provide specialized
instructions for the AI assistant.

See: https://agentskills.io/specification
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024


@dataclass
class Skill:
    """A loaded skill."""

    name: str
    description: str
    content: str
    file_path: str
    base_dir: str
    source: str
    disable_model_invocation: bool = False


@dataclass
class SkillDiagnostic:
    """Diagnostic message from skill loading."""

    path: str
    message: str
    level: str = "warning"  # "warning" or "error"


@dataclass
class LoadSkillsResult:
    """Result from loading skills."""

    skills: list[Skill] = field(default_factory=list)
    diagnostics: list[SkillDiagnostic] = field(default_factory=list)


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """
    Parse YAML frontmatter from markdown content.

    Returns (frontmatter_dict, body_content).
    """
    if not content.startswith("---"):
        return {}, content

    # Find the closing ---
    lines = content.split("\n")
    end_idx = -1
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx == -1:
        return {}, content

    # Parse frontmatter (simple YAML parsing)
    frontmatter_lines = lines[1:end_idx]
    frontmatter: dict[str, Any] = {}

    for line in frontmatter_lines:
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()

            # Handle quoted strings
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]

            # Handle booleans
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False

            frontmatter[key] = value

    # Body is everything after frontmatter
    body = "\n".join(lines[end_idx + 1:]).strip()

    return frontmatter, body


def validate_skill_name(name: str, parent_dir_name: str) -> list[str]:
    """Validate skill name per Agent Skills spec."""
    errors = []

    if name != parent_dir_name:
        errors.append(f'name "{name}" does not match parent directory "{parent_dir_name}"')

    if len(name) > MAX_NAME_LENGTH:
        errors.append(f"name exceeds {MAX_NAME_LENGTH} characters ({len(name)})")

    if not re.match(r"^[a-z0-9-]+$", name):
        errors.append("name contains invalid characters (must be lowercase a-z, 0-9, hyphens only)")

    if name.startswith("-") or name.endswith("-"):
        errors.append("name must not start or end with a hyphen")

    if "--" in name:
        errors.append("name must not contain consecutive hyphens")

    return errors


def validate_skill_description(description: str | None) -> list[str]:
    """Validate skill description per Agent Skills spec."""
    errors = []

    if not description or not description.strip():
        errors.append("description is required")
    elif len(description) > MAX_DESCRIPTION_LENGTH:
        errors.append(f"description exceeds {MAX_DESCRIPTION_LENGTH} characters ({len(description)})")

    return errors


def load_skill_from_file(
    file_path: Path,
    base_dir: Path,
    source: str,
) -> tuple[Skill | None, list[SkillDiagnostic]]:
    """Load a single skill from a markdown file."""
    diagnostics: list[SkillDiagnostic] = []

    try:
        content = file_path.read_text(encoding="utf-8")
    except IOError as e:
        diagnostics.append(SkillDiagnostic(
            path=str(file_path),
            message=f"Could not read file: {e}",
            level="error",
        ))
        return None, diagnostics

    frontmatter, body = parse_frontmatter(content)

    # Get name and description
    name = frontmatter.get("name", "")
    description = frontmatter.get("description", "")

    # If no frontmatter name, derive from filename
    if not name:
        name = file_path.stem.lower()

    # Validate name
    parent_dir = file_path.parent.name
    if file_path.name.lower() == "skill.md":
        # Standard skill file - name should match directory
        name_errors = validate_skill_name(name, parent_dir)
    else:
        # Direct .md file - more lenient
        name_errors = []
        if not name:
            name = file_path.stem.lower()

    for error in name_errors:
        diagnostics.append(SkillDiagnostic(
            path=str(file_path),
            message=error,
            level="warning",
        ))

    # Validate description (warning only)
    desc_errors = validate_skill_description(description)
    for error in desc_errors:
        diagnostics.append(SkillDiagnostic(
            path=str(file_path),
            message=error,
            level="warning",
        ))

    # If no body content, skip
    if not body.strip():
        diagnostics.append(SkillDiagnostic(
            path=str(file_path),
            message="Skill has no content",
            level="warning",
        ))
        return None, diagnostics

    skill = Skill(
        name=name,
        description=description or f"Skill: {name}",
        content=body,
        file_path=str(file_path),
        base_dir=str(base_dir),
        source=source,
        disable_model_invocation=frontmatter.get("disable-model-invocation", False),
    )

    return skill, diagnostics


def load_skills_from_dir(
    directory: str | Path,
    source: str = "user",
) -> LoadSkillsResult:
    """
    Load skills from a directory.

    Discovery rules:
    - Direct .md files in the root
    - SKILL.md files in subdirectories (recursive)
    """
    directory = Path(directory)
    result = LoadSkillsResult()

    if not directory.exists():
        return result

    # Load direct .md files in root
    for file_path in directory.glob("*.md"):
        if file_path.name.startswith("."):
            continue

        skill, diagnostics = load_skill_from_file(file_path, directory, source)
        result.diagnostics.extend(diagnostics)
        if skill:
            result.skills.append(skill)

    # Load SKILL.md files in subdirectories
    for skill_file in directory.rglob("SKILL.md"):
        # Skip node_modules and hidden directories
        if any(part.startswith(".") or part == "node_modules" for part in skill_file.parts):
            continue

        skill, diagnostics = load_skill_from_file(skill_file, skill_file.parent, source)
        result.diagnostics.extend(diagnostics)
        if skill:
            result.skills.append(skill)

    return result


def load_skills(
    paths: list[str | Path],
    source: str = "user",
) -> LoadSkillsResult:
    """Load skills from multiple paths (files or directories)."""
    result = LoadSkillsResult()

    for path in paths:
        path = Path(path)

        if path.is_file() and path.suffix == ".md":
            # Single file
            skill, diagnostics = load_skill_from_file(path, path.parent, source)
            result.diagnostics.extend(diagnostics)
            if skill:
                result.skills.append(skill)
        elif path.is_dir():
            # Directory
            dir_result = load_skills_from_dir(path, source)
            result.skills.extend(dir_result.skills)
            result.diagnostics.extend(dir_result.diagnostics)

    return result


def format_skills_for_prompt(skills: list[Skill]) -> str:
    """Format skills for inclusion in system prompt."""
    if not skills:
        return ""

    lines = [
        "",
        "The following skills provide specialized instructions for specific tasks.",
        "Use the read tool to load a skill's file when the task matches its description.",
        "When a skill file references a relative path, resolve it against the skill directory "
        "(parent of SKILL.md / dirname of the path) and use that absolute path in tool commands.",
        "",
        "<available_skills>",
    ]

    for skill in skills:
        lines.append(f"- **{skill.name}**: {skill.description} (location: {skill.file_path})")

    lines.append("</available_skills>")
    lines.append("")

    return "\n".join(lines)
