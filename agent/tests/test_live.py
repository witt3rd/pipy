"""Live integration tests with real API.

Run with: pytest tests/test_live.py -v -s
Requires OPENAI_API_KEY environment variable.
"""

import os
import pytest
from dotenv import load_dotenv

# Load from animus .env for API keys
load_dotenv("C:/Users/donal/animus/.env")


# Skip all tests if no API key
pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)


class TestLiveAgent:
    """Live tests with real LLM."""

    @pytest.mark.asyncio
    async def test_simple_prompt(self):
        """Test simple prompt without tools."""
        from pipy_agent import Agent

        agent = Agent(model="openai/gpt-4o-mini")
        agent.set_system_prompt("You are a helpful assistant. Be very brief.")

        events = []
        agent.subscribe(lambda e: events.append(e))

        await agent.prompt("Say 'hello' and nothing else.")

        # Check we got expected events
        event_types = [e.type for e in events]
        assert "agent_start" in event_types
        assert "turn_start" in event_types
        assert "message_start" in event_types
        assert "message_end" in event_types
        assert "agent_end" in event_types

        # Check we have a response
        assert len(agent.messages) >= 2  # User + Assistant
        assistant_msg = agent.messages[-1]
        assert assistant_msg.role == "assistant"
        assert "hello" in assistant_msg.text.lower()

    @pytest.mark.asyncio
    async def test_with_tool(self):
        """Test agent with tool execution."""
        from pipy_agent import Agent, tool, AgentToolResult, TextContent

        @tool(
            name="get_time",
            description="Get the current time",
            parameters={"type": "object", "properties": {}},
        )
        async def get_time(tool_call_id, params, signal, on_update):
            return AgentToolResult(
                content=[TextContent(text="The current time is 3:14 PM")],
                details={"hour": 15, "minute": 14},
            )

        agent = Agent(model="openai/gpt-4o-mini")
        agent.set_system_prompt("You are helpful. Use tools when appropriate.")
        agent.set_tools([get_time])

        events = []
        agent.subscribe(lambda e: events.append(e))

        await agent.prompt("What time is it?")

        event_types = [e.type for e in events]

        # Should have tool execution
        assert "tool_execution_start" in event_types
        assert "tool_execution_end" in event_types

        # Response should mention the time
        assistant_msgs = [m for m in agent.messages if m.role == "assistant"]
        assert len(assistant_msgs) >= 1
        # Final response should mention 3:14
        final_text = assistant_msgs[-1].text.lower()
        assert "3:14" in final_text or "3" in final_text

    @pytest.mark.asyncio
    async def test_streaming_events(self):
        """Test that streaming events are emitted."""
        from pipy_agent import Agent

        agent = Agent(model="openai/gpt-4o-mini")

        update_count = 0
        event_types = set()

        def on_event(event):
            nonlocal update_count
            event_types.add(event.type)
            if event.type == "message_update":
                update_count += 1

        agent.subscribe(on_event)

        await agent.prompt("Write a haiku about programming.")

        # Should have message_update events (streaming)
        assert "message_update" in event_types
        # Should have at least some updates
        assert update_count >= 1
        # Should have full lifecycle
        assert "agent_start" in event_types
        assert "agent_end" in event_types


class TestLiveLoop:
    """Live tests with agent_loop directly."""

    @pytest.mark.asyncio
    async def test_agent_loop_basic(self):
        """Test agent_loop function directly."""
        from pipy_agent import (
            agent_loop,
            AgentLoopConfig,
            UserMessage,
            TextContent,
        )

        config = AgentLoopConfig(model="openai/gpt-4o-mini")
        prompts = [UserMessage(content=[TextContent(text="Say 'test' only.")])]

        events = []
        async for event in agent_loop(
            prompts,
            system_prompt="Be extremely brief.",
            config=config,
        ):
            events.append(event)

        event_types = [e.type for e in events]
        assert "agent_start" in event_types
        assert "agent_end" in event_types

        # Get the final message from agent_end
        agent_end = next(e for e in events if e.type == "agent_end")
        assert len(agent_end.messages) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
