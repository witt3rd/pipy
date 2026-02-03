"""Tests for resource loader."""

import os
import tempfile
import pytest
from pathlib import Path

from pipy_coding_agent.resources import (
    DefaultResourceLoader,
    ContextFile,
    load_context_file_from_dir,
    load_ancestor_context_files,
)
from pipy_coding_agent.settings import SettingsManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestLoadContextFileFromDir:
    def test_load_claude_md(self, temp_dir):
        """Test loading CLAUDE.md."""
        claude_path = Path(temp_dir) / "CLAUDE.md"
        claude_path.write_text("# Claude Instructions\n\nDo the thing.")

        result = load_context_file_from_dir(Path(temp_dir))

        assert result is not None
        assert "CLAUDE.md" in result.path
        assert "Do the thing." in result.content

    def test_load_agents_md(self, temp_dir):
        """Test loading AGENTS.md."""
        agents_path = Path(temp_dir) / "AGENTS.md"
        agents_path.write_text("# Agent Instructions")

        result = load_context_file_from_dir(Path(temp_dir))

        assert result is not None
        assert "AGENTS.md" in result.path

    def test_claude_takes_precedence(self, temp_dir):
        """Test that AGENTS.md takes precedence over CLAUDE.md."""
        (Path(temp_dir) / "AGENTS.md").write_text("From AGENTS")
        (Path(temp_dir) / "CLAUDE.md").write_text("From CLAUDE")

        result = load_context_file_from_dir(Path(temp_dir))

        # AGENTS.md is checked first
        assert "AGENTS" in result.path

    def test_no_context_file(self, temp_dir):
        """Test directory with no context file."""
        result = load_context_file_from_dir(Path(temp_dir))
        assert result is None


class TestLoadAncestorContextFiles:
    def test_load_from_cwd(self, temp_dir):
        """Test loading context file from cwd."""
        (Path(temp_dir) / "CLAUDE.md").write_text("Project context")
        agent_dir = Path(temp_dir) / ".pipy"
        agent_dir.mkdir()

        files = load_ancestor_context_files(Path(temp_dir), agent_dir)

        assert len(files) == 1
        assert "Project context" in files[0].content

    def test_load_from_global(self, temp_dir):
        """Test loading context file from global dir."""
        agent_dir = Path(temp_dir) / ".pipy"
        agent_dir.mkdir()
        (agent_dir / "CLAUDE.md").write_text("Global context")

        cwd = Path(temp_dir) / "project"
        cwd.mkdir()

        files = load_ancestor_context_files(cwd, agent_dir)

        assert len(files) == 1
        assert "Global context" in files[0].content

    def test_load_from_ancestors(self, temp_dir):
        """Test loading context files from ancestor directories."""
        # Create nested structure
        parent = Path(temp_dir) / "parent"
        child = parent / "child"
        child.mkdir(parents=True)

        (parent / "CLAUDE.md").write_text("Parent context")
        (child / "CLAUDE.md").write_text("Child context")

        agent_dir = Path(temp_dir) / ".pipy"
        agent_dir.mkdir()

        files = load_ancestor_context_files(child, agent_dir)

        # Should have both parent and child (parent first)
        assert len(files) == 2
        assert "Parent context" in files[0].content
        assert "Child context" in files[1].content


class TestDefaultResourceLoader:
    def test_create_loader(self, temp_dir):
        """Test creating a resource loader."""
        loader = DefaultResourceLoader(cwd=temp_dir, agent_dir=temp_dir)

        skills = loader.get_skills()
        prompts = loader.get_prompts()

        assert skills.skills == []
        assert prompts.prompts == []

    def test_load_project_skills(self, temp_dir):
        """Test loading skills from project directory."""
        skills_dir = Path(temp_dir) / ".pi" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "test.md").write_text("""---
name: test
description: Test skill
---
Test content.""")

        loader = DefaultResourceLoader(cwd=temp_dir, agent_dir=temp_dir)

        skills = loader.get_skills()
        assert len(skills.skills) == 1
        assert skills.skills[0].name == "test"

    def test_load_global_skills(self, temp_dir):
        """Test loading skills from global directory."""
        agent_dir = Path(temp_dir) / ".pipy"
        skills_dir = agent_dir / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "global.md").write_text("""---
name: global
description: Global skill
---
Global content.""")

        loader = DefaultResourceLoader(cwd=temp_dir, agent_dir=agent_dir)

        skills = loader.get_skills()
        assert len(skills.skills) == 1
        assert skills.skills[0].name == "global"

    def test_load_project_prompts(self, temp_dir):
        """Test loading prompts from project directory."""
        prompts_dir = Path(temp_dir) / ".pi" / "prompts"
        prompts_dir.mkdir(parents=True)
        (prompts_dir / "test.md").write_text("""---
name: test-prompt
description: Test prompt
---
Hello $1!""")

        loader = DefaultResourceLoader(cwd=temp_dir, agent_dir=temp_dir)

        prompts = loader.get_prompts()
        assert len(prompts.prompts) == 1
        assert prompts.prompts[0].name == "test-prompt"

    def test_reload(self, temp_dir):
        """Test reloading resources."""
        skills_dir = Path(temp_dir) / ".pi" / "skills"
        skills_dir.mkdir(parents=True)

        loader = DefaultResourceLoader(cwd=temp_dir, agent_dir=temp_dir)

        # Initially no skills
        assert len(loader.get_skills().skills) == 0

        # Add a skill
        (skills_dir / "new.md").write_text("""---
name: new
description: New skill
---
New content.""")

        # Reload
        loader.reload()

        # Now should have the skill
        assert len(loader.get_skills().skills) == 1

    def test_build_system_prompt(self, temp_dir):
        """Test building system prompt."""
        # Create context file
        (Path(temp_dir) / "CLAUDE.md").write_text("Project instructions")

        # Create skill
        skills_dir = Path(temp_dir) / ".pi" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "test.md").write_text("""---
name: test
description: Test
---
Skill content.""")

        loader = DefaultResourceLoader(cwd=temp_dir, agent_dir=temp_dir)

        prompt = loader.build_system_prompt()

        assert "Project instructions" in prompt
        assert "Skill content" in prompt

    def test_system_prompt_override(self, temp_dir):
        """Test system prompt override."""
        loader = DefaultResourceLoader(
            cwd=temp_dir,
            agent_dir=temp_dir,
            system_prompt="Custom system prompt",
        )

        assert loader.get_system_prompt() == "Custom system prompt"
        assert "Custom system prompt" in loader.build_system_prompt()

    def test_settings_custom_paths(self, temp_dir):
        """Test loading from custom paths in settings."""
        # Create custom skills directory
        custom_dir = Path(temp_dir) / "custom-skills"
        custom_dir.mkdir()
        (custom_dir / "custom.md").write_text("""---
name: custom
description: Custom skill
---
Custom content.""")

        # Create settings with custom path
        settings = SettingsManager.in_memory()
        settings._settings.skills = [str(custom_dir)]

        loader = DefaultResourceLoader(
            cwd=temp_dir,
            agent_dir=temp_dir,
            settings_manager=settings,
        )

        skills = loader.get_skills()
        assert len(skills.skills) == 1
        assert skills.skills[0].name == "custom"
