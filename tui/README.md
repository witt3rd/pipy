# pipy-tui

Terminal UI components for AI assistants, built on [Textual](https://github.com/Textualize/textual).

## Installation

```bash
pip install pipy-tui
```

## Quick Start

```python
from pathlib import Path
from textual.app import App, ComposeResult
from pipy_tui import (
    PiEditor,
    CombinedProvider,
    SlashCommandProvider,
    FilePathProvider,
    SlashCommand,
)

class ChatApp(App):
    def compose(self) -> ComposeResult:
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
        print(f"Submitted: {event.text}")
        self.query_one(PiEditor).add_to_history(event.text)

if __name__ == "__main__":
    ChatApp().run()
```

## Features

### PiEditor Widget

A multi-line editor with pi-mono inspired features:

- **Multi-line editing** with word wrap
- **Cursor movement** (char, word, line, document)
- **Undo/redo** with Ctrl+Z
- **History navigation** (up/down arrows for previous prompts)
- **Kill ring** (Emacs-style Ctrl+K, Ctrl+Y)
- **Autocomplete** with popup

### Autocomplete System

Extensible autocomplete with built-in providers:

```python
# Slash commands
SlashCommandProvider([
    SlashCommand("help", "Show help"),
    SlashCommand("model", "Change model", argument_provider=model_provider),
])

# File paths with @
FilePathProvider(base_path=Path.cwd(), use_fd=True)

# Combine multiple providers
CombinedProvider([slash_provider, file_provider])
```

### Fuzzy Matching

```python
from pipy_tui import fuzzy_match, fuzzy_filter

# Match a pattern
result = fuzzy_match("hello_world", "hw")
# FuzzyMatch(score=108, indices=[0, 6])

# Filter and sort items
commands = ["help", "history", "hello"]
filtered = fuzzy_filter(commands, "he")
# ['help', 'hello', 'history']
```

### Configurable Keybindings

```python
from pipy_tui import KeybindingConfig, EditorAction, PiEditor

config = KeybindingConfig(bindings={
    EditorAction.SUBMIT: ["enter", "ctrl+enter"],
    EditorAction.NEW_LINE: ["shift+enter"],
    EditorAction.UNDO: ["ctrl+z", "cmd+z"],
})

editor = PiEditor(keybindings=config)
```

### Default Keybindings

| Action | Keys |
|--------|------|
| Submit | Enter |
| New line | Shift+Enter |
| Undo | Ctrl+Z |
| Cursor movement | Arrow keys |
| Word movement | Ctrl+Left/Right |
| Line start/end | Home/End, Ctrl+A/E |
| Delete word | Ctrl+Backspace, Ctrl+W |
| Kill line | Ctrl+K |
| Yank | Ctrl+Y |
| Autocomplete | Tab |

## Architecture

pipy-tui is built on Textual, adding pi-mono's editor/autocomplete experience:

```
┌─────────────────────────────────────────┐
│             Your App                     │
├─────────────────────────────────────────┤
│             pipy-tui                     │
│  • PiEditor (multi-line, undo, history) │
│  • Autocomplete (slash cmds, @files)    │
│  • Fuzzy matching                       │
│  • Configurable keybindings             │
├─────────────────────────────────────────┤
│              Textual                    │
│  • Rendering, layout, CSS, events       │
└─────────────────────────────────────────┘
```

## Acknowledgments

This library is a Python port inspired by the excellent TypeScript work of **Mario Zechner** ([@badlogic](https://github.com/badlogic)):

- **[pi-mono](https://github.com/mariozechner/pi)** - The original monorepo containing `@mariozechner/pi-tui`
- **[pi](https://github.com/mariozechner/pi)** - Mario's AI coding assistant built on these foundations

The editor and autocomplete patterns in pipy-tui closely follow Mario's elegant design. Thank you Mario for the inspiration and for open-sourcing your work! 🙏

## License

MIT
