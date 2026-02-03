"""Tests for autocomplete system."""

from pathlib import Path
from pipy_tui import (
    AutocompleteItem,
    SlashCommand,
    SlashCommandProvider,
    FilePathProvider,
    CombinedProvider,
)


class TestAutocompleteItem:
    def test_basic(self):
        item = AutocompleteItem(
            value="/help",
            label="/help",
            description="Show help",
        )
        assert item.value == "/help"
        assert item.label == "/help"
        assert item.description == "Show help"

    def test_defaults(self):
        item = AutocompleteItem(value="test", label="Test")
        assert item.description == ""


class TestSlashCommandProvider:
    def test_matches_slash(self):
        provider = SlashCommandProvider(
            [
                SlashCommand("help", "Show help"),
                SlashCommand("clear", "Clear chat"),
            ]
        )
        result = provider.get_suggestions(["/he"], 0, 3)
        assert result is not None
        assert len(result.items) == 1
        assert result.items[0].value == "/help"

    def test_no_match_without_slash(self):
        provider = SlashCommandProvider(
            [
                SlashCommand("help", "Show help"),
            ]
        )
        result = provider.get_suggestions(["he"], 0, 2)
        assert result is None

    def test_all_commands_on_slash(self):
        provider = SlashCommandProvider(
            [
                SlashCommand("help", "Show help"),
                SlashCommand("clear", "Clear chat"),
            ]
        )
        result = provider.get_suggestions(["/"], 0, 1)
        assert result is not None
        assert len(result.items) == 2

    def test_fuzzy_match(self):
        provider = SlashCommandProvider(
            [
                SlashCommand("help", "Show help"),
                SlashCommand("history", "Show history"),
            ]
        )
        result = provider.get_suggestions(["/hi"], 0, 3)
        assert result is not None
        # "history" should match "hi"
        assert any(item.value == "/history" for item in result.items)

    def test_apply_completion(self):
        provider = SlashCommandProvider(
            [
                SlashCommand("help", "Show help"),
            ]
        )
        item = AutocompleteItem(value="/help", label="/help")
        result = provider.apply_completion(["/he"], 0, 3, item, "/he")
        assert result.lines == ["/help "]  # Space added
        assert result.cursor_col == 6  # After space


class TestFilePathProvider:
    def test_matches_at_sign(self):
        provider = FilePathProvider(base_path=Path.cwd(), use_fd=False)
        # Just test that it recognizes @ prefix
        provider.get_suggestions(["@"], 0, 1)
        # May or may not have results depending on cwd
        # Just check it doesn't crash

    def test_no_match_without_at(self):
        provider = FilePathProvider(base_path=Path.cwd(), use_fd=False)
        result = provider.get_suggestions(["src/"], 0, 4)
        assert result is None

    def test_quoted_path(self):
        provider = FilePathProvider(base_path=Path.cwd(), use_fd=False)
        # Test that quoted paths are handled
        provider.get_suggestions(['@"'], 0, 2)
        # Just check it doesn't crash


class TestCombinedProvider:
    def test_tries_providers_in_order(self):
        slash_provider = SlashCommandProvider(
            [
                SlashCommand("help", "Show help"),
            ]
        )
        file_provider = FilePathProvider(base_path=Path.cwd(), use_fd=False)

        combined = CombinedProvider([slash_provider, file_provider])

        # Slash command should match
        result = combined.get_suggestions(["/he"], 0, 3)
        assert result is not None
        assert result.items[0].value == "/help"

    def test_returns_none_if_no_match(self):
        slash_provider = SlashCommandProvider(
            [
                SlashCommand("help", "Show help"),
            ]
        )

        combined = CombinedProvider([slash_provider])

        # No slash, no @, should return None
        result = combined.get_suggestions(["hello"], 0, 5)
        assert result is None

    def test_apply_delegates_to_provider(self):
        slash_provider = SlashCommandProvider(
            [
                SlashCommand("help", "Show help"),
            ]
        )

        combined = CombinedProvider([slash_provider])

        # Trigger to set _last_provider
        combined.get_suggestions(["/he"], 0, 3)

        item = AutocompleteItem(value="/help", label="/help")
        result = combined.apply_completion(["/he"], 0, 3, item, "/he")
        assert result.lines == ["/help "]  # Space added by SlashCommandProvider
