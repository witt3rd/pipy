"""
pipy-tui - Terminal UI components for AI assistants, built on Textual.

Example:
    from pipy_tui import PiEditor, CombinedProvider, SlashCommandProvider, FilePathProvider

    editor = PiEditor(
        placeholder="Type a message...",
        autocomplete=CombinedProvider([
            SlashCommandProvider([
                SlashCommand("help", "Show help"),
                SlashCommand("clear", "Clear chat"),
            ]),
            FilePathProvider(Path.cwd()),
        ]),
    )
"""

__version__ = "0.51.2"

# Editor widget
from .editor import PiEditor

# Autocomplete system
from .autocomplete import (
    AutocompleteItem,
    AutocompleteResult,
    CompletionResult,
    AutocompleteProvider,
    SlashCommand,
    SlashCommandProvider,
    FilePathProvider,
    CombinedProvider,
)

# Fuzzy matching
from .fuzzy import (
    FuzzyMatch,
    fuzzy_match,
    fuzzy_filter,
    highlight_match,
)

# Keybindings
from .keybindings import (
    EditorAction,
    KeybindingConfig,
    KeybindingManager,
    get_default_keybindings,
)

# Text utilities
from .utils import (
    visible_width,
    word_wrap_line,
    find_word_boundary_left,
    find_word_boundary_right,
    truncate_to_width,
    TextChunk,
)

__all__ = [
    # Version
    "__version__",
    # Editor
    "PiEditor",
    # Autocomplete
    "AutocompleteItem",
    "AutocompleteResult",
    "CompletionResult",
    "AutocompleteProvider",
    "SlashCommand",
    "SlashCommandProvider",
    "FilePathProvider",
    "CombinedProvider",
    # Fuzzy
    "FuzzyMatch",
    "fuzzy_match",
    "fuzzy_filter",
    "highlight_match",
    # Keybindings
    "EditorAction",
    "KeybindingConfig",
    "KeybindingManager",
    "get_default_keybindings",
    # Utils
    "visible_width",
    "word_wrap_line",
    "find_word_boundary_left",
    "find_word_boundary_right",
    "truncate_to_width",
    "TextChunk",
]
