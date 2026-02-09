"""Tests for provider module."""

from pipy_ai.provider import LiteLLMProvider, supports_xhigh
from pipy_ai.types import (
    SimpleStreamOptions,
    StreamOptions,
    ThinkingBudgets,
    ThinkingLevel,
)


class TestSupportsXhigh:
    """Test supports_xhigh function."""

    def test_gpt52_supported(self):
        assert supports_xhigh("openai/gpt-5.2") is True

    def test_gpt52_codex_supported(self):
        assert supports_xhigh("openai/gpt-5.2-codex") is True

    def test_gpt52_variant_supported(self):
        assert supports_xhigh("gpt-5.2-turbo") is True

    def test_gpt4_not_supported(self):
        assert supports_xhigh("openai/gpt-4") is False

    def test_gpt51_not_supported(self):
        assert supports_xhigh("openai/gpt-5.1-codex-max") is False

    def test_claude_not_supported(self):
        assert supports_xhigh("anthropic/claude-sonnet-4-20250514") is False


class TestBuildKwargs:
    """Test _build_kwargs method."""

    def setup_method(self):
        self.provider = LiteLLMProvider()
        self.messages = [{"role": "user", "content": "Hello"}]

    def test_basic_kwargs(self):
        kwargs = self.provider._build_kwargs(
            model="gpt-4",
            messages=self.messages,
            options=None,
        )
        assert kwargs["model"] == "gpt-4"
        assert kwargs["messages"] == self.messages
        assert kwargs["stream"] is False

    def test_with_temperature(self):
        options = StreamOptions(temperature=0.7)
        kwargs = self.provider._build_kwargs("gpt-4", self.messages, options)
        assert kwargs["temperature"] == 0.7

    def test_with_max_tokens(self):
        options = StreamOptions(max_tokens=1000)
        kwargs = self.provider._build_kwargs("gpt-4", self.messages, options)
        assert kwargs["max_tokens"] == 1000

    def test_with_api_key(self):
        options = StreamOptions(api_key="test-key")
        kwargs = self.provider._build_kwargs("gpt-4", self.messages, options)
        assert kwargs["api_key"] == "test-key"

    def test_with_headers(self):
        options = StreamOptions(headers={"X-Custom": "value"})
        kwargs = self.provider._build_kwargs("gpt-4", self.messages, options)
        assert kwargs["extra_headers"] == {"X-Custom": "value"}

    def test_with_session_id(self):
        options = StreamOptions(session_id="sess-123")
        kwargs = self.provider._build_kwargs("gpt-4", self.messages, options)
        assert kwargs["extra_headers"] == {"x-session-id": "sess-123"}

    def test_session_id_merged_with_headers(self):
        options = StreamOptions(
            session_id="sess-123",
            headers={"X-Custom": "value"},
        )
        kwargs = self.provider._build_kwargs("gpt-4", self.messages, options)
        assert kwargs["extra_headers"] == {
            "X-Custom": "value",
            "x-session-id": "sess-123",
        }

    def test_with_api_base(self):
        options = StreamOptions(api_base="http://localhost:11434")
        kwargs = self.provider._build_kwargs("ollama/llama3.1", self.messages, options)
        assert kwargs["api_base"] == "http://localhost:11434"

    def test_api_base_not_set_when_none(self):
        options = StreamOptions()
        kwargs = self.provider._build_kwargs("gpt-4", self.messages, options)
        assert "api_base" not in kwargs

    def test_anthropic_oauth_token_passed_as_api_key(self):
        """OAuth tokens are passed as api_key; litellm patch handles Bearer routing."""
        oauth_token = "sk-ant-oat01-abc123"
        options = StreamOptions(api_key=oauth_token)
        kwargs = self.provider._build_kwargs("anthropic/claude-sonnet-4-5", self.messages, options)
        assert kwargs["api_key"] == oauth_token

    def test_anthropic_oauth_token_injects_identity(self):
        """OAuth tokens trigger Claude Code identity injection as separate system message."""
        oauth_token = "sk-ant-oat01-abc123"
        messages = [{"role": "system", "content": "Be helpful"}, {"role": "user", "content": "hi"}]
        options = StreamOptions(api_key=oauth_token)
        kwargs = self.provider._build_kwargs("anthropic/claude-sonnet-4-5", messages, options)
        # Should have TWO system messages - identity first, then original
        from pipy_ai.provider import CLAUDE_CODE_IDENTITY
        assert kwargs["messages"][0]["role"] == "system"
        assert kwargs["messages"][0]["content"] == CLAUDE_CODE_IDENTITY
        assert kwargs["messages"][1]["role"] == "system"
        assert kwargs["messages"][1]["content"] == "Be helpful"

    def test_regular_api_key_no_identity_injection(self):
        """Regular API keys don't get Claude Code identity injected."""
        options = StreamOptions(api_key="sk-ant-api03-regular")
        messages = [{"role": "system", "content": "Be helpful"}, {"role": "user", "content": "hi"}]
        kwargs = self.provider._build_kwargs("anthropic/claude-sonnet-4-5", messages, options)
        # Should NOT have identity injected
        assert len([m for m in kwargs["messages"] if m["role"] == "system"]) == 1
        assert kwargs["messages"][0]["content"] == "Be helpful"


