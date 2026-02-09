"""Integration tests - require API keys, run manually.

Run with: pytest tests/test_integration.py -v --run-integration
"""

import os

import httpx
import pytest

from pipy_ai import (
    DoneEvent,
    SimpleStreamOptions,
    StreamOptions,
    TextDeltaEvent,
    ThinkingDeltaEvent,
    ThinkingLevel,
    complete,
    ctx,
    stream,
    user,
)


def _ollama_available() -> bool:
    """Check if Ollama is running locally."""
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


class TestOpenAIIntegration:
    """Test OpenAI models."""

    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set",
    )
    def test_complete_basic(self):
        """Test basic completion."""
        result = complete(
            "openai/gpt-4o-mini",
            ctx(user("Say 'hello' and nothing else")),
        )
        assert "hello" in result.text.lower()

    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set",
    )
    def test_stream_basic(self):
        """Test basic streaming."""
        events = list(
            stream(
                "openai/gpt-4o-mini",
                ctx(user("Say 'hello' and nothing else")),
            )
        )

        # Should have text delta events
        text_deltas = [e for e in events if isinstance(e, TextDeltaEvent)]
        assert len(text_deltas) > 0

        # Should end with done event
        assert isinstance(events[-1], DoneEvent)


class TestAnthropicIntegration:
    """Test Anthropic models."""

    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"),
        reason="ANTHROPIC_API_KEY not set",
    )
    def test_complete_basic(self):
        """Test basic completion."""
        result = complete(
            "anthropic/claude-3-haiku-20240307",
            ctx(user("Say 'hello' and nothing else")),
        )
        assert "hello" in result.text.lower()


class TestReasoningIntegration:
    """Test reasoning/thinking models."""

    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set",
    )
    def test_reasoning_with_o1_mini(self):
        """Test that reasoning_effort is passed through."""
        # Note: This test verifies the parameter is accepted, not that
        # the model actually uses it (that's hard to verify)
        result = complete(
            "openai/o1-mini",
            ctx(user("What is 2+2?")),
            SimpleStreamOptions(reasoning=ThinkingLevel.LOW),
        )
        assert "4" in result.text

    @pytest.mark.skipif(
        not os.getenv("DEEPSEEK_API_KEY"),
        reason="DEEPSEEK_API_KEY not set",
    )
    def test_deepseek_reasoning(self):
        """Test DeepSeek reasoning content parsing."""
        events = list(
            stream(
                "deepseek/deepseek-reasoner",
                ctx(user("What is 15 * 17?")),
            )
        )

        # Should have thinking deltas if model supports it
        thinking_deltas = [e for e in events if isinstance(e, ThinkingDeltaEvent)]
        # DeepSeek reasoner should produce thinking content
        assert len(thinking_deltas) > 0, "Expected thinking content from DeepSeek reasoner"

        # Final answer should be correct
        done = events[-1]
        assert isinstance(done, DoneEvent)
        assert "255" in done.message.text


class TestOllamaIntegration:
    """Test Ollama local models."""

    @pytest.mark.skipif(not _ollama_available(), reason="Ollama not running")
    def test_complete_basic(self):
        """Test basic completion via Ollama."""
        result = complete(
            "ollama/llama3.1",
            ctx(user("Say 'hello' and nothing else")),
            StreamOptions(max_tokens=32),
        )
        assert result.text.strip() != ""

    @pytest.mark.skipif(not _ollama_available(), reason="Ollama not running")
    def test_stream_basic(self):
        """Test basic streaming via Ollama."""
        events = list(
            stream(
                "ollama/llama3.1",
                ctx(user("Say 'hello' and nothing else")),
                StreamOptions(max_tokens=32),
            )
        )

        text_deltas = [e for e in events if isinstance(e, TextDeltaEvent)]
        assert len(text_deltas) > 0

        assert isinstance(events[-1], DoneEvent)
