# Pipy Port Audit

**Date:** 2026-02-04  
**Upstream version:** v0.51.6 (commit `9cf5758b`)  
**Pipy version:** v0.51.6

This document is an honest assessment of what has been ported from the upstream [pi-mono](https://github.com/badlogic/pi-mono) TypeScript packages to their Python counterparts.

## Summary

| | Upstream (TypeScript) | Pipy (Python) | Coverage |
|-|----------------------|---------------|----------|
| **Total source lines** | 68,901 | ~15,500 | **22%** |
| **Total test lines** | 11,997 | ~8,200 | 68% |
| **Tests passing** | — | 653 | — |
| **Packages** | 4 | 4 | ✅ |

### Per-Package Breakdown

| Package | Upstream Lines | Pipy Lines | Coverage |
|---------|---------------|------------|----------|
| pi-ai / pipy-ai | 21,509 | 3,300 | 15%¹ |
| pi-agent / pipy-agent | 1,465 | 1,200 | 82% |
| pi-tui / pipy-tui | 9,557 | 1,727 | 18%² |
| pi-coding-agent / pipy-coding-agent | 36,370 | 8,800 | 24% |

¹ pipy-ai uses LiteLLM instead of per-provider implementations, so the low percentage is expected — LiteLLM replaces ~15,000 lines of provider code.  
² pipy-tui uses Textual instead of a custom terminal renderer, so the core tui package is smaller, but the Textual framework provides the missing functionality.

---

## pipy-ai — ✅ Functional

**Architecture difference:** Uses LiteLLM as the backend instead of per-provider implementations. This is by design — LiteLLM abstracts 100+ providers vs. upstream's hand-rolled provider code.

### Ported & Working
- Core types: `Message`, `Context`, `Tool`, `Usage`, `Cost` — ✅
- Content types: `TextContent`, `ThinkingContent`, `ImageContent`, `ToolCall` — ✅
- Streaming events: `StartEvent`, `TextDeltaEvent`, `ThinkingDeltaEvent`, `ToolCallDeltaEvent`, `DoneEvent`, `ErrorEvent` — ✅
- Options: `StreamOptions`, `SimpleStreamOptions`, `ThinkingLevel`, `ThinkingBudgets`, `CacheRetention` — ✅
- API functions: `complete()`, `stream()`, `acomplete()`, `astream()`, `quick()`, `ctx()`, `user()` — ✅
- `AbortController`/`AbortSignal` for cancellation — ✅
- Model registry with models.dev integration — ✅
- `supports_xhigh()` check — ✅
- **OAuth module** (`pipy_ai.oauth`) — ✅
  - PKCE utilities — ✅
  - Provider registry with lazy loading — ✅
  - Anthropic OAuth (PKCE, code paste) — ✅
  - OpenAI Codex OAuth (PKCE, local callback server, JWT extraction) — ✅
  - GitHub Copilot (device code flow, enterprise domains) — ✅
  - Google Gemini CLI (Google Cloud OAuth, callback server, project discovery) — ✅
  - Auto-refresh for expired tokens — ✅
- **123 tests passing** (31 new OAuth tests)

### Not Applicable
- Per-provider streaming implementations (Anthropic, OpenAI, Google, Bedrock, etc.) — LiteLLM handles this
- Provider-specific streaming parsers — LiteLLM abstracts this
- `models.generated.ts` — LiteLLM has its own model catalog

---

## pipy-agent — ✅ Functional

### Ported & Working
- `Agent` class with tool execution loop — ✅
- `AgentLoop` with configurable callbacks — ✅
- Event system (subscribe/unsubscribe) — ✅
- `AgentTool` base class and `@tool` decorator — ✅
- `ThinkingBudgets`, `max_retry_delay_ms` options — ✅
- `session_id` property — ✅
- **69 tests passing**

### Not Ported
- Nothing major — this package is well covered

---

## pipy-tui — ⚠️ Components Only

**Architecture difference:** Uses [Textual](https://textual.textualize.io/) instead of a custom terminal renderer. The upstream builds everything from scratch with ANSI escape sequences; we use Textual widgets.

### Ported & Working
- `PiEditor` — multi-line editor widget with autocomplete — ✅
- `AutocompleteProvider` system — ✅
  - `SlashCommandProvider` — ✅
  - `FilePathProvider` with `fd` support — ✅
  - `CombinedProvider` — ✅
- `fuzzy_match()` and `fuzzy_filter()` — ✅
- `KeybindingManager` for configurable editor keybindings — ✅
- Text utilities (`visible_width`, `word_wrap_line`, etc.) — ✅
- **88 tests passing**

### Not Ported
- `Terminal` class (raw terminal management) — Textual handles this
- `Input` component (single-line) — Textual has built-in
- `SettingsList` component — ❌ Not ported
- `Editor` completions menu rendering — Textual handles rendering
- `drainInput()` / SSH fixes — Textual handles stdin

### Not Wired Up
- **The TUI components exist but are NOT connected to the coding agent's interactive mode.** The coding agent currently uses a plain `input()` REPL, not the Textual-based editor.

---

## pipy-coding-agent — ⚠️ Engine Only, No Frontend

This is where the biggest gap is. The engine (tools, sessions, compaction, settings) works, but the **entire user-facing experience is missing**.

### ✅ Ported & Working

| Module | Upstream Lines | Pipy Lines | Notes |
|--------|---------------|------------|-------|
| **Tools** (read, write, edit, bash, grep, find, ls, truncate, path_utils) | 2,483 | 2,361 | Solid — 200+ tests, cross-platform bash detection |
| **Session Manager** (entries, tree, persistence, branching) | 1,401 | 1,267 | Good — core JSONL tree, branching, context building |
| **Compaction** (token estimation, cut points, prepare, compact) | 1,322 | 1,176 | Good — token counting, summarization pipeline |
| **Settings Manager** (global/project merge, migration, reload) | 751 | 626 | Good — full settings hierarchy, migration, reload |
| **Skills Loader** (frontmatter, validation, discovery) | 391 | 297 | Good — matches spec |
| **Prompt Templates** (loading, arg substitution) | 299 | 214 | Good |
| **System Prompt Builder** | 188 | 213 | Good |
| **Resource Loader** (aggregate resources) | 871 | 267 | Simplified — loads skills/prompts/context, no package paths |
| **Extension Hooks** | 2,799 (full system) | 471 | Hooks only — no runner, no command registration, no tool wrapping |
| **Slash Commands** (definitions) | 37 | 60 | Data only — `BUILTIN_SLASH_COMMANDS` |
| **Config Value Resolution** (`!command`, env vars) | 64 | 70 | Good |

**373 tests passing** across all coding-agent modules (25 new auth tests).

### ⚠️ Partially Ported / Stubbed

| Module | Upstream Lines | Pipy Lines | What's Missing |
|--------|---------------|------------|----------------|
| **AgentSession** (the main orchestrator) | **2,769** | **565** | Only ~20% — basic prompt loop works, but missing: tool approval flow, extension wiring, scoped models, fork/resume from UI, thinking level clamping per model, follow-up messages, steering modes |
| **Model Resolver** | 544 (registry) | 100 | Hardcoded aliases only — no `models.json`, no custom models, no auth-based API key lookup |
| **CLI** | ~500 | 788 | Framework exists but **11 slash commands are stubs** (see below) |

#### Stubbed Slash Commands

| Command | Status |
|---------|--------|
| `/help` | ✅ Works |
| `/model <name>` | ✅ Works (basic) |
| `/thinking <level>` | ✅ Works |
| `/clear` | ✅ Works |
| `/new` | ✅ Works |
| `/session` | ✅ Works (basic info) |
| `/copy` | ✅ Works |
| `/name` | ✅ Works |
| `/reload` | ✅ Works |
| `/quit` / `/exit` | ✅ Works |
| `/compact` | ❌ Stub — prints "not yet implemented" |
| `/fork` | ❌ Stub |
| `/tree` | ❌ Stub |
| `/resume` | ❌ Stub (CLI flag `--resume` partially works) |
| `/login` | ✅ Works — OAuth for 4 providers + direct API key entry |
| `/logout` | ✅ Works — per-provider or all-at-once credential removal |
| `/export` | ❌ Stub |
| `/share` | ❌ Stub |
| `/settings` | ❌ Not implemented |
| `/hotkeys` | ❌ Not implemented |
| `/scoped-models` | ❌ Not implemented |
| `/changelog` | ❌ Not implemented |

### ❌ Not Ported At All

| Module | Upstream Lines | What It Does |
|--------|---------------|-------------|
| **Interactive Mode (TUI)** | **12,942** | The entire rich terminal UI — this is the flagship user experience |
| ↳ 30+ UI Components | ~10,000 | Model selector, session picker, settings UI, login dialog, theme selector, thinking selector, tree navigator, diff view, markdown rendering, streaming display, footer, etc. |
| ↳ Interactive Mode orchestrator | ~2,000 | Wires everything together — slash command handling, message rendering, tool execution display, autocomplete |
| ↳ Theme system | ~200 | Theming for the TUI |
| **RPC Mode** | **1,399** | VS Code / editor integration protocol — allows external editors to drive pi |
| **Auth Storage** | **331** | ✅ **Ported** — `auth.json` management, OAuth flows, API key storage, token refresh, priority chain |
| **Model Registry** | **544** | `models.json` parsing, custom model definitions, provider-specific config, API key resolution |
| **Package Manager** | **1,627** | `pi install/remove/update` for extensions — npm, git, local path sources |
| **Extension Runner** | **~800** | Full extension lifecycle — load, init, command registration, tool wrapping, event emission, `ExtensionAPI` |
| **Export HTML** | **303** | Session export to shareable HTML with tool rendering |
| **Bash Executor** | **278** | PTY-based command execution with proper streaming |
| **Edit Diff** | **308** | Rich diff display for the edit tool |
| **Keybindings** | **211** | Configurable keyboard shortcuts system (`keybindings.json`) |
| **Messages** | **195** | Message formatting and display helpers |
| **SDK** (`createAgentSession`) | **365** | The high-level session factory — the "right way" to create a session |
| **Migrations** | **295** | Session file format version migrations |
| **Utilities** | **1,321** | Clipboard (text + image), git operations, image resize/convert, shell detection, changelog parsing |

---

## What Actually Works End-to-End

If you run `pipy-coding-agent` today, you get:

1. **A plain `input()` REPL** — no syntax highlighting, no autocomplete, no rich rendering
2. **LLM responses** via LiteLLM (any provider with an API key in env vars)
3. **Tool execution** — read, write, edit, bash, grep, find, ls all work correctly
4. **Session persistence** — conversations saved to JSONL, can resume with `--session`
5. **Print mode** (`-p "prompt"`) — single prompt, output, exit
6. **Basic slash commands** — `/model`, `/thinking`, `/clear`, `/new`, `/session`
7. **OAuth login** (`/login`) — Anthropic, OpenAI Codex, GitHub Copilot, Google Gemini CLI
8. **Auth storage** (`~/.pipy/auth.json`) — API keys and OAuth credentials persisted with auto-refresh

What you **don't** get (that upstream has):
- No rich TUI (no markdown rendering, no streaming display, no footer)
- No autocomplete (no `/` commands menu, no `@` file picker)
- No custom models (`models.json` not supported)
- No extensions
- No package management
- No session fork/tree navigation
- No export/share
- No RPC mode for editor integration
- No image support in terminal
- No configurable keybindings

---

## Recommended Priority for Closing the Gap

### Phase 1: Make It Usable (Auth + Models) — ✅ DONE
1. ~~**Auth Storage** — `auth.json` with API key persistence, `resolve_config_value` wiring~~ ✅
2. ~~Wire `/login` and `/logout`~~ ✅ (OAuth + API key entry)
3. **Model Registry** — `models.json` support, custom models, provider config (nice-to-have)

### Phase 2: Make It Interactive (TUI)
4. **Wire pipy-tui into coding-agent** — replace `input()` REPL with Textual app
5. **Streaming display** — show LLM responses as they arrive with markdown
6. **Tool execution display** — show tool calls and results inline
7. **Slash command autocomplete** — wire `SlashCommandProvider`
8. **File autocomplete** — wire `FilePathProvider`

### Phase 3: Make It Complete (Parity)
9. **Extension Runner** — load and execute extensions
10. **Package Manager** — install/remove extensions
11. **Fork/Tree/Resume** — full session branching UI
12. **RPC Mode** — editor integration
13. **Export/Share** — HTML export, gist sharing
14. **Remaining UI components** — settings, model selector, theme selector, etc.

---

## Architecture Notes

### Intentional Differences (Not Bugs)

- **LiteLLM vs. per-provider**: pipy-ai uses LiteLLM (~2K lines) where upstream has ~20K lines of provider code. This is the right tradeoff — LiteLLM gives us 100+ providers for free.
- **Textual vs. custom TUI**: pipy-tui uses Textual where upstream builds from raw ANSI. Textual gives us a lot for free (layout, focus, mouse, accessibility) but means we can't do a line-by-line port of the interactive mode.
- **Python async model**: Python's async is different from Node.js. The agent loop uses `asyncio` where upstream uses synchronous generators with `yield`.

### Structural Gaps

- **No `createAgentSession()` SDK**: Upstream has a clean factory function that wires everything together. We have `AgentSession.__init__()` that does a fraction of the setup.
- **No event bus**: Upstream has a central event bus for session-wide events. We have direct method calls.
- **No resource path resolution**: Upstream resolves resources from packages, user dir, project dir, and PATH. We only check user and project dirs.
