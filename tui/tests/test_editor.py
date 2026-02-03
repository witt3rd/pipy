"""Tests for PiEditor widget."""

import pytest
from pipy_tui import PiEditor, SlashCommand, SlashCommandProvider


class TestPiEditorState:
    def test_initial_state(self):
        editor = PiEditor()
        assert editor.text == ""
        assert editor.cursor_line == 0
        assert editor.cursor_col == 0

    def test_set_text(self):
        editor = PiEditor()
        editor.text = "hello"
        assert editor.text == "hello"
        assert editor.cursor_col == 5  # Cursor at end

    def test_multiline_text(self):
        editor = PiEditor()
        editor.text = "line1\nline2"
        assert editor._lines == ["line1", "line2"]
        assert editor.cursor_line == 1

    def test_placeholder(self):
        editor = PiEditor(placeholder="Type here...")
        assert editor.placeholder == "Type here..."


class TestPiEditorHistory:
    def test_add_to_history(self):
        editor = PiEditor()
        editor.add_to_history("hello")
        assert "hello" in editor._history

    def test_history_trims_whitespace(self):
        editor = PiEditor()
        editor.add_to_history("  hello  ")
        assert editor._history[0] == "hello"

    def test_history_no_empty(self):
        editor = PiEditor()
        editor.add_to_history("")
        editor.add_to_history("   ")
        assert len(editor._history) == 0

    def test_history_no_consecutive_duplicates(self):
        editor = PiEditor()
        editor.add_to_history("hello")
        editor.add_to_history("hello")
        assert len(editor._history) == 1


class TestPiEditorKillRing:
    def test_kill_ring_push(self):
        editor = PiEditor()
        editor._kill_ring_push("hello")
        assert "hello" in editor._kill_ring

    def test_kill_ring_limit(self):
        editor = PiEditor()
        for i in range(40):
            editor._kill_ring_push(f"item{i}")
        assert len(editor._kill_ring) <= 30


class TestPiEditorUndo:
    def test_push_undo(self):
        editor = PiEditor()
        editor._push_undo()
        assert len(editor._undo_stack) == 1

    def test_undo_restores_state(self):
        editor = PiEditor()
        editor.text = "hello"
        editor._push_undo()
        editor.text = "world"
        editor._undo()
        assert editor.text == "hello"


class TestPiEditorTextManipulation:
    def test_insert_char(self):
        editor = PiEditor()
        editor._insert_char("h")
        assert editor.text == "h"
        assert editor.cursor_col == 1

    def test_insert_newline(self):
        editor = PiEditor()
        editor.text = "hello"
        editor.cursor_col = 2
        editor._push_undo()  # Manual push since we're testing internal method
        editor._insert_newline()
        assert editor._lines == ["he", "llo"]
        assert editor.cursor_line == 1
        assert editor.cursor_col == 0

    def test_delete_char_before(self):
        editor = PiEditor()
        editor.text = "hello"
        editor.cursor_col = 3
        editor._delete_char_before()
        assert editor.text == "helo"
        assert editor.cursor_col == 2

    def test_delete_char_at_start(self):
        editor = PiEditor()
        editor.text = "line1\nline2"
        editor.cursor_line = 1
        editor.cursor_col = 0
        editor._delete_char_before()
        assert editor._lines == ["line1line2"]
        assert editor.cursor_line == 0
        assert editor.cursor_col == 5


class TestPiEditorCursorMovement:
    def test_move_horizontal(self):
        editor = PiEditor()
        editor.text = "hello"
        editor.cursor_col = 2
        editor._move_cursor_horizontal(1)
        assert editor.cursor_col == 3
        editor._move_cursor_horizontal(-1)
        assert editor.cursor_col == 2

    def test_move_horizontal_wraps(self):
        editor = PiEditor()
        editor.text = "line1\nline2"
        editor.cursor_line = 0
        editor.cursor_col = 5
        editor._move_cursor_horizontal(1)
        assert editor.cursor_line == 1
        assert editor.cursor_col == 0

    def test_move_vertical(self):
        editor = PiEditor()
        editor.text = "line1\nline2\nline3"
        editor.cursor_line = 1
        editor._move_cursor_vertical(-1)
        assert editor.cursor_line == 0
        editor._move_cursor_vertical(1)
        assert editor.cursor_line == 1

    def test_move_word_right(self):
        editor = PiEditor()
        editor.text = "hello world"
        editor.cursor_col = 0
        editor._move_word_right()
        assert editor.cursor_col == 6  # After "hello "

    def test_move_word_left(self):
        editor = PiEditor()
        editor.text = "hello world"
        editor.cursor_col = 8
        editor._move_word_left()
        assert editor.cursor_col == 6  # Start of "world"


class TestPiEditorAutocomplete:
    def test_autocomplete_provider_set(self):
        provider = SlashCommandProvider([SlashCommand("help", "Help")])
        editor = PiEditor(autocomplete=provider)
        assert editor.autocomplete_provider is provider

    def test_trigger_autocomplete(self):
        provider = SlashCommandProvider([SlashCommand("help", "Help")])
        editor = PiEditor(autocomplete=provider)
        editor.text = "/he"
        editor.cursor_col = 3
        editor._trigger_autocomplete()
        assert editor._autocomplete_result is not None
        assert len(editor._autocomplete_result.items) == 1

    def test_dismiss_autocomplete(self):
        provider = SlashCommandProvider([SlashCommand("help", "Help")])
        editor = PiEditor(autocomplete=provider)
        editor.text = "/he"
        editor.cursor_col = 3
        editor._trigger_autocomplete()
        editor._dismiss_autocomplete()
        assert editor._autocomplete_result is None

    def test_autocomplete_navigation(self):
        provider = SlashCommandProvider([
            SlashCommand("help", "Help"),
            SlashCommand("history", "History"),
        ])
        editor = PiEditor(autocomplete=provider)
        editor.text = "/h"
        editor.cursor_col = 2
        editor._trigger_autocomplete()
        assert editor._autocomplete_index == 0
        editor._autocomplete_next()
        assert editor._autocomplete_index == 1
        editor._autocomplete_prev()
        assert editor._autocomplete_index == 0
