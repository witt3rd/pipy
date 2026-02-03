"""Tests for prompt template loading."""

import os
import tempfile
import pytest
from pathlib import Path

from pipy_coding_agent.resources.prompts import (
    PromptTemplate,
    parse_command_args,
    substitute_args,
    load_prompt_from_file,
    load_prompts_from_dir,
    load_prompts,
    expand_prompt_template,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestParseCommandArgs:
    def test_simple_args(self):
        """Test parsing simple arguments."""
        args = parse_command_args("hello world")
        assert args == ["hello", "world"]

    def test_quoted_args(self):
        """Test parsing quoted arguments."""
        args = parse_command_args('"hello world"')
        assert args == ["hello world"]

    def test_mixed_args(self):
        """Test parsing mixed arguments."""
        args = parse_command_args('foo "bar baz" qux')
        assert args == ["foo", "bar baz", "qux"]

    def test_single_quoted_args(self):
        """Test parsing single-quoted arguments."""
        args = parse_command_args("foo 'bar baz' qux")
        assert args == ["foo", "bar baz", "qux"]

    def test_empty_string(self):
        """Test parsing empty string."""
        args = parse_command_args("")
        assert args == []

    def test_extra_whitespace(self):
        """Test handling extra whitespace."""
        args = parse_command_args("  foo   bar  ")
        assert args == ["foo", "bar"]


class TestSubstituteArgs:
    def test_positional_args(self):
        """Test substituting positional arguments."""
        content = "Hello $1, welcome to $2!"
        args = ["Alice", "Wonderland"]

        result = substitute_args(content, args)

        assert result == "Hello Alice, welcome to Wonderland!"

    def test_missing_positional_arg(self):
        """Test missing positional argument."""
        content = "Hello $1, $2, $3!"
        args = ["one", "two"]

        result = substitute_args(content, args)

        assert result == "Hello one, two, !"

    def test_all_args_dollar_at(self):
        """Test $@ for all arguments."""
        content = "Run: $@"
        args = ["ls", "-la", "/tmp"]

        result = substitute_args(content, args)

        assert result == "Run: ls -la /tmp"

    def test_all_args_arguments(self):
        """Test $ARGUMENTS for all arguments."""
        content = "Command: $ARGUMENTS"
        args = ["echo", "hello"]

        result = substitute_args(content, args)

        assert result == "Command: echo hello"

    def test_slice_from_start(self):
        """Test ${@:N} for slicing from position."""
        content = "Rest: ${@:2}"
        args = ["first", "second", "third", "fourth"]

        result = substitute_args(content, args)

        assert result == "Rest: second third fourth"

    def test_slice_with_length(self):
        """Test ${@:N:L} for slicing with length."""
        content = "Middle: ${@:2:2}"
        args = ["a", "b", "c", "d", "e"]

        result = substitute_args(content, args)

        assert result == "Middle: b c"


class TestLoadPromptFromFile:
    def test_load_valid_prompt(self, temp_dir):
        """Test loading a valid prompt file."""
        prompt_path = Path(temp_dir) / "greet.md"
        prompt_path.write_text("""---
name: greet
description: Greeting prompt
---

Hello $1! How are you today?""")

        template, diagnostics = load_prompt_from_file(prompt_path, "test")

        assert template is not None
        assert template.name == "greet"
        assert template.description == "Greeting prompt"
        assert "$1" in template.content

    def test_load_prompt_no_frontmatter(self, temp_dir):
        """Test loading prompt without frontmatter."""
        prompt_path = Path(temp_dir) / "simple.md"
        prompt_path.write_text("Just run this: $@")

        template, diagnostics = load_prompt_from_file(prompt_path, "test")

        assert template is not None
        assert template.name == "simple"

    def test_load_empty_prompt(self, temp_dir):
        """Test loading prompt with no content."""
        prompt_path = Path(temp_dir) / "empty.md"
        prompt_path.write_text("""---
name: empty
---
""")

        template, diagnostics = load_prompt_from_file(prompt_path, "test")

        assert template is None
        assert any("no content" in d.message for d in diagnostics)


class TestLoadPromptsFromDir:
    def test_load_from_directory(self, temp_dir):
        """Test loading prompts from a directory."""
        (Path(temp_dir) / "p1.md").write_text("---\nname: p1\n---\nContent 1")
        (Path(temp_dir) / "p2.md").write_text("---\nname: p2\n---\nContent 2")

        result = load_prompts_from_dir(temp_dir)

        assert len(result.prompts) == 2
        names = {p.name for p in result.prompts}
        assert "p1" in names
        assert "p2" in names

    def test_skip_hidden_files(self, temp_dir):
        """Test that hidden files are skipped."""
        (Path(temp_dir) / ".hidden.md").write_text("Hidden")
        (Path(temp_dir) / "visible.md").write_text("---\nname: visible\n---\nContent")

        result = load_prompts_from_dir(temp_dir)

        assert len(result.prompts) == 1
        assert result.prompts[0].name == "visible"


class TestExpandPromptTemplate:
    def test_expand_with_args(self):
        """Test expanding template with arguments."""
        template = PromptTemplate(
            name="test",
            description="Test",
            content="Hello $1! You said: $ARGUMENTS",
            file_path="/test.md",
            source="test",
        )

        result = expand_prompt_template(template, "Alice welcome to the party")

        assert result == "Hello Alice! You said: Alice welcome to the party"

    def test_expand_no_args(self):
        """Test expanding template without arguments."""
        template = PromptTemplate(
            name="simple",
            description="Simple",
            content="This is a simple template.",
            file_path="/simple.md",
            source="test",
        )

        result = expand_prompt_template(template)

        assert result == "This is a simple template."
