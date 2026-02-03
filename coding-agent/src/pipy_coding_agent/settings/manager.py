"""Settings manager with global/project hierarchy."""

import json
import os
from dataclasses import asdict, fields, is_dataclass
from pathlib import Path
from typing import Any

from .types import (
    CompactionSettings,
    ImageSettings,
    RetrySettings,
    Settings,
    TerminalSettings,
    ThinkingBudgets,
)


CONFIG_DIR_NAME = ".pi"


def get_default_agent_dir() -> Path:
    """Get the default agent configuration directory."""
    return Path.home() / ".pipy"


def deep_merge(base: dict, overrides: dict) -> dict:
    """Deep merge two dictionaries. Overrides take precedence."""
    result = base.copy()

    for key, value in overrides.items():
        if value is None:
            continue

        base_value = result.get(key)

        # For nested dicts, merge recursively
        if (
            isinstance(value, dict)
            and isinstance(base_value, dict)
        ):
            result[key] = deep_merge(base_value, value)
        else:
            result[key] = value

    return result


def dict_to_settings(data: dict) -> Settings:
    """Convert a dictionary to Settings, handling nested dataclasses."""
    # Handle nested dataclasses
    if "compaction" in data and isinstance(data["compaction"], dict):
        data["compaction"] = CompactionSettings(**data["compaction"])
    if "retry" in data and isinstance(data["retry"], dict):
        data["retry"] = RetrySettings(**data["retry"])
    if "images" in data and isinstance(data["images"], dict):
        data["images"] = ImageSettings(**data["images"])
    if "terminal" in data and isinstance(data["terminal"], dict):
        data["terminal"] = TerminalSettings(**data["terminal"])
    if "thinking_budgets" in data and isinstance(data["thinking_budgets"], dict):
        data["thinking_budgets"] = ThinkingBudgets(**data["thinking_budgets"])

    # Filter to only valid Settings fields
    valid_fields = {f.name for f in fields(Settings)}
    filtered_data = {k: v for k, v in data.items() if k in valid_fields}

    return Settings(**filtered_data)


def settings_to_dict(settings: Settings) -> dict:
    """Convert Settings to a dictionary, handling nested dataclasses."""
    result = {}
    for f in fields(settings):
        value = getattr(settings, f.name)
        if is_dataclass(value) and not isinstance(value, type):
            result[f.name] = asdict(value)
        elif value != getattr(Settings, f.name, None):
            # Only include non-default values
            result[f.name] = value
    return result


def migrate_settings(data: dict) -> dict:
    """Migrate old settings format to new format."""
    # Migrate queueMode -> steering_mode
    if "queueMode" in data and "steering_mode" not in data:
        data["steering_mode"] = data.pop("queueMode")

    # Migrate camelCase to snake_case
    key_migrations = {
        "defaultProvider": "default_provider",
        "defaultModel": "default_model",
        "defaultThinkingLevel": "default_thinking_level",
        "steeringMode": "steering_mode",
        "followUpMode": "follow_up_mode",
        "hideThinkingBlock": "hide_thinking_block",
        "shellPath": "shell_path",
        "quietStartup": "quiet_startup",
        "shellCommandPrefix": "shell_command_prefix",
        "enableSkillCommands": "enable_skill_commands",
        "enabledModels": "enabled_models",
        "thinkingBudgets": "thinking_budgets",
    }

    for old_key, new_key in key_migrations.items():
        if old_key in data and new_key not in data:
            data[new_key] = data.pop(old_key)

    # Migrate nested settings
    if "compaction" in data and isinstance(data["compaction"], dict):
        comp = data["compaction"]
        if "reserveTokens" in comp:
            comp["reserve_tokens"] = comp.pop("reserveTokens")
        if "keepRecentTokens" in comp:
            comp["keep_recent_tokens"] = comp.pop("keepRecentTokens")

    if "retry" in data and isinstance(data["retry"], dict):
        retry = data["retry"]
        if "maxRetries" in retry:
            retry["max_retries"] = retry.pop("maxRetries")
        if "baseDelayMs" in retry:
            retry["base_delay_ms"] = retry.pop("baseDelayMs")
        if "maxDelayMs" in retry:
            retry["max_delay_ms"] = retry.pop("maxDelayMs")

    if "images" in data and isinstance(data["images"], dict):
        images = data["images"]
        if "autoResize" in images:
            images["auto_resize"] = images.pop("autoResize")
        if "blockImages" in images:
            images["block_images"] = images.pop("blockImages")

    if "terminal" in data and isinstance(data["terminal"], dict):
        terminal = data["terminal"]
        if "showImages" in terminal:
            terminal["show_images"] = terminal.pop("showImages")
        if "clearOnShrink" in terminal:
            terminal["clear_on_shrink"] = terminal.pop("clearOnShrink")

    # UI settings
    if "doubleEscapeAction" in data:
        data["double_escape_action"] = data.pop("doubleEscapeAction")
    if "autocompleteMaxVisible" in data:
        data["autocomplete_max_visible"] = data.pop("autocompleteMaxVisible")
    if "editorPaddingX" in data:
        data["editor_padding_x"] = data.pop("editorPaddingX")
    if "showHardwareCursor" in data:
        data["show_hardware_cursor"] = data.pop("showHardwareCursor")

    return data


