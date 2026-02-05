# Changelog

This changelog tracks pipy-coding-agent releases and their alignment with the upstream [@mariozechner/pi-coding-agent](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent) TypeScript package.

## [0.51.6.1] - 2026-02-04

### Added — Auth Storage & Login Commands

Ported credential storage from `pi-coding-agent/src/core/auth-storage.ts`:

- **AuthStorage** (`auth_storage.py`): `auth.json`-backed credential persistence
  - API key storage (plain, `!command`, env var via `resolve_config_value`)
  - OAuth credential storage with auto-refresh on expired tokens
  - Runtime API key overrides (non-persisted, highest priority)
  - Priority chain: runtime override → auth.json API key → auth.json OAuth → env var → fallback
  - Restricted file permissions (owner-only on Unix)
  - Handles corrupted/missing auth files gracefully
- **`/login` command**: Interactive OAuth login or direct API key entry
  - Provider menu with logged-in status indicators
  - Browser-based OAuth for all 4 providers
  - Direct API key entry with `api-key` subcommand
- **`/logout` command**: Remove stored credentials per-provider or all at once

25 new tests for AuthStorage CRUD, resolution priority, env vars, corruption.

## [0.51.6] - 2026-02-04

**Upstream sync:** [pi-coding-agent v0.51.6](https://github.com/badlogic/pi-mono/releases/tag/v0.51.6)  
**Upstream commit:** `9cf5758b`

### Added

- Added `resolve_config_value` module for shell command (`!command`) and env var resolution in config values (matches upstream `resolve-config-value.ts`)
- Added `slash_commands.py` with centralized `BUILTIN_SLASH_COMMANDS` definitions and `SlashCommandInfo` types
- Added `SettingsManager.reload()` method to re-read settings from files
- Added `AgentSession.reload()` method that re-reads settings and reloads resources
- Added `SessionManager.create_branched_session()` for creating forked sessions with correct file handling
- Added cross-platform bash detection: Unix now falls back to PATH lookup when `/bin/bash` unavailable (Termux support)
- Added Windows Git Bash detection in known installation paths

### Changed

- Removed `ALLOWED_FRONTMATTER_FIELDS` validation from skills loader — unknown frontmatter fields are now silently ignored (matches upstream)
- `AgentSession.set_thinking_level()` now persists the change to the session

### Fixed

- Fixed thinking level persistence: when restoring a session without a `thinking_level_change` entry, use settings default instead of potentially stale session context value (matches upstream v0.51.3 fix)
- Fixed new sessions now persist initial thinking level on creation
- Fixed session persistence: mark `_flushed = False` when no assistant message exists yet, so all entries are written when assistant message arrives (matches upstream fork fix)
- Fixed `create_branched_session()` updates `session_file` and `flushed` state after branching, preventing writes to parent session file (matches upstream v0.51.6 fork fix)

### Not Applicable (vs upstream v0.51.3–v0.51.6)

- v0.51.3: Command discovery `ExtensionAPI.getCommands()` → noted for future extension API work
- v0.51.3: Local path support for `pi install`/`pi remove` → package management not yet ported
- v0.51.3: RPC `SlashCommandSource` rename "template" → "prompt" → no RPC mode yet
- v0.51.4: Share URLs default to pi.dev → no share feature yet
- v0.51.5: Windows `.cmd` resolution for package installs → package management not yet ported
- v0.51.6: `resume` keybinding action → handled through Textual keybindings
- v0.51.6: Auth storage `resolveConfigValue` for `!command` API keys → utility module added (wiring to auth pending)

---

## [0.51.2] - 2026-02-02

**Upstream sync:** [pi-coding-agent v0.51.2](https://github.com/badlogic/pi-mono/releases/tag/v0.51.2)  
**Upstream commit:** `ff9a3f06`

### Initial Release 🎉

### Upstream Alignment (v0.50.0 → v0.51.2)

Applied all applicable changes from upstream commits:

#### Tools
- **bash.py:** Added `BashSpawnHook` for intercepting command/cwd/env before execution
- **path_utils.py:** Added `@`-prefix normalization (strips leading `@` from paths)
- **path_utils.py:** macOS filename handling already included (NFD, curly quotes)

#### Settings
- **types.py:** Added `TerminalSettings` (show_images, clear_on_shrink)
- **types.py:** Added `RetrySettings.max_delay_ms` (cap server-requested delays)
- **types.py:** Added `DoubleEscapeAction` with "none" option
- **types.py:** Added UI settings: `autocomplete_max_visible`, `editor_padding_x`, `show_hardware_cursor`
- **manager.py:** Added settings migration for new fields
- **manager.py:** Added `get_terminal_settings()` method

#### Resources
- **skills.py:** Updated skill prompt format with path resolution guidance

#### Session
- `SessionInfo.parent_session_path` already implemented

#### Not Applicable (Python differences)
- `*ToolInput` type exports (TypeScript-specific; Python uses Pydantic models)

Complete Python port of pi-coding-agent with 8 phases implemented:

#### Phase 1: Tools
- `Read` - Read file contents with offset/limit, image support
- `Write` - Create or overwrite files
- `Edit` - Surgical text replacement with fuzzy matching
- `Bash` - Execute shell commands with output truncation
- `Grep` - Search file contents with context lines
- `Find` - Find files by glob pattern
- `Ls` - List directory contents

#### Phase 2: Sessions
- JSONL append-only session storage
- Tree structure with id/parentId for branching
- Entry types: message, thinking_level_change, model_change, compaction, custom, custom_message, session_info, label
- Context building with compaction handling

#### Phase 3: Settings & Resources
- `SettingsManager` with global/project hierarchy (~/.pipy/ and .pi/)
- Settings migration from camelCase to snake_case
- Skill loading from markdown with YAML frontmatter
- Prompt templates with argument substitution ($1, $@, ${@:2})
- Context file loading (CLAUDE.md, AGENTS.md) from ancestors

#### Phase 4: Compaction
- Token estimation using chars/4 heuristic
- Cut point detection for token budget
- File operation tracking (read/write/edit)
- LLM summarization with structured prompts
- Iterative summary updates
- Split-turn handling

#### Phase 5: System Prompt
- Dynamic system prompt builder
- Tool-aware guidelines generation
- Context and skills integration

#### Phase 6: Agent Integration
- `AgentSession` combining agent with session management
- `ModelResolver` with aliases (sonnet, opus, gpt4o, etc.)
- Model capability detection (thinking support)

#### Phase 7: CLI
- Interactive mode with commands (/help, /clear, /model, /thinking)
- Single-prompt mode (-p flag)
- Version display

#### Phase 8: Extensions
- Extension loading from JSON manifests and README frontmatter
- Hook system with priority ordering
- Async and sync hook execution

### Stats

- **Source:** 7,584 lines
- **Tests:** 4,572 lines  
- **Test Results:** 318 passed, 2 skipped (Unix-only)

### Architecture Differences (vs upstream)

This is a Python port using pipy-ai/pipy-agent as the backend:

- Uses LiteLLM (via pipy-ai) for 100+ provider support
- Pydantic for type validation instead of TypeScript interfaces
- Sync-first API with async variants
- Textual-ready for future TUI integration (pipy-tui)

### Known Limitations

- HTML export is a placeholder
- Extension Python module loading is basic
- No OAuth flows (uses API keys via LiteLLM)
- Some TUI-specific features deferred to pipy-tui integration

### Dependencies

- pipy-ai >=0.51.2
- pipy-agent >=0.51.2
