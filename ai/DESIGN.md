# pipy-ai Design Document

This document explains the architecture and design decisions behind pipy-ai.

## Origin

pipy-ai is a Python port of [@mariozechner/pi-ai](https://github.com/mariozechner/pi), adapted to use [LiteLLM](https://github.com/BerriAI/litellm) as the backend and [models.dev](https://models.dev) for model metadata.

## Design Goals

1. **Sync-first API** - Python convention: `complete()` is sync, `acomplete()` is async
2. **Rich types** - Pydantic models for validation and IDE support
3. **Streaming** - First-class support for streaming responses
4. **Provider agnostic** - LiteLLM handles 100+ providers
5. **Model discovery** - Query capabilities, costs, limits via models.dev

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Public API                           │
│  complete() / stream() / quick() / ctx() / user()          │
│  acomplete() / astream() (async variants)                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        Provider                             │
│  LiteLLMProvider - adapts LiteLLM to our types             │
│  • Converts Context → LiteLLM messages                      │
│  • Converts LiteLLM response → AssistantMessage            │
│  • Handles streaming chunk → Event conversion               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        LiteLLM                              │
│  litellm.completion() / litellm.acompletion()              │
│  Handles actual API calls to providers                      │
└─────────────────────────────────────────────────────────────┘
```

## Module Structure

```
src/pipy_ai/
├── __init__.py      # Public exports
├── types.py         # Pydantic models (Message, Content, Tool, Context, etc.)
├── stream.py        # Streaming event types
├── api.py           # User-facing functions (complete, stream, quick, etc.)
├── provider.py      # LiteLLM adapter
├── abort.py         # AbortSignal/Controller for cancellation
├── cli/             # CLI commands
│   └── main.py
└── registry/        # Model registry (models.dev)
    ├── schema.py    # Model, ModelCost, ModelCapabilities
    ├── sync.py      # Fetch from models.dev
    └── registry.py  # Query interface
```

## Type System

### Content Types
```python
TextContent      # text, cache_control
ThinkingContent  # thinking, signature
ImageContent     # url or base64 data
ToolCall         # id, name, arguments
```

### Message Types
```python
UserMessage        # role="user", content: list[Text|Image]
AssistantMessage   # role="assistant", content: list[Text|Thinking|ToolCall]
ToolResultMessage  # role="toolResult", tool_call_id, content
```

### Context
```python
Context(
    system_prompt="...",
    messages=[...],
    tools=[...],        # Optional tool definitions
)
```

## Streaming Events

Events form a predictable sequence:

```
start
├── text_start → text_delta* → text_end
├── thinking_start → thinking_delta* → thinking_end
└── toolcall_start → toolcall_delta* → toolcall_end
done | error
```

Each event carries:
- `partial`: Current AssistantMessage state (accumulating)
- Event-specific data (delta text, tool call info, etc.)

## Key Design Decisions

### 1. Sync-First API

Python developers expect sync by default:
```python
# Primary API
result = complete(model, context)

# Async variant (suffix convention)
result = await acomplete(model, context)
```

### 2. Pydantic Over Dataclasses

- Runtime validation catches errors early
- JSON serialization built-in
- IDE autocomplete works better
- `.model_dump()` for clean export

### 3. LiteLLM as Backend

- Supports 100+ providers with unified interface
- Active maintenance and community
- Handles auth, retries, rate limits
- We adapt its types to our cleaner interface

### 4. models.dev for Metadata

- Community-maintained model database
- Costs, limits, capabilities
- Auto-sync with 7-day cache
- Query by provider, capability, modality

### 5. AbortSignal for Cancellation

Borrowed from JavaScript's pattern:
```python
controller = AbortController()
# Pass signal to operations
stream(..., signal=controller.signal)
# Cancel from elsewhere
controller.abort()
```

### 6. ThinkingLevel Enum

Unified interface for reasoning models:
```python
class ThinkingLevel(str, Enum):
    OFF = "off"
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"
```

Maps to provider-specific parameters internally.

## Data Storage

```
~/.pipy/
└── models.json    # Cached model registry (auto-synced)
```

Shared directory for future pipy-* packages.

## Relationship to pipy-agent

pipy-ai is the foundation. pipy-agent builds on top:

| pipy-ai | pipy-agent |
|---------|------------|
| Message types | AgentTool (Tool + execute) |
| Context | Agent loop |
| stream() | Tool execution |
| AbortSignal | Steering/follow-up |

pipy-agent imports from pipy-ai - no type duplication.

## Future Considerations

1. **Caching** - Response caching with cache_control
2. **Cost tracking** - Accumulate usage across calls
3. **Middleware** - Request/response interceptors
4. **More providers** - Provider-specific optimizations
