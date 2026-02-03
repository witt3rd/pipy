"""Configurable keybinding system."""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class EditorAction(Enum):
    """Actions that can be triggered by keybindings."""

    # Submission
    SUBMIT = auto()
    NEW_LINE = auto()

    # Cursor movement
    CURSOR_UP = auto()
    CURSOR_DOWN = auto()
    CURSOR_LEFT = auto()
    CURSOR_RIGHT = auto()
    CURSOR_WORD_LEFT = auto()
    CURSOR_WORD_RIGHT = auto()
    CURSOR_LINE_START = auto()
    CURSOR_LINE_END = auto()
    CURSOR_DOC_START = auto()
    CURSOR_DOC_END = auto()

    # Deletion
    DELETE_CHAR_BEFORE = auto()  # Backspace
    DELETE_CHAR_AFTER = auto()  # Delete
    DELETE_WORD_LEFT = auto()
    DELETE_WORD_RIGHT = auto()
    KILL_LINE = auto()

    # Clipboard / Kill ring
    YANK = auto()
    YANK_POP = auto()

    # Undo
    UNDO = auto()

    # Scrolling
    PAGE_UP = auto()
    PAGE_DOWN = auto()

    # Autocomplete
    AUTOCOMPLETE = auto()
    AUTOCOMPLETE_NEXT = auto()
    AUTOCOMPLETE_PREV = auto()
    AUTOCOMPLETE_ACCEPT = auto()
    AUTOCOMPLETE_DISMISS = auto()

    # Selection (future)
    SELECT_ALL = auto()


@dataclass
class KeybindingConfig:
    """Configuration for editor keybindings."""

    bindings: dict[EditorAction, list[str]] = field(default_factory=dict)

    def get_keys(self, action: EditorAction) -> list[str]:
        """Get key bindings for an action."""
        return self.bindings.get(action, [])

    def set_keys(self, action: EditorAction, keys: list[str]) -> None:
        """Set key bindings for an action."""
        self.bindings[action] = keys

    def add_key(self, action: EditorAction, key: str) -> None:
        """Add a key binding for an action."""
        if action not in self.bindings:
            self.bindings[action] = []
        if key not in self.bindings[action]:
            self.bindings[action].append(key)


def get_default_keybindings() -> KeybindingConfig:
    """Get default keybindings inspired by pi-mono and common conventions."""
    return KeybindingConfig(
        bindings={
            # Submission
            EditorAction.SUBMIT: ["enter"],
            EditorAction.NEW_LINE: ["shift+enter"],
            # Cursor movement
            EditorAction.CURSOR_UP: ["up"],
            EditorAction.CURSOR_DOWN: ["down"],
            EditorAction.CURSOR_LEFT: ["left"],
            EditorAction.CURSOR_RIGHT: ["right"],
            EditorAction.CURSOR_WORD_LEFT: ["ctrl+left"],
            EditorAction.CURSOR_WORD_RIGHT: ["ctrl+right"],
            EditorAction.CURSOR_LINE_START: ["home", "ctrl+a"],
            EditorAction.CURSOR_LINE_END: ["end", "ctrl+e"],
            EditorAction.CURSOR_DOC_START: ["ctrl+home"],
            EditorAction.CURSOR_DOC_END: ["ctrl+end"],
            # Deletion
            EditorAction.DELETE_CHAR_BEFORE: ["backspace"],
            EditorAction.DELETE_CHAR_AFTER: ["delete"],
            EditorAction.DELETE_WORD_LEFT: ["ctrl+backspace", "ctrl+w"],
            EditorAction.DELETE_WORD_RIGHT: ["ctrl+delete"],
            EditorAction.KILL_LINE: ["ctrl+k"],
            # Clipboard
            EditorAction.YANK: ["ctrl+y"],
            EditorAction.YANK_POP: ["alt+y"],
            # Undo
            EditorAction.UNDO: ["ctrl+z"],
            # Scrolling
            EditorAction.PAGE_UP: ["pageup"],
            EditorAction.PAGE_DOWN: ["pagedown"],
            # Autocomplete (these are handled specially in editor, not via general keybindings)
            EditorAction.AUTOCOMPLETE: ["tab"],
            # Note: AUTOCOMPLETE_NEXT/PREV/ACCEPT/DISMISS use the same keys as
            # cursor movement but are handled contextually in the editor when
            # autocomplete is active. They're defined here for documentation.
            # Selection
            EditorAction.SELECT_ALL: ["ctrl+shift+a"],
        }
    )


class KeybindingManager:
    """Manages keybinding lookups and matching."""

    def __init__(self, config: KeybindingConfig | None = None) -> None:
        self.config = config or get_default_keybindings()
        self._key_to_action: dict[str, EditorAction] = {}
        self._build_lookup()

    def _build_lookup(self) -> None:
        """Build reverse lookup from key to action."""
        self._key_to_action.clear()
        for action, keys in self.config.bindings.items():
            for key in keys:
                # Normalize key string
                normalized = self._normalize_key(key)
                self._key_to_action[normalized] = action

    def _normalize_key(self, key: str) -> str:
        """Normalize key string for consistent matching."""
        # Sort modifiers for consistent comparison
        parts = key.lower().split("+")
        if len(parts) == 1:
            return parts[0]

        # Separate modifiers and key
        modifiers = sorted([p for p in parts[:-1] if p in ("ctrl", "alt", "shift", "meta")])
        main_key = parts[-1]

        return "+".join(modifiers + [main_key])

    def match(self, key: str) -> EditorAction | None:
        """Match a key event to an action.

        Args:
            key: Key string (e.g., "ctrl+a", "enter", "shift+tab")

        Returns:
            Matched action or None
        """
        normalized = self._normalize_key(key)
        return self._key_to_action.get(normalized)

    def match_event(self, event: Any) -> EditorAction | None:
        """Match a Textual Key event to an action.

        Args:
            event: Textual Key event

        Returns:
            Matched action or None
        """
        # Build key string from Textual event
        key_str = event.key
        return self.match(key_str)

    def get_action_keys(self, action: EditorAction) -> list[str]:
        """Get all keys bound to an action."""
        return self.config.get_keys(action)
