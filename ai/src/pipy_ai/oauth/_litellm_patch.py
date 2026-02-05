"""Monkey-patch litellm to support Anthropic OAuth tokens.

Problem: LiteLLM's Anthropic handler always sets `x-api-key` in request headers.
When using an OAuth token (sk-ant-oat*), the Anthropic API rejects `x-api-key`
with "invalid x-api-key" because OAuth tokens must be sent via `Authorization: Bearer`.

Fix: Patch `AnthropicConfig.get_anthropic_headers` to replace `x-api-key` with
`Authorization: Bearer` when the key is an OAuth token.

This patch is applied once at import time by `pipy_ai.oauth`.
"""

from __future__ import annotations

_patched = False


def patch_litellm_anthropic_oauth() -> None:
    """Apply the OAuth patch to litellm's Anthropic handler.

    Safe to call multiple times — only patches once.
    """
    global _patched
    if _patched:
        return
    _patched = True

    try:
        from litellm.llms.anthropic.chat.transformation import AnthropicConfig
    except ImportError:
        return  # litellm not installed or structure changed

    _orig = AnthropicConfig.get_anthropic_headers

    def _patched_get_anthropic_headers(self, api_key, **kwargs):
        headers = _orig(self, api_key=api_key, **kwargs)
        # If this is an OAuth access token, use Bearer auth instead of x-api-key
        if isinstance(api_key, str) and api_key.startswith("sk-ant-oat"):
            headers.pop("x-api-key", None)
            headers["authorization"] = f"Bearer {api_key}"
            # Add required Claude Code / OAuth headers to identify as the CLI
            existing_beta = headers.get("anthropic-beta", "")
            beta_parts = [b.strip() for b in existing_beta.split(",") if b.strip()]
            # claude-code-20250219 identifies us as Claude Code CLI (required for OAuth tokens)
            if "claude-code-20250219" not in beta_parts:
                beta_parts.insert(0, "claude-code-20250219")
            if "oauth-2025-04-20" not in beta_parts:
                beta_parts.append("oauth-2025-04-20")
            headers["anthropic-beta"] = ",".join(beta_parts)
            headers["anthropic-dangerous-direct-browser-access"] = "true"
            headers["x-app"] = "cli"  # Identifies as CLI application
        return headers

    AnthropicConfig.get_anthropic_headers = _patched_get_anthropic_headers
