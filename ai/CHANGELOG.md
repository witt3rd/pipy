# Changelog

This changelog tracks pipy-ai releases and their alignment with the upstream [@mariozechner/pi-ai](https://github.com/badlogic/pi-mono/tree/main/packages/ai) TypeScript package.

## [0.51.2] - 2026-02-02

**Upstream sync:** [pi-ai v0.51.2](https://github.com/badlogic/pi-mono/releases/tag/v0.51.2)  
**Upstream commit:** `4cbc8652`

_No code changes in upstream ai package - version bump only._

---

## [0.51.1] - 2026-02-02

**Upstream sync:** [pi-ai v0.51.1](https://github.com/badlogic/pi-mono/releases/tag/v0.51.1)  
**Upstream commit:** `1fbafd6cc7b63fe6810cd8c4a42cb3232139751c`

### Added

- Wired up `reasoning` level from `SimpleStreamOptions` to LiteLLM's `reasoning_effort` parameter
- Wired up `thinking_budgets` to pass Anthropic-style `thinking` parameter with `budget_tokens`
- Wired up `headers` option to LiteLLM's `extra_headers`
- Wired up `session_id` option via `x-session-id` header for cache affinity
- Added `StopReason.SENSITIVE` for Anthropic content flagging
- Added `tests/test_provider.py` with 20 tests for `_build_kwargs` functionality
- Added `tests/test_integration.py` with skippable integration tests (run with `--run-integration`)
- Added `tests/conftest.py` for pytest configuration

### Fixed

- `reasoning` level was defined in types but never passed to LiteLLM (dead code)
- `thinking_budgets` was defined in types but never used

### Known Limitations (vs upstream)

- `max_retry_delay_ms` - Field exists for API compatibility but LiteLLM handles retries internally
- `cache_retention` - LiteLLM handles caching per-provider; not directly exposed
- Provider-specific OAuth flows not applicable (we use API keys via LiteLLM)

### Architecture Differences

This is a Python port using LiteLLM as the backend, not a direct translation. Key differences:

- LiteLLM abstracts 100+ providers vs upstream's per-provider implementations
- Many provider-specific fixes in upstream are handled by LiteLLM internally
- OAuth flows replaced by standard API key authentication

---

## [0.1.0] - 2026-02-02

**Initial release** - Python port of pi-ai using LiteLLM backend.

### Added

- Core types: `Message`, `Context`, `Tool`, `Usage`, `Cost`
- Content types: `TextContent`, `ThinkingContent`, `ImageContent`, `ToolCall`
- Streaming events: `StartEvent`, `TextDeltaEvent`, `ThinkingDeltaEvent`, `ToolCallDeltaEvent`, `DoneEvent`, `ErrorEvent`
- Options: `StreamOptions`, `SimpleStreamOptions`, `ThinkingLevel`, `ThinkingBudgets`, `CacheRetention`
- API functions: `complete()`, `stream()`, `acomplete()`, `astream()`, `quick()`, `ctx()`, `user()`
- `AbortController`/`AbortSignal` for cancellation
- Model registry with models.dev integration
- CLI with `pipy-ai models` command