class TestReasoningKwargs:
    """Test reasoning/thinking level handling."""

    def setup_method(self):
        self.provider = LiteLLMProvider()
        self.messages = [{"role": "user", "content": "Hello"}]

    def test_reasoning_off_not_set(self):
        options = SimpleStreamOptions(reasoning=ThinkingLevel.OFF)
        kwargs = self.provider._build_kwargs("gpt-4", self.messages, options)
        assert "reasoning_effort" not in kwargs

    def test_reasoning_low(self):
        options = SimpleStreamOptions(reasoning=ThinkingLevel.LOW)
        kwargs = self.provider._build_kwargs("gpt-4", self.messages, options)
        assert kwargs["reasoning_effort"] == "low"

    def test_reasoning_medium(self):
        options = SimpleStreamOptions(reasoning=ThinkingLevel.MEDIUM)
        kwargs = self.provider._build_kwargs("gpt-4", self.messages, options)
        assert kwargs["reasoning_effort"] == "medium"

    def test_reasoning_high(self):
        options = SimpleStreamOptions(reasoning=ThinkingLevel.HIGH)
        kwargs = self.provider._build_kwargs("gpt-4", self.messages, options)
        assert kwargs["reasoning_effort"] == "high"

    def test_reasoning_xhigh_maps_to_high_for_non_gpt52(self):
        options = SimpleStreamOptions(reasoning=ThinkingLevel.XHIGH)
        kwargs = self.provider._build_kwargs("gpt-4", self.messages, options)
        assert kwargs["reasoning_effort"] == "high"

    def test_reasoning_xhigh_passed_through_for_gpt52(self):
        options = SimpleStreamOptions(reasoning=ThinkingLevel.XHIGH)
        kwargs = self.provider._build_kwargs("openai/gpt-5.2", self.messages, options)
        assert kwargs["reasoning_effort"] == "xhigh"

    def test_reasoning_xhigh_passed_through_for_gpt52_codex(self):
        options = SimpleStreamOptions(reasoning=ThinkingLevel.XHIGH)
        kwargs = self.provider._build_kwargs("openai/gpt-5.2-codex", self.messages, options)
        assert kwargs["reasoning_effort"] == "xhigh"

    def test_reasoning_minimal_maps_to_low(self):
        options = SimpleStreamOptions(reasoning=ThinkingLevel.MINIMAL)
        kwargs = self.provider._build_kwargs("gpt-4", self.messages, options)
        assert kwargs["reasoning_effort"] == "low"

    def test_no_reasoning_option(self):
        options = SimpleStreamOptions()
        kwargs = self.provider._build_kwargs("gpt-4", self.messages, options)
        assert "reasoning_effort" not in kwargs


class TestThinkingBudgets:
    """Test thinking_budgets handling."""

    def setup_method(self):
        self.provider = LiteLLMProvider()
        self.messages = [{"role": "user", "content": "Hello"}]
        self.budgets = ThinkingBudgets(
            minimal=512,
            low=1024,
            medium=4096,
            high=8192,
        )

    def test_thinking_budgets_with_low(self):
        options = SimpleStreamOptions(
            reasoning=ThinkingLevel.LOW,
            thinking_budgets=self.budgets,
        )
        kwargs = self.provider._build_kwargs("claude-3", self.messages, options)
        assert kwargs["thinking"] == {"type": "enabled", "budget_tokens": 1024}

    def test_thinking_budgets_with_medium(self):
        options = SimpleStreamOptions(
            reasoning=ThinkingLevel.MEDIUM,
            thinking_budgets=self.budgets,
        )
        kwargs = self.provider._build_kwargs("claude-3", self.messages, options)
        assert kwargs["thinking"] == {"type": "enabled", "budget_tokens": 4096}

    def test_thinking_budgets_with_high(self):
        options = SimpleStreamOptions(
            reasoning=ThinkingLevel.HIGH,
            thinking_budgets=self.budgets,
        )
        kwargs = self.provider._build_kwargs("claude-3", self.messages, options)
        assert kwargs["thinking"] == {"type": "enabled", "budget_tokens": 8192}

    def test_thinking_budgets_xhigh_uses_high_budget(self):
        options = SimpleStreamOptions(
            reasoning=ThinkingLevel.XHIGH,
            thinking_budgets=self.budgets,
        )
        kwargs = self.provider._build_kwargs("claude-3", self.messages, options)
        assert kwargs["thinking"] == {"type": "enabled", "budget_tokens": 8192}

    def test_no_thinking_without_budgets(self):
        options = SimpleStreamOptions(reasoning=ThinkingLevel.HIGH)
        kwargs = self.provider._build_kwargs("claude-3", self.messages, options)
        assert "thinking" not in kwargs

    def test_no_thinking_when_off(self):
        options = SimpleStreamOptions(
            reasoning=ThinkingLevel.OFF,
            thinking_budgets=self.budgets,
        )
        kwargs = self.provider._build_kwargs("claude-3", self.messages, options)
        assert "thinking" not in kwargs
