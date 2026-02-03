"""Tests for agent types."""

import pytest
from pipy_agent import (
    # Re-exports from pipy-ai
    ThinkingLevel,
    TextContent,
    ImageContent,
    UserMessage,
    AssistantMessage,
    Tool,
    AbortController,
    AbortError,
    # Agent-specific
    AgentTool,
    AgentToolResult,
    tool,
    AgentState,
    AgentLoopConfig,
    # Events
    AgentStartEvent,
    AgentEndEvent,
    TurnStartEvent,
    TurnEndEvent,
    MessageStartEvent,
    MessageEndEvent,
    ToolExecutionStartEvent,
    ToolExecutionUpdateEvent,
    ToolExecutionEndEvent,
)


class TestReExports:
    """Test that pipy-ai types are properly re-exported."""

    def test_thinking_level_has_off(self):
        assert ThinkingLevel.OFF == "off"
        assert ThinkingLevel.MINIMAL == "minimal"
        assert ThinkingLevel.HIGH == "high"

    def test_abort_signal(self):
        controller = AbortController()
        assert controller.signal.aborted is False
        controller.abort()
        assert controller.signal.aborted is True

    def test_abort_error(self):
        with pytest.raises(AbortError):
            raise AbortError("test")

    def test_text_content(self):
        tc = TextContent(text="hello")
        assert tc.text == "hello"
        assert tc.type == "text"

    def test_user_message(self):
        msg = UserMessage(content=[TextContent(text="hi")])
        assert msg.role == "user"

    def test_tool(self):
        t = Tool(name="test", description="desc", parameters={})
        assert t.name == "test"

    def test_thinking_budgets(self):
        from pipy_agent import ThinkingBudgets

        budgets = ThinkingBudgets(
            minimal=1024,
            low=2048,
            medium=4096,
            high=8192,
        )
        assert budgets.minimal == 1024
        assert budgets.low == 2048
        assert budgets.medium == 4096
        assert budgets.high == 8192


class TestAgentToolResult:
    def test_empty_result(self):
        result = AgentToolResult()
        assert result.content == []
        assert result.details is None

    def test_with_content(self):
        result = AgentToolResult(
            content=[TextContent(text="hello")],
            details={"key": "value"},
        )
        assert len(result.content) == 1
        assert result.content[0].text == "hello"
        assert result.details == {"key": "value"}

    def test_with_image_content(self):
        result = AgentToolResult(
            content=[
                TextContent(text="caption"),
                ImageContent(url="http://example.com/img.png"),
            ]
        )
        assert len(result.content) == 2


class TestAgentTool:
    def test_basic_tool(self):
        t = AgentTool(
            name="test",
            description="A test tool",
            parameters={"type": "object", "properties": {}},
        )
        assert t.name == "test"
        assert t.label == ""

    def test_tool_with_label(self):
        t = AgentTool(
            name="test",
            description="desc",
            parameters={},
            label="Test Tool",
        )
        assert t.label == "Test Tool"

    def test_to_tool(self):
        at = AgentTool(
            name="test",
            description="desc",
            parameters={"type": "object"},
        )
        t = at.to_tool()
        assert isinstance(t, Tool)
        assert t.name == "test"
        assert t.description == "desc"

    @pytest.mark.asyncio
    async def test_execute_not_implemented(self):
        t = AgentTool(name="test", description="desc", parameters={})
        with pytest.raises(NotImplementedError):
            await t.execute("id", {})


