"""PiEditor - Multi-line editor widget with autocomplete."""

from dataclasses import dataclass, field
from typing import ClassVar

from rich.console import RenderableType
from rich.text import Text
from textual.binding import Binding
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from .autocomplete import AutocompleteProvider, AutocompleteItem, AutocompleteResult
from .keybindings import EditorAction, KeybindingManager, KeybindingConfig, get_default_keybindings
from .utils import (
    visible_width,
    word_wrap_line,
    find_word_boundary_left,
    find_word_boundary_right,
    TextChunk,
)


@dataclass
class EditorState:
    """Snapshot of editor state for undo."""

    lines: list[str]
    cursor_line: int
    cursor_col: int


class PiEditor(Widget, can_focus=True):
    """Multi-line editor with autocomplete, history, and pi-style keybindings.

    Features:
    - Multi-line editing with word wrap
    - Cursor movement (char, word, line)
    - Undo/redo
    - History navigation (up/down for previous prompts)
    - Kill ring (Emacs-style kill/yank)
    - Autocomplete with popup

    Example:
        editor = PiEditor(
            placeholder="Type a message...",
            autocomplete=CombinedProvider([
                SlashCommandProvider([...]),
                FilePathProvider(Path.cwd()),
            ]),
        )

        # Handle submission
        @on(PiEditor.Submitted)
        def on_submit(self, event: PiEditor.Submitted) -> None:
            print(f"Submitted: {event.text}")
    """

    DEFAULT_CSS = """
    PiEditor {
        height: auto;
        min-height: 3;
        max-height: 50%;
        padding: 0 1;
        border: solid $primary;
        background: $surface;
    }

    PiEditor:focus {
        border: solid $accent;
    }

    PiEditor > .autocomplete-popup {
        layer: autocomplete;
        background: $surface;
        border: solid $primary;
        padding: 0 1;
        max-height: 10;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "dismiss_autocomplete", "Dismiss", show=False),
    ]

    # Messages
    class Submitted(Message):
        """Emitted when user submits (Enter)."""

        def __init__(self, text: str) -> None:
            self.text = text
            super().__init__()

    class Changed(Message):
        """Emitted when text changes."""

        def __init__(self, text: str) -> None:
            self.text = text
            super().__init__()

    # Reactive properties
    cursor_line: reactive[int] = reactive(0)
    cursor_col: reactive[int] = reactive(0)

    def __init__(
        self,
        *,
        placeholder: str = "",
        autocomplete: AutocompleteProvider | None = None,
        keybindings: KeybindingConfig | None = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)

        self.placeholder = placeholder
        self.autocomplete_provider = autocomplete
        self.keybindings = KeybindingManager(keybindings)

        # Editor state
        self._lines: list[str] = [""]
        self._undo_stack: list[EditorState] = []
        self._redo_stack: list[EditorState] = []

        # History
        self._history: list[str] = []
        self._history_index: int = -1

        # Kill ring
        self._kill_ring: list[str] = []
        self._last_action: str | None = None

        # Autocomplete state
        self._autocomplete_result: AutocompleteResult | None = None
        self._autocomplete_index: int = 0

        # Scroll offset for long content
        self._scroll_offset: int = 0

    @property
    def text(self) -> str:
        """Get current text content."""
        return "\n".join(self._lines)

    @text.setter
    def text(self, value: str) -> None:
        """Set text content."""
        self._push_undo()
        self._lines = value.split("\n") if value else [""]
        self.cursor_line = len(self._lines) - 1
        self.cursor_col = len(self._lines[self.cursor_line])
        self._notify_change()

    def render(self) -> RenderableType:
        """Render the editor content."""
        if not self._lines or (len(self._lines) == 1 and not self._lines[0]):
            # Show placeholder
            if self.placeholder:
                return Text(self.placeholder, style="dim italic")
            return Text("")

        # Build rendered text with cursor
        result = Text()

        for line_idx, line in enumerate(self._lines):
            if line_idx > 0:
                result.append("\n")

            if line_idx == self.cursor_line:
                # Insert cursor marker
                before = line[: self.cursor_col]
                after = line[self.cursor_col :]
                result.append(before)
                result.append("│", style="bold blink")  # Cursor
                result.append(after)
            else:
                result.append(line)

        return result

    def on_key(self, event) -> None:
        """Handle keyboard input."""
        # Check for autocomplete keys first
        if self._autocomplete_result:
            if event.key == "escape":
                self._dismiss_autocomplete()
                event.stop()
                return
            elif event.key == "enter":
                self._accept_autocomplete()
                event.stop()
                return
            elif event.key == "down" or event.key == "tab":
                self._autocomplete_next()
                event.stop()
                return
            elif event.key == "up" or event.key == "shift+tab":
                self._autocomplete_prev()
                event.stop()
                return

        # Match keybinding
        action = self.keybindings.match(event.key)

        if action:
            self._handle_action(action, event)
            event.stop()
        elif event.is_printable and event.character:
            self._insert_char(event.character)
            event.stop()

    def _handle_action(self, action: EditorAction, event) -> None:
        """Dispatch editor action."""
        match action:
            case EditorAction.SUBMIT:
                self._submit()
            case EditorAction.NEW_LINE:
                self._insert_newline()
            case EditorAction.CURSOR_UP:
                self._move_cursor_vertical(-1)
            case EditorAction.CURSOR_DOWN:
                self._move_cursor_vertical(1)
            case EditorAction.CURSOR_LEFT:
                self._move_cursor_horizontal(-1)
            case EditorAction.CURSOR_RIGHT:
                self._move_cursor_horizontal(1)
            case EditorAction.CURSOR_WORD_LEFT:
                self._move_word_left()
            case EditorAction.CURSOR_WORD_RIGHT:
                self._move_word_right()
            case EditorAction.CURSOR_LINE_START:
                self.cursor_col = 0
            case EditorAction.CURSOR_LINE_END:
                self.cursor_col = len(self._lines[self.cursor_line])
            case EditorAction.DELETE_CHAR_BEFORE:
                self._delete_char_before()
            case EditorAction.DELETE_CHAR_AFTER:
                self._delete_char_after()
            case EditorAction.DELETE_WORD_LEFT:
                self._delete_word_left()
            case EditorAction.KILL_LINE:
                self._kill_line()
            case EditorAction.YANK:
                self._yank()
            case EditorAction.UNDO:
                self._undo()
            case EditorAction.AUTOCOMPLETE:
                self._trigger_autocomplete()

        self._last_action = action.name

    # === Text Manipulation ===

    def _insert_char(self, char: str) -> None:
        """Insert a character at cursor."""
        self._push_undo()
        line = self._lines[self.cursor_line]
        self._lines[self.cursor_line] = (
            line[: self.cursor_col] + char + line[self.cursor_col :]
        )
        self.cursor_col += len(char)
        self._notify_change()
        self._update_autocomplete()

    def _insert_newline(self) -> None:
        """Insert a new line."""
        self._push_undo()
        line = self._lines[self.cursor_line]
        before = line[: self.cursor_col]
        after = line[self.cursor_col :]

        self._lines[self.cursor_line] = before
        self._lines.insert(self.cursor_line + 1, after)
        self.cursor_line += 1
        self.cursor_col = 0
        self._notify_change()

    def _delete_char_before(self) -> None:
        """Delete character before cursor (backspace)."""
        if self.cursor_col > 0:
            self._push_undo()
            line = self._lines[self.cursor_line]
            self._lines[self.cursor_line] = (
                line[: self.cursor_col - 1] + line[self.cursor_col :]
            )
            self.cursor_col -= 1
            self._notify_change()
            self._update_autocomplete()
        elif self.cursor_line > 0:
            # Join with previous line
            self._push_undo()
            prev_line = self._lines[self.cursor_line - 1]
            curr_line = self._lines[self.cursor_line]
            self._lines[self.cursor_line - 1] = prev_line + curr_line
            self._lines.pop(self.cursor_line)
            self.cursor_line -= 1
            self.cursor_col = len(prev_line)
            self._notify_change()

    def _delete_char_after(self) -> None:
        """Delete character after cursor (delete key)."""
        line = self._lines[self.cursor_line]
        if self.cursor_col < len(line):
            self._push_undo()
            self._lines[self.cursor_line] = (
                line[: self.cursor_col] + line[self.cursor_col + 1 :]
            )
            self._notify_change()
        elif self.cursor_line < len(self._lines) - 1:
            # Join with next line
            self._push_undo()
            next_line = self._lines[self.cursor_line + 1]
            self._lines[self.cursor_line] = line + next_line
            self._lines.pop(self.cursor_line + 1)
            self._notify_change()

    def _delete_word_left(self) -> None:
        """Delete word before cursor."""
        line = self._lines[self.cursor_line]
        new_col = find_word_boundary_left(line, self.cursor_col)

        if new_col < self.cursor_col:
            self._push_undo()
            deleted = line[new_col : self.cursor_col]
            self._kill_ring_push(deleted)
            self._lines[self.cursor_line] = line[:new_col] + line[self.cursor_col :]
            self.cursor_col = new_col
            self._notify_change()
            self._update_autocomplete()

    def _kill_line(self) -> None:
        """Kill from cursor to end of line."""
        line = self._lines[self.cursor_line]
        if self.cursor_col < len(line):
            self._push_undo()
            killed = line[self.cursor_col :]
            self._kill_ring_push(killed)
            self._lines[self.cursor_line] = line[: self.cursor_col]
            self._notify_change()
        elif self.cursor_line < len(self._lines) - 1:
            # Kill newline (join with next line)
            self._push_undo()
            next_line = self._lines[self.cursor_line + 1]
            self._lines[self.cursor_line] = line + next_line
            self._lines.pop(self.cursor_line + 1)
            self._notify_change()

    def _yank(self) -> None:
        """Yank (paste) from kill ring."""
        if self._kill_ring:
            self._push_undo()
            text = self._kill_ring[-1]
            self._insert_text(text)

    def _insert_text(self, text: str) -> None:
        """Insert text at cursor, handling newlines."""
        lines = text.split("\n")

        if len(lines) == 1:
            # Single line insert
            line = self._lines[self.cursor_line]
            self._lines[self.cursor_line] = (
                line[: self.cursor_col] + text + line[self.cursor_col :]
            )
            self.cursor_col += len(text)
        else:
            # Multi-line insert
            curr_line = self._lines[self.cursor_line]
            before = curr_line[: self.cursor_col]
            after = curr_line[self.cursor_col :]

            self._lines[self.cursor_line] = before + lines[0]

            for i, insert_line in enumerate(lines[1:-1], 1):
                self._lines.insert(self.cursor_line + i, insert_line)

            last_line = lines[-1] + after
            self._lines.insert(self.cursor_line + len(lines) - 1, last_line)

            self.cursor_line += len(lines) - 1
            self.cursor_col = len(lines[-1])

        self._notify_change()

    # === Cursor Movement ===

    def _move_cursor_horizontal(self, delta: int) -> None:
        """Move cursor horizontally."""
        line = self._lines[self.cursor_line]

        if delta < 0 and self.cursor_col > 0:
            self.cursor_col -= 1
        elif delta < 0 and self.cursor_line > 0:
            # Move to end of previous line
            self.cursor_line -= 1
            self.cursor_col = len(self._lines[self.cursor_line])
        elif delta > 0 and self.cursor_col < len(line):
            self.cursor_col += 1
        elif delta > 0 and self.cursor_line < len(self._lines) - 1:
            # Move to start of next line
            self.cursor_line += 1
            self.cursor_col = 0

        self._dismiss_autocomplete()

    def _move_cursor_vertical(self, delta: int) -> None:
        """Move cursor vertically."""
        # Check for history navigation
        if delta < 0 and self.cursor_line == 0:
            if self._history:
                self._navigate_history(-1)
                return

        if delta > 0 and self.cursor_line == len(self._lines) - 1:
            if self._history_index >= 0:
                self._navigate_history(1)
                return

        new_line = self.cursor_line + delta
        if 0 <= new_line < len(self._lines):
            self.cursor_line = new_line
            # Clamp cursor to line length
            self.cursor_col = min(self.cursor_col, len(self._lines[self.cursor_line]))

        self._dismiss_autocomplete()

    def _move_word_left(self) -> None:
        """Move cursor to start of previous word."""
        line = self._lines[self.cursor_line]
        self.cursor_col = find_word_boundary_left(line, self.cursor_col)
        self._dismiss_autocomplete()

    def _move_word_right(self) -> None:
        """Move cursor to end of next word."""
        line = self._lines[self.cursor_line]
        self.cursor_col = find_word_boundary_right(line, self.cursor_col)
        self._dismiss_autocomplete()

    # === Undo/Redo ===

    def _push_undo(self) -> None:
        """Save current state to undo stack."""
        state = EditorState(
            lines=self._lines.copy(),
            cursor_line=self.cursor_line,
            cursor_col=self.cursor_col,
        )
        self._undo_stack.append(state)
        self._redo_stack.clear()

        # Limit stack size
        if len(self._undo_stack) > 100:
            self._undo_stack.pop(0)

    def _undo(self) -> None:
        """Undo last action."""
        if not self._undo_stack:
            return

        # Save current state to redo
        current = EditorState(
            lines=self._lines.copy(),
            cursor_line=self.cursor_line,
            cursor_col=self.cursor_col,
        )
        self._redo_stack.append(current)

        # Restore previous state
        state = self._undo_stack.pop()
        self._lines = state.lines
        self.cursor_line = state.cursor_line
        self.cursor_col = state.cursor_col
        self._notify_change()

    # === Kill Ring ===

    def _kill_ring_push(self, text: str) -> None:
        """Add text to kill ring."""
        if text:
            self._kill_ring.append(text)
            if len(self._kill_ring) > 30:
                self._kill_ring.pop(0)

    # === History ===

    def add_to_history(self, text: str) -> None:
        """Add text to history for up/down navigation."""
        text = text.strip()
        if not text:
            return

        # Don't add duplicates at top
        if self._history and self._history[0] == text:
            return

        self._history.insert(0, text)
        if len(self._history) > 100:
            self._history.pop()

    def _navigate_history(self, direction: int) -> None:
        """Navigate through history."""
        if not self._history:
            return

        new_index = self._history_index - direction

        if new_index < -1:
            return
        if new_index >= len(self._history):
            return

        self._history_index = new_index

        if self._history_index == -1:
            # Back to empty/current
            self._lines = [""]
            self.cursor_line = 0
            self.cursor_col = 0
        else:
            text = self._history[self._history_index]
            self._lines = text.split("\n")
            self.cursor_line = len(self._lines) - 1
            self.cursor_col = len(self._lines[self.cursor_line])

        self.refresh()

    # === Autocomplete ===

    def _trigger_autocomplete(self) -> None:
        """Trigger autocomplete popup."""
        if not self.autocomplete_provider:
            return

        result = self.autocomplete_provider.get_suggestions(
            self._lines, self.cursor_line, self.cursor_col
        )

        if result and result.items:
            self._autocomplete_result = result
            self._autocomplete_index = 0
            self.refresh()
        else:
            self._dismiss_autocomplete()

    def _update_autocomplete(self) -> None:
        """Update autocomplete after text change."""
        if self._autocomplete_result and self.autocomplete_provider:
            # Re-query with current state
            result = self.autocomplete_provider.get_suggestions(
                self._lines, self.cursor_line, self.cursor_col
            )
            if result and result.items:
                self._autocomplete_result = result
                self._autocomplete_index = min(
                    self._autocomplete_index, len(result.items) - 1
                )
            else:
                self._dismiss_autocomplete()

    def _dismiss_autocomplete(self) -> None:
        """Dismiss autocomplete popup."""
        self._autocomplete_result = None
        self._autocomplete_index = 0
        self.refresh()

    def _autocomplete_next(self) -> None:
        """Select next autocomplete item."""
        if self._autocomplete_result:
            self._autocomplete_index = (self._autocomplete_index + 1) % len(
                self._autocomplete_result.items
            )
            self.refresh()

    def _autocomplete_prev(self) -> None:
        """Select previous autocomplete item."""
        if self._autocomplete_result:
            self._autocomplete_index = (self._autocomplete_index - 1) % len(
                self._autocomplete_result.items
            )
            self.refresh()

    def _accept_autocomplete(self) -> None:
        """Accept selected autocomplete item."""
        if not self._autocomplete_result:
            return

        item = self._autocomplete_result.items[self._autocomplete_index]
        prefix = self._autocomplete_result.prefix

        if self.autocomplete_provider:
            result = self.autocomplete_provider.apply_completion(
                self._lines, self.cursor_line, self.cursor_col, item, prefix
            )
            self._push_undo()
            self._lines = result.lines
            self.cursor_line = result.cursor_line
            self.cursor_col = result.cursor_col
            self._notify_change()

        self._dismiss_autocomplete()

    # === Submission ===

    def _submit(self) -> None:
        """Submit current text."""
        text = self.text.strip()

        # Reset state
        self._lines = [""]
        self.cursor_line = 0
        self.cursor_col = 0
        self._history_index = -1
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._dismiss_autocomplete()

        self.refresh()
        self.post_message(self.Submitted(text))

    def _notify_change(self) -> None:
        """Notify that text changed."""
        self.refresh()
        self.post_message(self.Changed(self.text))

    # === Actions ===

    def action_dismiss_autocomplete(self) -> None:
        """Action to dismiss autocomplete."""
        self._dismiss_autocomplete()
