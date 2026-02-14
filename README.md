# pipy

Python ports of [pi-mono](https://github.com/badlogic/pi-mono) packages - LLM streaming, agent framework, TUI components, and coding assistant.

## Packages

| Package | Description | Status |
|---------|-------------|--------|
| [pipy-ai](./ai/) | LLM streaming with rich types, models.dev integration, LiteLLM backend | ✅ v0.51.2 |
| [pipy-agent](./agent/) | Agent framework with tool execution, steering, follow-up queues | ✅ v0.51.2 |
| [pipy-tui](./tui/) | Terminal UI components (editor, autocomplete, markdown) | 🚧 v0.1.0 |
| [pipy-coding-agent](./coding-agent/) | AI coding assistant with bash, read, write, edit tools | 🚧 v0.1.0 |

## Quick Start

```bash
# Clone the repo
git clone https://github.com/witt3rd/pipy.git
cd pipy

# Install all packages with dev dependencies
uv sync --all-packages --all-extras

# Upgrade all packages to latest versions
uv sync --all-packages --all-extras -U

# Or install specific package
uv sync --package pipy-ai --extra dev
```

## Development

### Run Tests

```bash
# All packages (run sequentially to avoid test name conflicts)
uv run --package pipy-ai pytest ai/tests && \
uv run --package pipy-agent pytest agent/tests && \
uv run --package pipy-tui pytest tui/tests && \
uv run --package pipy-coding-agent pytest coding-agent/tests

# Specific package
uv run --package pipy-ai pytest ai/tests -v
uv run --package pipy-agent pytest agent/tests -v
uv run --package pipy-tui pytest tui/tests -v
uv run --package pipy-coding-agent pytest coding-agent/tests -v
```

### Lint

```bash
uv run ruff check .
uv run ruff format .
```

### Package Dependencies

```
pipy-ai (foundation)
    └── pipy-agent (depends on pipy-ai)
            └── pipy-coding-agent (depends on pipy-agent, pipy-ai)
    
pipy-tui (standalone)
    └── pipy-coding-agent (optional TUI support)
```

## Upstream Sync

These packages track the upstream TypeScript implementations in [pi-mono](https://github.com/badlogic/pi-mono). See [UPDATE_PI_PORTS.md](./UPDATE_PI_PORTS.md) for the sync process.

| Package | Upstream | Synced To |
|---------|----------|-----------|
| pipy-ai | @mariozechner/pi-ai | v0.51.2 |
| pipy-agent | @mariozechner/pi-agent | v0.51.2 |
| pipy-tui | @mariozechner/pi-tui | v0.1.0 (initial) |
| pipy-coding-agent | @mariozechner/pi-coding-agent | v0.1.0 (initial) |

## Architecture

This is a **UV workspace** monorepo. Each package:
- Has its own `pyproject.toml` with version and dependencies
- Can depend on sibling packages via `{ workspace = true }`
- Shares a single `uv.lock` file for consistent dependencies
- Can be published independently to PyPI

## Acknowledgments

These libraries are Python ports inspired by the excellent TypeScript work of **Mario Zechner** ([@badlogic](https://github.com/badlogic)):

- **[pi-mono](https://github.com/badlogic/pi-mono)** - The original monorepo
- **[pi](https://github.com/badlogic/pi)** - Mario's AI coding assistant

Thank you Mario for the inspiration and for open-sourcing your work! 🙏

## License

MIT
