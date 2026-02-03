"""Tests for model resolver."""

import pytest

from pipy_coding_agent.agent.model_resolver import (
    ModelResolver,
    ResolvedModel,
    resolve_model,
    MODEL_ALIASES,
)


class TestModelResolver:
    def test_resolve_full_model_id(self):
        """Test resolving a full model ID."""
        resolver = ModelResolver()

        result = resolver.resolve("anthropic/claude-sonnet-4-20250514")

        assert result.provider == "anthropic"
        assert result.model_name == "claude-sonnet-4-20250514"
        assert result.model_id == "anthropic/claude-sonnet-4-20250514"

    def test_resolve_alias(self):
        """Test resolving a model alias."""
        resolver = ModelResolver()

        result = resolver.resolve("sonnet")

        assert result.provider == "anthropic"
        assert "claude" in result.model_name.lower()

    def test_resolve_case_insensitive(self):
        """Test that aliases are case-insensitive."""
        resolver = ModelResolver()

        result1 = resolver.resolve("SONNET")
        result2 = resolver.resolve("Sonnet")
        result3 = resolver.resolve("sonnet")

        assert result1.model_id == result2.model_id == result3.model_id

    def test_default_provider(self):
        """Test default provider when not specified."""
        resolver = ModelResolver(default_provider="openai")

        result = resolver.resolve("gpt-4")

        assert result.provider == "openai"
        assert result.model_id == "openai/gpt-4"

    def test_custom_aliases(self):
        """Test custom aliases."""
        resolver = ModelResolver(
            aliases={"mymodel": "custom/my-model-v1"}
        )

        result = resolver.resolve("mymodel")

        assert result.provider == "custom"
        assert result.model_name == "my-model-v1"

    def test_custom_context_window(self):
        """Test custom context window."""
        resolver = ModelResolver(
            context_windows={"anthropic/claude-sonnet-4-20250514": 500000}
        )

        result = resolver.resolve("anthropic/claude-sonnet-4-20250514")

        assert result.context_window == 500000

    def test_default_context_window(self):
        """Test default context window for unknown model."""
        resolver = ModelResolver()

        result = resolver.resolve("unknown/model")

        assert result.context_window == 128000  # Default

    def test_supports_thinking(self):
        """Test thinking support detection."""
        resolver = ModelResolver()

        claude = resolver.resolve("sonnet")
        gpt = resolver.resolve("gpt4o")

        assert claude.supports_thinking is True
        # GPT-4 doesn't have extended thinking like Claude
        assert gpt.supports_thinking is False

    def test_list_aliases(self):
        """Test listing aliases."""
        resolver = ModelResolver()

        aliases = resolver.list_aliases()

        assert "sonnet" in aliases
        assert "claude" in aliases
        assert "gpt4" in aliases


class TestResolveModelFunction:
    def test_convenience_function(self):
        """Test the convenience resolve_model function."""
        result = resolve_model("sonnet")

        assert isinstance(result, ResolvedModel)
        assert result.provider == "anthropic"


class TestModelAliases:
    def test_common_aliases_exist(self):
        """Test that common aliases are defined."""
        expected = ["claude", "sonnet", "opus", "haiku", "gpt4", "gpt4o", "gemini"]

        for alias in expected:
            assert alias in MODEL_ALIASES
