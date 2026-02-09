# pipy-tui: Textual + pi-mono Features

**Goal**: Build pipy-tui on Textual, adding the pi-mono TUI features that create the AI coding assistant experience.

---

## Philosophy

**Don't reinvent Textual. Extend it with pi-mono's UX.**

| Layer | Responsibility |
|-------|----------------|
| **Textual** | Rendering, components, layout, CSS, events, async |
| **pipy-tui** | Editor widget, autocomplete system, keybindings, pi-style UX |

This is analogous to:
- pipy-ai uses **LiteLLM** for API calls, adds clean types
- pipy-tui uses **Textual** for rendering, adds editor/autocomplete

---

## Features to Port from pi-mono/tui

### 1. Multi-line Editor (~2000 lines in TypeScript)

**Core capabilities:**
- Multi-line text editing with word wrap
- Cursor movement (char, word, line, document)
- Selection with Shift+arrows
- Undo/redo stack
- History navigation (up/down arrows for previous prompts)
- Kill ring (Emacs-style kill/yank)
- Character jump mode (f/F for forward/backward)
- Bracketed paste handling
- Large paste collapse (shows `[paste #1 +50 lines]`)
- Scroll support for long content
- Visual line tracking (word wrap aware cursor movement)

**Keybindings (configurable):**
```
submit: Enter
newLine: Shift+Enter, Alt+Enter
cursorUp/Down/Left/Right: Arrow keys
cursorWordLeft/Right: Alt+Left/Right, Ctrl+Left/Right
cursorLineStart/End: Home/End, Ctrl+A/E
deleteWordLeft/Right: Alt+Backspace, Ctrl+W
killLine: Ctrl+K
yank: Ctrl+Y
undo: Ctrl+Z
pageUp/Down: PageUp/PageDown
jumpForward/Backward: Ctrl+F/B (then type char)
```

### 2. Autocomplete System (~550 lines)

**Providers:**
- Slash commands (`/help`, `/clear`, `/model`)
- File paths with fuzzy matching (`@src/main.py`)
- Custom providers (extensible)

**Features:**
- Popup anchored to cursor position
- Fuzzy matching with scoring
- Directory prioritization
- Quote handling for paths with spaces
- fd integration for fast file search
- Tab to force file completion

**Interface:**
```python
class AutocompleteProvider(Protocol):
    def get_suggestions(
        self, lines: list[str], cursor_line: int, cursor_col: int
    ) -> AutocompleteResult | None: ...
    
    def apply_completion(
        self, lines: list[str], cursor_line: int, cursor_col: int,
        item: AutocompleteItem, prefix: str
    ) -> CompletionResult: ...
```

### 3. Fuzzy Matching (~100 lines)

- Character-by-character fuzzy match
- Score based on: exact match > prefix > substring > path match
- Highlight matched characters in results

### 4. Configurable Keybindings (~180 lines)

- Load from config file
- Override defaults
- Action → key mapping

---

## Architecture

```
pipy-tui/
├── src/pipy_tui/
│   ├── __init__.py           # Public API
│   ├── editor.py             # PiEditor(Widget) - multi-line editor
│   ├── autocomplete.py       # AutocompleteProvider, CombinedProvider
│   ├── fuzzy.py              # fuzzy_match(), fuzzy_filter()
│   ├── keybindings.py        # KeybindingManager, default bindings
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── select_list.py    # Autocomplete popup widget
│   │   └── markdown.py       # Enhanced markdown (if needed beyond Rich)
│   └── utils.py              # Text utilities (visible_width, word_wrap)
└── tests/
```

---

## PiEditor Widget

The heart of pipy-tui - a Textual Widget that provides pi-mono's editor experience:

