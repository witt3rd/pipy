"""OpenAI Codex (ChatGPT) OAuth flow.

Port of pi-ai/src/utils/oauth/openai-codex.ts.
Uses a local HTTP callback server for the OAuth redirect.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Awaitable, Callable
from urllib.parse import urlencode, urlparse, parse_qs

import httpx

from .pkce import generate_pkce
from .types import OAuthAuthInfo, OAuthCredentials, OAuthPrompt

_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
_AUTHORIZE_URL = "https://auth.openai.com/oauth/authorize"
_TOKEN_URL = "https://auth.openai.com/oauth/token"
_REDIRECT_URI = "http://localhost:1455/auth/callback"
_SCOPE = "openid profile email offline_access"
_JWT_CLAIM_PATH = "https://api.openai.com/auth"

_SUCCESS_HTML = b"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/><title>Authentication successful</title></head>
<body><p>Authentication successful. Return to your terminal to continue.</p></body></html>"""


def _create_state() -> str:
    return os.urandom(16).hex()


def _parse_authorization_input(value: str) -> dict[str, str | None]:
    """Parse various formats of authorization input."""
    value = value.strip()
    if not value:
        return {}

    # Try as URL
    try:
        parsed = urlparse(value)
        if parsed.scheme:
            qs = parse_qs(parsed.query)
            return {
                "code": qs.get("code", [None])[0],
                "state": qs.get("state", [None])[0],
            }
    except Exception:
        pass

    # Try code#state format
    if "#" in value:
        parts = value.split("#", 1)
        return {"code": parts[0], "state": parts[1]}

    # Try query string
    if "code=" in value:
        qs = parse_qs(value)
        return {
            "code": qs.get("code", [None])[0],
            "state": qs.get("state", [None])[0],
        }

    return {"code": value, "state": None}


def _decode_jwt_payload(token: str) -> dict | None:
    """Decode JWT payload (no verification)."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        # Add padding
        payload = parts[1]
        payload += "=" * (4 - len(payload) % 4)
        decoded = base64.b64decode(payload)
        return json.loads(decoded)
    except Exception:
        return None


def _get_account_id(access_token: str) -> str | None:
    """Extract accountId from JWT token."""
    payload = _decode_jwt_payload(access_token)
    if not payload:
        return None
    auth = payload.get(_JWT_CLAIM_PATH, {})
    account_id = auth.get("chatgpt_account_id")
    return account_id if isinstance(account_id, str) and account_id else None


async def _exchange_code(code: str, verifier: str) -> dict | None:
    """Exchange authorization code for tokens."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            _TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": _CLIENT_ID,
                "code": code,
                "code_verifier": verifier,
                "redirect_uri": _REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if response.status_code != 200:
        return None

    data = response.json()
    if not all(k in data for k in ("access_token", "refresh_token", "expires_in")):
        return None

    return {
        "access": data["access_token"],
        "refresh": data["refresh_token"],
        "expires": time.time() * 1000 + data["expires_in"] * 1000,
    }


