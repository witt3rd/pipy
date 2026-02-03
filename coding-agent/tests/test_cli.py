"""Tests for CLI."""

import pytest

from pipy_coding_agent.cli import (
    create_parser,
    main,
    parse_message_args,
    read_file_contents,
    SLASH_COMMANDS,
)


class TestCreateParser:
    def test_default_values(self):
        """Test parser default values."""
        parser = create_parser()
        args = parser.parse_args([])

        assert args.model == "sonnet"
        assert args.thinking == "medium"
        assert args.no_session is False
        assert args.cwd is None
        assert args.print_mode is False

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

    def test_print_mode_flag(self):
        """Test -p/--print flag."""
        parser = create_parser()

        args = parser.parse_args(["-p"])
        assert args.print_mode is True

        args = parser.parse_args(["--print"])
        assert args.print_mode is True

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
        """Test --system-prompt flag."""
        parser = create_parser()

        args = parser.parse_args(["--system-prompt", "You are helpful."])
        assert args.system_prompt == "You are helpful."

    def test_continue_flag(self):
        """Test -c/--continue flag."""
        parser = create_parser()

        args = parser.parse_args(["-c"])
        assert args.continue_session is True

        args = parser.parse_args(["--continue"])
        assert args.continue_session is True

    def test_resume_flag(self):
        """Test -r/--resume flag."""
        parser = create_parser()

        args = parser.parse_args(["-r"])
        assert args.resume is True

    def test_provider_flag(self):
        """Test --provider flag."""
        parser = create_parser()

        args = parser.parse_args(["--provider", "openai"])
        assert args.provider == "openai"

    def test_api_key_flag(self):
        """Test --api-key flag."""
        parser = create_parser()

        args = parser.parse_args(["--api-key", "sk-test"])
        assert args.api_key == "sk-test"

    def test_positional_args(self):
        """Test positional message arguments."""
        parser = create_parser()

        args = parser.parse_args(["hello", "world"])
        assert args.args == ["hello", "world"]

    def test_file_args(self):
        """Test @file arguments."""
        parser = create_parser()

        args = parser.parse_args(["@file.txt", "explain this"])
        assert args.args == ["@file.txt", "explain this"]


class TestParseMessageArgs:
    def test_messages_only(self):
        """Test parsing message arguments."""
        messages, files = parse_message_args(["hello", "world"])
        assert messages == ["hello", "world"]
        assert files == []

    def test_file_args(self, tmp_path):
        """Test parsing @file arguments."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        messages, files = parse_message_args([f"@{test_file}", "explain"])
        assert messages == ["explain"]
        assert len(files) == 1
        assert files[0] == test_file

    def test_nonexistent_file(self, capsys):
        """Test @file with nonexistent file."""
        messages, files = parse_message_args(["@nonexistent.txt"])
        assert messages == []
        assert files == []
        captured = capsys.readouterr()
        assert "not found" in captured.err


class TestReadFileContents:
    def test_read_files(self, tmp_path):
        """Test reading file contents."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        content = read_file_contents([test_file])
        assert "test.py" in content
        assert "print('hello')" in content
        assert "```" in content

    def test_empty_files(self):
        """Test with no files."""
        content = read_file_contents([])
        assert content == ""


class TestSlashCommands:
    def test_slash_commands_registered(self):
        """Test that slash commands are registered."""
        assert "help" in SLASH_COMMANDS
        assert "model" in SLASH_COMMANDS
        assert "thinking" in SLASH_COMMANDS
        assert "clear" in SLASH_COMMANDS
        assert "session" in SLASH_COMMANDS
        assert "export" in SLASH_COMMANDS
        assert "quit" in SLASH_COMMANDS

    def test_all_commands_have_description(self):
        """Test that all commands have descriptions."""
        for name, info in SLASH_COMMANDS.items():
            assert "description" in info
            assert info["description"]


class TestMain:
    def test_version(self, capsys):
        """Test --version output."""
        result = main(["--version"])

        assert result == 0
        captured = capsys.readouterr()
        assert "pipy-coding-agent" in captured.out
        assert "v" in captured.out

    def test_print_mode_no_prompt(self, capsys):
        """Test print mode without prompt fails."""
        result = main(["-p"])
        assert result == 1
        captured = capsys.readouterr()
        assert "No prompt provided" in captured.err


# Note: Full CLI tests with prompts would require mocking the LLM