```python
from textual.widget import Widget
from textual.reactive import reactive
from textual.message import Message

class PiEditor(Widget):
    """Multi-line editor with autocomplete, history, and pi-style keybindings."""
    
    # Reactive state
    text = reactive("")
    cursor_line = reactive(0)
    cursor_col = reactive(0)
    
    # Configuration
    autocomplete_provider: AutocompleteProvider | None = None
    keybindings: KeybindingManager
    
    # Events
    class Submitted(Message):
        """Emitted when user presses Enter to submit."""
        def __init__(self, text: str) -> None:
            self.text = text
            super().__init__()
    
    class Changed(Message):
        """Emitted when text changes."""
        def __init__(self, text: str) -> None:
            self.text = text
            super().__init__()
    
    def __init__(
        self,
        *,
        placeholder: str = "",
        autocomplete: AutocompleteProvider | None = None,
        keybindings: KeybindingConfig | None = None,
    ) -> None:
        super().__init__()
        self.autocomplete_provider = autocomplete
        self.keybindings = KeybindingManager(keybindings)
        self._lines: list[str] = [""]
        self._history: list[str] = []
        self._history_index = -1
        self._undo_stack: list[EditorState] = []
        self._kill_ring: list[str] = []
    
    def render(self) -> RenderResult:
        """Render the editor content with cursor."""
        # Use Rich for rendering, handle word wrap, cursor positioning
        ...
    
    def on_key(self, event: Key) -> None:
        """Handle keyboard input with keybinding dispatch."""
        action = self.keybindings.match(event)
        if action:
            self._dispatch_action(action)
        elif event.is_printable:
            self._insert_character(event.character)
    
    # Editor actions
    def _move_cursor(self, lines: int, cols: int) -> None: ...
    def _move_word_forward(self) -> None: ...
    def _move_word_backward(self) -> None: ...
    def _delete_word_backward(self) -> None: ...
    def _kill_line(self) -> None: ...
    def _yank(self) -> None: ...
    def _undo(self) -> None: ...
    def _submit(self) -> None: ...
    def _new_line(self) -> None: ...
    
    # History
    def add_to_history(self, text: str) -> None: ...
    def _navigate_history(self, direction: int) -> None: ...
    
    # Autocomplete integration
    def _show_autocomplete(self) -> None: ...
    def _hide_autocomplete(self) -> None: ...
    def _apply_completion(self, item: AutocompleteItem) -> None: ...
```

---

## Autocomplete System

```python
from dataclasses import dataclass
from typing import Protocol

@dataclass
class AutocompleteItem:
    value: str        # What gets inserted
    label: str        # What's displayed
    description: str = ""  # Optional description

@dataclass 
class AutocompleteResult:
    items: list[AutocompleteItem]
    prefix: str  # What we're matching against

@dataclass
class CompletionResult:
    lines: list[str]
    cursor_line: int
    cursor_col: int

class AutocompleteProvider(Protocol):
    def get_suggestions(
        self, lines: list[str], cursor_line: int, cursor_col: int
    ) -> AutocompleteResult | None:
        """Get suggestions for current cursor position."""
        ...
    
    def apply_completion(
        self, lines: list[str], cursor_line: int, cursor_col: int,
        item: AutocompleteItem, prefix: str
    ) -> CompletionResult:
        """Apply selected completion."""
        ...


class SlashCommandProvider(AutocompleteProvider):
    """Provides /command completions."""
    
    def __init__(self, commands: list[SlashCommand]) -> None:
        self.commands = commands
    
    def get_suggestions(self, lines, cursor_line, cursor_col):
        text = lines[cursor_line][:cursor_col]
        if not text.startswith("/"):
            return None
        
        prefix = text[1:]  # Remove /
        matches = fuzzy_filter(self.commands, prefix, key=lambda c: c.name)
        return AutocompleteResult(
            items=[AutocompleteItem(c.name, c.name, c.description) for c in matches],
            prefix=text,
        )


class FilePathProvider(AutocompleteProvider):
    """Provides @file/path completions with fuzzy matching."""
    
    def __init__(self, base_path: Path, use_fd: bool = True) -> None:
        self.base_path = base_path
        self.use_fd = use_fd
    
    def get_suggestions(self, lines, cursor_line, cursor_col):
        text = lines[cursor_line][:cursor_col]
        prefix = self._extract_file_prefix(text)
        if prefix is None:
            return None
        
        if self.use_fd:
            files = self._search_with_fd(prefix)
        else:
            files = self._search_directory(prefix)
        
        return AutocompleteResult(items=files, prefix=prefix)


class CombinedProvider(AutocompleteProvider):
    """Combines multiple providers (slash commands + file paths)."""
    
    def __init__(self, providers: list[AutocompleteProvider]) -> None:
        self.providers = providers
    
    def get_suggestions(self, lines, cursor_line, cursor_col):
        for provider in self.providers:
            result = provider.get_suggestions(lines, cursor_line, cursor_col)
            if result:
                return result
        return None
```

