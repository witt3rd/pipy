# pipy-coding-agent Port Status

**Tracking progress against upstream pi-coding-agent**

## CLI Flags

| Flag | Status | Notes |
|------|--------|-------|
| `--help` | ✅ | Full help with examples |
| `--version` | ✅ | |
| `-m/--model` | ✅ | With aliases |
| `--provider` | ✅ | Sets env var |
| `--api-key` | ✅ | Sets env var |
| `--thinking` | ✅ | off/minimal/low/medium/high |
| `-p/--print` | ✅ | Non-interactive mode |
| `--system-prompt` | ✅ | |
| `--append-system-prompt` | ✅ | Supports file paths |
| `-c/--continue` | ✅ | Continue previous session |
| `-r/--resume` | ✅ | Interactive session picker |
| `--session` | ✅ | Specific session file |
| `--session-dir` | ✅ | Custom session directory |
| `--no-session` | ✅ | Ephemeral mode |
| `--tools` | 🔶 | Parsed, not wired |
| `--no-tools` | ✅ | |
| `-e/--extension` | 🔶 | Parsed, not wired |
| `--skill` | 🔶 | Parsed, not wired |
| `--prompt-template` | 🔶 | Parsed, not wired |
| `--theme` | 🔶 | Parsed, not wired |
| `--no-extensions` | 🔶 | Parsed, not wired |
| `--no-skills` | 🔶 | Parsed, not wired |
| `--mode` | 🔶 | text only, json/rpc not done |
| `--export` | 🔶 | Parsed, export basic |
| `--list-models` | ✅ | With pattern filter |
| `--verbose` | ✅ | |
| `--cwd` | ✅ | |
| `@file` args | ✅ | Read file into prompt |

## Slash Commands

| Command | Status | Notes |
|---------|--------|-------|
| `/help` | ✅ | Lists all commands |
| `/model` | ✅ | Change model |
| `/thinking` | ✅ | Set thinking level |
| `/clear` | ✅ | Clear and start fresh |
| `/new` | ✅ | Start new session |
| `/session` | ✅ | Show session info |
| `/export` | ✅ | Basic HTML export |
| `/copy` | ✅ | Copy to clipboard |
| `/reload` | ✅ | Reload resources |
| `/login` | ✅ | Shows env var instructions |
| `/logout` | ✅ | N/A (env vars) |
| `/quit` | ✅ | Exit |
| `/exit` | ✅ | Exit |
| `/fork` | 🔶 | Stub |
| `/tree` | 🔶 | Stub |
| `/compact` | 🔶 | Stub |
| `/resume` | 🔶 | Stub (use --resume flag) |
| `/settings` | ❌ | Needs TUI |
| `/share` | ❌ | GitHub gist upload |
| `/scoped-models` | ❌ | Needs TUI |
| `/changelog` | ❌ | |
| `/hotkeys` | ❌ | |

## Core Features

| Feature | Status | Notes |
|---------|--------|-------|
| Tools (7) | ✅ | read, write, edit, bash, grep, find, ls |
| Session persistence | ✅ | JSONL with tree structure |
| Session branching | ✅ | Backend done, UI stub |
| Settings | ✅ | Global + project hierarchy |
| Skills loading | ✅ | From markdown |
| Prompt templates | ✅ | With arg substitution |
| Context files | ✅ | CLAUDE.md, AGENTS.md |
| Compaction | ✅ | Backend done |
| Model aliases | ✅ | sonnet, opus, etc |
| Extensions | 🔶 | Hook system, no Python modules |
| Streaming display | ❌ | Shows after completion |
| OAuth | ❌ | Uses env vars via LiteLLM |

## TUI (Interactive Mode)

| Component | Status |
|-----------|--------|
| Basic readline loop | ✅ |
| Slash command parsing | ✅ |
| Streaming tokens | ❌ |
| Tool execution display | ❌ |
| Session picker | 🔶 (text) |
| Model selector | ❌ |
| Settings UI | ❌ |
| Tree navigator | ❌ |
| Footer/keybindings | ❌ |
| Theme support | ❌ |

## Test Coverage

- **332 tests passed**, 2 skipped
- Source: ~7,700 lines
- Tests: ~4,800 lines

## Summary

**CLI: ~70%** - Most flags implemented, some need wiring

**Commands: ~60%** - Core commands work, tree/fork/compact are stubs

**TUI: ~10%** - Readline only, no real TUI yet

## Next Steps

1. Wire up remaining CLI flags (tools, extensions, skills)
2. Implement /fork, /tree, /compact commands
3. Add streaming token display
4. Build TUI with pipy-tui
