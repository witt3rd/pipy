"""Tests for CLI."""

import pytest

from pipy_coding_agent.cli import create_parser, main


class TestCreateParser:
    def test_default_values(self):
        """Test parser default values."""
        parser = create_parser()
        args = parser.parse_args([])

        assert args.model == "sonnet"
        assert args.thinking == "medium"
        assert args.no_session is False
        assert args.cwd is None
        assert args.prompt is None

    def test_model_flag(self):
        """Test -m/--model flag."""
        parser = create_parser()

        args = parser.parse_args(["-m", "opus"])
        assert args.model == "opus"

        args = parser.parse_args(["--model", "gpt4o"])
        assert args.model == "gpt4o"

    def test_thinking_flag(self):
        """Test --thinking flag."""
        parser = create_parser()

        args = parser.parse_args(["--thinking", "high"])
        assert args.thinking == "high"

    def test_prompt_flag(self):
        """Test -p/--prompt flag."""
        parser = create_parser()

        args = parser.parse_args(["-p", "hello world"])
        assert args.prompt == "hello world"

        args = parser.parse_args(["--prompt", "test prompt"])
        assert args.prompt == "test prompt"

    def test_cwd_flag(self):
        """Test --cwd flag."""
        parser = create_parser()

        args = parser.parse_args(["--cwd", "/path/to/dir"])
        assert args.cwd == "/path/to/dir"

    def test_no_session_flag(self):
        """Test --no-session flag."""
        parser = create_parser()

        args = parser.parse_args(["--no-session"])
        assert args.no_session is True

    def test_verbose_flag(self):
        """Test -v/--verbose flag."""
        parser = create_parser()

        args = parser.parse_args(["-v"])
        assert args.verbose is True

        args = parser.parse_args(["--verbose"])
        assert args.verbose is True

    def test_version_flag(self):
        """Test --version flag."""
        parser = create_parser()

        args = parser.parse_args(["--version"])
        assert args.version is True

    def test_system_prompt_flag(self):
        """Test --system flag."""
        parser = create_parser()

        args = parser.parse_args(["--system", "You are helpful."])
        assert args.system == "You are helpful."


class TestMain:
    def test_version(self, capsys):
        """Test --version output."""
        result = main(["--version"])

        assert result == 0
        captured = capsys.readouterr()
        assert "pipy-coding-agent" in captured.out
        assert "v" in captured.out


# Note: Full CLI tests with prompts would require mocking
