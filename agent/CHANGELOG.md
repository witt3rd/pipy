# Changelog

This changelog tracks pipy-agent releases and their alignment with the upstream [@mariozechner/pi-agent](https://github.com/badlogic/pi-mono/tree/main/packages/agent) TypeScript package.

## [0.51.2] - 2026-02-02

**Upstream sync:** [pi-agent v0.51.2](https://github.com/badlogic/pi-mono/releases/tag/v0.51.2)  
**Upstream commit:** `ff9a3f06`

### Added

- Added `thinking_budgets` option to `Agent` and `AgentLoopConfig` for customizing token budgets per thinking level (synced from v0.38.0)
- Added `max_retry_delay_ms` option to cap server-requested retry delays (synced from v0.50.8)
- Added `session_id` property with getter/setter on `Agent` class
- Re-exported `ThinkingBudgets` from pipy-ai for convenience

### Fixed

- Options are now properly passed through to pipy-ai stream calls

### Known Limitations (vs upstream)

- `max_retry_delay_ms` - Passed to pipy-ai, but LiteLLM may handle retries internally
- Provider-specific OAuth flows not applicable (we use API keys via LiteLLM)

### Architecture Differences

This is a Python port using LiteLLM as the backend, not a direct translation. Key differences:

- LiteLLM abstracts 100+ providers vs upstream's per-provider implementations
- Many provider-specific fixes in upstream are handled by LiteLLM internally
- OAuth flows replaced by standard API key authentication

---

## [0.1.0] - 2026-02-02

**Initial release** - Python port of pi-agent using pipy-ai/LiteLLM backend.

### Added

- `Agent` class with state management and event subscriptions
- `AgentTool` and `@tool` decorator for defining executable tools
- `AgentToolResult` for structured tool responses
- Agent loop with steering and follow-up queue support
- Events: `agent_start`, `agent_end`, `turn_start`, `turn_end`, `message_start`, `message_update`, `message_end`, `tool_execution_start`, `tool_execution_update`, `tool_execution_end`
- Low-level `agent_loop()` and `agent_loop_continue()` functions
- Re-exports common pipy-ai types for convenience
