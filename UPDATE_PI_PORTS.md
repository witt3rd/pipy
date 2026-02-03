# Updating Pi Python Ports

This document describes the process for syncing Python ports (pipy-*) with their upstream TypeScript counterparts in [pi-mono](https://github.com/badlogic/pi-mono).

## Repository Structure

This is a **UV workspace monorepo** at [github.com/witt3rd/pipy](https://github.com/witt3rd/pipy), mirroring the structure of upstream pi-mono:

```
~/src/witt3rd/pipy/           # Monorepo root
├── pyproject.toml            # Workspace configuration
├── uv.lock                   # Shared lockfile (committed)
├── ai/                       # pipy-ai (syncs with @mariozechner/pi-ai)
│   ├── CHANGELOG.md          # ← Each package has its own CHANGELOG
│   ├── pyproject.toml
│   └── src/pipy_ai/
├── agent/                    # pipy-agent (syncs with @mariozechner/pi-agent)
│   ├── CHANGELOG.md
│   ├── pyproject.toml
│   └── src/pipy_agent/
├── tui/                      # pipy-tui (syncs with @mariozechner/pi-tui)
│   ├── CHANGELOG.md
│   ├── pyproject.toml
│   └── src/pipy_tui/
└── coding-agent/             # pipy-coding-agent (syncs with @mariozechner/pi-coding-agent)
    ├── CHANGELOG.md
    ├── pyproject.toml
    └── src/pipy_coding_agent/
```

### Package Dependencies

```
pipy-ai (foundation - no internal deps)
    └── pipy-agent (depends on pipy-ai)
            └── pipy-coding-agent (depends on pipy-agent, pipy-ai, optionally pipy-tui)

pipy-tui (standalone - no internal deps)
    └── pipy-coding-agent (optional TUI support)
```

### Upstream Package Mapping

| Pipy Package | Upstream Package | Upstream Path |
|--------------|------------------|---------------|
| pipy-ai | @mariozechner/pi-ai | `~/src/ext/pi-mono/packages/ai/` |
| pipy-agent | @mariozechner/pi-agent | `~/src/ext/pi-mono/packages/agent/` |
| pipy-tui | @mariozechner/pi-tui | `~/src/ext/pi-mono/packages/tui/` |
| pipy-coding-agent | @mariozechner/pi-coding-agent | `~/src/ext/pi-mono/packages/coding-agent/` |

## Overview

The pipy-* packages are Python ports inspired by Mario Zechner's pi-mono TypeScript packages. While not direct translations (we use LiteLLM as the backend instead of per-provider implementations), we track upstream versions and incorporate relevant fixes and features.

## Important: Each Package Maintains Its Own CHANGELOG

**Every package must have its own `CHANGELOG.md`** that tracks:
- Version history
- Upstream sync information (commit hash, version)
- Changes made in each release
- Known limitations vs upstream

This is critical because:
1. Packages may be synced independently
2. Users need to know what version of upstream each package tracks
3. Dependencies between packages require version coordination

## Prerequisites

- Access to both repos:
  - Upstream: `~/src/ext/pi-mono/` (clone of https://github.com/badlogic/pi-mono)
  - Port: `~/src/witt3rd/pipy/` (this monorepo)
- UV installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- The port's `CHANGELOG.md` should contain the last synced upstream commit hash

## Step 1: Discover Upstream Changes

### Check the upstream's recent commits and changelog:

```bash
# Navigate to upstream repo
cd ~/src/ext/pi-mono
git pull

# Check specific package (e.g., agent)
cd packages/agent
git log --oneline -20
cat CHANGELOG.md
```

### Identify the starting point:

If this is the **first sync**, look at the latest release tag/version in the upstream CHANGELOG.md.

If you've synced before, find the last synced commit in your port's `CHANGELOG.md`:

```markdown
## [0.51.2] - 2026-02-02
**Upstream commit:** `ff9a3f06`
```

### View changes since last sync:

```bash
# See what changed since last sync
git log --oneline <last-synced-commit>..HEAD

# See detailed file changes for specific package
git diff <last-synced-commit>..HEAD --stat packages/agent/src/

# View specific file changes
git diff <last-synced-commit>..HEAD -- packages/agent/src/agent.ts
```

## Step 2: Analyze Changes for Applicability

Not all upstream changes apply to the Python port. Categorize them:

### ✅ Likely Applicable

- **Type/interface changes** - New fields, enums, options
- **Bug fixes in logic** - Error handling, edge cases
- **New features** - Options, capabilities, stop reasons
- **API changes** - New parameters, return types

### ⚠️ May Need Adaptation

- **Provider-specific fixes** - LiteLLM may handle these internally
- **Streaming parsing** - LiteLLM abstracts this
- **Authentication/OAuth** - We use API keys via LiteLLM

### ❌ Usually Not Applicable

- **Provider-specific OAuth flows** - Not relevant (LiteLLM uses API keys)
- **JavaScript/TypeScript-specific** - Browser compatibility, ESM/CJS
- **SDK version bumps** - We use LiteLLM, not direct SDKs

### Create a checklist:

```markdown
## Upstream Changes Analysis (v0.50.0 → v0.51.2)

### Applicable:
- [ ] v0.50.8: maxRetryDelayMs option
- [ ] v0.38.0: thinkingBudgets option

### LiteLLM handles:
- [ ] Provider-specific retry logic
- [ ] Tool call ID normalization

### Not applicable:
- [ ] OAuth flows (Gemini CLI, Codex, Antigravity)
- [ ] Browser compatibility fixes
```

### Version-only syncs (no code changes)

Sometimes upstream releases have no changes to a specific package. Check with:

```bash
git diff <last-synced-commit>..HEAD --stat packages/agent/src/
# (no output) = no source changes
```

If there are no code changes, still bump the version to stay in sync:

1. Update `pyproject.toml` version
2. Add a minimal CHANGELOG entry:

```markdown
## [0.51.2] - 2026-02-03

**Upstream sync:** [pi-agent v0.51.2](https://github.com/badlogic/pi-mono/releases/tag/v0.51.2)  
**Upstream commit:** `ff9a3f06`

_No code changes in upstream agent package - version bump only._
```

## Step 3: Implement Changes

### Update types first:

```python
# Add new enums, fields, options
class StopReason(str, Enum):
    SENSITIVE = "sensitive"  # NEW: Anthropic content flagging
```

### Update provider/logic:

```python
# Wire up new options
if options.reasoning:
    kwargs["reasoning_effort"] = options.reasoning.value
```

### Document limitations:

```python
class StreamOptions(BaseModel):
    # Note: max_retry_delay_ms exists for API compatibility
    # but LiteLLM handles retries internally
    max_retry_delay_ms: int = 60000
```

## Step 4: Update Package CHANGELOG.md

**Each package maintains its own CHANGELOG.** Follow this format:

```markdown
# Changelog

## [0.51.2] - 2026-02-02

**Upstream sync:** [pi-agent v0.51.2](https://github.com/badlogic/pi-mono/releases/tag/v0.51.2)  
**Upstream commit:** `ff9a3f06`

### Added
- Added `thinking_budgets` option for custom token budgets per thinking level
- Added `max_retry_delay_ms` option to cap server-requested retry delays

### Fixed
- Options now properly passed through to stream calls

### Known Limitations (vs upstream)
- `max_retry_delay_ms` - Passed to pipy-ai, but LiteLLM may handle retries internally
- Provider-specific OAuth not applicable
```

### Get the upstream commit hash:

```bash
cd ~/src/ext/pi-mono
git rev-parse HEAD
# ff9a3f0660e7e4dfcd81d58cd5de9b2a35bb55b4
# Use short form in CHANGELOG: ff9a3f06
```

## Step 5: Add/Update Tests

### Unit tests for new functionality:

```python
# tests/test_agent.py
def test_thinking_budgets_init(self):
    from pipy_agent import ThinkingBudgets
    budgets = ThinkingBudgets(minimal=1024, low=2048)
    agent = Agent(thinking_budgets=budgets)
    assert agent.thinking_budgets == budgets
```

### Run tests for specific package:

```bash
cd ~/src/witt3rd/pipy
uv run --package pipy-agent pytest agent/tests -v --tb=short
```

### Run all tests:

```bash
cd ~/src/witt3rd/pipy
uv run --package pipy-ai pytest ai/tests -q && \
uv run --package pipy-agent pytest agent/tests -q && \
uv run --package pipy-tui pytest tui/tests -q && \
uv run --package pipy-coding-agent pytest coding-agent/tests -q
```

## Step 6: Update Version Numbers

Match the upstream version for easy tracking. Update in **two places**:

### 1. `pyproject.toml`:
```toml
[project]
version = "0.51.2"  # Match upstream version
```

### 2. `__init__.py`:
```python
__version__ = "0.51.2"
```

### Coordinating dependent package versions

When updating `pipy-ai`, also check if `pipy-agent` needs updates:
- If `pipy-ai` adds new types/options that `pipy-agent` should expose
- Update `pipy-agent`'s dependency: `dependencies = ["pipy-ai>=0.51.2"]`

## Step 7: Commit and Push

Since this is a monorepo, commits can include changes to multiple packages:

```bash
cd ~/src/witt3rd/pipy

# Stage all changes
git add -A

# Commit with descriptive message
git commit -m "feat(agent): sync with upstream pi-agent v0.51.2

Upstream sync: pi-agent v0.51.2 (commit ff9a3f06)

Features:
- Add thinking_budgets option
- Add max_retry_delay_ms option
- Add session_id property getter/setter

Also updates pipy-ai dependency to >=0.51.2

Tests: 69 passed"

# Push
git push
```

### Commit message conventions

Use conventional commits with package scope:
- `feat(ai): add new feature to pipy-ai`
- `fix(agent): fix bug in pipy-agent`
- `chore(tui): update dependencies`
- `feat(ai,agent): sync both packages to v0.51.2`

## Quick Reference: Commands

```bash
# === SETUP ===
cd ~/src/witt3rd/pipy
uv sync --all-packages --all-extras

# === UPSTREAM REPO ===
cd ~/src/ext/pi-mono
git pull
git log --oneline -20 -- packages/agent/
cat packages/agent/CHANGELOG.md
git rev-parse --short HEAD  # Get commit hash for CHANGELOG

# === WORKING ON A PACKAGE ===
cd ~/src/witt3rd/pipy

# Check current state
cat agent/CHANGELOG.md | head -20  # Find last synced commit

# Run tests for specific package
uv run --package pipy-agent pytest agent/tests -v

# Lint
uv run ruff check agent/
uv run ruff format agent/

# === COMMIT ===
git add -A
git commit -m "feat(agent): sync with upstream v0.51.2"
git push
```

## Checklist Template

Copy this for each sync:

```markdown
## Sync Checklist: pi-agent vX.Y.Z → pipy-agent vX.Y.Z

- [ ] Pull latest upstream: `cd ~/src/ext/pi-mono && git pull`
- [ ] Read upstream CHANGELOG: `cat packages/agent/CHANGELOG.md`
- [ ] Check for source changes: `git diff <last-commit>..HEAD --stat packages/agent/src/`

### If code changes exist:
- [ ] Categorize changes (applicable / LiteLLM handles / N/A)
- [ ] Update types.py (new enums, fields, options)
- [ ] Update agent.py / loop.py (wire up new options)
- [ ] Add unit tests for new functionality
- [ ] Run tests: `uv run --package pipy-agent pytest agent/tests -v`

### If no code changes (version-only):
- [ ] Note in CHANGELOG: "No code changes - version bump only"

### Always:
- [ ] Update agent/CHANGELOG.md with upstream commit hash
- [ ] Update version in agent/pyproject.toml
- [ ] Update version in agent/src/pipy_agent/__init__.py
- [ ] Check if dependent packages need updates (coding-agent depends on agent)
- [ ] Commit: `git commit -m "feat(agent): sync with upstream vX.Y.Z"`
- [ ] Push: `git push`
```

## Multi-Package Sync

When upstream releases update multiple packages, sync them in dependency order:

1. **pipy-ai** first (no internal dependencies)
2. **pipy-tui** (no internal dependencies)
3. **pipy-agent** (depends on pipy-ai)
4. **pipy-coding-agent** last (depends on agent, ai, optionally tui)

Example commit for multi-package sync:
```bash
git commit -m "feat(ai,agent): sync with upstream v0.51.2

Synced packages:
- pipy-ai v0.51.2 (commit ff9a3f06)
- pipy-agent v0.51.2 (commit ff9a3f06)

Features:
- ai: Add ThinkingBudgets, max_retry_delay_ms
- agent: Wire up new ai options

Tests: 153 passed (ai: 84, agent: 69)"
```
