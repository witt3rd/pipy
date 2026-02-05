"""Anthropic OAuth flow (Claude Pro/Max).

Port of pi-ai/src/utils/oauth/anthropic.ts.
"""

from __future__ import annotations

import base64
from typing import Awaitable, Callable

import httpx

from .pkce import generate_pkce
from .types import OAuthAuthInfo, OAuthCredentials, OAuthPrompt

_CLIENT_ID = base64.b64decode("OWQxYzI1MGEtZTYxYi00NGQ5LTg4ZWQtNTk0NGQxOTYyZjVl").decode()
_AUTHORIZE_URL = "https://claude.ai/oauth/authorize"
_TOKEN_URL = "https://console.anthropic.com/v1/oauth/token"
_REDIRECT_URI = "https://console.anthropic.com/oauth/code/callback"
_SCOPES = "org:create_api_key user:profile user:inference"


async def login_anthropic(
    on_auth_url: Callable[[str], None],
    on_prompt_code: Callable[[], Awaitable[str]],
) -> OAuthCredentials:
    """Login with Anthropic OAuth (PKCE flow).

    Args:
        on_auth_url: Called with the authorization URL to open in browser.
        on_prompt_code: Called to get the authorization code from the user.

    Returns:
        OAuth credentials.
    """
    verifier, challenge = generate_pkce()

    # Build authorization URL
    params = {
        "code": "true",
        "client_id": _CLIENT_ID,
        "response_type": "code",
        "redirect_uri": _REDIRECT_URI,
        "scope": _SCOPES,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": verifier,
    }
    from urllib.parse import urlencode
    auth_url = f"{_AUTHORIZE_URL}?{urlencode(params)}"

    # Notify caller with URL to open
    on_auth_url(auth_url)

    # Wait for user to paste authorization code (format: code#state)
    auth_code = await on_prompt_code()
    splits = auth_code.split("#")
    code = splits[0]
    state = splits[1] if len(splits) > 1 else ""

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        response = await client.post(
            _TOKEN_URL,
            json={
                "grant_type": "authorization_code",
                "client_id": _CLIENT_ID,
                "code": code,
                "state": state,
                "redirect_uri": _REDIRECT_URI,
                "code_verifier": verifier,
            },
            headers={"Content-Type": "application/json"},
        )

    if response.status_code != 200:
        raise RuntimeError(f"Token exchange failed: {response.text}")

    data = response.json()
    expires_at = _now_ms() + data["expires_in"] * 1000 - 5 * 60 * 1000  # 5 min buffer

    return OAuthCredentials(
        refresh=data["refresh_token"],
        access=data["access_token"],
        expires=expires_at,
    )


async def refresh_anthropic_token(refresh_token: str) -> OAuthCredentials:
    """Refresh Anthropic OAuth token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            _TOKEN_URL,
            json={
                "grant_type": "refresh_token",
                "client_id": _CLIENT_ID,
                "refresh_token": refresh_token,
            },
            headers={"Content-Type": "application/json"},
        )

    if response.status_code != 200:
        raise RuntimeError(f"Anthropic token refresh failed: {response.text}")

    data = response.json()
    return OAuthCredentials(
        refresh=data["refresh_token"],
        access=data["access_token"],
        expires=_now_ms() + data["expires_in"] * 1000 - 5 * 60 * 1000,
    )


def _now_ms() -> float:
    """Current time in milliseconds."""
    import time
    return time.time() * 1000


class AnthropicOAuthProvider:
    """Anthropic OAuth provider."""

    id = "anthropic"
    name = "Anthropic (Claude Pro/Max)"
    uses_callback_server = False

    async def login(
        self,
        on_auth: Callable[[OAuthAuthInfo], None],
        on_prompt: Callable[[OAuthPrompt], Awaitable[str]],
        on_progress: Callable[[str], None] | None = None,
        on_manual_code_input: Callable[[], Awaitable[str]] | None = None,
        signal=None,
    ) -> OAuthCredentials:
        return await login_anthropic(
            on_auth_url=lambda url: on_auth(OAuthAuthInfo(url=url)),
            on_prompt_code=lambda: on_prompt(OAuthPrompt(message="Paste the authorization code:")),
        )

    async def refresh_token(self, credentials: OAuthCredentials) -> OAuthCredentials:
        return await refresh_anthropic_token(credentials.refresh)

    def get_api_key(self, credentials: OAuthCredentials) -> str:
        return credentials.access
