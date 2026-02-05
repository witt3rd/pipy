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
            # Add required OAuth beta headers (in case they weren't set upstream)
            existing_beta = headers.get("anthropic-beta", "")
            if "oauth-" not in existing_beta:
                beta_parts = [b for b in existing_beta.split(",") if b.strip()]
                beta_parts.append("oauth-2025-04-20")
                headers["anthropic-beta"] = ",".join(beta_parts)
            headers.setdefault("anthropic-dangerous-direct-browser-access", "true")
        return headers

    AnthropicConfig.get_anthropic_headers = _patched_get_anthropic_headers