---

## Fuzzy Matching

```python
from dataclasses import dataclass

@dataclass
class FuzzyMatch:
    item: Any
    score: int
    indices: list[int]  # Matched character positions

def fuzzy_match(text: str, pattern: str) -> FuzzyMatch | None:
    """Match pattern against text, return score and match positions."""
    if not pattern:
        return FuzzyMatch(text, 0, [])
    
    text_lower = text.lower()
    pattern_lower = pattern.lower()
    
    indices = []
    pattern_idx = 0
    
    for i, char in enumerate(text_lower):
        if pattern_idx < len(pattern_lower) and char == pattern_lower[pattern_idx]:
            indices.append(i)
            pattern_idx += 1
    
    if pattern_idx != len(pattern_lower):
        return None  # Not all pattern chars matched
    
    # Score: prefer consecutive matches, early matches
    score = 100
    for i, idx in enumerate(indices):
        if i > 0 and idx == indices[i-1] + 1:
            score += 10  # Consecutive bonus
        score -= idx  # Penalty for late matches
    
    return FuzzyMatch(text, score, indices)


def fuzzy_filter[T](
    items: list[T], 
    pattern: str, 
    key: Callable[[T], str] = str,
) -> list[T]:
    """Filter and sort items by fuzzy match score."""
    if not pattern:
        return items
    
    matches = []
    for item in items:
        match = fuzzy_match(key(item), pattern)
        if match:
            matches.append((item, match.score))
    
    matches.sort(key=lambda x: -x[1])  # Highest score first
    return [item for item, _ in matches]
```

---

## Keybindings

```python
from dataclasses import dataclass, field
from enum import Enum, auto

class EditorAction(Enum):
    SUBMIT = auto()
    NEW_LINE = auto()
    CURSOR_UP = auto()
    CURSOR_DOWN = auto()
    CURSOR_LEFT = auto()
    CURSOR_RIGHT = auto()
    CURSOR_WORD_LEFT = auto()
    CURSOR_WORD_RIGHT = auto()
    CURSOR_LINE_START = auto()
    CURSOR_LINE_END = auto()
    DELETE_CHAR = auto()
    DELETE_WORD_LEFT = auto()
    DELETE_WORD_RIGHT = auto()
    KILL_LINE = auto()
    YANK = auto()
    UNDO = auto()
    PAGE_UP = auto()
    PAGE_DOWN = auto()
    AUTOCOMPLETE = auto()
    AUTOCOMPLETE_ACCEPT = auto()
    AUTOCOMPLETE_DISMISS = auto()

@dataclass
class KeybindingConfig:
    bindings: dict[EditorAction, list[str]] = field(default_factory=dict)

DEFAULT_KEYBINDINGS = KeybindingConfig(bindings={
    EditorAction.SUBMIT: ["enter"],
    EditorAction.NEW_LINE: ["shift+enter", "alt+enter"],
    EditorAction.CURSOR_UP: ["up"],
    EditorAction.CURSOR_DOWN: ["down"],
    EditorAction.CURSOR_LEFT: ["left"],
    EditorAction.CURSOR_RIGHT: ["right"],
    EditorAction.CURSOR_WORD_LEFT: ["alt+left", "ctrl+left"],
    EditorAction.CURSOR_WORD_RIGHT: ["alt+right", "ctrl+right"],
    EditorAction.CURSOR_LINE_START: ["home", "ctrl+a"],
    EditorAction.CURSOR_LINE_END: ["end", "ctrl+e"],
    EditorAction.DELETE_CHAR: ["backspace"],
    EditorAction.DELETE_WORD_LEFT: ["alt+backspace", "ctrl+w"],
    EditorAction.KILL_LINE: ["ctrl+k"],
    EditorAction.YANK: ["ctrl+y"],
    EditorAction.UNDO: ["ctrl+z"],
    EditorAction.AUTOCOMPLETE: ["tab"],
})

class KeybindingManager:
    def __init__(self, config: KeybindingConfig | None = None) -> None:
        self.config = config or DEFAULT_KEYBINDINGS
        self._build_lookup()
    
    def _build_lookup(self) -> None:
        self._key_to_action: dict[str, EditorAction] = {}
        for action, keys in self.config.bindings.items():
            for key in keys:
                self._key_to_action[key.lower()] = action
    
    def match(self, event: Key) -> EditorAction | None:
        key_str = self._event_to_string(event)
        return self._key_to_action.get(key_str)
```

