"""Tests for the litellm Anthropic OAuth patch."""

from pipy_ai.oauth._litellm_patch import patch_litellm_anthropic_oauth


class TestLiteLLMAnthropicOAuthPatch:
    """Verify the monkey-patch correctly routes OAuth tokens via Bearer auth."""

    def setup_method(self):
        # Ensure patch is applied
        patch_litellm_anthropic_oauth()
        from litellm.llms.anthropic.chat.transformation import AnthropicConfig
        self.config = AnthropicConfig()

    def test_oauth_token_uses_bearer_auth(self):
        headers = self.config.get_anthropic_headers(api_key="sk-ant-oat01-abc123")
        assert "x-api-key" not in headers
        assert headers["authorization"] == "Bearer sk-ant-oat01-abc123"

    def test_oauth_token_sets_beta_header(self):
        headers = self.config.get_anthropic_headers(api_key="sk-ant-oat01-abc123")
        assert "oauth-2025-04-20" in headers["anthropic-beta"]

    def test_oauth_token_sets_browser_access_header(self):
        headers = self.config.get_anthropic_headers(api_key="sk-ant-oat01-abc123")
        assert headers["anthropic-dangerous-direct-browser-access"] == "true"

    def test_regular_api_key_unchanged(self):
        headers = self.config.get_anthropic_headers(api_key="sk-ant-api03-regular")
        assert headers["x-api-key"] == "sk-ant-api03-regular"
        assert "authorization" not in headers

    def test_non_anthropic_key_unchanged(self):
        headers = self.config.get_anthropic_headers(api_key="some-other-key")
        assert headers["x-api-key"] == "some-other-key"
        assert "authorization" not in headers

    def test_preserves_anthropic_version(self):
        headers = self.config.get_anthropic_headers(api_key="sk-ant-oat01-test")
        assert headers["anthropic-version"] == "2023-06-01"

    def test_preserves_content_type(self):
        headers = self.config.get_anthropic_headers(api_key="sk-ant-oat01-test")
        assert headers["content-type"] == "application/json"
        assert headers["accept"] == "application/json"

    def test_idempotent_patch(self):
        """Calling patch multiple times doesn't stack patches."""
        patch_litellm_anthropic_oauth()
        patch_litellm_anthropic_oauth()
        headers = self.config.get_anthropic_headers(api_key="sk-ant-oat01-test")
        assert headers["authorization"] == "Bearer sk-ant-oat01-test"
        # Only one oauth beta entry
        beta_parts = [b.strip() for b in headers["anthropic-beta"].split(",")]
        assert beta_parts.count("oauth-2025-04-20") == 1
