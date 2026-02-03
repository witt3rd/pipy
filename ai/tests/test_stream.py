"""Tests for stream events module."""

import pytest

from pipy_ai import (
    AssistantMessage,
    StopReason,
    TextContent,
    ToolCall,
)
from pipy_ai.stream import (
    DoneEvent,
    ErrorEvent,
    StartEvent,
    TextDeltaEvent,
    TextEndEvent,
    TextStartEvent,
    ThinkingDeltaEvent,
    ThinkingEndEvent,
    ThinkingStartEvent,
    ToolCallDeltaEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
)


@pytest.fixture
def partial_message():
    return AssistantMessage(
        content=[TextContent(text="Hello")],
        model="test-model",
        provider="test",
    )


class TestTextEvents:
    def test_text_start_event(self, partial_message):
        event = TextStartEvent(
            content_index=0,
            partial=partial_message,
        )
        assert event.type == "text_start"
        assert event.content_index == 0
        assert event.partial.model == "test-model"

    def test_text_delta_event(self, partial_message):
        event = TextDeltaEvent(
            content_index=0,
            delta="world",
            partial=partial_message,
        )
        assert event.type == "text_delta"
        assert event.delta == "world"

    def test_text_end_event(self, partial_message):
        event = TextEndEvent(
            content_index=0,
            content="Hello world",
            partial=partial_message,
        )
        assert event.type == "text_end"
        assert event.content == "Hello world"


class TestThinkingEvents:
    def test_thinking_start_event(self, partial_message):
        event = ThinkingStartEvent(
            content_index=0,
            partial=partial_message,
        )
        assert event.type == "thinking_start"

    def test_thinking_delta_event(self, partial_message):
        event = ThinkingDeltaEvent(
            content_index=0,
            delta="Let me think...",
            partial=partial_message,
        )
        assert event.type == "thinking_delta"
        assert event.delta == "Let me think..."

    def test_thinking_end_event(self, partial_message):
        event = ThinkingEndEvent(
            content_index=0,
            content="Full thinking content",
            partial=partial_message,
        )
        assert event.type == "thinking_end"


class TestToolCallEvents:
    def test_toolcall_start_event(self, partial_message):
        event = ToolCallStartEvent(
            content_index=0,
            partial=partial_message,
        )
        assert event.type == "toolcall_start"

    def test_toolcall_delta_event(self, partial_message):
        event = ToolCallDeltaEvent(
            content_index=0,
            delta='{"location":',
            partial=partial_message,
        )
        assert event.type == "toolcall_delta"
        assert event.delta == '{"location":'

    def test_toolcall_end_event(self, partial_message):
        tool_call = ToolCall(
            id="call_123",
            name="get_weather",
            arguments={"location": "Tokyo"},
        )
        event = ToolCallEndEvent(
            content_index=0,
            tool_call=tool_call,
            partial=partial_message,
        )
        assert event.type == "toolcall_end"
        assert event.tool_call.name == "get_weather"


class TestCompletionEvents:
    def test_start_event(self, partial_message):
        event = StartEvent(partial=partial_message)
        assert event.type == "start"

    def test_done_event(self, partial_message):
        event = DoneEvent(
            reason=StopReason.STOP,
            message=partial_message,
        )
        assert event.type == "done"
        assert event.reason == StopReason.STOP

    def test_done_event_tool_use(self, partial_message):
        event = DoneEvent(
            reason=StopReason.TOOL_USE,
            message=partial_message,
        )
        assert event.reason == StopReason.TOOL_USE

    def test_error_event(self, partial_message):
        partial_message.error_message = "Something went wrong"
        event = ErrorEvent(
            reason=StopReason.ERROR,
            error=partial_message,
        )
        assert event.type == "error"
        assert event.reason == StopReason.ERROR
        assert event.error.error_message == "Something went wrong"
