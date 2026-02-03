# pipy-tui Design Document

This document explains the architecture and design decisions behind pipy-tui.

## Origin

pipy-tui is a Python library built on [Textual](https://github.com/Textualize/textual), adding the editor and autocomplete features from [@mariozechner/pi-tui](https://github.com/mariozechner/pi).

## Design Philosophy

**Don't reinvent Textual. Extend it with pi-mono's UX.**

| Layer | Responsibility |
|-------|----------------|
| **Textual** | Rendering, components, layout, CSS, events |
| **pipy-tui** | Editor widget, autocomplete system, keybindings |

This mirrors:
- pipy-ai uses **LiteLLM** for API calls, adds clean types
- pipy-tui uses **Textual** for rendering, adds editor/autocomplete

## Architecture

```
pipy-tui/
├── editor.py         # PiEditor widget (~600 lines)
├── autocomplete.py   # Provider system (~400 lines)
├── fuzzy.py          # Fuzzy matching (~100 lines)
├── keybindings.py    # Action dispatch (~200 lines)
└── utils.py          # Text utilities (~200 lines)
```

Total: ~1500 lines (vs ~9400 in pi-mono/tui)

We achieved 84% reduction by using Textual for:
- Differential rendering
- Component lifecycle
- CSS styling
- Event dispatch
- Focus management

## Module Responsibilities

### editor.py - PiEditor Widget

The core widget, extending Textual's Widget:

```python
class PiEditor(Widget, can_focus=True):
    # State
    _lines: list[str]       # Text content
    cursor_line: reactive   # Current line
    cursor_col: reactive    # Current column
    _undo_stack: list       # Undo history
    _history: list          # Prompt history
    _kill_ring: list        # Emacs-style clipboard
    
    # Events
    class Submitted(Message): ...
    class Changed(Message): ...
```

Key methods:
- `render()` - Returns Rich renderable
- `on_key()` - Handles keyboard input
- `_handle_action()` - Dispatches keybinding actions

### autocomplete.py - Provider System

Extensible autocomplete with protocol:

```python
class AutocompleteProvider(ABC):
    def get_suggestions(lines, cursor_line, cursor_col) -> AutocompleteResult | None
    def apply_completion(lines, cursor_line, cursor_col, item, prefix) -> CompletionResult
```

Built-in providers:
- `SlashCommandProvider` - `/command` completions
- `FilePathProvider` - `@file/path` completions with fuzzy
- `CombinedProvider` - Chains multiple providers

### fuzzy.py - Matching

Character-by-character fuzzy matching:

```python
def fuzzy_match(text: str, pattern: str) -> FuzzyMatch | None
def fuzzy_filter(items, pattern, key) -> list
def highlight_match(text, indices, highlight) -> str
```

Scoring:
- +15 for consecutive matches
- +10 for word boundary matches
- -1 per position from start

### keybindings.py - Action Dispatch

Maps keys to actions:

```python
class EditorAction(Enum):
    SUBMIT, NEW_LINE, CURSOR_UP, UNDO, ...

class KeybindingManager:
    def match(key: str) -> EditorAction | None
```

Supports modifier keys (ctrl, alt, shift) with normalization.

### utils.py - Text Utilities

Terminal-aware text handling:

```python
def visible_width(text) -> int      # Handle wide chars, ANSI
def word_wrap_line(line, width)     # Word-boundary wrapping
def find_word_boundary_left/right() # Word navigation
def truncate_to_width()             # Ellipsis truncation
```

## Key Design Decisions

### 1. Textual as Foundation

We don't reimplement:
- Rendering (Textual + Rich)
- Component lifecycle
- Event system
- CSS styling

We focus on:
- Editor logic (cursor, undo, history)
- Autocomplete (providers, fuzzy)
- Keybindings (action dispatch)

### 2. Protocol-Based Autocomplete

Providers implement a simple protocol:

```python
class AutocompleteProvider(ABC):
    @abstractmethod
    def get_suggestions(...) -> AutocompleteResult | None: ...
```

Benefits:
- Easy to add custom providers
- Providers are composable
- Clean separation of concerns

### 3. Reactive Cursor Position

Using Textual's reactive properties:

```python
cursor_line: reactive[int] = reactive(0)
cursor_col: reactive[int] = reactive(0)
```

Changes automatically trigger re-render.

### 4. Kill Ring over System Clipboard

Following pi-mono's design:
- Internal kill ring (30 items)
- Ctrl+K kills line
- Ctrl+Y yanks

Rationale: Terminal clipboard is unreliable across SSH, tmux, etc.

### 5. History as First-Class Feature

Up/down arrows navigate prompt history:
- Empty editor: browse history
- First line: browse history
- Otherwise: move cursor

This matches shell behavior.

## What We Ported

From pi-mono/tui (~9400 lines):

| Component | pi-mono | pipy-tui | Notes |
|-----------|---------|----------|-------|
| Editor | 2000 lines | ~600 lines | Core editing logic |
| Autocomplete | 550 lines | ~400 lines | Provider system |
| Fuzzy | 100 lines | ~100 lines | Direct port |
| Keybindings | 180 lines | ~200 lines | Action dispatch |
| Utils | 889 lines | ~200 lines | Subset needed |

## What Textual Provides

| Feature | pi-mono | Textual |
|---------|---------|---------|
| Rendering | tui.ts (1131 lines) | Built-in |
| Components | Component interface | Widget class |
| Styling | Manual ANSI | CSS |
| Events | Custom | Message system |
| Focus | Focusable interface | Built-in |
| Overlays | OverlayHandle | Layers/Modals |

## Future Considerations

1. **Selection support** - Shift+arrows for selection
2. **Autocomplete popup widget** - Visual dropdown
3. **Syntax highlighting** - For code input
4. **IME support** - For international input
5. **Vi mode** - Optional keybinding set

## Relationship to pipy Ecosystem

```
pipy-ai     → LLM calls, types
pipy-agent  → Tool execution, agent loop
pipy-tui    → Editor, autocomplete (this package)
???         → The actual AI assistant app
```

pipy-tui provides the "input experience" for building AI assistant interfaces.
