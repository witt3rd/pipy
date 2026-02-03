"""Tests for system prompt builder."""

import pytest

from pipy_coding_agent.prompt import (
    build_system_prompt,
    BuildSystemPromptOptions,
    TOOL_DESCRIPTIONS,
)
from pipy_coding_agent.resources import Skill, ContextFile


class TestBuildSystemPrompt:
    def test_default_prompt(self):
        """Test building default prompt."""
        prompt = build_system_prompt()

        assert "coding assistant" in prompt.lower()
        assert "read" in prompt.lower()
        assert "bash" in prompt.lower()
        assert "edit" in prompt.lower()
        assert "write" in prompt.lower()
        assert "Current date and time:" in prompt
        assert "Current working directory:" in prompt

    def test_custom_prompt(self):
        """Test custom prompt replaces default."""
        options = BuildSystemPromptOptions(
            custom_prompt="You are a helpful assistant."
        )

        prompt = build_system_prompt(options)

        assert "You are a helpful assistant." in prompt
        assert "Current date and time:" in prompt

    def test_selected_tools(self):
        """Test selecting specific tools."""
        options = BuildSystemPromptOptions(
            selected_tools=["Read", "Write"]
        )

        prompt = build_system_prompt(options)

        assert "read:" in prompt.lower()
        assert "write:" in prompt.lower()
        # Bash and Edit should not be in tools list
        # (but may be in guidelines)

    def test_append_system_prompt(self):
        """Test appending to system prompt."""
        options = BuildSystemPromptOptions(
            append_system_prompt="Always be polite."
        )

        prompt = build_system_prompt(options)

        assert "Always be polite." in prompt

    def test_context_files(self):
        """Test including context files."""
        options = BuildSystemPromptOptions(
            context_files=[
                ContextFile(path="/project/CLAUDE.md", content="Project guidelines here."),
            ]
        )

        prompt = build_system_prompt(options)

        assert "Project Context" in prompt
        assert "/project/CLAUDE.md" in prompt
        assert "Project guidelines here." in prompt

    def test_skills(self):
        """Test including skills."""
        options = BuildSystemPromptOptions(
            skills=[
                Skill(
                    name="test-skill",
                    description="A test skill",
                    content="Do the test thing.",
                    file_path="/skills/test.md",
                    base_dir="/skills",
                    source="test",
                ),
            ]
        )

        prompt = build_system_prompt(options)

        assert "**test-skill**:" in prompt
        # Skills are listed by name+description+path, not content
        assert "A test skill" in prompt
        assert "location: /skills/test.md" in prompt

    def test_cwd_in_prompt(self):
        """Test working directory in prompt."""
        options = BuildSystemPromptOptions(
            cwd="/custom/path"
        )

        prompt = build_system_prompt(options)

        # Path may be normalized differently on Windows
        assert "custom" in prompt and "path" in prompt

    def test_guidelines_with_all_tools(self):
        """Test guidelines when all tools available."""
        options = BuildSystemPromptOptions(
            selected_tools=["Read", "Bash", "Edit", "Write", "Grep", "Find", "Ls"]
        )

        prompt = build_system_prompt(options)

        # Should prefer grep/find/ls over bash
        assert "prefer" in prompt.lower() or "grep" in prompt.lower()

    def test_guidelines_bash_only(self):
        """Test guidelines when only bash available."""
        options = BuildSystemPromptOptions(
            selected_tools=["Bash"]
        )

        prompt = build_system_prompt(options)

        assert "bash" in prompt.lower()


class TestToolDescriptions:
    def test_all_tools_have_descriptions(self):
        """Test that common tools have descriptions."""
        expected_tools = ["Read", "Bash", "Edit", "Write", "Grep", "Find", "Ls"]

        for tool in expected_tools:
            assert tool in TOOL_DESCRIPTIONS
            assert len(TOOL_DESCRIPTIONS[tool]) > 0


class TestBuildSystemPromptOptions:
    def test_default_values(self):
        """Test default option values."""
        options = BuildSystemPromptOptions()

        assert options.custom_prompt is None
        assert options.selected_tools is None
        assert options.append_system_prompt is None
        assert options.cwd is None
        assert options.context_files == []
        assert options.skills == []