class TestToolDecorator:
    def test_creates_agent_tool(self):
        @tool(
            name="greet",
            description="Greet someone",
            parameters={"type": "object", "properties": {"name": {"type": "string"}}},
        )
        async def greet(tool_call_id, params, signal, on_update):
            return AgentToolResult(content=[TextContent(text=f"Hello {params['name']}!")])

        assert isinstance(greet, AgentTool)
        assert greet.name == "greet"
        assert greet.description == "Greet someone"

    def test_label_defaults_to_name(self):
        @tool(name="test", description="desc", parameters={})
        async def test_fn(tool_call_id, params, signal, on_update):
            return AgentToolResult()

        assert test_fn.label == "test"

    def test_custom_label(self):
        @tool(name="test", description="desc", parameters={}, label="Custom Label")
        async def test_fn(tool_call_id, params, signal, on_update):
            return AgentToolResult()

        assert test_fn.label == "Custom Label"

    @pytest.mark.asyncio
    async def test_execute_works(self):
        @tool(
            name="add",
            description="Add numbers",
            parameters={
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                },
            },
        )
        async def add(tool_call_id, params, signal, on_update):
            result = params["a"] + params["b"]
            return AgentToolResult(
                content=[TextContent(text=f"Result: {result}")],
                details={"result": result},
            )

        result = await add.execute("call_1", {"a": 2, "b": 3})
        assert result.details["result"] == 5
        assert "5" in result.content[0].text


class TestAgentState:
    def test_defaults(self):
        state = AgentState()
        assert state.system_prompt == ""
        assert state.model == ""
        assert state.thinking_level == ThinkingLevel.OFF
        assert state.tools == []
        assert state.messages == []
        assert state.is_streaming is False
        assert state.error is None

    def test_with_values(self):
        state = AgentState(
            system_prompt="You are helpful.",
            model="anthropic/claude-sonnet-4-5",
            thinking_level=ThinkingLevel.HIGH,
        )
        assert state.system_prompt == "You are helpful."
        assert state.model == "anthropic/claude-sonnet-4-5"
        assert state.thinking_level == ThinkingLevel.HIGH


class TestAgentLoopConfig:
    def test_minimal_config(self):
        config = AgentLoopConfig(model="anthropic/claude-sonnet-4-5")
        assert config.model == "anthropic/claude-sonnet-4-5"
        assert config.temperature is None
        assert config.max_tokens is None

    def test_full_config(self):
        config = AgentLoopConfig(
            model="openai/gpt-4o",
            temperature=0.7,
            max_tokens=4096,
            reasoning=ThinkingLevel.MEDIUM,
            session_id="sess_123",
            api_key="sk-test",
        )
        assert config.temperature == 0.7
        assert config.max_tokens == 4096
        assert config.reasoning == ThinkingLevel.MEDIUM


class TestAgentEvents:
    def test_agent_start(self):
        e = AgentStartEvent()
        assert e.type == "agent_start"

    def test_agent_end(self):
        e = AgentEndEvent(messages=[])
        assert e.type == "agent_end"
        assert e.messages == []

    def test_turn_start(self):
        e = TurnStartEvent()
        assert e.type == "turn_start"

    def test_turn_end(self):
        msg = AssistantMessage(content=[TextContent(text="hi")])
        e = TurnEndEvent(message=msg, tool_results=[])
        assert e.type == "turn_end"
        assert e.message == msg

    def test_message_events(self):
        msg = UserMessage(content=[TextContent(text="hello")])
        assert MessageStartEvent(message=msg).type == "message_start"
        assert MessageEndEvent(message=msg).type == "message_end"

    def test_tool_execution_events(self):
        start = ToolExecutionStartEvent(
            tool_call_id="call_1",
            tool_name="test",
            args={"x": 1},
        )
        assert start.type == "tool_execution_start"
        assert start.tool_call_id == "call_1"

        update = ToolExecutionUpdateEvent(
            tool_call_id="call_1",
            tool_name="test",
            partial_result=AgentToolResult(content=[TextContent(text="50%")]),
        )
        assert update.type == "tool_execution_update"

        end = ToolExecutionEndEvent(
            tool_call_id="call_1",
            tool_name="test",
            result=AgentToolResult(content=[TextContent(text="done")]),
            is_error=False,
        )
        assert end.type == "tool_execution_end"
        assert end.is_error is False
