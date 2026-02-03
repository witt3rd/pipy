"""Resource loader for skills, prompts, and context files.

Loads resources from:
1. Global directory (~/.pipy/)
2. Project directory (<cwd>/.pi/)
3. Ancestor directories (CLAUDE.md, AGENTS.md files)
4. Custom paths from settings
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from ..settings import SettingsManager, get_default_agent_dir, CONFIG_DIR_NAME
from .prompts import LoadPromptsResult, PromptTemplate, load_prompts, load_prompts_from_dir
from .skills import LoadSkillsResult, Skill, load_skills, load_skills_from_dir


@dataclass
class ContextFile:
    """A context file (CLAUDE.md or AGENTS.md)."""

    path: str
    content: str


@dataclass
class ResourceLoaderResult:
    """Aggregated result from resource loading."""

    skills: list[Skill] = field(default_factory=list)
    prompts: list[PromptTemplate] = field(default_factory=list)
    context_files: list[ContextFile] = field(default_factory=list)
    system_prompt: str | None = None


class ResourceLoader(Protocol):
    """Protocol for resource loaders."""

    def get_skills(self) -> LoadSkillsResult:
        ...

    def get_prompts(self) -> LoadPromptsResult:
        ...

    def get_context_files(self) -> list[ContextFile]:
        ...

    def get_system_prompt(self) -> str | None:
        ...

    def reload(self) -> None:
        ...


def load_context_file_from_dir(directory: Path) -> ContextFile | None:
    """Load AGENTS.md or CLAUDE.md from a directory."""
    candidates = ["AGENTS.md", "CLAUDE.md"]

    for filename in candidates:
        file_path = directory / filename
        if file_path.exists():
            try:
                content = file_path.read_text(encoding="utf-8")
                return ContextFile(path=str(file_path), content=content)
            except IOError:
                pass

    return None


def load_ancestor_context_files(cwd: Path, agent_dir: Path) -> list[ContextFile]:
    """
    Load context files from cwd and all ancestor directories.

    Also includes global context from agent_dir.
    Returns files ordered from global -> root -> cwd (inner files last).
    """
    context_files: list[ContextFile] = []
    seen_paths: set[str] = set()

    # Global context first
    global_ctx = load_context_file_from_dir(agent_dir)
    if global_ctx:
        context_files.append(global_ctx)
        seen_paths.add(global_ctx.path)

    # Walk from root to cwd, collecting context files
    ancestor_files: list[ContextFile] = []
    current = cwd.resolve()
    root = Path(current.anchor)

    while True:
        ctx_file = load_context_file_from_dir(current)
        if ctx_file and ctx_file.path not in seen_paths:
            ancestor_files.insert(0, ctx_file)  # Prepend (root-first order)
            seen_paths.add(ctx_file.path)

        if current == root:
            break

        parent = current.parent
        if parent == current:
            break
        current = parent

    context_files.extend(ancestor_files)

    return context_files


class DefaultResourceLoader:
    """
    Default resource loader implementation.

    Loads resources from:
    - Global: ~/.pipy/skills/, ~/.pipy/prompts/
    - Project: <cwd>/.pi/skills/, <cwd>/.pi/prompts/
    - Custom paths from settings
    - Context files (CLAUDE.md, AGENTS.md) from ancestors
    """

    def __init__(
        self,
        cwd: str | Path | None = None,
        agent_dir: str | Path | None = None,
        settings_manager: SettingsManager | None = None,
        system_prompt: str | None = None,
    ):
        """
        Initialize resource loader.

        Args:
            cwd: Working directory
            agent_dir: Global config directory
            settings_manager: Settings manager (optional)
            system_prompt: Override system prompt
        """
        self._cwd = Path(cwd) if cwd else Path.cwd()
        self._agent_dir = Path(agent_dir) if agent_dir else get_default_agent_dir()
        self._settings = settings_manager or SettingsManager.in_memory()
        self._system_prompt_override = system_prompt

        # Cached results
        self._skills_result: LoadSkillsResult | None = None
        self._prompts_result: LoadPromptsResult | None = None
        self._context_files: list[ContextFile] | None = None

    def reload(self) -> None:
        """Reload all resources."""
        self._skills_result = None
        self._prompts_result = None
        self._context_files = None

    def get_skills(self) -> LoadSkillsResult:
        """Get loaded skills."""
        if self._skills_result is None:
            self._skills_result = self._load_skills()
        return self._skills_result

    def get_prompts(self) -> LoadPromptsResult:
        """Get loaded prompt templates."""
        if self._prompts_result is None:
            self._prompts_result = self._load_prompts()
        return self._prompts_result

    def get_context_files(self) -> list[ContextFile]:
        """Get loaded context files."""
        if self._context_files is None:
            self._context_files = load_ancestor_context_files(self._cwd, self._agent_dir)
        return self._context_files

    def get_system_prompt(self) -> str | None:
        """Get system prompt override."""
        return self._system_prompt_override

    def _load_skills(self) -> LoadSkillsResult:
        """Load skills from all sources."""
        result = LoadSkillsResult()
        seen_names: set[str] = set()

        # Helper to add skills, avoiding duplicates
        def add_skills(skills_result: LoadSkillsResult, source_priority: int) -> None:
            for skill in skills_result.skills:
                if skill.name not in seen_names:
                    result.skills.append(skill)
                    seen_names.add(skill.name)
            result.diagnostics.extend(skills_result.diagnostics)

        # 1. Custom paths from settings (highest priority)
        custom_paths = self._settings.get_skill_paths()
        if custom_paths:
            custom_result = load_skills(
                [Path(p) if not Path(p).is_absolute() else Path(p) for p in custom_paths],
                source="settings",
            )
            add_skills(custom_result, 0)

        # 2. Project skills
        project_skills_dir = self._cwd / CONFIG_DIR_NAME / "skills"
        if project_skills_dir.exists():
            project_result = load_skills_from_dir(project_skills_dir, source="project")
            add_skills(project_result, 1)

        # 3. Global skills
        global_skills_dir = self._agent_dir / "skills"
        if global_skills_dir.exists():
            global_result = load_skills_from_dir(global_skills_dir, source="global")
            add_skills(global_result, 2)

        return result

    def _load_prompts(self) -> LoadPromptsResult:
        """Load prompts from all sources."""
        result = LoadPromptsResult()
        seen_names: set[str] = set()

        # Helper to add prompts, avoiding duplicates
        def add_prompts(prompts_result: LoadPromptsResult) -> None:
            for prompt in prompts_result.prompts:
                if prompt.name not in seen_names:
                    result.prompts.append(prompt)
                    seen_names.add(prompt.name)
            result.diagnostics.extend(prompts_result.diagnostics)

        # 1. Custom paths from settings
        custom_paths = self._settings.get_prompt_paths()
        if custom_paths:
            custom_result = load_prompts(
                [Path(p) for p in custom_paths],
                source="settings",
            )
            add_prompts(custom_result)

        # 2. Project prompts
        project_prompts_dir = self._cwd / CONFIG_DIR_NAME / "prompts"
        if project_prompts_dir.exists():
            project_result = load_prompts_from_dir(project_prompts_dir, source="project")
            add_prompts(project_result)

        # 3. Global prompts
        global_prompts_dir = self._agent_dir / "prompts"
        if global_prompts_dir.exists():
            global_result = load_prompts_from_dir(global_prompts_dir, source="global")
            add_prompts(global_result)

        return result

    def build_system_prompt(self) -> str:
        """Build the complete system prompt from all sources."""
        parts: list[str] = []

        # System prompt override
        if self._system_prompt_override:
            parts.append(self._system_prompt_override)

        # Context files
        for ctx_file in self.get_context_files():
            parts.append(f"# Context from {ctx_file.path}\n\n{ctx_file.content}")

        # Skills
        skills = self.get_skills().skills
        if skills:
            from .skills import format_skills_for_prompt
            parts.append(format_skills_for_prompt(skills))

        return "\n\n".join(parts)
