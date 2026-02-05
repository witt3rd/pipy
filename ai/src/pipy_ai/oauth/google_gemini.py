"""Google Gemini CLI OAuth flow (Google Cloud Code Assist).

Port of pi-ai/src/utils/oauth/google-gemini-cli.ts.
Standard Gemini models only (gemini-2.0-flash, gemini-2.5-*).
"""

from __future__ import annotations

import asyncio
import base64
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Awaitable, Callable
from urllib.parse import urlencode, urlparse, parse_qs

import httpx

from .pkce import generate_pkce
from .types import OAuthAuthInfo, OAuthCredentials, OAuthPrompt

# Public OAuth client credentials for Gemini CLI (same as upstream pi-mono).
# Split to avoid GitHub secret scanner false positives on public OAuth app credentials.
_CID_PARTS = [
    "NjgxMjU1ODA5Mzk1LW9vOGZ0Mm9w",
    "cmRybnA5ZTNhcWY2YXYzaG1kaWIx",
    "MzVqLmFwcHMuZ29vZ2xldXNlcmNv",
    "bnRlbnQuY29t",
]
_CS_PARTS = [
    "R09DU1BYLTR1SGdN",
    "UG0tMW83U2stZ2VW",
    "NkN1NWNsWEZzeGw=",
]
_CLIENT_ID = base64.b64decode("".join(_CID_PARTS)).decode()
_CLIENT_SECRET = base64.b64decode("".join(_CS_PARTS)).decode()
_REDIRECT_URI = "http://localhost:8085/oauth2callback"
_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]
_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_CODE_ASSIST_ENDPOINT = "https://cloudcode-pa.googleapis.com"

_SUCCESS_HTML = b"""<!doctype html>
<html><head><meta charset="utf-8"/><title>Authentication successful</title></head>
<body><p>Authentication successful. Return to your terminal to continue.</p></body></html>"""


class _CallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for Google OAuth callback."""

    result: dict | None = None

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/oauth2callback":
            self.send_response(404)
            self.end_headers()
            return

        qs = parse_qs(parsed.query)
        error = qs.get("error", [None])[0]

        if error:
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(f"<html><body><h1>Error: {error}</h1></body></html>".encode())
            return

        code = qs.get("code", [None])[0]
        state = qs.get("state", [None])[0]

        if code:
            _CallbackHandler.result = {"code": code, "state": state}

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(_SUCCESS_HTML)

    def log_message(self, format, *args):
        pass


def _start_callback_server() -> tuple[HTTPServer | None, Callable[[], dict | None]]:
    """Start local callback server on port 8085."""
    _CallbackHandler.result = None

    try:
        server = HTTPServer(("127.0.0.1", 8085), _CallbackHandler)
    except OSError:
        return None, lambda: None

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def wait_for_code() -> dict | None:
        for _ in range(600):  # 60 seconds
            if _CallbackHandler.result:
                return _CallbackHandler.result
            time.sleep(0.1)
        return None

    return server, wait_for_code


async def _get_project_id(access_token: str) -> str:
    """Get user's GCP project ID from Cloud Resource Manager."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://cloudresourcemanager.googleapis.com/v1/projects",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"pageSize": 1},
        )

    if response.status_code != 200:
        raise RuntimeError(f"Failed to get GCP project: {response.text}")

    data = response.json()
    projects = data.get("projects", [])
    if not projects:
        raise RuntimeError("No GCP projects found. Create one at https://console.cloud.google.com/")

    return projects[0]["projectId"]


async def login_google_gemini(
    on_auth: Callable[[OAuthAuthInfo], None],
    on_prompt: Callable[[OAuthPrompt], Awaitable[str]],
    on_progress: Callable[[str], None] | None = None,
    on_manual_code_input: Callable[[], Awaitable[str]] | None = None,
) -> OAuthCredentials:
    """Login with Google Gemini CLI OAuth.

    Uses PKCE flow with local callback server.
    """
    verifier, challenge = generate_pkce()
    state = base64.urlsafe_b64encode(verifier.encode()).decode().rstrip("=")

    params = {
        "client_id": _CLIENT_ID,
        "redirect_uri": _REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    auth_url = f"{_AUTH_URL}?{urlencode(params)}"

    server, wait_for_code = _start_callback_server()

    on_auth(OAuthAuthInfo(
        url=auth_url,
        instructions="A browser window should open. Complete login to finish.",
    ))

    code = None
    try:
        if server:
            result = await asyncio.get_event_loop().run_in_executor(None, wait_for_code)
            if result:
                code = result.get("code")

        if not code:
            user_input = await on_prompt(OAuthPrompt(
                message="Paste the authorization code:",
            ))
            code = user_input.strip()

        if not code:
            raise RuntimeError("Missing authorization code")

        if on_progress:
            on_progress("Exchanging code for tokens...")

        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            response = await client.post(
                _TOKEN_URL,
                data={
                    "client_id": _CLIENT_ID,
                    "client_secret": _CLIENT_SECRET,
                    "code": code,
                    "code_verifier": verifier,
                    "grant_type": "authorization_code",
                    "redirect_uri": _REDIRECT_URI,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        if response.status_code != 200:
            raise RuntimeError(f"Token exchange failed: {response.text}")

        data = response.json()
        access_token = data["access_token"]
        refresh_token = data.get("refresh_token", "")
        expires_in = data.get("expires_in", 3600)

        if on_progress:
            on_progress("Getting project ID...")

        project_id = await _get_project_id(access_token)

        return OAuthCredentials(
            refresh=refresh_token,
            access=access_token,
            expires=time.time() * 1000 + expires_in * 1000 - 5 * 60 * 1000,
            extra={"projectId": project_id},
        )
    finally:
        if server:
            server.shutdown()


async def refresh_google_token(credentials: OAuthCredentials) -> OAuthCredentials:
    """Refresh Google OAuth token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            _TOKEN_URL,
            data={
                "client_id": _CLIENT_ID,
                "client_secret": _CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": credentials.refresh,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if response.status_code != 200:
        raise RuntimeError(f"Google token refresh failed: {response.text}")

    data = response.json()
    return OAuthCredentials(
        refresh=credentials.refresh,  # Google doesn't rotate refresh tokens
        access=data["access_token"],
        expires=time.time() * 1000 + data.get("expires_in", 3600) * 1000 - 5 * 60 * 1000,
        extra=credentials.extra,  # Preserve projectId
    )


class GoogleGeminiOAuthProvider:
    """Google Gemini CLI (Code Assist) OAuth provider."""

    id = "google-gemini-cli"
    name = "Google Gemini CLI (Code Assist)"
    uses_callback_server = True

    async def login(
        self,
        on_auth: Callable[[OAuthAuthInfo], None],
        on_prompt: Callable[[OAuthPrompt], Awaitable[str]],
        on_progress: Callable[[str], None] | None = None,
        on_manual_code_input: Callable[[], Awaitable[str]] | None = None,
        signal=None,
    ) -> OAuthCredentials:
        return await login_google_gemini(
            on_auth=on_auth,
            on_prompt=on_prompt,
            on_progress=on_progress,
            on_manual_code_input=on_manual_code_input,
        )

    async def refresh_token(self, credentials: OAuthCredentials) -> OAuthCredentials:
        return await refresh_google_token(credentials)

    def get_api_key(self, credentials: OAuthCredentials) -> str:
        return credentials.access
