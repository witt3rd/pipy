"""OAuth provider registry.

Port of the registry portion of pi-ai/src/utils/oauth/index.ts.
"""

from __future__ import annotations

import time
from typing import Any

from .types import OAuthCredentials

# Lazy-loaded providers to avoid import-time HTTP dependencies
_registry: dict[str, Any] | None = None


def _ensure_registry() -> dict[str, Any]:
    global _registry
    if _registry is None:
        from .anthropic import AnthropicOAuthProvider
        from .openai_codex import OpenAICodexOAuthProvider
        from .github_copilot import GitHubCopilotOAuthProvider
        from .google_gemini import GoogleGeminiOAuthProvider

        _registry = {}
        for provider in [
            AnthropicOAuthProvider(),
            OpenAICodexOAuthProvider(),
            GitHubCopilotOAuthProvider(),
            GoogleGeminiOAuthProvider(),
        ]:
            _registry[provider.id] = provider

    return _registry


def get_oauth_provider(provider_id: str):
    """Get an OAuth provider by ID.

    Returns:
        Provider instance, or None if not found.
    """
    return _ensure_registry().get(provider_id)


def get_oauth_providers() -> list:
    """Get all registered OAuth providers."""
    return list(_ensure_registry().values())


def register_oauth_provider(provider) -> None:
    """Register a custom OAuth provider."""
    _ensure_registry()[provider.id] = provider


async def get_oauth_api_key(
    provider_id: str,
    credentials: dict[str, OAuthCredentials],
) -> dict[str, Any] | None:
    """Get API key for a provider from OAuth credentials.

    Automatically refreshes expired tokens.

    Args:
        provider_id: Provider ID.
        credentials: Dict mapping provider IDs to credentials.

    Returns:
        {"new_credentials": OAuthCredentials, "api_key": str} or None.
    """
    provider = get_oauth_provider(provider_id)
    if not provider:
        raise RuntimeError(f"Unknown OAuth provider: {provider_id}")

    creds = credentials.get(provider_id)
    if not creds:
        return None

    # Refresh if expired
    if time.time() * 1000 >= creds.expires:
        try:
            creds = await provider.refresh_token(creds)
        except Exception:
            raise RuntimeError(f"Failed to refresh OAuth token for {provider_id}")

    api_key = provider.get_api_key(creds)
    return {"new_credentials": creds, "api_key": api_key}
