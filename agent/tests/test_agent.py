"""Tests for Agent class."""

import pytest
from pipy_agent import (
    Agent,
    AgentToolResult,
    tool,
    TextContent,
    UserMessage,
    ThinkingLevel,
)


class TestAgentInit:
    def test_default_init(self):
        agent = Agent()
        assert agent.state.model == "anthropic/claude-sonnet-4-5"
        assert agent.state.system_prompt == ""
        assert agent.state.tools == []
        assert agent.state.messages == []

    def test_custom_init(self):
        agent = Agent(
            model="openai/gpt-4o",
            system_prompt="You are helpful.",
        )
        assert agent.state.model == "openai/gpt-4o"
        assert agent.state.system_prompt == "You are helpful."

    def test_with_tools(self):
        @tool(name="test", description="desc", parameters={})
        async def test_tool(tool_call_id, params, signal, on_update):
            return AgentToolResult()

        agent = Agent(tools=[test_tool])
        assert len(agent.state.tools) == 1
        assert agent.state.tools[0].name == "test"


class TestAgentStateMutators:
    def test_set_system_prompt(self):
        agent = Agent()
        agent.set_system_prompt("New prompt")
        assert agent.state.system_prompt == "New prompt"

    def test_set_model(self):
        agent = Agent()
        agent.set_model("openai/gpt-4o")
        assert agent.state.model == "openai/gpt-4o"

    def test_set_thinking_level(self):
        agent = Agent()
        agent.set_thinking_level(ThinkingLevel.HIGH)
        assert agent.state.thinking_level == ThinkingLevel.HIGH

    def test_set_tools(self):
        agent = Agent()

        @tool(name="t1", description="d1", parameters={})
        async def t1(tool_call_id, params, signal, on_update):
            return AgentToolResult()

        agent.set_tools([t1])
        assert len(agent.state.tools) == 1

    def test_message_operations(self):
        agent = Agent()
        msg = UserMessage(content=[TextContent(text="hello")])

        # Append
        agent.append_message(msg)
        assert len(agent.messages) == 1

        # Replace
        agent.replace_messages([msg, msg])
        assert len(agent.messages) == 2

        # Clear
        agent.clear_messages()
        assert len(agent.messages) == 0


class TestAgentSubscription:
    def test_subscribe_returns_unsubscribe(self):
        agent = Agent()
        events = []

        unsub = agent.subscribe(lambda e: events.append(e))
        assert callable(unsub)

    def test_unsubscribe_removes_listener(self):
        agent = Agent()
        events = []

        unsub = agent.subscribe(lambda e: events.append(e))
        unsub()

        # Manually emit to test (normally internal)
        from pipy_agent import AgentStartEvent

        agent._emit(AgentStartEvent())
        assert len(events) == 0

    def test_multiple_subscribers(self):
        agent = Agent()
        events1 = []
        events2 = []

        agent.subscribe(lambda e: events1.append(e))
        agent.subscribe(lambda e: events2.append(e))

        from pipy_agent import AgentStartEvent

        agent._emit(AgentStartEvent())
        assert len(events1) == 1
        assert len(events2) == 1


class TestAgentQueues:
    def test_steer(self):
        agent = Agent()
        msg = UserMessage(content=[TextContent(text="interrupt")])

        agent.steer(msg)
        assert len(agent._steering_queue) == 1
        assert agent._steering_queue[0] == msg

    def test_follow_up(self):
        agent = Agent()
        msg = UserMessage(content=[TextContent(text="next")])

        agent.follow_up(msg)
        assert len(agent._follow_up_queue) == 1

    def test_clear_queues(self):
        agent = Agent()
        agent.steer(UserMessage(content=[TextContent(text="1")]))
        agent.follow_up(UserMessage(content=[TextContent(text="2")]))

        agent.clear_queues()
        assert len(agent._steering_queue) == 0
        assert len(agent._follow_up_queue) == 0


class TestAgentControl:
    def test_reset(self):
        agent = Agent()
        agent.append_message(UserMessage(content=[TextContent(text="hi")]))
        agent.steer(UserMessage(content=[TextContent(text="steer")]))
        agent._state.error = "some error"

        agent.reset()
        assert agent.messages == []
        assert agent._steering_queue == []
        assert agent._follow_up_queue == []
        assert agent.state.error is None

    def test_abort_when_not_streaming(self):
        agent = Agent()
        # Should not raise
        agent.abort()


class TestAgentPromptValidation:
    @pytest.mark.asyncio
    async def test_prompt_while_streaming_raises(self):
        agent = Agent()
        agent._state.is_streaming = True

        with pytest.raises(RuntimeError, match="Already streaming"):
            await agent.prompt("test")

    @pytest.mark.asyncio
    async def test_continue_with_no_messages_raises(self):
        agent = Agent()

        with pytest.raises(ValueError, match="No messages"):
            await agent.continue_()

    @pytest.mark.asyncio
    async def test_continue_from_assistant_raises(self):
        from pipy_agent import AssistantMessage

        agent = Agent()
        agent.append_message(AssistantMessage(content=[TextContent(text="hi")]))

        with pytest.raises(ValueError, match="Cannot continue from assistant"):
            await agent.continue_()


class TestAgentProperties:
    def test_messages_property(self):
        agent = Agent()
        assert agent.messages == []

        msg = UserMessage(content=[TextContent(text="hi")])
        agent.append_message(msg)
        assert agent.messages == [msg]

    def test_is_streaming_property(self):
        agent = Agent()
        assert agent.is_streaming is False

        agent._state.is_streaming = True
        assert agent.is_streaming is True


class TestAgentNewOptions:
    """Tests for thinking_budgets and max_retry_delay_ms options."""

    def test_session_id_property(self):
        agent = Agent(session_id="test-session")
        assert agent.session_id == "test-session"

        agent.session_id = "new-session"
        assert agent.session_id == "new-session"

    def test_thinking_budgets_init(self):
        from pipy_agent import ThinkingBudgets

        budgets = ThinkingBudgets(
            minimal=1024,
            low=2048,
            medium=4096,
            high=8192,
        )
        agent = Agent(thinking_budgets=budgets)
        assert agent.thinking_budgets == budgets

    def test_thinking_budgets_property(self):
        from pipy_agent import ThinkingBudgets

        agent = Agent()
        assert agent.thinking_budgets is None

        budgets = ThinkingBudgets(minimal=1000)
        agent.thinking_budgets = budgets
        assert agent.thinking_budgets == budgets

    def test_max_retry_delay_ms_init(self):
        agent = Agent(max_retry_delay_ms=30000)
        assert agent.max_retry_delay_ms == 30000

    def test_max_retry_delay_ms_property(self):
        agent = Agent()
        assert agent.max_retry_delay_ms is None

        agent.max_retry_delay_ms = 45000
        assert agent.max_retry_delay_ms == 45000

    def test_max_retry_delay_ms_zero_disables_cap(self):
        agent = Agent(max_retry_delay_ms=0)
        assert agent.max_retry_delay_ms == 0
