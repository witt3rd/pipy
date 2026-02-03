# Updating Pi Python Ports

This document describes the process for syncing Python ports (pipy-*) with their upstream TypeScript counterparts in [pi-mono](https://github.com/badlogic/pi-mono).

## Overview

The pipy-* packages are Python ports inspired by Mario Zechner's pi-mono TypeScript packages. While not direct translations (we use LiteLLM as the backend instead of per-provider implementations), we track upstream versions and incorporate relevant fixes and features.

## Prerequisites

- Access to both repos:
  - Upstream: `~/src/ext/pi-mono/packages/ai/` (or wherever you cloned it)
  - Port: `~/src/witt3rd/pipy/ai/` (or the specific package)
- The port's `CHANGELOG.md` should contain the last synced upstream commit hash

## Step 1: Discover Upstream Changes

### Check the upstream's recent commits and changelog:

```bash
# Navigate to upstream repo
cd ~/src/ext/pi-mono/packages/ai

# Pull latest changes
git pull

# View recent commits
git log --oneline -20

# Read the changelog for detailed changes
cat CHANGELOG.md
```

### Identify the starting point:

If this is the **first sync**, look at the latest release tag/version in the upstream CHANGELOG.md.

If you've synced before, find the last synced commit in your port's `CHANGELOG.md`:

```markdown
## [0.51.1] - 2026-02-02
**Upstream commit:** `1fbafd6cc7b63fe6810cd8c4a42cb3232139751c`
```

### View changes since last sync:

```bash
# See what changed since last sync
git log --oneline <last-synced-commit>..HEAD

# See detailed file changes
git diff <last-synced-commit>..HEAD --stat src/

# View specific file changes
git diff <last-synced-commit>..HEAD -- src/providers/anthropic.ts
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
## Upstream Changes Analysis (v0.50.0 → v0.51.1)

### Applicable:
- [ ] v0.51.1: cache_control for string user messages
- [ ] v0.51.0: StopReason.SENSITIVE
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

Sometimes upstream releases have no changes to the `ai` package (changes may be in `coding-agent` or other packages). Check with:

```bash
git diff <last-synced-commit>..HEAD --stat src/
# (no output) = no source changes
```

If there are no code changes, still bump the version to stay in sync:

1. Update `pyproject.toml` version
2. Add a minimal CHANGELOG entry:

```markdown
## [0.51.2] - 2026-02-03

**Upstream sync:** [pi-ai v0.51.2](https://github.com/badlogic/pi-mono/releases/tag/v0.51.2)  
**Upstream commit:** `4cbc8652`

_No code changes in upstream ai package - version bump only._
```

3. Commit: `git commit -m "chore: sync with upstream pi-ai v0.51.2 (no code changes)"`

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

## Step 4: Update CHANGELOG.md

Follow this format to track upstream sync:

```markdown
# Changelog

## [0.51.1] - 2026-02-02

**Upstream sync:** [pi-ai v0.51.1](https://github.com/badlogic/pi-mono/releases/tag/v0.51.1)  
**Upstream commit:** `1fbafd6cc7b63fe6810cd8c4a42cb3232139751c`

### Added
- Wired up `reasoning` level to LiteLLM's `reasoning_effort` parameter
- Added `StopReason.SENSITIVE` for Anthropic content flagging

### Fixed
- `reasoning` level was defined but never passed to LiteLLM

### Known Limitations (vs upstream)
- `max_retry_delay_ms` - LiteLLM handles retries internally
- Provider-specific OAuth not applicable
```

### Get the upstream commit hash:

```bash
cd ~/src/ext/pi-mono/packages/ai
git rev-parse HEAD
# 1fbafd6cc7b63fe6810cd8c4a42cb3232139751c
```

## Step 5: Add/Update Tests

### Unit tests for new functionality:

```python
# tests/test_provider.py
def test_reasoning_high(self):
    options = SimpleStreamOptions(reasoning=ThinkingLevel.HIGH)
    kwargs = self.provider._build_kwargs("gpt-4", self.messages, options)
    assert kwargs["reasoning_effort"] == "high"
```

### Integration tests (skippable):

```python
# tests/test_integration.py
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="No API key")
def test_reasoning_with_o1_mini(self):
    result = complete("openai/o1-mini", ctx(user("What is 2+2?")),
                      SimpleStreamOptions(reasoning=ThinkingLevel.LOW))
    assert "4" in result.text
```

### Set up CI (first time only):

Create `.github/workflows/ci.yml`:

```yaml
name: CI
on:
  push:
    branches: [master, main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --extra dev
      - run: uv run pytest tests/ -v --tb=short
      - run: uv run ruff check src/ tests/
```

### Set up pre-commit hooks (first time only):

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      # On commit: auto-fix issues
      - id: ruff-check
        name: ruff check
        entry: uv run ruff check --fix
        language: system
        types: [python]
        pass_filenames: false
        stages: [pre-commit]

      - id: ruff-format
        name: ruff format
        entry: uv run ruff format
        language: system
        types: [python]
        pass_filenames: false
        stages: [pre-commit]

      # On push: check only (no modifications), run tests
      - id: ruff-check-push
        name: ruff check (push)
        entry: uv run ruff check  # NO --fix here!
        language: system
        types: [python]
        pass_filenames: false
        stages: [pre-push]

      - id: pytest
        name: pytest
        entry: uv run pytest tests/ -v --tb=short
        language: system
        types: [python]
        pass_filenames: false
        stages: [pre-push]
```

> ⚠️ **Important:** Pre-push hooks must NOT auto-fix files (no `--fix` flag). If hooks modify files during push, the push will fail because there are uncommitted changes.

Install the hooks:

```bash
uv sync --extra dev  # Ensure pre-commit is installed
uv run pre-commit install
uv run pre-commit install --hook-type pre-push
```

## Step 6: Update Version Number

Match the upstream version for easy tracking:

```toml
# pyproject.toml
[project]
version = "0.51.1"  # Match upstream pi-ai version
```

This makes it easy to see at a glance which upstream version the port is based on.

## Step 7: Commit and Push

```bash
# Stage all changes
git add -A

# Commit with descriptive message
git commit -m "feat: sync with upstream pi-ai v0.51.1

Upstream sync: pi-ai v0.51.1 (commit 1fbafd6c)

Features:
- Wire up reasoning level to LiteLLM's reasoning_effort
- Add StopReason.SENSITIVE

CI/Testing:
- Add GitHub Actions workflow
- Add pre-commit hooks
- Add test_provider.py with new tests

Documentation:
- Add CHANGELOG.md tracking upstream sync
- Version bump to 0.51.1"

# Push
git push
```

## Quick Reference: Commands

```bash
# === UPSTREAM REPO ===
cd ~/src/ext/pi-mono/packages/ai
git pull
git log --oneline -20
cat CHANGELOG.md
git rev-parse HEAD  # Get commit hash for CHANGELOG

# === PORT REPO ===
cd ~/src/witt3rd/pipy/ai

# Check current state
cat CHANGELOG.md | head -20  # Find last synced commit

# After making changes
uv sync --extra dev
uv run pytest tests/ -v
uv run ruff check --fix src/ tests/
uv run ruff format src/ tests/

# Commit
git add -A
git commit  # Pre-commit hooks will run
git push
```

## Checklist Template

Copy this for each sync:

```markdown
## Sync Checklist: pi-ai vX.Y.Z → pipy-ai vX.Y.Z

- [ ] Pull latest upstream changes
- [ ] Read upstream CHANGELOG since last sync
- [ ] Check for source changes: `git diff <last-commit>..HEAD --stat src/`

### If code changes exist:
- [ ] Categorize changes (applicable / LiteLLM handles / N/A)
- [ ] Update types.py (new enums, fields, options)
- [ ] Update provider.py (wire up new options)
- [ ] Update stop reason mappings (if new reasons added)
- [ ] Add unit tests for new functionality
- [ ] Run full test suite

### If no code changes (version-only):
- [ ] Note in CHANGELOG: "No code changes - version bump only"

### Always:
- [ ] Update CHANGELOG.md with upstream commit hash
- [ ] Update version in pyproject.toml
- [ ] Commit and push
```
