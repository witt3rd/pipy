"""Agent-specific types. LLM types imported from pipy-ai."""

from typing import Any, Callable, Awaitable, TypeVar, Generic
from pydantic import BaseModel, Field, ConfigDict

# Import ALL LLM types from pipy-ai (no redefinition!)
# Note: Many imports are for re-export via __init__.py, not used directly here
from pipy_ai import (  # noqa: F401
    # Enums
    ThinkingLevel,
    StopReason,
    # Content types
    TextContent,
    ImageContent,
    ThinkingContent,
    ToolCall,
    # Messages
    Message,
    UserMessage,
    AssistantMessage,
    ToolResultMessage,
    # Context & Tool
    Context,
    Tool,
    # Streaming
    AssistantMessageEvent,
    SimpleStreamOptions,
    # Options
    ThinkingBudgets,
    # Cancellation
    AbortSignal,
    AbortController,
    AbortError,
)

T = TypeVar("T")


# === Agent Tool ===


class AgentToolResult(BaseModel, Generic[T]):
    """Result from tool execution."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    content: list[TextContent | ImageContent] = Field(default_factory=list)
    details: T | None = None


# Callback for streaming tool updates
AgentToolUpdateCallback = Callable[[AgentToolResult], None]


class AgentTool(BaseModel):
    """Tool with executable function.

    Extends pipy-ai's Tool concept with:
    - label: Human-readable name for UI
    - execute: Async function to run the tool
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema
    label: str = ""  # UI display name

    async def execute(
        self,
        tool_call_id: str,
        params: dict[str, Any],
        signal: AbortSignal | None = None,
        on_update: AgentToolUpdateCallback | None = None,
    ) -> AgentToolResult:
        """Execute the tool. Override in subclass or use @tool decorator."""
        raise NotImplementedError(f"Tool {self.name} has no execute implementation")

    def to_tool(self) -> Tool:
        """Convert to pipy-ai Tool for LLM calls."""
        return Tool(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )


def tool(
    name: str,
    description: str,
    parameters: dict[str, Any],
    label: str = "",
) -> Callable[[Callable], AgentTool]:
    """Decorator to create an AgentTool from an async function.

    Example:
        @tool(
            name="get_weather",
            description="Get weather for a location",
            parameters={
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"]
            },
            label="Weather"
        )
        async def get_weather(tool_call_id, params, signal, on_update):
            location = params["location"]
            return AgentToolResult(
                content=[TextContent(text=f"Weather in {location}: Sunny, 22°C")],
                details={"temp": 22}
            )
    """

    def decorator(fn: Callable) -> AgentTool:
        class DecoratedTool(AgentTool):
            async def execute(
                self,
                tool_call_id: str,
                params: dict[str, Any],
                signal: AbortSignal | None = None,
                on_update: AgentToolUpdateCallback | None = None,
            ) -> AgentToolResult:
                return await fn(tool_call_id, params, signal, on_update)

        return DecoratedTool(
            name=name,
            description=description,
            parameters=parameters,
            label=label or name,
        )

    return decorator


# === Agent Message ===

# AgentMessage = LLM messages + custom app messages
# Base case: just LLM messages (apps extend with Union)
AgentMessage = Message

# Example extension:
# class ArtifactMessage(BaseModel):
#     role: Literal["artifact"] = "artifact"
#     content: str
#     timestamp: int = 0
#
# AgentMessage = Message | ArtifactMessage


# === Agent State ===


class AgentState(BaseModel):
    """Current state of the agent."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    system_prompt: str = ""
    model: str = ""  # Model identifier (e.g., "anthropic/claude-sonnet-4-5")
    thinking_level: ThinkingLevel = ThinkingLevel.OFF
    tools: list[AgentTool] = Field(default_factory=list)
    messages: list[AgentMessage] = Field(default_factory=list)
    is_streaming: bool = False
    stream_message: AssistantMessage | None = None
    pending_tool_calls: set[str] = Field(default_factory=set)
    error: str | None = None


# === Agent Events ===


class AgentStartEvent(BaseModel):
    """Agent execution started."""

    type: str = "agent_start"


class AgentEndEvent(BaseModel):
    """Agent execution ended."""

    type: str = "agent_end"
    messages: list[AgentMessage] = Field(default_factory=list)


class TurnStartEvent(BaseModel):
    """A turn started (assistant response + tool calls)."""

    type: str = "turn_start"


class TurnEndEvent(BaseModel):
    """A turn ended."""

    type: str = "turn_end"
    message: AssistantMessage
    tool_results: list[ToolResultMessage] = Field(default_factory=list)


class MessageStartEvent(BaseModel):
    """A message started streaming."""

    type: str = "message_start"
    message: AgentMessage


class MessageUpdateEvent(BaseModel):
    """A message updated during streaming."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    type: str = "message_update"
    message: AssistantMessage
    assistant_event: AssistantMessageEvent  # The underlying pipy-ai event


class MessageEndEvent(BaseModel):
    """A message finished."""

    type: str = "message_end"
    message: AgentMessage


class ToolExecutionStartEvent(BaseModel):
    """Tool execution started."""

    type: str = "tool_execution_start"
    tool_call_id: str
    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)


class ToolExecutionUpdateEvent(BaseModel):
    """Tool execution progress update."""

    type: str = "tool_execution_update"
    tool_call_id: str
    tool_name: str
    partial_result: AgentToolResult | None = None


class ToolExecutionEndEvent(BaseModel):
    """Tool execution ended."""

    type: str = "tool_execution_end"
    tool_call_id: str
    tool_name: str
    result: AgentToolResult | None = None
    is_error: bool = False


# Union of all agent events
AgentEvent = (
    AgentStartEvent
    | AgentEndEvent
    | TurnStartEvent
    | TurnEndEvent
    | MessageStartEvent
    | MessageUpdateEvent
    | MessageEndEvent
    | ToolExecutionStartEvent
    | ToolExecutionUpdateEvent
    | ToolExecutionEndEvent
)


# === Loop Config ===


class AgentLoopConfig(BaseModel):
    """Configuration for the agent loop.

    Inherits stream options from pipy-ai, adds agent-specific callbacks.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model: str  # Model identifier

    # Stream options (passed to pipy-ai)
    temperature: float | None = None
    max_tokens: int | None = None
    reasoning: ThinkingLevel | None = None
    session_id: str | None = None
    api_key: str | None = None

    # Custom token budgets for thinking levels (token-based providers only)
    thinking_budgets: ThinkingBudgets | None = None

    # Maximum delay in ms to wait for server-requested retries.
    # If server requests longer delay, the request fails immediately,
    # allowing higher-level retry logic to handle it with user visibility.
    # Default: 60000 (60 seconds). Set to 0 to disable the cap.
    max_retry_delay_ms: int | None = None


# Type aliases for callbacks (set on config instance, not serialized)
ConvertToLlmFn = Callable[[list[AgentMessage]], list[Message]]
TransformContextFn = Callable[
    [list[AgentMessage], AbortSignal | None], Awaitable[list[AgentMessage]]
]
GetApiKeyFn = Callable[[str], Awaitable[str | None] | str | None]
GetMessagesFn = Callable[[], Awaitable[list[AgentMessage]]]
