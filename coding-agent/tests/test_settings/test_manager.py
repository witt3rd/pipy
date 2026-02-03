"""Tests for settings manager."""

import json
import os
import tempfile
import pytest

from pipy_coding_agent.settings import (
    Settings,
    SettingsManager,
    CompactionSettings,
    deep_merge,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestDeepMerge:
    def test_simple_merge(self):
        """Test merging flat dictionaries."""
        base = {"a": 1, "b": 2}
        overrides = {"b": 3, "c": 4}

        result = deep_merge(base, overrides)

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        """Test merging nested dictionaries."""
        base = {"a": {"x": 1, "y": 2}}
        overrides = {"a": {"y": 3, "z": 4}}

        result = deep_merge(base, overrides)

        assert result == {"a": {"x": 1, "y": 3, "z": 4}}

    def test_override_none_ignored(self):
        """Test that None values in overrides are ignored."""
        base = {"a": 1, "b": 2}
        overrides = {"a": None, "c": 3}

        result = deep_merge(base, overrides)

        assert result == {"a": 1, "b": 2, "c": 3}


class TestSettingsManagerBasic:
    def test_in_memory(self):
        """Test creating in-memory settings."""
        manager = SettingsManager.in_memory()

        assert manager.settings is not None
        assert manager.get_default_thinking_level() == "medium"

    def test_in_memory_with_settings(self):
        """Test in-memory with custom settings."""
        settings = Settings(default_provider="anthropic")
        manager = SettingsManager.in_memory(settings)

        assert manager.get_default_provider() == "anthropic"

    def test_default_values(self):
        """Test default values."""
        manager = SettingsManager.in_memory()

        assert manager.get_default_provider() is None
        assert manager.get_default_model() is None
        assert manager.get_default_thinking_level() == "medium"
        assert manager.get_steering_mode() == "all"
        assert manager.get_follow_up_mode() == "all"
        assert not manager.is_quiet_startup()
        assert manager.is_skill_commands_enabled()


class TestSettingsManagerPersistence:
    def test_create_with_paths(self, temp_dir):
        """Test creating with explicit paths."""
        manager = SettingsManager(
            cwd=temp_dir,
            agent_dir=temp_dir,
        )

        assert str(manager.cwd) == temp_dir
        assert str(manager.agent_dir) == temp_dir

    def test_load_global_settings(self, temp_dir):
        """Test loading global settings from file."""
        settings_path = os.path.join(temp_dir, "settings.json")
        with open(settings_path, "w") as f:
            json.dump({
                "default_provider": "openai",
                "default_model": "gpt-4",
            }, f)

        manager = SettingsManager(cwd=temp_dir, agent_dir=temp_dir)

        assert manager.get_default_provider() == "openai"
        assert manager.get_default_model() == "gpt-4"

    def test_load_project_settings(self, temp_dir):
        """Test loading project settings."""
        # Create project settings dir
        project_dir = os.path.join(temp_dir, ".pi")
        os.makedirs(project_dir)
        settings_path = os.path.join(project_dir, "settings.json")
        with open(settings_path, "w") as f:
            json.dump({"theme": "dark"}, f)

        manager = SettingsManager(cwd=temp_dir, agent_dir=temp_dir)

        assert manager.get_theme() == "dark"

    def test_project_overrides_global(self, temp_dir):
        """Test that project settings override global."""
        # Global settings
        global_path = os.path.join(temp_dir, "settings.json")
        with open(global_path, "w") as f:
            json.dump({
                "default_provider": "anthropic",
                "theme": "light",
            }, f)

        # Project settings
        project_dir = os.path.join(temp_dir, ".pi")
        os.makedirs(project_dir)
        project_path = os.path.join(project_dir, "settings.json")
        with open(project_path, "w") as f:
            json.dump({"theme": "dark"}, f)

        manager = SettingsManager(cwd=temp_dir, agent_dir=temp_dir)

        assert manager.get_default_provider() == "anthropic"  # From global
        assert manager.get_theme() == "dark"  # From project (override)

    def test_save_settings(self, temp_dir):
        """Test saving modified settings."""
        manager = SettingsManager(cwd=temp_dir, agent_dir=temp_dir)

        manager.set_default_provider("anthropic")
        manager.set_default_model("claude-3-opus")

        # Reload and verify
        manager2 = SettingsManager(cwd=temp_dir, agent_dir=temp_dir)
        assert manager2.get_default_provider() == "anthropic"
        assert manager2.get_default_model() == "claude-3-opus"


class TestSettingsManagerMigration:
    def test_migrate_camel_case(self, temp_dir):
        """Test migrating camelCase keys to snake_case."""
        settings_path = os.path.join(temp_dir, "settings.json")
        with open(settings_path, "w") as f:
            json.dump({
                "defaultProvider": "anthropic",
                "defaultModel": "claude-3",
                "quietStartup": True,
            }, f)

        manager = SettingsManager(cwd=temp_dir, agent_dir=temp_dir)

        assert manager.get_default_provider() == "anthropic"
        assert manager.get_default_model() == "claude-3"
        assert manager.is_quiet_startup()


class TestSettingsManagerGettersSetters:
    def test_set_theme(self):
        """Test setting theme."""
        manager = SettingsManager.in_memory()

        manager.set_theme("monokai")

        assert manager.get_theme() == "monokai"

    def test_set_steering_mode(self):
        """Test setting steering mode."""
        manager = SettingsManager.in_memory()

        manager.set_steering_mode("one-at-a-time")

        assert manager.get_steering_mode() == "one-at-a-time"

    def test_get_compaction_settings(self):
        """Test getting compaction settings."""
        manager = SettingsManager.in_memory()

        compaction = manager.get_compaction_settings()

        assert compaction.enabled
        assert compaction.reserve_tokens == 16384
        assert compaction.keep_recent_tokens == 20000

    def test_get_retry_settings(self):
        """Test getting retry settings."""
        manager = SettingsManager.in_memory()

        retry = manager.get_retry_settings()

        assert retry.enabled
        assert retry.max_retries == 3
        assert retry.base_delay_ms == 2000

    def test_apply_overrides(self):
        """Test applying overrides."""
        manager = SettingsManager.in_memory()

        manager.apply_overrides({
            "default_provider": "openai",
            "quiet_startup": True,
        })

        assert manager.get_default_provider() == "openai"
        assert manager.is_quiet_startup()
