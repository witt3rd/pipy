"""Tests for provider module."""

from pipy_ai.provider import LiteLLMProvider
from pipy_ai.types import (
    SimpleStreamOptions,
    StreamOptions,
    ThinkingBudgets,
    ThinkingLevel,
)


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

    def test_reasoning_xhigh_maps_to_high(self):
        options = SimpleStreamOptions(reasoning=ThinkingLevel.XHIGH)
        kwargs = self.provider._build_kwargs("gpt-4", self.messages, options)
        assert kwargs["reasoning_effort"] == "high"

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
