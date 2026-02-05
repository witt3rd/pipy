"""OAuth credential management for AI providers.

Handles login, token refresh, and credential storage for OAuth-based providers:
- Anthropic (Claude Pro/Max)
- OpenAI Codex (ChatGPT Plus/Pro)
- GitHub Copilot
- Google Gemini CLI (Code Assist)
- Google Antigravity (Gemini 3, Claude, GPT-OSS via Google Cloud)

Port of pi-ai/src/utils/oauth/
"""

from .types import (
    OAuthAuthInfo,
    OAuthCredentials,
    OAuthLoginCallbacks,
    OAuthPrompt,
    OAuthProviderInterface,
)
from .pkce import generate_pkce
from .registry import (
    get_oauth_provider,
    get_oauth_providers,
    register_oauth_provider,
    get_oauth_api_key,
)
from ._litellm_patch import patch_litellm_anthropic_oauth

# Apply litellm patch for Anthropic OAuth support on import
patch_litellm_anthropic_oauth()

__all__ = [
    # Types
    "OAuthCredentials",
    "OAuthPrompt",
    "OAuthAuthInfo",
    "OAuthLoginCallbacks",
    "OAuthProviderInterface",
    # PKCE
    "generate_pkce",
    # Registry
    "get_oauth_provider",
    "get_oauth_providers",
    "register_oauth_provider",
    "get_oauth_api_key",
]
