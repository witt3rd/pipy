# pipy-agent: Python Agent Framework Spec

**Goal**: Create a standalone Python agent framework (publishable to PyPI) built on `pipy-ai`.

---

## Design Principles

### Orthogonality with pipy-ai

| Responsibility | pipy-ai | pipy-agent |
|----------------|---------|------------|
| **LLM Types** | Message, Content, Tool, Context | Imports from pipy-ai |
| **Streaming** | Events, stream(), astream() | Wraps pipy-ai streaming |
| **Cancellation** | AbortSignal, AbortController | Imports from pipy-ai |
| **Model Registry** | models.dev integration | Imports from pipy-ai |
| **Tool Definition** | `Tool` (schema only) | `AgentTool` (schema + execute) |
| **Agent Loop** | ❌ | ✅ Loop logic |
| **Tool Execution** | ❌ | ✅ Execute & stream updates |
| **Steering/Follow-up** | ❌ | ✅ Message queues |
| **Agent Events** | ❌ | ✅ Lifecycle events |

### What pipy-agent adds:
1. **AgentTool** - Tool with executable function (extends pipy-ai's Tool)
2. **Agent Loop** - Outer/inner loop for tool execution and steering
3. **Agent Events** - Lifecycle events (turn_start, tool_execution_update, etc.)
4. **Agent Class** - State management, subscriptions, queues

### What pipy-agent imports from pipy-ai:
- `ThinkingLevel` (including OFF)
- `Message`, `UserMessage`, `AssistantMessage`, `ToolResultMessage`
- `TextContent`, `ImageContent`, `ThinkingContent`, `ToolCall`
- `Context`, `Tool`
- `stream`, `astream`, `SimpleStreamOptions`
- `AssistantMessageEvent` (all streaming events)
- `AbortSignal`, `AbortController`, `AbortError`

---

## Package Structure

```
~/src/witt3rd/pipy/agent/
├── pyproject.toml
├── README.md
├── src/pipy_agent/
│   ├── __init__.py       # Public API
│   ├── types.py          # AgentTool, AgentEvent, AgentState (agent-specific only)
│   ├── agent.py          # Agent class
│   └── loop.py           # agent_loop(), agent_loop_continue()
└── tests/
    ├── test_types.py
    ├── test_loop.py
    └── test_agent.py
```

---

## Type System (`types.py`)

Only agent-specific types. Everything else imported from pipy-ai.

```python
"""Agent-specific types. LLM types imported from pipy-ai."""

from typing import Any, Callable, Awaitable, TypeVar, Generic
from pydantic import BaseModel, Field

# Import ALL LLM types from pipy-ai (no redefinition!)
from pipy_ai import (
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
    # Cancellation
    AbortSignal,
    AbortController,
    AbortError,
)

T = TypeVar("T")


# === Agent Tool ===

class AgentToolResult(BaseModel, Generic[T]):
    """Result from tool execution."""
    content: list[TextContent | ImageContent] = Field(default_factory=list)
    details: T | None = None

    class Config:
        arbitrary_types_allowed = True


# Callback for streaming tool updates
AgentToolUpdateCallback = Callable[[AgentToolResult], None]


class AgentTool(BaseModel):
    """Tool with executable function.
    
    Extends pipy-ai's Tool concept with:
    - label: Human-readable name for UI
    - execute: Async function to run the tool
    """
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema
    label: str = ""  # UI display name
    
    class Config:
        arbitrary_types_allowed = True

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
            async def execute(self, tool_call_id, params, signal, on_update):
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
    system_prompt: str = ""
    model: str = ""  # Model identifier (e.g., "anthropic/claude-sonnet-4-5")
    thinking_level: ThinkingLevel = ThinkingLevel.OFF
    tools: list[AgentTool] = Field(default_factory=list)
    messages: list[AgentMessage] = Field(default_factory=list)
    is_streaming: bool = False
    stream_message: AssistantMessage | None = None
    pending_tool_calls: set[str] = Field(default_factory=set)
    error: str | None = None

    class Config:
        arbitrary_types_allowed = True


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
    model: str  # Model identifier
    
    # Stream options (passed to pipy-ai)
    temperature: float | None = None
    max_tokens: int | None = None
    reasoning: ThinkingLevel | None = None
    session_id: str | None = None
    api_key: str | None = None

    class Config:
        arbitrary_types_allowed = True


# Type aliases for callbacks (set on config instance, not serialized)
ConvertToLlmFn = Callable[[list[AgentMessage]], list[Message]]
TransformContextFn = Callable[[list[AgentMessage], AbortSignal | None], Awaitable[list[AgentMessage]]]
GetApiKeyFn = Callable[[str], Awaitable[str | None] | str | None]
GetMessagesFn = Callable[[], Awaitable[list[AgentMessage]]]
```

---

## Agent Loop (`loop.py`)

```python
"""Agent loop implementation using pipy-ai for LLM calls."""

from typing import AsyncIterator, Callable, Awaitable

from pipy_ai import (
    astream,
    Context,
    Message,
    AssistantMessage,
    ToolResultMessage,
    TextContent,
    SimpleStreamOptions,
    ThinkingLevel,
    AbortSignal,
)

from .types import (
    AgentMessage,
    AgentTool,
    AgentToolResult,
    AgentLoopConfig,
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
    ConvertToLlmFn,
    TransformContextFn,
    GetApiKeyFn,
    GetMessagesFn,
)


def default_convert_to_llm(messages: list[AgentMessage]) -> list[Message]:
    """Default: keep only LLM-compatible messages."""
    return [m for m in messages if m.role in ("user", "assistant", "toolResult")]


async def agent_loop(
    prompts: list[AgentMessage],
    *,
    system_prompt: str = "",
    messages: list[AgentMessage] | None = None,
    tools: list[AgentTool] | None = None,
    config: AgentLoopConfig,
    signal: AbortSignal | None = None,
    convert_to_llm: ConvertToLlmFn | None = None,
    transform_context: TransformContextFn | None = None,
    get_api_key: GetApiKeyFn | None = None,
    get_steering_messages: GetMessagesFn | None = None,
    get_follow_up_messages: GetMessagesFn | None = None,
) -> AsyncIterator[AgentEvent]:
    """Run agent loop with new prompt messages.
    
    Args:
        prompts: New messages to add (typically user message)
        system_prompt: System prompt for LLM
        messages: Existing conversation messages
        tools: Available tools
        config: Loop configuration (model, temperature, etc.)
        signal: Cancellation signal
        convert_to_llm: Convert AgentMessage[] to Message[] for LLM
        transform_context: Transform context before LLM call (e.g., pruning)
        get_api_key: Resolve API key dynamically
        get_steering_messages: Get messages to inject mid-run
        get_follow_up_messages: Get messages to process after completion
    
    Yields:
        AgentEvent for UI updates
    
    Example:
        async for event in agent_loop(
            [UserMessage(content="Hello")],
            system_prompt="You are helpful.",
            tools=[weather_tool],
            config=AgentLoopConfig(model="anthropic/claude-sonnet-4-5"),
        ):
            if event.type == "message_update":
                print(event.message.text, end="")
    """
    convert = convert_to_llm or default_convert_to_llm
    current_messages = list(messages or []) + list(prompts)
    new_messages: list[AgentMessage] = list(prompts)
    
    yield AgentStartEvent()
    yield TurnStartEvent()
    
    # Emit events for prompt messages
    for prompt in prompts:
        yield MessageStartEvent(message=prompt)
        yield MessageEndEvent(message=prompt)
    
    # Run the loop
    async for event in _run_loop(
        system_prompt=system_prompt,
        messages=current_messages,
        new_messages=new_messages,
        tools=tools,
        config=config,
        signal=signal,
        convert_to_llm=convert,
        transform_context=transform_context,
        get_api_key=get_api_key,
        get_steering_messages=get_steering_messages,
        get_follow_up_messages=get_follow_up_messages,
    ):
        yield event


async def agent_loop_continue(
    *,
    system_prompt: str = "",
    messages: list[AgentMessage],
    tools: list[AgentTool] | None = None,
    config: AgentLoopConfig,
    signal: AbortSignal | None = None,
    convert_to_llm: ConvertToLlmFn | None = None,
    transform_context: TransformContextFn | None = None,
    get_api_key: GetApiKeyFn | None = None,
    get_steering_messages: GetMessagesFn | None = None,
    get_follow_up_messages: GetMessagesFn | None = None,
) -> AsyncIterator[AgentEvent]:
    """Continue agent loop from existing context (for retry)."""
    if not messages:
        raise ValueError("Cannot continue: no messages")
    if messages[-1].role == "assistant":
        raise ValueError("Cannot continue from assistant message")
    
    convert = convert_to_llm or default_convert_to_llm
    
    yield AgentStartEvent()
    yield TurnStartEvent()
    
    async for event in _run_loop(
        system_prompt=system_prompt,
        messages=list(messages),
        new_messages=[],
        tools=tools,
        config=config,
        signal=signal,
        convert_to_llm=convert,
        transform_context=transform_context,
        get_api_key=get_api_key,
        get_steering_messages=get_steering_messages,
        get_follow_up_messages=get_follow_up_messages,
    ):
        yield event


async def _run_loop(
    system_prompt: str,
    messages: list[AgentMessage],
    new_messages: list[AgentMessage],
    tools: list[AgentTool] | None,
    config: AgentLoopConfig,
    signal: AbortSignal | None,
    convert_to_llm: ConvertToLlmFn,
    transform_context: TransformContextFn | None,
    get_api_key: GetApiKeyFn | None,
    get_steering_messages: GetMessagesFn | None,
    get_follow_up_messages: GetMessagesFn | None,
) -> AsyncIterator[AgentEvent]:
    """Main loop logic."""
    first_turn = True
    pending: list[AgentMessage] = []
    
    # Check for steering at start
    if get_steering_messages:
        pending = await get_steering_messages()
    
    # Outer loop: continues when follow-up messages arrive
    while True:
        has_tool_calls = True
        steering_after_tools: list[AgentMessage] | None = None
        
        # Inner loop: process tool calls and steering
        while has_tool_calls or pending:
            if not first_turn:
                yield TurnStartEvent()
            first_turn = False
            
            # Process pending messages
            for msg in pending:
                yield MessageStartEvent(message=msg)
                yield MessageEndEvent(message=msg)
                messages.append(msg)
                new_messages.append(msg)
            pending = []
            
            # Stream assistant response
            assistant_msg, events = await _stream_response(
                system_prompt, messages, tools, config, signal,
                convert_to_llm, transform_context, get_api_key,
            )
            for event in events:
                yield event
            new_messages.append(assistant_msg)
            
            if assistant_msg.stop_reason in ("error", "aborted"):
                yield TurnEndEvent(message=assistant_msg, tool_results=[])
                yield AgentEndEvent(messages=new_messages)
                return
            
            # Execute tool calls
            tool_calls = [c for c in assistant_msg.content if c.type == "toolCall"]
            has_tool_calls = len(tool_calls) > 0
            
            tool_results: list[ToolResultMessage] = []
            if has_tool_calls:
                async for item in _execute_tools(
                    tools, assistant_msg, signal, get_steering_messages
                ):
                    if isinstance(item, ToolResultMessage):
                        tool_results.append(item)
                        messages.append(item)
                        new_messages.append(item)
                    elif isinstance(item, list):  # Steering
                        steering_after_tools = item
                    else:
                        yield item
            
            yield TurnEndEvent(message=assistant_msg, tool_results=tool_results)
            
            # Get more steering
            if steering_after_tools:
                pending = steering_after_tools
            elif get_steering_messages:
                pending = await get_steering_messages()
        
        # Check for follow-up
        if get_follow_up_messages:
            follow_up = await get_follow_up_messages()
            if follow_up:
                pending = follow_up
                continue
        break
    
    yield AgentEndEvent(messages=new_messages)


async def _stream_response(
    system_prompt: str,
    messages: list[AgentMessage],
    tools: list[AgentTool] | None,
    config: AgentLoopConfig,
    signal: AbortSignal | None,
    convert_to_llm: ConvertToLlmFn,
    transform_context: TransformContextFn | None,
    get_api_key: GetApiKeyFn | None,
) -> tuple[AssistantMessage, list[AgentEvent]]:
    """Stream assistant response using pipy-ai."""
    events: list[AgentEvent] = []
    
    # Transform context if configured
    ctx_messages = messages
    if transform_context:
        ctx_messages = await transform_context(messages, signal)
    
    # Convert to LLM messages
    llm_messages = convert_to_llm(ctx_messages)
    
    # Build pipy-ai context
    context = Context(
        system_prompt=system_prompt,
        messages=llm_messages,
        tools=[t.to_tool() for t in (tools or [])],
    )
    
    # Resolve API key
    api_key = config.api_key
    if get_api_key:
        resolved = await get_api_key(config.model.split("/")[0])
        if resolved:
            api_key = resolved
    
    # Build options
    reasoning = config.reasoning if config.reasoning != ThinkingLevel.OFF else None
    options = SimpleStreamOptions(
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        reasoning=reasoning,
        session_id=config.session_id,
        api_key=api_key,
    )
    
    # Stream from pipy-ai
    partial: AssistantMessage | None = None
    started = False
    
    async for event in astream(config.model, context, options):
        if signal and signal.aborted:
            raise AbortError("Aborted")
        
        if event.type == "start":
            partial = event.partial
            messages.append(partial)
            started = True
            events.append(MessageStartEvent(message=partial))
        
        elif event.type in ("text_delta", "thinking_delta", "toolcall_delta"):
            if partial:
                partial = event.partial
                messages[-1] = partial
                events.append(MessageUpdateEvent(
                    message=partial,
                    assistant_event=event,
                ))
        
        elif event.type in ("done", "error"):
            final = event.message if event.type == "done" else event.error
            if started:
                messages[-1] = final
            else:
                messages.append(final)
                events.append(MessageStartEvent(message=final))
            events.append(MessageEndEvent(message=final))
            return final, events
    
    raise RuntimeError("Stream ended unexpectedly")


async def _execute_tools(
    tools: list[AgentTool] | None,
    assistant_msg: AssistantMessage,
    signal: AbortSignal | None,
    get_steering: GetMessagesFn | None,
) -> AsyncIterator[AgentEvent | ToolResultMessage | list[AgentMessage]]:
    """Execute tool calls."""
    from pipy_ai import AbortError
    
    tool_calls = [c for c in assistant_msg.content if c.type == "toolCall"]
    
    for i, tc in enumerate(tool_calls):
        tool = next((t for t in (tools or []) if t.name == tc.name), None)
        
        yield ToolExecutionStartEvent(
            tool_call_id=tc.id,
            tool_name=tc.name,
            args=tc.arguments,
        )
        
        result: AgentToolResult
        is_error = False
        
        try:
            if not tool:
                raise ValueError(f"Tool not found: {tc.name}")
            
            def on_update(partial: AgentToolResult):
                pass  # Could queue for yielding
            
            result = await tool.execute(tc.id, tc.arguments, signal, on_update)
        
        except Exception as e:
            result = AgentToolResult(content=[TextContent(text=str(e))])
            is_error = True
        
        yield ToolExecutionEndEvent(
            tool_call_id=tc.id,
            tool_name=tc.name,
            result=result,
            is_error=is_error,
        )
        
        tool_result = ToolResultMessage(
            tool_call_id=tc.id,
            tool_name=tc.name,
            content=result.content,
            details=result.details,
            is_error=is_error,
        )
        
        yield MessageStartEvent(message=tool_result)
        yield MessageEndEvent(message=tool_result)
        yield tool_result
        
        # Check steering
        if get_steering:
            steering = await get_steering()
            if steering:
                yield steering
                # Skip remaining
                for skip in tool_calls[i+1:]:
                    yield ToolExecutionStartEvent(
                        tool_call_id=skip.id,
                        tool_name=skip.name,
                        args=skip.arguments,
                    )
                    skip_result = AgentToolResult(
                        content=[TextContent(text="Skipped")]
                    )
                    yield ToolExecutionEndEvent(
                        tool_call_id=skip.id,
                        tool_name=skip.name,
                        result=skip_result,
                        is_error=True,
                    )
                    skip_msg = ToolResultMessage(
                        tool_call_id=skip.id,
                        tool_name=skip.name,
                        content=skip_result.content,
                        is_error=True,
                    )
                    yield MessageStartEvent(message=skip_msg)
                    yield MessageEndEvent(message=skip_msg)
                    yield skip_msg
                break
```

---

## Agent Class (`agent.py`)

```python
"""Agent class with state management."""

import asyncio
from typing import Callable

from pipy_ai import (
    UserMessage,
    AssistantMessage,
    ImageContent,
    TextContent,
    ThinkingLevel,
    AbortController,
    Message,
)

from .types import (
    AgentMessage,
    AgentState,
    AgentTool,
    AgentEvent,
    AgentEndEvent,
    AgentLoopConfig,
    ConvertToLlmFn,
    TransformContextFn,
    GetApiKeyFn,
)
from .loop import agent_loop, agent_loop_continue, default_convert_to_llm


class Agent:
    """Agent with state management, events, and message queues.
    
    Example:
        agent = Agent(model="anthropic/claude-sonnet-4-5")
        agent.set_system_prompt("You are helpful.")
        agent.set_tools([weather_tool])
        
        agent.subscribe(lambda e: print(e.type))
        
        await agent.prompt("What's the weather?")
    """
    
    def __init__(
        self,
        model: str = "anthropic/claude-sonnet-4-5",
        system_prompt: str = "",
        tools: list[AgentTool] | None = None,
        convert_to_llm: ConvertToLlmFn | None = None,
        transform_context: TransformContextFn | None = None,
        get_api_key: GetApiKeyFn | None = None,
        steering_mode: str = "one-at-a-time",
        follow_up_mode: str = "one-at-a-time",
        session_id: str | None = None,
    ):
        self._state = AgentState(
            model=model,
            system_prompt=system_prompt,
            tools=tools or [],
        )
        self._listeners: set[Callable[[AgentEvent], None]] = set()
        self._abort: AbortController | None = None
        self._convert_to_llm = convert_to_llm or default_convert_to_llm
        self._transform_context = transform_context
        self._get_api_key = get_api_key
        self._steering_queue: list[AgentMessage] = []
        self._follow_up_queue: list[AgentMessage] = []
        self._steering_mode = steering_mode
        self._follow_up_mode = follow_up_mode
        self._session_id = session_id
    
    @property
    def state(self) -> AgentState:
        return self._state
    
    # === State Mutators ===
    
    def set_system_prompt(self, prompt: str):
        self._state.system_prompt = prompt
    
    def set_model(self, model: str):
        self._state.model = model
    
    def set_thinking_level(self, level: ThinkingLevel):
        self._state.thinking_level = level
    
    def set_tools(self, tools: list[AgentTool]):
        self._state.tools = tools
    
    def replace_messages(self, messages: list[AgentMessage]):
        self._state.messages = list(messages)
    
    def append_message(self, message: AgentMessage):
        self._state.messages.append(message)
    
    def clear_messages(self):
        self._state.messages = []
    
    # === Events ===
    
    def subscribe(self, fn: Callable[[AgentEvent], None]) -> Callable[[], None]:
        self._listeners.add(fn)
        return lambda: self._listeners.discard(fn)
    
    def _emit(self, event: AgentEvent):
        for fn in self._listeners:
            fn(event)
    
    # === Queues ===
    
    def steer(self, message: AgentMessage):
        """Queue steering message to interrupt mid-run."""
        self._steering_queue.append(message)
    
    def follow_up(self, message: AgentMessage):
        """Queue follow-up message for after completion."""
        self._follow_up_queue.append(message)
    
    def clear_queues(self):
        self._steering_queue = []
        self._follow_up_queue = []
    
    # === Control ===
    
    def abort(self):
        if self._abort:
            self._abort.abort()
    
    def reset(self):
        self._state.messages = []
        self._state.is_streaming = False
        self._state.error = None
        self.clear_queues()
    
    # === Prompt ===
    
    async def prompt(
        self,
        input: str | AgentMessage | list[AgentMessage],
        images: list[ImageContent] | None = None,
    ):
        """Send a prompt."""
        if self._state.is_streaming:
            raise RuntimeError("Already streaming. Use steer() or wait.")
        
        if isinstance(input, list):
            msgs = input
        elif isinstance(input, str):
            content = [TextContent(text=input)]
            if images:
                content.extend(images)
            msgs = [UserMessage(content=content)]
        else:
            msgs = [input]
        
        await self._run(msgs)
    
    async def continue_(self):
        """Continue from current context."""
        if self._state.is_streaming:
            raise RuntimeError("Already streaming.")
        if not self._state.messages:
            raise ValueError("No messages to continue from")
        if self._state.messages[-1].role == "assistant":
            raise ValueError("Cannot continue from assistant message")
        
        await self._run(None)
    
    async def _run(self, prompts: list[AgentMessage] | None):
        self._abort = AbortController()
        self._state.is_streaming = True
        self._state.error = None
        
        config = AgentLoopConfig(
            model=self._state.model,
            reasoning=self._state.thinking_level,
            session_id=self._session_id,
        )
        
        try:
            if prompts:
                stream = agent_loop(
                    prompts,
                    system_prompt=self._state.system_prompt,
                    messages=self._state.messages,
                    tools=self._state.tools,
                    config=config,
                    signal=self._abort.signal,
                    convert_to_llm=self._convert_to_llm,
                    transform_context=self._transform_context,
                    get_api_key=self._get_api_key,
                    get_steering_messages=self._get_steering,
                    get_follow_up_messages=self._get_follow_up,
                )
            else:
                stream = agent_loop_continue(
                    system_prompt=self._state.system_prompt,
                    messages=self._state.messages,
                    tools=self._state.tools,
                    config=config,
                    signal=self._abort.signal,
                    convert_to_llm=self._convert_to_llm,
                    transform_context=self._transform_context,
                    get_api_key=self._get_api_key,
                    get_steering_messages=self._get_steering,
                    get_follow_up_messages=self._get_follow_up,
                )
            
            async for event in stream:
                self._update_state(event)
                self._emit(event)
        
        except Exception as e:
            self._state.error = str(e)
            self._emit(AgentEndEvent())
        
        finally:
            self._state.is_streaming = False
            self._abort = None
    
    def _update_state(self, event: AgentEvent):
        match event.type:
            case "message_start":
                if hasattr(event, 'message') and event.message.role == "assistant":
                    self._state.stream_message = event.message
            case "message_update":
                self._state.stream_message = event.message
            case "message_end":
                self._state.stream_message = None
                self.append_message(event.message)
            case "tool_execution_start":
                self._state.pending_tool_calls.add(event.tool_call_id)
            case "tool_execution_end":
                self._state.pending_tool_calls.discard(event.tool_call_id)
            case "agent_end":
                self._state.is_streaming = False
    
    async def _get_steering(self) -> list[AgentMessage]:
        if not self._steering_queue:
            return []
        if self._steering_mode == "one-at-a-time":
            return [self._steering_queue.pop(0)]
        msgs = self._steering_queue
        self._steering_queue = []
        return msgs
    
    async def _get_follow_up(self) -> list[AgentMessage]:
        if not self._follow_up_queue:
            return []
        if self._follow_up_mode == "one-at-a-time":
            return [self._follow_up_queue.pop(0)]
        msgs = self._follow_up_queue
        self._follow_up_queue = []
        return msgs
```

---

## Public API (`__init__.py`)

```python
"""
pipy-agent - Agent framework built on pipy-ai.

Example:
    from pipy_agent import Agent, tool, AgentToolResult
    from pipy_ai import TextContent
    
    @tool(name="greet", description="Greet someone", parameters={...})
    async def greet(tool_call_id, params, signal, on_update):
        return AgentToolResult(content=[TextContent(text=f"Hello {params['name']}!")])
    
    agent = Agent(model="anthropic/claude-sonnet-4-5")
    agent.set_tools([greet])
    await agent.prompt("Greet Alice")
"""

__version__ = "0.1.0"

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
```

---

## pyproject.toml

```toml
[project]
name = "pipy-agent"
version = "0.1.0"
description = "Agent framework with tool execution, built on pipy-ai."
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.11"
authors = [{ name = "Donald Thompson", email = "donald@witt3rd.com" }]
keywords = ["llm", "ai", "agent", "tools", "pipy"]

dependencies = [
    "pipy-ai>=0.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.5.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/pipy_agent"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

---

## Summary: Clean Split

### pipy-ai owns:
- All LLM types (Message, Content, Tool, Context)
- ThinkingLevel (including OFF)
- Streaming (events, stream/astream)
- AbortSignal/Controller/Error
- Model registry

### pipy-agent owns:
- AgentTool (Tool + execute)
- AgentToolResult
- Agent loop logic
- Agent events (lifecycle)
- Agent class (state, queues)
- @tool decorator

### No duplication:
- pipy-agent imports everything from pipy-ai
- No type redefinitions
- Clear dependency direction: pipy-agent → pipy-ai
