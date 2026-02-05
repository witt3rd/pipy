"""Tests for OAuth module."""

from pipy_ai.oauth import (
    generate_pkce,
    get_oauth_provider,
    get_oauth_providers,
    OAuthCredentials,
)
from pipy_ai.oauth.pkce import _base64url_encode


class TestPKCE:
    def test_generate_pkce_returns_tuple(self):
        verifier, challenge = generate_pkce()
        assert isinstance(verifier, str)
        assert isinstance(challenge, str)

    def test_generate_pkce_different_each_time(self):
        v1, c1 = generate_pkce()
        v2, c2 = generate_pkce()
        assert v1 != v2
        assert c1 != c2

    def test_verifier_is_base64url(self):
        verifier, _ = generate_pkce()
        # base64url has no +, /, or = characters
        assert "+" not in verifier
        assert "/" not in verifier
        assert "=" not in verifier

    def test_challenge_is_sha256_of_verifier(self):
        import hashlib
        verifier, challenge = generate_pkce()
        expected_hash = hashlib.sha256(verifier.encode("ascii")).digest()
        expected_challenge = _base64url_encode(expected_hash)
        assert challenge == expected_challenge

    def test_base64url_encode_no_padding(self):
        result = _base64url_encode(b"\x00" * 3)
        assert "=" not in result


class TestOAuthRegistry:
    def test_get_all_providers(self):
        providers = get_oauth_providers()
        assert len(providers) >= 4
        ids = [p.id for p in providers]
        assert "anthropic" in ids
        assert "openai-codex" in ids
        assert "github-copilot" in ids
        assert "google-gemini-cli" in ids

    def test_get_provider_by_id(self):
        provider = get_oauth_provider("anthropic")
        assert provider is not None
        assert provider.id == "anthropic"
        assert provider.name == "Anthropic (Claude Pro/Max)"

    def test_get_unknown_provider(self):
        provider = get_oauth_provider("nonexistent-provider")
        assert provider is None

    def test_provider_has_required_methods(self):
        for provider in get_oauth_providers():
            assert hasattr(provider, "id")
            assert hasattr(provider, "name")
            assert hasattr(provider, "login")
            assert hasattr(provider, "refresh_token")
            assert hasattr(provider, "get_api_key")

    def test_anthropic_get_api_key(self):
        provider = get_oauth_provider("anthropic")
        creds = OAuthCredentials(
            refresh="refresh-token",
            access="access-token-123",
            expires=9999999999999.0,
        )
        assert provider.get_api_key(creds) == "access-token-123"

    def test_openai_codex_get_api_key(self):
        provider = get_oauth_provider("openai-codex")
        creds = OAuthCredentials(
            refresh="refresh-token",
            access="codex-access-token",
            expires=9999999999999.0,
        )
        assert provider.get_api_key(creds) == "codex-access-token"


class TestOAuthCredentials:
    def test_create_credentials(self):
        creds = OAuthCredentials(
            refresh="refresh",
            access="access",
            expires=1234567890.0,
        )
        assert creds.refresh == "refresh"
        assert creds.access == "access"
        assert creds.expires == 1234567890.0
        assert creds.extra == {}

    def test_credentials_with_extra(self):
        creds = OAuthCredentials(
            refresh="refresh",
            access="access",
            expires=1234567890.0,
            extra={"accountId": "abc123"},
        )
        assert creds.extra["accountId"] == "abc123"
