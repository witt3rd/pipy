# pipy-agent Design Document

This document explains the architecture and design decisions behind pipy-agent.

## Origin

pipy-agent is a Python port of [@mariozechner/pi-agent](https://github.com/mariozechner/pi), built on top of [pipy-ai](https://github.com/witt3rd/pipy-ai).

## Design Goals

1. **Tool execution** - Define and execute tools with streaming updates
2. **Agent loop** - Handle multi-turn conversations with tool calls
3. **Steering** - Interrupt agent mid-execution with new instructions
4. **Follow-up** - Queue messages for after completion
5. **Events** - Fine-grained lifecycle events for UI updates

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Agent Class                            │
│  • State management (messages, tools, streaming status)     │
│  • Event subscription system                                │
│  • Steering and follow-up queues                           │
│  • Abort control                                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Agent Loop                             │
│  • Outer loop: follow-up messages                          │
│  • Inner loop: tool calls + steering                       │
│  • Tool execution with partial updates                      │
│  • Event emission                                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       pipy-ai                               │
│  • astream() for LLM calls                                 │
│  • Message/Content types                                    │
│  • AbortSignal for cancellation                            │
└─────────────────────────────────────────────────────────────┘
```

## Module Structure

```
src/pipy_agent/
├── __init__.py      # Public exports (+ re-exports from pipy-ai)
├── types.py         # Agent-specific types only
├── loop.py          # agent_loop(), agent_loop_continue()
└── agent.py         # Agent class
```

## The Agent Loop

The loop has two nested levels:

```
┌─────────────────────────────────────────────────────────────┐
│                      OUTER LOOP                             │
│  Continues when follow-up messages arrive after completion  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                    INNER LOOP                          │ │
│  │  Processes tool calls and steering messages            │ │
│  │                                                        │ │
│  │  1. Process pending messages (steering/follow-up)      │ │
│  │  2. Stream assistant response (via pipy-ai)            │ │
│  │  3. Execute tool calls (with steering check after each)│ │
│  │  4. Check for more steering messages                   │ │
│  │  5. Repeat if has tool calls or steering               │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  Check for follow-up → if any, continue outer loop          │
└─────────────────────────────────────────────────────────────┘
```

## Type System

### What pipy-agent defines (agent-specific):

```python
AgentTool          # Tool with execute() method
AgentToolResult    # Execution result with content + details
AgentState         # Agent's current state
AgentLoopConfig    # Loop configuration
AgentEvent         # Lifecycle events (union of all event types)
```

### What pipy-agent imports from pipy-ai (no redefinition):

```python
Message, UserMessage, AssistantMessage, ToolResultMessage
TextContent, ImageContent, ThinkingContent, ToolCall
Context, Tool
ThinkingLevel, StopReason
AbortSignal, AbortController, AbortError
```

## AgentTool vs Tool

pipy-ai's `Tool` is just a schema (name, description, parameters).

pipy-agent's `AgentTool` adds execution:

```python
class AgentTool(BaseModel):
    name: str
    description: str
    parameters: dict        # JSON Schema
    label: str              # UI display name
    
    async def execute(self, tool_call_id, params, signal, on_update):
        # Actually run the tool
        ...
    
    def to_tool(self) -> Tool:
        # Convert to pipy-ai Tool for LLM calls
        ...
```

The `@tool` decorator makes this ergonomic:

```python
@tool(name="get_weather", description="...", parameters={...})
async def get_weather(tool_call_id, params, signal, on_update):
    return AgentToolResult(
        content=[TextContent(text="Sunny, 22°C")],
        details={"temp": 22}
    )
```

## Event System

Events provide fine-grained UI updates:

```
agent_start
└── turn_start
    ├── message_start (user message)
    ├── message_end
    ├── message_start (assistant)
    ├── message_update* (streaming)
    ├── message_end
    ├── tool_execution_start
    ├── tool_execution_update* (progress)
    ├── tool_execution_end
    ├── message_start (tool result)
    └── message_end
└── turn_end
agent_end
```

Subscribe to events:
```python
agent.subscribe(lambda e: print(e.type))
```

## Steering and Follow-up

### Steering
Interrupt the agent mid-execution:
```python
# Agent is running...
agent.steer(UserMessage(content="Actually, focus on X instead"))
# Agent receives this after current tool completes
```

### Follow-up
Queue for after completion:
```python
agent.follow_up(UserMessage(content="Now summarize"))
# Agent processes this after finishing current task
```

## Key Design Decisions

### 1. Imports from pipy-ai (No Duplication)

All LLM types come from pipy-ai:
```python
from pipy_ai import Message, Context, ThinkingLevel, AbortSignal
```

This ensures:
- Single source of truth
- No type mismatches
- Clear dependency direction

### 2. Re-exports for Convenience

pipy-agent re-exports pipy-ai types so users can import from one place:
```python
# Users can do this:
from pipy_agent import Agent, UserMessage, TextContent
# Instead of:
from pipy_agent import Agent
from pipy_ai import UserMessage, TextContent
```

### 3. Agent Class vs Loop Functions

Two levels of abstraction:

**Agent class** (high-level):
```python
agent = Agent(model="...")
agent.set_tools([...])
agent.subscribe(handler)
await agent.prompt("Hello")
```

**Loop functions** (low-level):
```python
async for event in agent_loop(prompts, config=config, tools=tools):
    handle(event)
```

### 4. Async Tool Execution

Tools are always async:
```python
async def execute(self, tool_call_id, params, signal, on_update):
    ...
```

This allows:
- Network calls
- File I/O
- Streaming updates via `on_update`
- Cancellation via `signal`

### 5. Generic AgentToolResult

```python
class AgentToolResult(BaseModel, Generic[T]):
    content: list[TextContent | ImageContent]  # For LLM
    details: T | None                           # For app
```

- `content` goes back to the LLM
- `details` is app-specific (UI display, logging, etc.)

## Relationship to pipy-ai

```
pipy-ai (foundation)
├── Types: Message, Content, Tool, Context
├── Streaming: Events, stream(), astream()
├── Cancellation: AbortSignal, AbortController
└── Registry: models.dev integration

pipy-agent (builds on top)
├── AgentTool: Tool + execute
├── Agent loop: Outer/inner loop
├── Agent class: State + subscriptions
└── Events: Lifecycle events
```

## Future Considerations

1. **Proxy support** - Route LLM calls through a server
2. **Parallel tool execution** - Run independent tools concurrently
3. **Tool streaming** - First-class support for `on_update`
4. **Checkpointing** - Save/restore agent state
5. **Middleware** - Pre/post tool execution hooks