---

## Usage Example

```python
from textual.app import App, ComposeResult
from textual.widgets import Static, Markdown
from pipy_tui import PiEditor, CombinedProvider, SlashCommandProvider, FilePathProvider

class ChatApp(App):
    CSS = """
    PiEditor {
        dock: bottom;
        height: auto;
        max-height: 30%;
        border: solid green;
    }
    #messages {
        height: 1fr;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Static(id="messages")
        yield PiEditor(
            placeholder="Type a message...",
            autocomplete=CombinedProvider([
                SlashCommandProvider([
                    SlashCommand("help", "Show help"),
                    SlashCommand("clear", "Clear chat"),
                    SlashCommand("model", "Change model"),
                ]),
                FilePathProvider(Path.cwd()),
            ]),
        )
    
    def on_pi_editor_submitted(self, event: PiEditor.Submitted) -> None:
        # Handle submitted text
        self.query_one("#messages").update(f"You: {event.text}")
        self.query_one(PiEditor).add_to_history(event.text)
```

---

## Dependencies

```toml
[project]
dependencies = [
    "textual>=0.50.0",
    "rich>=13.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
]
```

---

## Implementation Plan

### Phase 1: Core Editor (3-4 days)
- [ ] Basic multi-line editing
- [ ] Word wrap with visual line tracking
- [ ] Cursor movement (all directions)
- [ ] Basic keybindings

### Phase 2: Advanced Editor (2-3 days)
- [ ] Undo/redo
- [ ] History navigation
- [ ] Kill ring
- [ ] Selection support

### Phase 3: Autocomplete (2-3 days)
- [ ] Provider interface
- [ ] Slash commands
- [ ] File path completion
- [ ] Fuzzy matching
- [ ] Popup widget

### Phase 4: Polish (1-2 days)
- [ ] Configurable keybindings
- [ ] Theming support
- [ ] Tests
- [ ] Documentation

**Total: 8-12 days**

---

## Comparison

| Aspect | Full Port (pipy-tui from scratch) | Textual + Features (this approach) |
|--------|-----------------------------------|-----------------------------------|
| Effort | 20-30 days | 8-12 days |
| Rendering | Custom (reinvent wheel) | Textual (mature) |
| Components | Port all ~9400 lines | Port ~2700 lines (editor + autocomplete) |
| Maintenance | Two systems | One system (Textual) |
| Ecosystem | Isolated | Textual plugins work |

---

## Summary

**pipy-tui = Textual + pi-mono's editor/autocomplete UX**

We get:
- ✅ Textual's rendering, layout, CSS, events
- ✅ pi-mono's editor experience (multi-line, undo, history)
- ✅ pi-mono's autocomplete (slash commands, file paths, fuzzy)
- ✅ Configurable keybindings
- ✅ Ready for the next layer (the actual AI assistant)

This positions pipy-tui as the "experience layer" on top of Textual, just like pipy-ai is the "clean API layer" on top of LiteLLM.
