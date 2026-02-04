"""
pipy-agent - Agent framework built on pipy-ai.

Example:
    from pipy_agent import Agent, tool, AgentToolResult, TextContent

    @tool(name="greet", description="Greet someone", parameters={...})
    async def greet(tool_call_id, params, signal, on_update):
        return AgentToolResult(content=[TextContent(text=f"Hello {params['name']}!")])

    agent = Agent(model="anthropic/claude-sonnet-4-5")
    agent.set_tools([greet])
    await agent.prompt("Greet Alice")
"""

__version__ = "0.51.6"

# Re-export pipy-ai types that agent users need
from pipy_ai import (
    # Messages & Content (for building prompts)
    Message,
    UserMessage,
    AssistantMessage,
    ToolResultMessage,
    TextContent,
    ImageContent,
    ThinkingContent,
    ToolCall,
    # Context & Tool (for reference)
    Context,
    Tool,
    # Enums
    ThinkingLevel,
    StopReason,
    # Options
    ThinkingBudgets,
    # Cancellation
    AbortSignal,
    AbortController,
    AbortError,
)

# Agent-specific types
from .types import (
    # Tool
    AgentTool,
    AgentToolResult,
    AgentToolUpdateCallback,
    tool,
    # Message
    AgentMessage,
    # State
    AgentState,
    # Events
    AgentEvent,
    AgentStartEvent,
    AgentEndEvent,
    TurnStartEvent,
    TurnEndEvent,
    MessageStartEvent,
    MessageUpdateEvent,
    MessageEndEvent,
    ToolExecutionStartEvent,
    ToolExecutionUpdateEvent,
    ToolExecutionEndEvent,
    # Config
    AgentLoopConfig,
)

# Agent class
from .agent import Agent

# Loop functions
from .loop import (
    agent_loop,
    agent_loop_continue,
    default_convert_to_llm,
)

__all__ = [
    # Version
    "__version__",
    # Re-exported from pipy-ai
    "Message",
    "UserMessage",
    "AssistantMessage",
    "ToolResultMessage",
    "TextContent",
    "ImageContent",
    "ThinkingContent",
    "ToolCall",
    "Context",
    "Tool",
    "ThinkingLevel",
    "StopReason",
    "ThinkingBudgets",
    "AbortSignal",
    "AbortController",
    "AbortError",
    # Agent-specific
    "Agent",
    "AgentTool",
    "AgentToolResult",
    "AgentToolUpdateCallback",
    "tool",
    "AgentMessage",
    "AgentState",
    "AgentLoopConfig",
    # Events
    "AgentEvent",
    "AgentStartEvent",
    "AgentEndEvent",
    "TurnStartEvent",
    "TurnEndEvent",
    "MessageStartEvent",
    "MessageUpdateEvent",
    "MessageEndEvent",
    "ToolExecutionStartEvent",
    "ToolExecutionUpdateEvent",
    "ToolExecutionEndEvent",
    # Loop
    "agent_loop",
    "agent_loop_continue",
    "default_convert_to_llm",
]
