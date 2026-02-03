"""Extension loading and management."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from ..resources import parse_frontmatter


@dataclass
class ExtensionManifest:
    """Extension manifest from package.json or frontmatter."""

    name: str
    """Extension name."""

    version: str = "0.0.0"
    """Extension version."""

    description: str = ""
    """Extension description."""

    author: str = ""
    """Extension author."""

    main: str | None = None
    """Main entry point (Python module)."""

    skills: list[str] = field(default_factory=list)
    """Skill files provided by extension."""

    prompts: list[str] = field(default_factory=list)
    """Prompt template files."""

    tools: list[str] = field(default_factory=list)
    """Tool definitions."""

    hooks: dict[str, str] = field(default_factory=dict)
    """Hook handlers (hook_name -> function_path)."""


@dataclass
class Extension:
    """A loaded extension."""

    manifest: ExtensionManifest
    """Extension manifest."""

    path: Path
    """Path to extension directory."""

    loaded: bool = False
    """Whether the extension is loaded."""

    error: str | None = None
    """Error message if loading failed."""

    module: Any = None
    """Loaded Python module (if any)."""


def load_manifest_from_json(path: Path) -> ExtensionManifest | None:
    """Load manifest from package.json or extension.json."""
    for filename in ["extension.json", "package.json"]:
        json_path = path / filename
        if json_path.exists():
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                return ExtensionManifest(
                    name=data.get("name", path.name),
                    version=data.get("version", "0.0.0"),
                    description=data.get("description", ""),
                    author=data.get("author", ""),
                    main=data.get("main"),
                    skills=data.get("skills", []),
                    prompts=data.get("prompts", []),
                    tools=data.get("tools", []),
                    hooks=data.get("hooks", {}),
                )
            except (json.JSONDecodeError, IOError):
                pass
    return None


def load_manifest_from_readme(path: Path) -> ExtensionManifest | None:
    """Load manifest from README.md frontmatter."""
    readme_path = path / "README.md"
    if not readme_path.exists():
        return None

    try:
        content = readme_path.read_text(encoding="utf-8")
        frontmatter, _ = parse_frontmatter(content)

        if not frontmatter:
            return None

        return ExtensionManifest(
            name=frontmatter.get("name", path.name),
            version=frontmatter.get("version", "0.0.0"),
            description=frontmatter.get("description", ""),
            author=frontmatter.get("author", ""),
            main=frontmatter.get("main"),
        )
    except IOError:
        return None


def load_extension(path: str | Path) -> Extension:
    """
    Load an extension from a directory.

    Args:
        path: Path to extension directory

    Returns:
        Extension object
    """
    path = Path(path)

    if not path.exists():
        return Extension(
            manifest=ExtensionManifest(name=path.name),
            path=path,
            error=f"Extension path does not exist: {path}",
        )

    if not path.is_dir():
        return Extension(
            manifest=ExtensionManifest(name=path.name),
            path=path,
            error=f"Extension path is not a directory: {path}",
        )

    # Try to load manifest
    manifest = load_manifest_from_json(path)
    if manifest is None:
        manifest = load_manifest_from_readme(path)
    if manifest is None:
        manifest = ExtensionManifest(name=path.name)

    ext = Extension(
        manifest=manifest,
        path=path,
        loaded=True,
    )

    # Try to load Python module if specified
    if manifest.main:
        try:
            import importlib.util
            module_path = path / manifest.main
            if module_path.exists():
                spec = importlib.util.spec_from_file_location(
                    manifest.name, module_path
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    ext.module = module
        except Exception as e:
            ext.error = f"Failed to load module: {e}"

    return ext


def load_extensions_from_dir(directory: str | Path) -> list[Extension]:
    """
    Load all extensions from a directory.

    Each subdirectory is treated as a potential extension.

    Args:
        directory: Directory containing extensions

    Returns:
        List of loaded extensions
    """
    directory = Path(directory)
    extensions: list[Extension] = []

    if not directory.exists():
        return extensions

    for item in directory.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            ext = load_extension(item)
            extensions.append(ext)

    return extensions


class ExtensionLoader:
    """
    Manages extension loading and lifecycle.

    Loads extensions from:
    - Global: ~/.pipy/extensions/
    - Project: <cwd>/.pi/extensions/
    - Custom paths
    """

    def __init__(
        self,
        cwd: str | Path | None = None,
        agent_dir: str | Path | None = None,
    ):
        """
        Initialize extension loader.

        Args:
            cwd: Working directory for project extensions
            agent_dir: Global config directory
        """
        self._cwd = Path(cwd) if cwd else Path.cwd()
        self._agent_dir = Path(agent_dir) if agent_dir else Path.home() / ".pipy"
        self._extensions: dict[str, Extension] = {}

    def load_all(self) -> list[Extension]:
        """Load extensions from all sources."""
        extensions: list[Extension] = []

        # Global extensions
        global_dir = self._agent_dir / "extensions"
        extensions.extend(load_extensions_from_dir(global_dir))

        # Project extensions
        project_dir = self._cwd / ".pi" / "extensions"
        extensions.extend(load_extensions_from_dir(project_dir))

        # Store by name
        for ext in extensions:
            self._extensions[ext.manifest.name] = ext

        return extensions

    def get(self, name: str) -> Extension | None:
        """Get extension by name."""
        return self._extensions.get(name)

    def list(self) -> list[Extension]:
        """List all loaded extensions."""
        return list(self._extensions.values())
