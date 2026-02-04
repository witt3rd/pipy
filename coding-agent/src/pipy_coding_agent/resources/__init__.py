"""Resource loading for skills, prompts, and context files."""

from .loader import (
    ContextFile,
    DefaultResourceLoader,
    ResourceLoader,
    ResourceLoaderResult,
    load_ancestor_context_files,
    load_context_file_from_dir,
)
from .prompts import (
    LoadPromptsResult,
    PromptDiagnostic,
    PromptTemplate,
    expand_prompt_template,
    load_prompt_from_file,
    load_prompts,
    load_prompts_from_dir,
    parse_command_args,
    substitute_args,
)
from .skills import (
    LoadSkillsResult,
    Skill,
    SkillDiagnostic,
    format_skills_for_prompt,
    load_skill_from_file,
    load_skills,
    load_skills_from_dir,
    parse_frontmatter,
)

__all__ = [
    # Loader
    "ResourceLoader",
    "DefaultResourceLoader",
    "ResourceLoaderResult",
    "ContextFile",
    "load_context_file_from_dir",
    "load_ancestor_context_files",
    # Skills
    "Skill",
    "SkillDiagnostic",
    "LoadSkillsResult",
    "load_skills",
    "load_skills_from_dir",
    "load_skill_from_file",
    "format_skills_for_prompt",
    "parse_frontmatter",

    # Prompts
    "PromptTemplate",
    "PromptDiagnostic",
    "LoadPromptsResult",
    "load_prompts",
    "load_prompts_from_dir",
    "load_prompt_from_file",
    "expand_prompt_template",
    "parse_command_args",
    "substitute_args",
]
