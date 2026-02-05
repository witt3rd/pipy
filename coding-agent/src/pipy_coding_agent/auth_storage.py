"""Credential storage for API keys and OAuth tokens.

Handles loading, saving, and refreshing credentials from auth.json.

Port of pi-coding-agent/src/core/auth-storage.ts.
"""

from __future__ import annotations

import json
import os
import stat
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from pipy_ai.oauth import (
    OAuthCredentials,
    get_oauth_provider,
    get_oauth_providers,
)

from .settings.resolve_config_value import resolve_config_value


class AuthStorage:
    """Credential storage backed by auth.json.

    Priority for API key resolution:
    1. Runtime override (CLI --api-key)
    2. API key from auth.json (supports !command and env var resolution)
    3. OAuth token from auth.json (auto-refreshed)
    4. Environment variable
    5. Fallback resolver (e.g., models.json custom providers)
    """

    def __init__(self, auth_path: str | Path | None = None):
        if auth_path:
            self._auth_path = Path(auth_path)
        else:
            self._auth_path = Path.home() / ".pipy" / "auth.json"

        self._data: dict[str, dict[str, Any]] = {}
        self._runtime_overrides: dict[str, str] = {}
        self._fallback_resolver: Any = None
        self.reload()

    def reload(self) -> None:
        """Reload credentials from disk."""
        if not self._auth_path.exists():
            self._data = {}
            return
        try:
            content = self._auth_path.read_text(encoding="utf-8")
            self._data = json.loads(content)
        except (json.JSONDecodeError, IOError):
            self._data = {}

    def _save(self) -> None:
        """Save credentials to disk with restricted permissions."""
        self._auth_path.parent.mkdir(parents=True, exist_ok=True)
        self._auth_path.write_text(
            json.dumps(self._data, indent=2),
            encoding="utf-8",
        )
        # Restrict permissions (owner only) - best effort on Windows
        try:
            os.chmod(self._auth_path, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass

    # =========================================================================
    # Runtime overrides
    # =========================================================================

    def set_runtime_api_key(self, provider: str, api_key: str) -> None:
        """Set a runtime API key override (not persisted to disk)."""
        self._runtime_overrides[provider] = api_key

    def remove_runtime_api_key(self, provider: str) -> None:
        """Remove a runtime API key override."""
        self._runtime_overrides.pop(provider, None)

    def set_fallback_resolver(self, resolver) -> None:
        """Set a fallback resolver for API keys not in auth.json or env."""
        self._fallback_resolver = resolver

    # =========================================================================
    # Credential CRUD
    # =========================================================================

    def get(self, provider: str) -> dict[str, Any] | None:
        """Get raw credential for a provider."""
        return self._data.get(provider)

    def set_api_key(self, provider: str, key: str) -> None:
        """Store an API key credential."""
        self._data[provider] = {"type": "api_key", "key": key}
        self._save()

    def set_oauth(self, provider: str, credentials: OAuthCredentials) -> None:
        """Store OAuth credentials."""
        data: dict[str, Any] = {
            "type": "oauth",
            "refresh": credentials.refresh,
            "access": credentials.access,
            "expires": credentials.expires,
        }
        data.update(credentials.extra)
        self._data[provider] = data
        self._save()

    def remove(self, provider: str) -> None:
        """Remove credential for a provider."""
        self._data.pop(provider, None)
        self._save()

    def get_providers_with_credentials(self) -> list[str]:
        """Get list of provider IDs that have stored credentials."""
        return list(self._data.keys())

    # =========================================================================
    # API key resolution
    # =========================================================================

    async def get_api_key(self, provider_id: str) -> str | None:
        """Get API key for a provider.

        Priority:
        1. Runtime override (CLI --api-key)
        2. API key from auth.json (supports !command and env var resolution)
        3. OAuth token from auth.json (auto-refreshed)
        4. Environment variable
        5. Fallback resolver
        """
        # 1. Runtime override
        runtime_key = self._runtime_overrides.get(provider_id)
        if runtime_key:
            return runtime_key

        cred = self._data.get(provider_id)

        # 2. API key from auth.json
        if cred and cred.get("type") == "api_key":
            return resolve_config_value(cred["key"])

        # 3. OAuth token from auth.json
        if cred and cred.get("type") == "oauth":
            provider = get_oauth_provider(provider_id)
            if not provider:
                return None

            oauth_creds = OAuthCredentials(
                refresh=cred["refresh"],
                access=cred["access"],
                expires=cred["expires"],
                extra={k: v for k, v in cred.items()
                       if k not in ("type", "refresh", "access", "expires")},
            )

            # Check if token needs refresh
            if time.time() * 1000 >= oauth_creds.expires:
                try:
                    refreshed = await provider.refresh_token(oauth_creds)
                    self.set_oauth(provider_id, refreshed)
                    return provider.get_api_key(refreshed)
                except Exception:
                    return None
            else:
                return provider.get_api_key(oauth_creds)

        # 4. Environment variable
        env_key = _get_env_api_key(provider_id)
        if env_key:
            return env_key

        # 5. Fallback resolver
        if self._fallback_resolver:
            return self._fallback_resolver(provider_id)

        return None


# =========================================================================
# Environment variable API key lookup
# =========================================================================

_ENV_MAP: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
    "xai": "XAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "vercel-ai-gateway": "AI_GATEWAY_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "huggingface": "HF_TOKEN",
    "github-copilot": "COPILOT_GITHUB_TOKEN",
}

# Additional env vars to check (fallbacks)
_ENV_FALLBACKS: dict[str, list[str]] = {
    "anthropic": ["ANTHROPIC_OAUTH_TOKEN"],
    "github-copilot": ["GH_TOKEN", "GITHUB_TOKEN"],
}


def _get_env_api_key(provider: str) -> str | None:
    """Get API key from environment variables."""
    # Check fallbacks first (higher priority for some providers)
    for env_var in _ENV_FALLBACKS.get(provider, []):
        value = os.environ.get(env_var)
        if value:
            return value

    # Check primary env var
    env_var = _ENV_MAP.get(provider)
    if env_var:
        value = os.environ.get(env_var)
        if value:
            return value

    return None
