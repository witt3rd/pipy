"""OAuth types matching upstream pi-ai/src/utils/oauth/types.ts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Protocol


@dataclass
class OAuthCredentials:
    """OAuth credentials for a provider."""

    refresh: str
    """Refresh token."""

    access: str
    """Access token."""

    expires: float
    """Expiry timestamp in milliseconds since epoch."""

    extra: dict[str, Any] = field(default_factory=dict)
    """Provider-specific extra data (e.g., accountId, enterpriseUrl, projectId)."""


@dataclass
class OAuthPrompt:
    """Prompt for user input during OAuth flow."""

    message: str
    placeholder: str | None = None
    allow_empty: bool = False


@dataclass
class OAuthAuthInfo:
    """Authorization info to show the user."""

    url: str
    instructions: str | None = None


class OAuthLoginCallbacks(Protocol):
    """Callbacks for the OAuth login flow."""

    def on_auth(self, info: OAuthAuthInfo) -> None:
        """Called with URL and instructions when auth starts."""
        ...

    async def on_prompt(self, prompt: OAuthPrompt) -> str:
        """Called to prompt user for input."""
        ...

    def on_progress(self, message: str) -> None:
        """Optional progress messages."""
        ...

    async def on_manual_code_input(self) -> str:
        """Optional: prompt for manual code paste (races with browser callback)."""
        ...


class OAuthProviderInterface(Protocol):
    """Interface for an OAuth provider."""

    @property
    def id(self) -> str:
        """Provider ID (e.g., 'anthropic', 'openai-codex')."""
        ...

    @property
    def name(self) -> str:
        """Human-readable provider name."""
        ...

    @property
    def uses_callback_server(self) -> bool:
        """Whether login uses a local callback server."""
        ...

    async def login(
        self,
        on_auth: Callable[[OAuthAuthInfo], None],
        on_prompt: Callable[[OAuthPrompt], Awaitable[str]],
        on_progress: Callable[[str], None] | None = None,
        on_manual_code_input: Callable[[], Awaitable[str]] | None = None,
        signal: Any | None = None,
    ) -> OAuthCredentials:
        """Run the login flow, return credentials to persist."""
        ...

    async def refresh_token(self, credentials: OAuthCredentials) -> OAuthCredentials:
        """Refresh expired credentials."""
        ...

    def get_api_key(self, credentials: OAuthCredentials) -> str:
        """Convert credentials to API key string for the provider."""
        ...