class _CallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback."""

    code: str | None = None
    expected_state: str = ""

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/auth/callback":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return

        qs = parse_qs(parsed.query)
        state = qs.get("state", [None])[0]
        code = qs.get("code", [None])[0]

        if state != self.expected_state:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"State mismatch")
            return

        if not code:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing authorization code")
            return

        _CallbackHandler.code = code
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(_SUCCESS_HTML)

    def log_message(self, format, *args):
        pass  # Suppress server logs


def _start_callback_server(state: str) -> tuple[HTTPServer, Callable[[], str | None]]:
    """Start local OAuth callback server on port 1455.

    Returns:
        (server, wait_for_code) tuple.
    """
    _CallbackHandler.code = None
    _CallbackHandler.expected_state = state

    try:
        server = HTTPServer(("127.0.0.1", 1455), _CallbackHandler)
    except OSError:
        # Port in use — fall back to manual paste
        return None, lambda: None

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def wait_for_code() -> str | None:
        for _ in range(600):  # 60 seconds
            if _CallbackHandler.code:
                return _CallbackHandler.code
            time.sleep(0.1)
        return None

    return server, wait_for_code


async def login_openai_codex(
    on_auth: Callable[[OAuthAuthInfo], None],
    on_prompt: Callable[[OAuthPrompt], Awaitable[str]],
    on_progress: Callable[[str], None] | None = None,
    on_manual_code_input: Callable[[], Awaitable[str]] | None = None,
) -> OAuthCredentials:
    """Login with OpenAI Codex OAuth.

    Starts a local callback server and opens the browser for authentication.
    Falls back to manual code paste if the server can't bind.
    """
    verifier, challenge = generate_pkce()
    state = _create_state()

    params = {
        "response_type": "code",
        "client_id": _CLIENT_ID,
        "redirect_uri": _REDIRECT_URI,
        "scope": _SCOPE,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "id_token_add_organizations": "true",
        "codex_cli_simplified_flow": "true",
        "originator": "pi",
    }
    auth_url = f"{_AUTHORIZE_URL}?{urlencode(params)}"

    server, wait_for_code = _start_callback_server(state)

    on_auth(OAuthAuthInfo(
        url=auth_url,
        instructions="A browser window should open. Complete login to finish.",
    ))

    code = None
    try:
        if on_manual_code_input and server:
            # Race between browser callback and manual input
            loop = asyncio.get_event_loop()
            server_task = loop.run_in_executor(None, wait_for_code)
            manual_task = asyncio.ensure_future(on_manual_code_input())

            done, pending = await asyncio.wait(
                [server_task, manual_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()

            for task in done:
                result = task.result()
                if isinstance(result, str) and result:
                    if result == wait_for_code:
                        code = result
                    else:
                        parsed = _parse_authorization_input(result)
                        code = parsed.get("code")
                elif result:
                    code = result
        elif server:
            # Wait for browser callback
            code = await asyncio.get_event_loop().run_in_executor(None, wait_for_code)

        # Fallback to manual prompt
        if not code:
            user_input = await on_prompt(OAuthPrompt(
                message="Paste the authorization code (or full redirect URL):",
            ))
            parsed = _parse_authorization_input(user_input)
            if parsed.get("state") and parsed["state"] != state:
                raise RuntimeError("State mismatch")
            code = parsed.get("code")

        if not code:
            raise RuntimeError("Missing authorization code")

        token_data = await _exchange_code(code, verifier)
        if not token_data:
            raise RuntimeError("Token exchange failed")

        account_id = _get_account_id(token_data["access"])
        if not account_id:
            raise RuntimeError("Failed to extract accountId from token")

        return OAuthCredentials(
            refresh=token_data["refresh"],
            access=token_data["access"],
            expires=token_data["expires"],
            extra={"accountId": account_id},
        )
    finally:
        if server:
            server.shutdown()


async def refresh_openai_codex_token(refresh_token: str) -> OAuthCredentials:
    """Refresh OpenAI Codex OAuth token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            _TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": _CLIENT_ID,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if response.status_code != 200:
        raise RuntimeError(f"Failed to refresh OpenAI Codex token: {response.text}")

    data = response.json()
    if not all(k in data for k in ("access_token", "refresh_token", "expires_in")):
        raise RuntimeError("Token refresh response missing fields")

    access = data["access_token"]
    account_id = _get_account_id(access)
    if not account_id:
        raise RuntimeError("Failed to extract accountId from refreshed token")

    return OAuthCredentials(
        refresh=data["refresh_token"],
        access=access,
        expires=time.time() * 1000 + data["expires_in"] * 1000,
        extra={"accountId": account_id},
    )


class OpenAICodexOAuthProvider:
    """OpenAI Codex (ChatGPT Plus/Pro) OAuth provider."""

    id = "openai-codex"
    name = "ChatGPT Plus/Pro (Codex Subscription)"
    uses_callback_server = True

    async def login(
        self,
        on_auth: Callable[[OAuthAuthInfo], None],
        on_prompt: Callable[[OAuthPrompt], Awaitable[str]],
        on_progress: Callable[[str], None] | None = None,
        on_manual_code_input: Callable[[], Awaitable[str]] | None = None,
        signal=None,
    ) -> OAuthCredentials:
        return await login_openai_codex(
            on_auth=on_auth,
            on_prompt=on_prompt,
            on_progress=on_progress,
            on_manual_code_input=on_manual_code_input,
        )

    async def refresh_token(self, credentials: OAuthCredentials) -> OAuthCredentials:
        return await refresh_openai_codex_token(credentials.refresh)

    def get_api_key(self, credentials: OAuthCredentials) -> str:
        return credentials.access
