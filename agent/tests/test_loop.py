"""Tests for agent loop."""

import pytest
from pipy_agent import (
    default_convert_to_llm,
    AgentLoopConfig,
    UserMessage,
    AssistantMessage,
    ToolResultMessage,
    TextContent,
)
from pipy_agent.loop import agent_loop, agent_loop_continue


class TestDefaultConvertToLlm:
    def test_keeps_user_messages(self):
        messages = [UserMessage(content=[TextContent(text="hello")])]
        result = default_convert_to_llm(messages)
        assert len(result) == 1
        assert result[0].role == "user"

    def test_keeps_assistant_messages(self):
        messages = [AssistantMessage(content=[TextContent(text="hi")])]
        result = default_convert_to_llm(messages)
        assert len(result) == 1
        assert result[0].role == "assistant"

    def test_keeps_tool_result_messages(self):
        messages = [
            ToolResultMessage(
                tool_call_id="call_1",
                tool_name="test",
                content=[TextContent(text="result")],
            )
        ]
        result = default_convert_to_llm(messages)
        assert len(result) == 1
        assert result[0].role == "toolResult"

    def test_filters_unknown_roles(self):
        # This would be a custom message type
        from pydantic import BaseModel

        class CustomMessage(BaseModel):
            role: str = "custom"
            content: str = "test"

        messages = [
            UserMessage(content=[TextContent(text="hello")]),
            CustomMessage(),  # Should be filtered
            AssistantMessage(content=[TextContent(text="hi")]),
        ]
        result = default_convert_to_llm(messages)
        assert len(result) == 2


class TestAgentLoopConfig:
    def test_model_required(self):
        config = AgentLoopConfig(model="test/model")
        assert config.model == "test/model"

    def test_optional_fields(self):
        config = AgentLoopConfig(
            model="test/model",
            temperature=0.5,
            max_tokens=1000,
        )
        assert config.temperature == 0.5
        assert config.max_tokens == 1000


class TestAgentLoopValidation:
    @pytest.mark.asyncio
    async def test_agent_loop_continue_empty_messages(self):
        config = AgentLoopConfig(model="test/model")

        with pytest.raises(ValueError, match="no messages"):
            async for _ in agent_loop_continue(messages=[], config=config):
                pass

    @pytest.mark.asyncio
    async def test_agent_loop_continue_from_assistant(self):
        config = AgentLoopConfig(model="test/model")
        messages = [AssistantMessage(content=[TextContent(text="hi")])]

        with pytest.raises(ValueError, match="Cannot continue from assistant"):
            async for _ in agent_loop_continue(messages=messages, config=config):
                pass


class TestAgentLoopEvents:
    """Test that agent_loop emits correct events.

    Note: Full integration tests require mocking pipy_ai.astream.
    These tests verify the initial event sequence before LLM call.
    """

    @pytest.mark.asyncio
    async def test_emits_start_events(self):
        """Test that loop emits AgentStartEvent and TurnStartEvent."""
        from unittest.mock import patch

        config = AgentLoopConfig(model="test/model")
        prompts = [UserMessage(content=[TextContent(text="hello")])]

        events = []

        # Mock astream to return empty (will cause error but we catch events first)
        async def mock_stream(*args, **kwargs):
            # Yield nothing, causing "Stream ended unexpectedly"
            return
            yield  # Make it an async generator

        with patch("pipy_agent.loop.astream", mock_stream):
            try:
                async for event in agent_loop(prompts, config=config):
                    events.append(event)
                    # Stop after getting initial events
                    if len(events) >= 4:
                        break
            except RuntimeError:
                pass  # Expected: "Stream ended unexpectedly"

        # Should have: AgentStart, TurnStart, MessageStart (prompt), MessageEnd (prompt)
        assert len(events) >= 4
        assert events[0].type == "agent_start"
        assert events[1].type == "turn_start"
        assert events[2].type == "message_start"
        assert events[3].type == "message_end"


class TestConvertToLlmCallback:
    @pytest.mark.asyncio
    async def test_custom_convert_to_llm(self):
        """Test that custom convert_to_llm is used."""
        from unittest.mock import patch

        called_with = []

        def custom_convert(messages):
            called_with.append(messages)
            return default_convert_to_llm(messages)

        config = AgentLoopConfig(model="test/model")
        prompts = [UserMessage(content=[TextContent(text="hello")])]

        # Mock astream
        async def mock_stream(*args, **kwargs):
            return
            yield

        with patch("pipy_agent.loop.astream", mock_stream):
            try:
                async for _ in agent_loop(
                    prompts, config=config, convert_to_llm=custom_convert
                ):
                    pass
            except RuntimeError:
                pass

        # custom_convert should have been called
        assert len(called_with) > 0
