# pipy-coding-agent Port Status

**Honest assessment of what's ported vs upstream pi-coding-agent**

## What Works ✅

### Core Libraries (Backend)
- **Tools** (7/7): read, write, edit, bash, grep, find, ls - FULLY FUNCTIONAL
- **Session storage**: JSONL format, tree structure, branching - WORKS
- **Settings**: Global/project hierarchy, migration - WORKS
- **Resources**: Skills loading, prompt templates, context files - WORKS
- **Compaction**: Token estimation, cut points, summarization - WORKS (untested with real LLM)
- **Model resolver**: Aliases (sonnet→claude-sonnet-4, etc) - WORKS
- **Extensions**: Hook system, loader - BASIC (no Python module loading)

### CLI
- `-p/--prompt` single prompt mode - WORKS (if you have API key)
- `--model` - WORKS
- `--thinking` - WORKS  
- `--no-session` - WORKS
- Basic interactive loop - WORKS (barely)

## What's Missing ❌

### CLI Flags (17+ missing)
- `--provider` - NOT IMPLEMENTED
- `--api-key` - NOT IMPLEMENTED (env vars only)
- `--continue/-c` - NOT IMPLEMENTED
- `--resume/-r` - NOT IMPLEMENTED
- `--session <path>` - NOT IMPLEMENTED
- `--session-dir` - NOT IMPLEMENTED
- `--models` (cycling) - NOT IMPLEMENTED
- `--tools/--no-tools` - NOT IMPLEMENTED
- `--export` - NOT IMPLEMENTED
- `--extension/-e` - NOT IMPLEMENTED
- `--skill` - NOT IMPLEMENTED
- `--prompt-template` - NOT IMPLEMENTED
- `--theme` - NOT IMPLEMENTED
- `--list-models` - NOT IMPLEMENTED
- `--mode` (json/rpc) - NOT IMPLEMENTED
- `@file` args - NOT IMPLEMENTED

### Slash Commands (15+ missing)
- `/login` - NOT IMPLEMENTED
- `/logout` - NOT IMPLEMENTED
- `/settings` - NOT IMPLEMENTED
- `/export` - NOT IMPLEMENTED
- `/share` - NOT IMPLEMENTED
- `/copy` - NOT IMPLEMENTED
- `/name` - NOT IMPLEMENTED
- `/session` - NOT IMPLEMENTED
- `/fork` - NOT IMPLEMENTED
- `/tree` - NOT IMPLEMENTED
- `/compact` - NOT IMPLEMENTED
- `/resume` - NOT IMPLEMENTED
- `/reload` - NOT IMPLEMENTED
- `/new` - NOT IMPLEMENTED
- `/hotkeys` - NOT IMPLEMENTED

### TUI (Interactive Mode)
- **Entire TUI is missing** - We have readline, upstream has full Textual-style UI
- No streaming token display
- No tool execution visualization
- No session picker
- No model selector
- No settings UI
- No tree navigator
- No OAuth dialogs
- No theme support in UI
- No keyboard shortcuts beyond basic readline

### Authentication
- OAuth flows - NOT IMPLEMENTED
- API key management - NOT IMPLEMENTED (just reads env vars)
- auth.json storage - NOT IMPLEMENTED

### Package Management
- `pi install/remove/update/list` - NOT IMPLEMENTED
- Extension installation - NOT IMPLEMENTED

## Summary

**Backend: ~80% ported** - Core libraries work, tested with 318 unit tests

**CLI: ~20% ported** - Basic flags only, most features missing

**TUI: ~0% ported** - Just a readline loop, not the real interactive mode

**The "8 phases" built the backend SDK, not the user-facing application.**

## To Match Upstream

1. Add 17+ CLI flags
2. Add 15+ slash commands  
3. Build TUI with pipy-tui (30+ components)
4. Add OAuth/auth system
5. Add package management
6. Wire up streaming display
7. Add all the UI components

This is substantial work - probably 3-4x what's been done.
