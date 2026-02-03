"""Tests for summarization."""

import pytest

from pipy_ai import UserMessage, AssistantMessage, ToolResultMessage

from pipy_coding_agent.compaction.summarize import (
    serialize_conversation,
    SUMMARIZATION_SYSTEM_PROMPT,
    SUMMARIZATION_PROMPT,
    UPDATE_SUMMARIZATION_PROMPT,
)


class TestSerializeConversation:
    def test_user_message_string(self):
        """Test serializing user message with string content."""
        messages = [
            UserMessage(role="user", content="Hello, how are you?"),
        ]

        result = serialize_conversation(messages)

        assert "[User]: Hello, how are you?" in result

    def test_user_message_blocks(self):
        """Test serializing user message with content blocks."""
        messages = [
            UserMessage(
                role="user",
                content=[{"type": "text", "text": "Block content"}],
            ),
        ]

        result = serialize_conversation(messages)

        assert "[User]: Block content" in result

    def test_assistant_text(self):
        """Test serializing assistant text response."""
        messages = [
            AssistantMessage(
                role="assistant",
                content=[{"type": "text", "text": "Here's my answer"}],
                stop_reason="stop",
            ),
        ]

        result = serialize_conversation(messages)

        assert "[Assistant]: Here's my answer" in result

    def test_assistant_thinking(self):
        """Test serializing assistant thinking."""
        messages = [
            AssistantMessage(
                role="assistant",
                content=[
                    {"type": "thinking", "thinking": "Let me think..."},
                    {"type": "text", "text": "The answer is 42"},
                ],
                stop_reason="stop",
            ),
        ]

        result = serialize_conversation(messages)

        assert "[Assistant thinking]: Let me think..." in result
        assert "[Assistant]: The answer is 42" in result

    def test_assistant_tool_calls(self):
        """Test serializing assistant tool calls."""
        messages = [
            AssistantMessage(
                role="assistant",
                content=[{
                    "type": "toolCall",
                    "id": "123",
                    "name": "Read",
                    "arguments": {"path": "/test.txt"},
                }],
                stop_reason="toolUse",
            ),
        ]

        result = serialize_conversation(messages)

        assert "[Assistant tool calls]:" in result
        assert "Read" in result
        assert "/test.txt" in result

    def test_tool_result(self):
        """Test serializing tool result."""
        messages = [
            ToolResultMessage(
                role="toolResult",
                content=[{"type": "text", "text": "File contents here"}],
                tool_call_id="123",
                tool_name="Read",
            ),
        ]

        result = serialize_conversation(messages)

        assert "[Tool result]: File contents here" in result

    def test_full_conversation(self):
        """Test serializing a full conversation."""
        messages = [
            UserMessage(role="user", content="Read the file"),
            AssistantMessage(
                role="assistant",
                content=[{
                    "type": "toolCall",
                    "id": "1",
                    "name": "Read",
                    "arguments": {"path": "/test.txt"},
                }],
                stop_reason="toolUse",
            ),
            ToolResultMessage(
                role="toolResult",
                content=[{"type": "text", "text": "Hello world"}],
                tool_call_id="1",
                tool_name="Read",
            ),
            AssistantMessage(
                role="assistant",
                content=[{"type": "text", "text": "The file contains: Hello world"}],
                stop_reason="stop",
            ),
        ]

        result = serialize_conversation(messages)

        assert "[User]:" in result
        assert "[Assistant tool calls]:" in result
        assert "[Tool result]:" in result
        assert "[Assistant]:" in result

    def test_empty_messages(self):
        """Test serializing empty message list."""
        result = serialize_conversation([])
        assert result == ""


class TestPromptConstants:
    def test_system_prompt_exists(self):
        """Test that system prompt is defined."""
        assert len(SUMMARIZATION_SYSTEM_PROMPT) > 0
        assert "summarization" in SUMMARIZATION_SYSTEM_PROMPT.lower()

    def test_summarization_prompt_format(self):
        """Test that summarization prompt has expected sections."""
        assert "## Goal" in SUMMARIZATION_PROMPT
        assert "## Progress" in SUMMARIZATION_PROMPT
        assert "## Key Decisions" in SUMMARIZATION_PROMPT
        assert "## Next Steps" in SUMMARIZATION_PROMPT

    def test_update_prompt_differs(self):
        """Test that update prompt differs from initial."""
        assert UPDATE_SUMMARIZATION_PROMPT != SUMMARIZATION_PROMPT
        assert "previous-summary" in UPDATE_SUMMARIZATION_PROMPT.lower()


# Note: generate_summary and generate_turn_prefix_summary tests would require
# mocking the LLM call, which we'll skip for now as they're integration tests
