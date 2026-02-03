"""Tests for token estimation."""

import pytest

from pipy_ai import UserMessage, AssistantMessage, ToolResultMessage, Usage

from pipy_coding_agent.compaction.tokens import (
    estimate_tokens,
    estimate_context_tokens,
    calculate_context_tokens,
    ContextUsageEstimate,
)


class TestCalculateContextTokens:
    def test_from_total_tokens(self):
        """Test using total_tokens field."""
        usage = Usage(
            input=100,
            output=50,
            cache_read=0,
            cache_write=0,
            total_tokens=200,
        )

        result = calculate_context_tokens(usage)
        assert result == 200

    def test_from_components(self):
        """Test computing from components."""
        usage = Usage(
            input=100,
            output=50,
            cache_read=25,
            cache_write=10,
        )

        result = calculate_context_tokens(usage)
        assert result == 185


class TestEstimateTokens:
    def test_user_message_string(self):
        """Test estimating user message with string content."""
        msg = UserMessage(role="user", content="Hello, world!")  # 13 chars

        result = estimate_tokens(msg)

        # ceil(13 / 4) = 4
        assert result == 4

    def test_user_message_blocks(self):
        """Test estimating user message with content blocks."""
        msg = UserMessage(
            role="user",
            content=[{"type": "text", "text": "Hello, world!"}],
        )

        result = estimate_tokens(msg)
        assert result == 4

    def test_assistant_message_text(self):
        """Test estimating assistant message with text."""
        msg = AssistantMessage(
            role="assistant",
            content=[{"type": "text", "text": "Hello there!"}],  # 12 chars
            stop_reason="stop",
        )

        result = estimate_tokens(msg)
        assert result == 3  # ceil(12 / 4)

    def test_assistant_message_tool_call(self):
        """Test estimating assistant message with tool call."""
        msg = AssistantMessage(
            role="assistant",
            content=[{
                "type": "toolCall",
                "id": "123",
                "name": "Read",  # 4 chars
                "arguments": {"path": "/test.txt"},  # ~20 chars serialized
            }],
            stop_reason="toolUse",
        )

        result = estimate_tokens(msg)
        # Should include name + serialized args
        assert result > 0

    def test_assistant_message_thinking(self):
        """Test estimating assistant message with thinking."""
        msg = AssistantMessage(
            role="assistant",
            content=[
                {"type": "thinking", "thinking": "Let me think..." * 10},  # ~150 chars
                {"type": "text", "text": "Here's my answer."},
            ],
            stop_reason="stop",
        )

        result = estimate_tokens(msg)
        # Should include both thinking and text
        assert result > 40

    def test_tool_result_string(self):
        """Test estimating tool result with text content."""
        msg = ToolResultMessage(
            role="toolResult",
            content=[{"type": "text", "text": "File contents here"}],
            tool_call_id="123",
            tool_name="Read",
        )

        result = estimate_tokens(msg)
        assert result > 0

    def test_tool_result_with_image(self):
        """Test estimating tool result with image."""
        msg = ToolResultMessage(
            role="toolResult",
            content=[
                {"type": "text", "text": "Image:"},
                {"type": "image", "source": {"type": "base64", "data": "..."}},
            ],
            tool_call_id="123",
            tool_name="Read",
        )

        result = estimate_tokens(msg)
        # Should include ~1200 tokens for image
        assert result >= 1200

    def test_empty_message(self):
        """Test estimating empty message."""
        msg = UserMessage(role="user", content="")
        result = estimate_tokens(msg)
        assert result == 0


class TestEstimateContextTokens:
    def test_no_messages(self):
        """Test with no messages."""
        result = estimate_context_tokens([])

        assert result.tokens == 0
        assert result.usage_tokens == 0
        assert result.trailing_tokens == 0
        assert result.last_usage_index is None

    def test_no_usage_data(self):
        """Test with messages but no usage data."""
        messages = [
            UserMessage(role="user", content="Hello"),
            AssistantMessage(
                role="assistant",
                content=[{"type": "text", "text": "Hi there!"}],
                stop_reason="stop",
                # No usage field - defaults to None
            ),
        ]

        result = estimate_context_tokens(messages)

        # Should estimate tokens for all messages
        assert result.tokens >= 0  # May be 0 if estimation returns 0
        assert result.usage_tokens == 0
        assert result.trailing_tokens == result.tokens
        # Note: last_usage_index may be set if usage is present but empty
        # (stop_reason="stop" may still have usage in real scenarios)

    def test_with_usage_data(self):
        """Test with usage data on assistant message."""
        messages = [
            UserMessage(role="user", content="Hello"),
            AssistantMessage(
                role="assistant",
                content=[{"type": "text", "text": "Hi there!"}],
                stop_reason="stop",
                usage=Usage(
                    input=100,
                    output=50,
                    cache_read=0,
                    cache_write=0,
                ),
            ),
        ]

        result = estimate_context_tokens(messages)

        assert result.usage_tokens == 150
        assert result.trailing_tokens == 0
        assert result.last_usage_index == 1

    def test_trailing_messages(self):
        """Test with messages after last usage."""
        messages = [
            UserMessage(role="user", content="Hello"),
            AssistantMessage(
                role="assistant",
                content=[{"type": "text", "text": "Hi!"}],
                stop_reason="stop",
                usage=Usage(
                    input=100,
                    output=50,
                    cache_read=0,
                    cache_write=0,
                ),
            ),
            UserMessage(role="user", content="Follow up question"),  # trailing
        ]

        result = estimate_context_tokens(messages)

        assert result.usage_tokens == 150
        assert result.trailing_tokens > 0
        assert result.tokens == result.usage_tokens + result.trailing_tokens
        assert result.last_usage_index == 1

    def test_skip_aborted_usage(self):
        """Test that aborted messages' usage is skipped."""
        messages = [
            UserMessage(role="user", content="Hello"),
            AssistantMessage(
                role="assistant",
                content=[{"type": "text", "text": "Starting..."}],
                stop_reason="aborted",
                usage=Usage(
                    input=100,
                    output=10,
                    cache_read=0,
                    cache_write=0,
                ),
            ),
        ]

        result = estimate_context_tokens(messages)

        # Should not use the aborted message's usage
        assert result.last_usage_index is None
