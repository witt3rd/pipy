# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**pipy** is a UV workspace monorepo containing Python ports of Mario Zechner's TypeScript [pi-mono](https://github.com/badlogic/pi-mono) packages. It provides LLM streaming, an agent framework, TUI components, and a coding assistant. Current upstream sync version: **v0.51.6**.

## Build & Development Commands

```bash
# Install all packages with dev dependencies
uv sync --all-packages --all-extras

# Upgrade all packages to latest versions
uv sync --all-packages --all-extras -U

# Install a specific package
uv sync --package pipy-ai --extra dev

# Run tests for a specific package
uv run --package pipy-ai pytest ai/tests -v
uv run --package pipy-agent pytest agent/tests -v
uv run --package pipy-tui pytest tui/tests -v
uv run --package pipy-coding-agent pytest coding-agent/tests -v

# Run a single test file or test
uv run --package pipy-ai pytest ai/tests/test_types.py -v
uv run --package pipy-ai pytest ai/tests/test_types.py::test_name -v

# Run all tests sequentially (required to avoid test name conflicts)
uv run --package pipy-ai pytest ai/tests && uv run --package pipy-agent pytest agent/tests && uv run --package pipy-tui pytest tui/tests && uv run --package pipy-coding-agent pytest coding-agent/tests

# Lint and format
uv run ruff check .
uv run ruff format .

# Lint a specific package
uv run ruff check ai/
uv run ruff format ai/
```

## Package Architecture

```
pipy-ai (foundation - no internal deps)
    └── pipy-agent (depends on pipy-ai)
            └── pipy-coding-agent (depends on pipy-agent, pipy-ai)

pipy-tui (standalone - no internal deps)
    └── pipy-coding-agent (optional TUI support via [tui] extra)
```

### pipy-ai (`ai/src/pipy_ai/`)
Streaming LLM library. LiteLLM as backend instead of per-provider implementations. Pydantic v2 models for all types (`Message`, `Context`, `Content`, `Tool`, `Usage`). Public API in `api.py`: `complete()`, `stream()`, `quick()`, `ctx()`, `user()` (sync-first, async variants prefixed with `a`). Provider adapter in `provider.py`. Model registry via models.dev in `registry/`. OAuth support in `oauth/`.

### pipy-agent (`agent/src/pipy_agent/`)
Agent framework. `Agent` class in `agent.py` with state management and event subscriptions. Nested loop in `loop.py`: outer loop handles follow-ups, inner loop handles tool calls + steering. `AgentTool` extends pipy-ai's `Tool` with an `execute()` method. `@tool` decorator for ergonomic tool definition. All LLM types imported from pipy-ai (no duplication). Re-exports pipy-ai types for convenience.

### pipy-tui (`tui/src/pipy_tui/`)
Terminal UI components built on Textual. `PiEditor` multi-line widget with undo/history/autocomplete. Protocol-based autocomplete provider system. Fuzzy matching in `fuzzy.py`.

### pipy-coding-agent (`coding-agent/src/pipy_coding_agent/`)
AI coding assistant. Session management in `agent/`. Tools for file/bash operations. Context compaction in `compaction/`. Hook system in `extensions/`. Prompt building in `prompt/`. CLI entry point in `cli.py`.

## Key Conventions

- **Python >=3.11**, build backend is Hatchling
- **Ruff** for linting/formatting: line-length 100, rules E/F/I/UP/B
- **pytest-asyncio** with `asyncio_mode="auto"` - async tests just work
- **Conventional commits** with package scope: `feat(ai): ...`, `fix(agent): ...`, `feat(ai,agent): ...`
- **Version tracking**: versions in `pyproject.toml` and `__init__.py` match upstream pi-mono versions
- Each package has its own `CHANGELOG.md` tracking upstream sync commit hashes

## Upstream Sync

Packages track upstream TypeScript implementations in pi-mono. See `UPDATE_PI_PORTS.md` for the full sync process. Sync in dependency order: pipy-ai first, then pipy-tui, then pipy-agent, then pipy-coding-agent. Each package's `CHANGELOG.md` records the last synced upstream commit hash.

## Pre-commit Hooks

Configured in `ai/.pre-commit-config.yaml`:
- **On commit**: `ruff check --fix` and `ruff format` (auto-fix)
- **On push**: `ruff check` (check-only) and `pytest` (tests)
