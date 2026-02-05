"""Tests for AuthStorage."""

import json
import os
import pytest
import asyncio
from pathlib import Path

from pipy_coding_agent.auth_storage import AuthStorage, _get_env_api_key
from pipy_ai.oauth import OAuthCredentials


@pytest.fixture
def auth_path(tmp_path):
    return tmp_path / "auth.json"


@pytest.fixture
def auth(auth_path):
    return AuthStorage(auth_path=auth_path)


class TestAuthStorageCRUD:
    def test_new_storage_is_empty(self, auth):
        assert auth.get_providers_with_credentials() == []

    def test_set_api_key(self, auth, auth_path):
        auth.set_api_key("anthropic", "sk-ant-123")
        assert auth_path.exists()
        data = json.loads(auth_path.read_text())
        assert data["anthropic"]["type"] == "api_key"
        assert data["anthropic"]["key"] == "sk-ant-123"

    def test_get_api_key_credential(self, auth):
        auth.set_api_key("openai", "sk-openai-abc")
        cred = auth.get("openai")
        assert cred["type"] == "api_key"
        assert cred["key"] == "sk-openai-abc"

    def test_set_oauth(self, auth, auth_path):
        creds = OAuthCredentials(
            refresh="r-token",
            access="a-token",
            expires=9999999999999.0,
            extra={"accountId": "acct_123"},
        )
        auth.set_oauth("openai-codex", creds)

        data = json.loads(auth_path.read_text())
        assert data["openai-codex"]["type"] == "oauth"
        assert data["openai-codex"]["refresh"] == "r-token"
        assert data["openai-codex"]["access"] == "a-token"
        assert data["openai-codex"]["accountId"] == "acct_123"

    def test_remove(self, auth):
        auth.set_api_key("test", "key")
        assert "test" in auth.get_providers_with_credentials()
        auth.remove("test")
        assert "test" not in auth.get_providers_with_credentials()

    def test_remove_nonexistent(self, auth):
        auth.remove("nonexistent")  # Should not raise

    def test_reload(self, auth_path):
        # Write data externally
        auth_path.parent.mkdir(parents=True, exist_ok=True)
        auth_path.write_text(json.dumps({
            "anthropic": {"type": "api_key", "key": "external-key"}
        }))

        auth = AuthStorage(auth_path=auth_path)
        cred = auth.get("anthropic")
        assert cred["key"] == "external-key"

    def test_reload_after_external_change(self, auth, auth_path):
        auth.set_api_key("provider1", "key1")

        # External modification
        data = json.loads(auth_path.read_text())
        data["provider2"] = {"type": "api_key", "key": "key2"}
        auth_path.write_text(json.dumps(data))

        auth.reload()
        assert "provider2" in auth.get_providers_with_credentials()


class TestAuthStorageResolution:
    def test_runtime_override_highest_priority(self, auth):
        auth.set_api_key("anthropic", "stored-key")
        auth.set_runtime_api_key("anthropic", "runtime-key")
        key = asyncio.run(auth.get_api_key("anthropic"))
        assert key == "runtime-key"

    def test_stored_api_key(self, auth):
        auth.set_api_key("openai", "stored-openai-key")
        key = asyncio.run(auth.get_api_key("openai"))
        assert key == "stored-openai-key"

    def test_env_var_fallback(self, auth, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")
        key = asyncio.run(auth.get_api_key("openai"))
        assert key == "env-key"

    def test_no_key_returns_none(self, auth, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        key = asyncio.run(auth.get_api_key("openai"))
        assert key is None

    def test_stored_api_key_beats_env(self, auth, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")
        auth.set_api_key("openai", "stored-key")
        key = asyncio.run(auth.get_api_key("openai"))
        assert key == "stored-key"

    def test_remove_runtime_override(self, auth):
        auth.set_runtime_api_key("anthropic", "runtime-key")
        auth.remove_runtime_api_key("anthropic")
        auth.set_api_key("anthropic", "stored-key")
        key = asyncio.run(auth.get_api_key("anthropic"))
        assert key == "stored-key"


class TestEnvApiKey:
    def test_anthropic_env(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
        assert _get_env_api_key("anthropic") == "sk-ant"

    def test_anthropic_oauth_token_priority(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
        monkeypatch.setenv("ANTHROPIC_OAUTH_TOKEN", "oauth-token")
        # OAuth token is in fallbacks, checked first
        assert _get_env_api_key("anthropic") == "oauth-token"

    def test_github_copilot_fallbacks(self, monkeypatch):
        monkeypatch.setenv("GH_TOKEN", "gh-token")
        assert _get_env_api_key("github-copilot") == "gh-token"

    def test_unknown_provider(self):
        assert _get_env_api_key("unknown-provider") is None

    def test_openai(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-oai")
        assert _get_env_api_key("openai") == "sk-oai"

    def test_google(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "gem-key")
        assert _get_env_api_key("google") == "gem-key"


class TestAuthStorageMultipleProviders:
    def test_multiple_providers(self, auth):
        auth.set_api_key("anthropic", "ant-key")
        auth.set_api_key("openai", "oai-key")
        creds = OAuthCredentials(
            refresh="r", access="a", expires=9999999999999.0,
        )
        auth.set_oauth("github-copilot", creds)

        providers = auth.get_providers_with_credentials()
        assert set(providers) == {"anthropic", "openai", "github-copilot"}

    def test_overwrite_api_key(self, auth):
        auth.set_api_key("anthropic", "key1")
        auth.set_api_key("anthropic", "key2")
        cred = auth.get("anthropic")
        assert cred["key"] == "key2"

    def test_file_permissions(self, auth, auth_path):
        auth.set_api_key("test", "key")
        if os.name != "nt":
            mode = oct(auth_path.stat().st_mode)[-3:]
            assert mode == "600"


class TestCorruptedAuthFile:
    def test_corrupted_json(self, auth_path):
        auth_path.parent.mkdir(parents=True, exist_ok=True)
        auth_path.write_text("not-valid-json{{{")
        auth = AuthStorage(auth_path=auth_path)
        assert auth.get_providers_with_credentials() == []

    def test_missing_auth_file(self, tmp_path):
        auth = AuthStorage(auth_path=tmp_path / "nonexistent" / "auth.json")
        assert auth.get_providers_with_credentials() == []
