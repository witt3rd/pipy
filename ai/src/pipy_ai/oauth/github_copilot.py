"""GitHub Copilot OAuth flow (device code flow).

Port of pi-ai/src/utils/oauth/github-copilot.ts.
"""

from __future__ import annotations

import asyncio
import base64
import time
from typing import Awaitable, Callable
from urllib.parse import urlparse

import httpx

from .types import OAuthAuthInfo, OAuthCredentials, OAuthPrompt

_CLIENT_ID = base64.b64decode("SXYxLmI1MDdhMDhjODdlY2ZlOTg=").decode()

_COPILOT_HEADERS = {
    "User-Agent": "GitHubCopilotChat/0.35.0",
    "Editor-Version": "vscode/1.107.0",
    "Editor-Plugin-Version": "copilot-chat/0.35.0",
    "Copilot-Integration-Id": "vscode-chat",
}


def normalize_domain(input_str: str) -> str | None:
    """Normalize a GitHub domain input to a hostname."""
    trimmed = input_str.strip()
    if not trimmed:
        return None
    try:
        url = trimmed if "://" in trimmed else f"https://{trimmed}"
        parsed = urlparse(url)
        return parsed.hostname
    except Exception:
        return None


def _get_urls(domain: str) -> dict[str, str]:
    return {
        "device_code": f"https://{domain}/login/device/code",
        "access_token": f"https://{domain}/login/oauth/access_token",
        "copilot_token": f"https://api.{domain}/copilot_internal/v2/token",
    }


def get_github_copilot_base_url(
    token: str | None = None,
    enterprise_domain: str | None = None,
) -> str:
    """Get the API base URL for GitHub Copilot.

    Parses proxy-ep from the Copilot token if available.
    """
    if token:
        import re
        match = re.search(r"proxy-ep=([^;]+)", token)
        if match:
            proxy_host = match.group(1)
            api_host = proxy_host.replace("proxy.", "api.", 1) if proxy_host.startswith("proxy.") else proxy_host
            return f"https://{api_host}"

    if enterprise_domain:
        return f"https://copilot-api.{enterprise_domain}"
    return "https://api.individual.githubcopilot.com"


async def _start_device_flow(client: httpx.AsyncClient, domain: str) -> dict:
    """Start GitHub device code flow."""
    urls = _get_urls(domain)
    response = await client.post(
        urls["device_code"],
        json={"client_id": _CLIENT_ID, "scope": "read:user"},
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "GitHubCopilotChat/0.35.0",
        },
    )
    if response.status_code != 200:
        raise RuntimeError(f"Device code request failed: {response.text}")

    data = response.json()
    required = ("device_code", "user_code", "verification_uri", "interval", "expires_in")
    if not all(k in data for k in required):
        raise RuntimeError(f"Invalid device code response: {data}")
    return data


async def _poll_for_access_token(
    client: httpx.AsyncClient,
    domain: str,
    device_code: str,
    interval_seconds: int,
    expires_in: int,
) -> str:
    """Poll for GitHub access token after device code flow."""
    urls = _get_urls(domain)
    deadline = time.time() + expires_in
    interval_ms = max(1.0, interval_seconds)

    while time.time() < deadline:
        response = await client.post(
            urls["access_token"],
            json={
                "client_id": _CLIENT_ID,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "GitHubCopilotChat/0.35.0",
            },
        )

        data = response.json()

        if "access_token" in data:
            return data["access_token"]

        error = data.get("error", "")
        if error == "authorization_pending":
            await asyncio.sleep(interval_ms)
            continue
        elif error == "slow_down":
            interval_ms += 5
            await asyncio.sleep(interval_ms)
            continue
        elif error:
            raise RuntimeError(f"Device flow failed: {error}")

        await asyncio.sleep(interval_ms)

    raise RuntimeError("Device flow timed out")


async def refresh_github_copilot_token(
    refresh_token: str,
    enterprise_domain: str | None = None,
) -> OAuthCredentials:
    """Refresh GitHub Copilot token.

    The refresh_token here is the GitHub access token.
    We exchange it for a Copilot-specific short-lived token.
    """
    domain = enterprise_domain or "github.com"
    urls = _get_urls(domain)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            urls["copilot_token"],
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {refresh_token}",
                **_COPILOT_HEADERS,
            },
        )

    if response.status_code != 200:
        raise RuntimeError(f"Copilot token refresh failed: {response.text}")

    data = response.json()
    token = data.get("token")
    expires_at = data.get("expires_at")

    if not isinstance(token, str) or not isinstance(expires_at, (int, float)):
        raise RuntimeError(f"Invalid Copilot token response: {data}")

    return OAuthCredentials(
        refresh=refresh_token,
        access=token,
        expires=expires_at * 1000 - 5 * 60 * 1000,  # 5 min buffer
        extra={"enterpriseUrl": enterprise_domain} if enterprise_domain else {},
    )


async def login_github_copilot(
    on_auth: Callable[[OAuthAuthInfo], None],
    on_prompt: Callable[[OAuthPrompt], Awaitable[str]],
    on_progress: Callable[[str], None] | None = None,
    signal=None,
) -> OAuthCredentials:
    """Login with GitHub Copilot (device code flow).

    Prompts for optional GitHub Enterprise domain, then uses device code flow.
    """
    # Ask for enterprise domain
    domain_input = await on_prompt(OAuthPrompt(
        message="GitHub Enterprise URL/domain (blank for github.com)",
        placeholder="company.ghe.com",
        allow_empty=True,
    ))

    trimmed = domain_input.strip()
    enterprise_domain = normalize_domain(domain_input) if trimmed else None
    if trimmed and not enterprise_domain:
        raise RuntimeError("Invalid GitHub Enterprise URL/domain")
    domain = enterprise_domain or "github.com"

    async with httpx.AsyncClient() as client:
        # Start device flow
        device = await _start_device_flow(client, domain)

        # Show user code and verification URL
        on_auth(OAuthAuthInfo(
            url=device["verification_uri"],
            instructions=f"Enter code: {device['user_code']}",
        ))

        # Poll for GitHub access token
        github_access_token = await _poll_for_access_token(
            client,
            domain,
            device["device_code"],
            device["interval"],
            device["expires_in"],
        )

    # Exchange GitHub token for Copilot token
    credentials = await refresh_github_copilot_token(
        github_access_token,
        enterprise_domain,
    )

    if on_progress:
        on_progress("Enabling models...")

    return credentials


class GitHubCopilotOAuthProvider:
    """GitHub Copilot OAuth provider."""

    id = "github-copilot"
    name = "GitHub Copilot"
    uses_callback_server = False

    async def login(
        self,
        on_auth: Callable[[OAuthAuthInfo], None],
        on_prompt: Callable[[OAuthPrompt], Awaitable[str]],
        on_progress: Callable[[str], None] | None = None,
        on_manual_code_input: Callable[[], Awaitable[str]] | None = None,
        signal=None,
    ) -> OAuthCredentials:
        return await login_github_copilot(
            on_auth=on_auth,
            on_prompt=on_prompt,
            on_progress=on_progress,
            signal=signal,
        )

    async def refresh_token(self, credentials: OAuthCredentials) -> OAuthCredentials:
        enterprise = credentials.extra.get("enterpriseUrl")
        return await refresh_github_copilot_token(credentials.refresh, enterprise)

    def get_api_key(self, credentials: OAuthCredentials) -> str:
        return credentials.access
