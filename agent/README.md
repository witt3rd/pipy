# pipy-agent

Agent framework with tool execution, built on [pipy-ai](https://github.com/witt3rd/pipy-ai).

## Installation

```bash
pip install pipy-agent
```

## Quick Start

```python
from pipy_agent import Agent, tool, AgentToolResult, TextContent

# Define a tool
@tool(
    name="get_weather",
    description="Get weather for a location",
    parameters={
        "type": "object",
        "properties": {"location": {"type": "string"}},
        "required": ["location"]
    }
)
async def get_weather(tool_call_id, params, signal, on_update):
    location = params["location"]
    return AgentToolResult(
        content=[TextContent(text=f"Weather in {location}: Sunny, 22°C")],
        details={"temp": 22, "condition": "sunny"}
    )

# Create agent
agent = Agent(model="anthropic/claude-sonnet-4-5")
agent.set_system_prompt("You are a helpful weather assistant.")
agent.set_tools([get_weather])

# Subscribe to events
def on_event(event):
    if event.type == "message_update":
        print(event.message.text, end="", flush=True)
    elif event.type == "tool_execution_start":
        print(f"\n[Running {event.tool_name}...]")

agent.subscribe(on_event)

# Run
await agent.prompt("What's the weather in Tokyo?")
```

## Features

### Tool Execution

Define tools with the `@tool` decorator:

```python
@tool(
    name="calculate",
    description="Evaluate a math expression",
    parameters={
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "Math expression"}
        },
        "required": ["expression"]
    },
    label="Calculator"
)
async def calculate(tool_call_id, params, signal, on_update):
    result = eval(params["expression"])  # Use safe eval in production!
    return AgentToolResult(
        content=[TextContent(text=f"Result: {result}")],
        details={"result": result}
    )
```

### Streaming Updates

Tools can stream partial results:

```python
@tool(name="long_task", description="...", parameters={...})
async def long_task(tool_call_id, params, signal, on_update):
    for i in range(10):
        if signal and signal.aborted:
            break
        # Report progress
        on_update(AgentToolResult(
            content=[TextContent(text=f"Progress: {i*10}%")]
        ))
        await asyncio.sleep(1)
    
    return AgentToolResult(content=[TextContent(text="Done!")])
```

### Steering

Interrupt the agent mid-execution:

```python
# Start a long task
task = asyncio.create_task(agent.prompt("Analyze this dataset..."))

# User interrupts
await asyncio.sleep(2)
agent.steer(UserMessage(content="Actually, focus on column A only"))

await task
```

### Follow-up

Queue messages for after completion:

```python
agent.follow_up(UserMessage(content="Now summarize your findings"))
await agent.prompt("Analyze the data")
# Agent will process follow-up automatically after analysis
```

### Events

Subscribe to lifecycle events:

```python
def on_event(event):
    match event.type:
        case "agent_start":
            print("Agent started")
        case "turn_start":
            print("New turn")
        case "message_start":
            print(f"Message from {event.message.role}")
        case "message_update":
            print(event.message.text, end="")
        case "message_end":
            print()
        case "tool_execution_start":
            print(f"Running {event.tool_name}...")
        case "tool_execution_end":
            print(f"Tool finished (error={event.is_error})")
        case "turn_end":
            print(f"Turn ended with {len(event.tool_results)} tool results")
        case "agent_end":
            print(f"Agent finished with {len(event.messages)} new messages")

agent.subscribe(on_event)
```

## Low-Level API

Use the loop functions directly for more control:

```python
from pipy_agent import agent_loop, AgentLoopConfig, UserMessage

config = AgentLoopConfig(
    model="anthropic/claude-sonnet-4-5",
    temperature=0.7,
    max_tokens=4096,
)

async for event in agent_loop(
    [UserMessage(content="Hello!")],
    system_prompt="You are helpful.",
    tools=[my_tool],
    config=config,
):
    print(event.type)
```

## Architecture

pipy-agent is built on pipy-ai and adds:

- **AgentTool**: Tool with executable function (extends pipy-ai's Tool)
- **Agent Loop**: Nested loops for tool execution and steering
- **Agent Events**: Lifecycle events for UI updates
- **Agent Class**: State management with subscriptions

```
┌─────────────────────────────────────────────┐
│                 pipy-ai                      │
│  • Message types • Streaming • AbortSignal  │
└─────────────────────────────────────────────┘
                      ▲
                      │
┌─────────────────────────────────────────────┐
│                pipy-agent                    │
│  • AgentTool • Agent Loop • Agent Class     │
└─────────────────────────────────────────────┘
```

## Acknowledgments

This library is a Python port inspired by the excellent TypeScript work of **Mario Zechner** ([@badlogic](https://github.com/badlogic)):

- **[pi-mono](https://github.com/mariozechner/pi)** - The original monorepo containing `@mariozechner/pi-agent`
- **[pi](https://github.com/mariozechner/pi)** - Mario's AI coding assistant built on these foundations

The agent loop architecture, tool execution patterns, and steering/follow-up queues in pipy-agent closely follow Mario's elegant design. Thank you Mario for the inspiration and for open-sourcing your work! 🙏

## License

MIT
