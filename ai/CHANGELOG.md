# Changelog

This changelog tracks pipy-ai releases and their alignment with the upstream [@mariozechner/pi-ai](https://github.com/badlogic/pi-mono/tree/main/packages/ai) TypeScript package.

## [0.51.6.1] - 2026-02-04

### Added — OAuth module (`pipy_ai.oauth`)

Ported OAuth credential management from `pi-ai/src/utils/oauth/`:

- **PKCE utilities** (`pkce.py`): `generate_pkce()` — code verifier + SHA-256 challenge
- **Types** (`types.py`): `OAuthCredentials`, `OAuthPrompt`, `OAuthAuthInfo`, `OAuthLoginCallbacks`, `OAuthProviderInterface`
- **Provider registry** (`registry.py`): `get_oauth_provider()`, `get_oauth_providers()`, `register_oauth_provider()`, `get_oauth_api_key()` with auto-refresh
- **Anthropic** (`anthropic.py`): PKCE OAuth flow, manual code paste, token refresh
- **OpenAI Codex** (`openai_codex.py`): PKCE + local callback server (port 1455), JWT accountId extraction, code paste fallback
- **GitHub Copilot** (`github_copilot.py`): Device code flow, enterprise domain support, Copilot token exchange
- **Google Gemini CLI** (`google_gemini.py`): Google Cloud OAuth, local callback server (port 8085), GCP project discovery

31 new tests for PKCE, registry, provider helpers.

## [0.51.6] - 2026-02-04

**Upstream sync:** [pi-ai v0.51.6](https://github.com/badlogic/pi-mono/releases/tag/v0.51.6)  
**Upstream commit:** `9cf5758b`

### Added

- Added `supports_xhigh()` function to check if a model supports xhigh thinking level
- xhigh thinking level now passed through (not downgraded to high) for gpt-5.2 models

### Changed

- `supportsXhigh` check changed from hardcoded model set to `"gpt-5.2" in model_id` (matches upstream)

### Not Applicable (vs upstream v0.51.3–v0.51.6)

- v0.51.3: xhigh model set fix → applied as `supports_xhigh()` function
- v0.51.4: No ai changes
- v0.51.5: Bedrock model generation changes → N/A (we use LiteLLM)
- v0.51.6: OpenAI Codex Responses baseUrl fix → N/A (LiteLLM handles provider URLs)
- `models.generated.ts` regeneration → N/A (we use LiteLLM's model registry)

---

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