class SettingsManager:
    """
    Manages settings with global/project hierarchy.

    Settings are loaded from:
    1. Global: ~/.pipy/settings.json
    2. Project: <cwd>/.pi/settings.json

    Project settings override global settings.
    """

    def __init__(
        self,
        cwd: str | Path | None = None,
        agent_dir: str | Path | None = None,
        persist: bool = True,
    ):
        """
        Initialize settings manager.

        Args:
            cwd: Working directory for project settings
            agent_dir: Global config directory (default: ~/.pipy)
            persist: Whether to save changes to disk
        """
        self._cwd = Path(cwd) if cwd else Path.cwd()
        self._agent_dir = Path(agent_dir) if agent_dir else get_default_agent_dir()
        self._persist = persist

        # Paths
        self._global_settings_path = self._agent_dir / "settings.json"
        self._project_settings_path = self._cwd / CONFIG_DIR_NAME / "settings.json"

        # Load settings
        self._global_settings: dict = {}
        self._project_settings: dict = {}
        self._settings: Settings = Settings()
        self._modified_fields: set[str] = set()

        self._load()

    @classmethod
    def create(cls, cwd: str | Path | None = None) -> "SettingsManager":
        """Create a settings manager with default paths."""
        return cls(cwd=cwd)

    @classmethod
    def in_memory(cls, settings: Settings | None = None) -> "SettingsManager":
        """Create an in-memory settings manager (no persistence)."""
        manager = cls(persist=False)
        if settings:
            manager._settings = settings
        return manager

    def _load(self) -> None:
        """Load settings from files."""
        # Load global settings
        self._global_settings = self._load_from_file(self._global_settings_path)

        # Load project settings
        self._project_settings = self._load_from_file(self._project_settings_path)

        # Merge: global <- project
        merged = deep_merge(
            self._global_settings,
            self._project_settings,
        )

        # Convert to Settings object
        if merged:
            self._settings = dict_to_settings(merged)
        else:
            self._settings = Settings()

    def _load_from_file(self, path: Path) -> dict:
        """Load settings from a JSON file."""
        if not path.exists():
            return {}

        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            return migrate_settings(data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load settings from {path}: {e}")
            return {}

    def _save(self) -> None:
        """Save modified settings to global file."""
        if not self._persist or not self._modified_fields:
            return

        try:
            # Ensure directory exists
            self._global_settings_path.parent.mkdir(parents=True, exist_ok=True)

            # Load current file to preserve external changes
            current = self._load_from_file(self._global_settings_path)

            # Update only modified fields
            settings_dict = settings_to_dict(self._settings)
            for field_name in self._modified_fields:
                if field_name in settings_dict:
                    current[field_name] = settings_dict[field_name]

            # Write back
            self._global_settings_path.write_text(
                json.dumps(current, indent=2),
                encoding="utf-8",
            )
        except IOError as e:
            print(f"Warning: Could not save settings: {e}")

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def settings(self) -> Settings:
        """Get the merged settings."""
        return self._settings

    @property
    def cwd(self) -> Path:
        return self._cwd

    @property
    def agent_dir(self) -> Path:
        return self._agent_dir

    # =========================================================================
    # Getters (convenience methods)
    # =========================================================================

    def get_default_provider(self) -> str | None:
        return self._settings.default_provider

    def get_default_model(self) -> str | None:
        return self._settings.default_model

    def get_default_thinking_level(self) -> str:
        return self._settings.default_thinking_level

    def get_steering_mode(self) -> str:
        return self._settings.steering_mode

    def get_follow_up_mode(self) -> str:
        return self._settings.follow_up_mode

    def get_theme(self) -> str | None:
        return self._settings.theme

    def get_compaction_settings(self) -> CompactionSettings:
        return self._settings.compaction

    def get_retry_settings(self) -> RetrySettings:
        return self._settings.retry

    def get_image_settings(self) -> ImageSettings:
        return self._settings.images

    def get_terminal_settings(self) -> TerminalSettings:
        return self._settings.terminal

    def get_thinking_budgets(self) -> ThinkingBudgets:
        return self._settings.thinking_budgets

    def get_shell_path(self) -> str | None:
        return self._settings.shell_path

    def get_shell_command_prefix(self) -> str | None:
        return self._settings.shell_command_prefix

    def get_block_images(self) -> bool:
        return self._settings.images.block_images

    def is_quiet_startup(self) -> bool:
        return self._settings.quiet_startup

    def get_skill_paths(self) -> list[str]:
        return self._settings.skills

    def get_prompt_paths(self) -> list[str]:
        return self._settings.prompts

    def get_extension_paths(self) -> list[str]:
        return self._settings.extensions

    def get_theme_paths(self) -> list[str]:
        return self._settings.themes

    def is_skill_commands_enabled(self) -> bool:
        return self._settings.enable_skill_commands

    def get_enabled_models(self) -> list[str]:
        return self._settings.enabled_models

    # =========================================================================
    # Setters
    # =========================================================================

    def set_default_provider(self, provider: str | None) -> None:
        self._settings.default_provider = provider
        self._modified_fields.add("default_provider")
        self._save()

    def set_default_model(self, model: str | None) -> None:
        self._settings.default_model = model
        self._modified_fields.add("default_model")
        self._save()

    def set_default_thinking_level(self, level: str) -> None:
        self._settings.default_thinking_level = level
        self._modified_fields.add("default_thinking_level")
        self._save()

    def set_theme(self, theme: str | None) -> None:
        self._settings.theme = theme
        self._modified_fields.add("theme")
        self._save()

    def set_steering_mode(self, mode: str) -> None:
        self._settings.steering_mode = mode
        self._modified_fields.add("steering_mode")
        self._save()

    def set_follow_up_mode(self, mode: str) -> None:
        self._settings.follow_up_mode = mode
        self._modified_fields.add("follow_up_mode")
        self._save()

    # =========================================================================
    # Raw access
    # =========================================================================

    def get_global_settings(self) -> dict:
        """Get raw global settings dict."""
        return self._global_settings.copy()

    def get_project_settings(self) -> dict:
        """Get raw project settings dict."""
        return self._project_settings.copy()

    def apply_overrides(self, overrides: dict) -> None:
        """Apply additional overrides on top of current settings."""
        merged = deep_merge(settings_to_dict(self._settings), overrides)
        self._settings = dict_to_settings(merged)
