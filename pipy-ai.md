# pi-ai-litellm: Python AI Library Spec

**Goal**: Create a standalone Python library (publishable to PyPI) equivalent to `@mariozechner/pi-mono/packages/ai`, using LiteLLM as the backend provider abstraction and models.dev for model metadata.

---

## Package Identity

### Name

**`pipy-ai`** — Honors the pi-mono lineage while being Pythonic.

| Aspect | Value |
|--------|-------|
| PyPI name | `pipy-ai` |
| Import name | `pipy_ai` |
| CLI command | `pipy` |
| Data directory | `~/.pipy/` |
| GitHub | `github.com/yourname/pipy-ai` |

### Package Structure

```
pipy-ai/                         # Root repo
├── pyproject.toml               # Package config, dependencies
├── README.md                    # PyPI readme
├── LICENSE                      # MIT
├── src/
│   └── pipy_ai/                 # Import as: from pipy_ai import ...
│       ├── __init__.py          # Public API exports
│       ├── types.py             # Rich type system
│       ├── context.py           # Context builder
│       ├── stream.py            # Event stream
│       ├── api.py               # stream(), complete(), etc.
│       ├── provider.py          # LiteLLM provider
│       ├── registry/
│       │   ├── __init__.py
│       │   ├── schema.py        # Model, Cost, Capabilities
│       │   ├── registry.py      # ModelRegistry
│       │   ├── sync.py          # models.dev sync
│       │   └── config.py        # LiteLLM config generation
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── overflow.py      # Context overflow
│       │   └── json_parse.py    # Streaming JSON
│       └── cli/
│           ├── __init__.py
│           └── main.py          # CLI: pipy sync, pipy models, etc.
└── tests/
    ├── test_types.py
    ├── test_stream.py
    ├── test_registry.py
    └── test_api.py
```

### pyproject.toml

```toml
[project]
name = "pipy-ai"
version = "0.1.0"
description = "Streaming LLM library with rich types, models.dev integration, and LiteLLM backend. Inspired by pi-mono/ai."
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.11"
authors = [
    { name = "Your Name", email = "you@example.com" }
]
keywords = ["llm", "ai", "streaming", "litellm", "anthropic", "openai", "gemini", "pi"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
]

dependencies = [
    "litellm",           # Latest - no version pinning
    "pydantic>=2.0",     # Type validation & serialization
    "pyyaml>=6.0",
    "httpx>=0.27.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.5.0",
    "mypy>=1.10",
]

[project.scripts]
pipy = "pipy_ai.cli.main:main"

[project.urls]
Homepage = "https://github.com/yourname/pipy-ai"
Documentation = "https://github.com/yourname/pipy-ai#readme"
Repository = "https://github.com/yourname/pipy-ai"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/pipy_ai"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.mypy]
python_version = "3.11"
strict = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### Public API (`__init__.py`)

```python
"""
pipy-ai - Streaming LLM library with rich types and models.dev integration.

Inspired by @mariozechner/pi-mono/packages/ai, built for Python with LiteLLM.

Quick start:
    from pipy_ai import quick, complete, stream, ctx, user

    # One-liner
    result = quick("What is 2+2?")
    print(result.text)  # "4"

    # Standard (sync)
    result = complete("anthropic/claude-sonnet-4-5", ctx(
        user("Hello!"),
        system="You are helpful."
    ))
    print(result.text)

    # Streaming (sync)
    for event in stream(model, context):
        if event.type == "text_delta":
            print(event.delta, end="")

    # Async variants available: acomplete(), astream()
"""

__version__ = "0.1.0"

# Types (Pydantic models)
from .types import (
    # Enums
    ThinkingLevel,
    CacheRetention,
    StopReason,
    # Content
    TextContent,
    ThinkingContent,
    ImageContent,
    ToolCall,
    # Messages
    UserMessage,
    AssistantMessage,
    ToolResultMessage,
    Message,
    # Context
    Context,
    Tool,
    # Usage
    Usage,
    Cost,
    # Options
    StreamOptions,
    SimpleStreamOptions,
    ThinkingBudgets,
)

# Events
from .stream import (
    StartEvent,
    TextStartEvent,
    TextDeltaEvent,
    TextEndEvent,
    ThinkingStartEvent,
    ThinkingDeltaEvent,
    ThinkingEndEvent,
    ToolCallStartEvent,
    ToolCallDeltaEvent,
    ToolCallEndEvent,
    DoneEvent,
    ErrorEvent,
    AssistantMessageEvent,
)

# API (sync-first)
from .api import (
    # Sync (primary)
    complete,
    stream,
    complete_simple,
    stream_simple,
    quick,
    # Async variants
    acomplete,
    astream,
    acomplete_simple,
    astream_simple,
    # Builders
    user,
    ctx,
)

# Registry (models.dev)
from .registry import (
    get_model,
    get_models,
    get_registry,
    sync_models,
    estimate_cost,
    calculate_cost,
    Model,
    ModelCost,
    ModelLimits,
    ModelCapabilities,
    ModelModalities,
)

__all__ = [
    # Version
    "__version__",
    # Enums
    "ThinkingLevel",
    "CacheRetention", 
    "StopReason",
    # Content
    "TextContent",
    "ThinkingContent",
    "ImageContent",
    "ToolCall",
    # Messages
    "UserMessage",
    "AssistantMessage",
    "ToolResultMessage",
    "Message",
    # Context
    "Context",
    "Tool",
    # Usage
    "Usage",
    "Cost",
    # Options
    "StreamOptions",
    "SimpleStreamOptions",
    "ThinkingBudgets",
    # Events
    "StartEvent",
    "TextStartEvent",
    "TextDeltaEvent",
    "TextEndEvent",
    "ThinkingStartEvent",
    "ThinkingDeltaEvent",
    "ThinkingEndEvent",
    "ToolCallStartEvent",
    "ToolCallDeltaEvent",
    "ToolCallEndEvent",
    "DoneEvent",
    "ErrorEvent",
    "AssistantMessageEvent",
    # API - Sync (primary)
    "complete",
    "stream",
    "complete_simple",
    "stream_simple",
    "quick",
    # API - Async variants
    "acomplete",
    "astream",
    "acomplete_simple",
    "astream_simple",
    # API - Builders
    "user",
    "ctx",
    # Registry
    "get_model",
    "get_models",
    "get_registry",
    "sync_models",
    "estimate_cost",
    "calculate_cost",
    "Model",
    "ModelCost",
    "ModelLimits",
    "ModelCapabilities",
    "ModelModalities",
]
```

---

## Architecture Comparison

### pi-mono/ai (TypeScript)

```
src/
├── types.ts              # Rich type system (Api, Provider, Model, Message, Context, Tool, etc.)
├── api-registry.ts       # Pluggable provider registry
├── models.ts             # Model registry + cost calculation
├── models.generated.ts   # Pre-generated model database (296KB!)
├── stream.ts             # Unified streaming API
├── env-api-keys.ts       # Environment-based API key resolution
├── providers/            # Native SDK implementations
│   ├── anthropic.ts
│   ├── openai-completions.ts
│   ├── openai-responses.ts
│   ├── google.ts
│   ├── google-vertex.ts
│   ├── amazon-bedrock.ts
│   └── ...
└── utils/
    ├── event-stream.ts   # AsyncIterable event stream with result promise
    ├── json-parse.ts     # Streaming JSON parser
    ├── overflow.ts       # Context overflow handling
    └── validation.ts     # TypeBox validation
```

**Key Features:**
- **Granular streaming events**: `text_start`, `text_delta`, `text_end`, `thinking_start`, `thinking_delta`, `thinking_end`, `toolcall_start`, `toolcall_delta`, `toolcall_end`
- **AssistantMessageEventStream**: AsyncIterable with `.result()` promise for final message
- **Thinking levels**: `minimal | low | medium | high | xhigh` with configurable token budgets
- **Tool support**: Full tool calling with TypeBox schemas
- **Cache control**: `CacheRetention` enum (`none | short | long`)
- **Provider compat layer**: `OpenAICompletionsCompat` for handling provider quirks

### animus/llm (Python Current)

```
llm/
├── __init__.py           # Public API exports
├── invoke.py             # invoke(), invoke_stream(), invoke_prompt()
├── adapters/
│   ├── base.py           # FrameworkAdapter ABC, InvokeRequest/Response
│   ├── litellm.py        # LiteLLM Router implementation
│   └── anthropic_sdk.py  # Direct Anthropic SDK
├── registry/
│   ├── schema.py         # Model, Provider, Cost, Limits, Capabilities
│   ├── registry.py       # ModelRegistry singleton
│   ├── sync.py           # Sync from models.dev
│   └── generate.py       # Generate LiteLLM config
├── template.py           # Jinja2 template rendering
├── edit.py               # Line-number based file editing
└── rag.py                # RAG query helpers
```

**Key Features:**
- **Simple events**: `ThinkingEvent`, `TextEvent`, `ResultEvent`
- **LiteLLM Router**: YAML-configured model routing
- **Model registry**: Syncs from models.dev API
- **InvokeRequest/Response**: Clean but limited abstraction

---

## Gap Analysis

| Feature | pi-mono/ai | animus/llm | Gap |
|---------|------------|------------|-----|
| **Type System** | Rich (Message, Content, Tool, etc.) | Simple (InvokeRequest/Response) | Need rich message types |
| **Event Stream** | Granular events + `.result()` | Simple events | Need granular streaming |
| **Thinking** | Levels + budgets | `reasoning_effort` only | Need levels + budgets |
| **Tools** | Full TypeBox schemas | Not implemented | Need tool support |
| **Context** | `systemPrompt + messages + tools` | Prompt string | Need structured context |
| **Cache** | `CacheRetention` enum | Not exposed | Need cache control |
| **Model Registry** | Generated 296KB code | **models.dev integration** | **animus is BETTER** |
| **Provider Abstraction** | Native SDK per provider | LiteLLM unified | LiteLLM is fine |

### 🌟 models.dev Integration (KEEP & ENHANCE)

The existing models.dev integration is a **major advantage** over pi-mono/ai:

```
registry/
├── sync.py      # Fetches https://models.dev/api.json
├── generate.py  # Generates litellm_config.yaml
├── registry.py  # Runtime ModelRegistry singleton
└── schema.py    # Model, Cost, Limits, Capabilities, Modalities
```

**What models.dev provides:**
- **100+ providers**: anthropic, openai, google, mistral, groq, together, fireworks, etc.
- **Live pricing**: `cost.input`, `cost.output`, `cost.cache_read`, `cost.reasoning`
- **Token limits**: `limits.context`, `limits.output`
- **Capabilities**: `reasoning`, `tool_call`, `structured_output`, `attachment`
- **Modalities**: `input: [text, image, audio, video, pdf]`, `output: [text, image]`
- **Metadata**: `knowledge_cutoff`, `release_date`, `status`, `open_weights`

**Workflow:**
```bash
# Sync latest models from models.dev
animus llm sync-models

# Generate LiteLLM config from synced data
animus llm generate-config

# Query models
animus llm list --provider anthropic
animus llm info anthropic/claude-sonnet-4-5
```

**vs pi-mono/ai**: They generate a static 296KB TypeScript file (`models.generated.ts`) that requires code changes to update. Our approach:
1. **Always fresh**: `sync-models` pulls latest from models.dev API
2. **No code changes**: New models just work after sync
3. **Rich queries**: Filter by capability, modality, cost, etc.

---

## Proposed Architecture

```
src/pipy_ai/
├── __init__.py              # Public API exports
├── types.py                 # Rich type system (Message, Context, Tool, etc.)
├── context.py               # Context builder helpers
├── stream.py                # AssistantMessageEventStream with granular events
├── api.py                   # stream(), complete(), stream_simple(), complete_simple()
├── provider.py              # LiteLLM provider implementation
├── registry/
│   ├── __init__.py          # Registry exports
│   ├── schema.py            # Model, Cost, Limits, Capabilities, Modalities
│   ├── registry.py          # ModelRegistry singleton with rich queries
│   ├── sync.py              # Sync from models.dev API
│   └── config.py            # Generate LiteLLM router config
├── utils/
│   ├── __init__.py
│   ├── overflow.py          # Context window overflow handling
│   └── json_parse.py        # Streaming JSON parser for tool calls
└── cli/
    ├── __init__.py
    └── main.py              # CLI: pipy sync, pipy models, pipy cost
```

---

## Type System (`types.py`)

```python
"""Rich type system with Pydantic validation."""

from enum import Enum
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, Field

# === Enums ===

class ThinkingLevel(str, Enum):
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"

class CacheRetention(str, Enum):
    NONE = "none"
    SHORT = "short"
    LONG = "long"

class StopReason(str, Enum):
    STOP = "stop"
    LENGTH = "length"
    TOOL_USE = "toolUse"
    ERROR = "error"
    ABORTED = "aborted"

# === Content Types ===

class TextContent(BaseModel):
    type: Literal["text"] = "text"
    text: str = ""
    text_signature: str | None = None  # For provider-specific IDs

class ThinkingContent(BaseModel):
    type: Literal["thinking"] = "thinking"
    thinking: str = ""
    thinking_signature: str | None = None

class ImageContent(BaseModel):
    type: Literal["image"] = "image"
    data: str = ""  # Base64 encoded
    mime_type: str = "image/png"

class ToolCall(BaseModel):
    type: Literal["toolCall"] = "toolCall"
    id: str = ""
    name: str = ""
    arguments: dict[str, Any] = Field(default_factory=dict)
    thought_signature: str | None = None  # Google-specific

# Type aliases
UserContent: TypeAlias = TextContent | ImageContent
AssistantContent: TypeAlias = TextContent | ThinkingContent | ToolCall
ToolResultContent: TypeAlias = TextContent | ImageContent

# === Messages ===

class UserMessage(BaseModel):
    role: Literal["user"] = "user"
    content: str | list[UserContent] = ""
    timestamp: int = 0  # Unix ms

class AssistantMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: list[AssistantContent] = Field(default_factory=list)
    api: str = ""
    provider: str = ""
    model: str = ""
    usage: "Usage" = Field(default_factory=lambda: Usage())
    stop_reason: StopReason = StopReason.STOP
    error_message: str | None = None
    timestamp: int = 0
    
    @property
    def text(self) -> str:
        """Convenience: concatenated text content."""
        return "\n".join(
            c.text for c in self.content if isinstance(c, TextContent)
        )
    
    @property
    def thinking_text(self) -> str:
        """Convenience: concatenated thinking content."""
        return "\n".join(
            c.thinking for c in self.content if isinstance(c, ThinkingContent)
        )
    
    @property
    def tool_calls(self) -> list[ToolCall]:
        """Convenience: all tool calls."""
        return [c for c in self.content if isinstance(c, ToolCall)]

class ToolResultMessage(BaseModel):
    role: Literal["toolResult"] = "toolResult"
    tool_call_id: str = ""
    tool_name: str = ""
    content: list[ToolResultContent] = Field(default_factory=list)
    details: Any = None
    is_error: bool = False
    timestamp: int = 0

Message: TypeAlias = UserMessage | AssistantMessage | ToolResultMessage

# === Usage & Cost ===

class Cost(BaseModel):
    input: float = 0.0
    output: float = 0.0
    cache_read: float = 0.0
    cache_write: float = 0.0
    total: float = 0.0

class Usage(BaseModel):
    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write: int = 0
    total_tokens: int = 0
    cost: Cost = Field(default_factory=Cost)

# === Tools ===

class Tool(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema

# === Context ===

class Context(BaseModel):
    system_prompt: str | None = None
    messages: list[Message] = Field(default_factory=list)
    tools: list[Tool] | None = None

# === Options ===

class ThinkingBudgets(BaseModel):
    minimal: int = 1024
    low: int = 2048
    medium: int = 8192
    high: int = 16384

class StreamOptions(BaseModel):
    temperature: float | None = None
    max_tokens: int | None = None
    cache_retention: CacheRetention = CacheRetention.SHORT
    session_id: str | None = None
    headers: dict[str, str] | None = None
    api_key: str | None = None
    max_retry_delay_ms: int = 60000

class SimpleStreamOptions(StreamOptions):
    reasoning: ThinkingLevel | None = None
    thinking_budgets: ThinkingBudgets | None = None
```

---

## Event Stream (`stream.py`)

```python
"""Event stream with async iteration and result promise."""

from dataclasses import dataclass
from typing import Any, AsyncIterator, Generic, TypeVar
import asyncio

from .types import AssistantMessage, StopReason

# === Event Types ===

@dataclass
class StartEvent:
    type: str = "start"
    partial: AssistantMessage = None

@dataclass
class TextStartEvent:
    type: str = "text_start"
    content_index: int = 0
    partial: AssistantMessage = None

@dataclass
class TextDeltaEvent:
    type: str = "text_delta"
    content_index: int = 0
    delta: str = ""
    partial: AssistantMessage = None

@dataclass
class TextEndEvent:
    type: str = "text_end"
    content_index: int = 0
    content: str = ""
    partial: AssistantMessage = None

@dataclass
class ThinkingStartEvent:
    type: str = "thinking_start"
    content_index: int = 0
    partial: AssistantMessage = None

@dataclass
class ThinkingDeltaEvent:
    type: str = "thinking_delta"
    content_index: int = 0
    delta: str = ""
    partial: AssistantMessage = None

@dataclass
class ThinkingEndEvent:
    type: str = "thinking_end"
    content_index: int = 0
    content: str = ""
    partial: AssistantMessage = None

@dataclass
class ToolCallStartEvent:
    type: str = "toolcall_start"
    content_index: int = 0
    partial: AssistantMessage = None

@dataclass
class ToolCallDeltaEvent:
    type: str = "toolcall_delta"
    content_index: int = 0
    delta: str = ""
    partial: AssistantMessage = None

@dataclass
class ToolCallEndEvent:
    type: str = "toolcall_end"
    content_index: int = 0
    tool_call: Any = None
    partial: AssistantMessage = None

@dataclass
class DoneEvent:
    type: str = "done"
    reason: StopReason = StopReason.STOP
    message: AssistantMessage = None

@dataclass
class ErrorEvent:
    type: str = "error"
    reason: StopReason = StopReason.ERROR
    error: AssistantMessage = None

AssistantMessageEvent = (
    StartEvent | TextStartEvent | TextDeltaEvent | TextEndEvent |
    ThinkingStartEvent | ThinkingDeltaEvent | ThinkingEndEvent |
    ToolCallStartEvent | ToolCallDeltaEvent | ToolCallEndEvent |
    DoneEvent | ErrorEvent
)

# === Event Stream ===

class AssistantMessageEventStream:
    """Async event stream with result() promise.
    
    Usage:
        stream = provider.stream(model, context, options)
        
        # Iterate events
        async for event in stream:
            match event.type:
                case "text_delta":
                    print(event.delta, end="")
                case "done":
                    break
        
        # Or just get final result
        result = await stream.result()
    """
    
    def __init__(self):
        self._queue: asyncio.Queue[AssistantMessageEvent] = asyncio.Queue()
        self._done = False
        self._result_future: asyncio.Future[AssistantMessage] = asyncio.get_event_loop().create_future()
    
    def push(self, event: AssistantMessageEvent) -> None:
        """Push an event to the stream."""
        if self._done:
            return
        
        self._queue.put_nowait(event)
        
        if event.type == "done":
            self._done = True
            self._result_future.set_result(event.message)
        elif event.type == "error":
            self._done = True
            self._result_future.set_result(event.error)
    
    def end(self, result: AssistantMessage | None = None) -> None:
        """End the stream."""
        self._done = True
        if result and not self._result_future.done():
            self._result_future.set_result(result)
    
    async def __aiter__(self) -> AsyncIterator[AssistantMessageEvent]:
        """Async iteration over events."""
        while True:
            if self._done and self._queue.empty():
                return
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=0.1)
                yield event
                if event.type in ("done", "error"):
                    return
            except asyncio.TimeoutError:
                if self._done:
                    return
    
    async def result(self) -> AssistantMessage:
        """Get the final AssistantMessage (awaitable)."""
        return await self._result_future

    # Sync iteration for non-async contexts
    def __iter__(self):
        """Sync iteration (blocks)."""
        while True:
            if self._done and self._queue.empty():
                return
            try:
                event = self._queue.get_nowait()
                yield event
                if event.type in ("done", "error"):
                    return
            except asyncio.QueueEmpty:
                if self._done:
                    return
                import time
                time.sleep(0.01)
```

---

## Unified API (`api.py`)

```python
"""Unified API - sync-first with async variants."""

import asyncio
import time
from typing import Iterator, AsyncIterator

from .types import (
    Context,
    UserMessage,
    AssistantMessage,
    SimpleStreamOptions,
    StreamOptions,
    ThinkingLevel,
)
from .stream import AssistantMessageEvent
from .provider import LiteLLMProvider

# Default provider singleton
_provider: LiteLLMProvider | None = None


def _get_provider() -> LiteLLMProvider:
    global _provider
    if _provider is None:
        _provider = LiteLLMProvider()
    return _provider


# === Completion (sync-first) ===

def complete(
    model: str,
    context: Context,
    options: StreamOptions | None = None,
) -> AssistantMessage:
    """Complete a request (sync, blocking).
    
    Args:
        model: Model identifier (e.g., "anthropic/claude-sonnet-4-5")
        context: System prompt, messages, and optional tools
        options: Temperature, max_tokens, cache settings, etc.
    
    Returns:
        AssistantMessage with response text, usage, etc.
    
    Example:
        from pipy_ai import complete, Context, UserMessage
        
        context = Context(
            system_prompt="You are a helpful assistant.",
            messages=[UserMessage(content="Hello!")]
        )
        
        result = complete("anthropic/claude-sonnet-4-5", context)
        print(result.text)
    """
    return asyncio.run(acomplete(model, context, options))


async def acomplete(
    model: str,
    context: Context,
    options: StreamOptions | None = None,
) -> AssistantMessage:
    """Complete a request (async variant).
    
    Example:
        result = await acomplete("anthropic/claude-sonnet-4-5", context)
        print(result.text)
    """
    return await _get_provider().acomplete(model, context, options)


# === Streaming (sync-first) ===

def stream(
    model: str,
    context: Context,
    options: StreamOptions | None = None,
) -> Iterator[AssistantMessageEvent]:
    """Stream a response (sync, blocking iterator).
    
    Example:
        from pipy_ai import stream, Context, UserMessage
        
        context = Context(messages=[UserMessage(content="Write a poem.")])
        
        for event in stream("anthropic/claude-sonnet-4-5", context):
            if event.type == "text_delta":
                print(event.delta, end="", flush=True)
        print()  # newline at end
    """
    return _get_provider().stream(model, context, options)


async def astream(
    model: str,
    context: Context,
    options: StreamOptions | None = None,
) -> AsyncIterator[AssistantMessageEvent]:
    """Stream a response (async variant).
    
    Example:
        async for event in astream("anthropic/claude-sonnet-4-5", context):
            if event.type == "text_delta":
                print(event.delta, end="", flush=True)
    """
    async for event in _get_provider().astream(model, context, options):
        yield event


# === Simple variants (with reasoning) ===

def complete_simple(
    model: str,
    context: Context,
    options: SimpleStreamOptions | None = None,
) -> AssistantMessage:
    """Complete with reasoning support (sync).
    
    Example:
        from pipy_ai import complete_simple, SimpleStreamOptions, ThinkingLevel
        
        options = SimpleStreamOptions(reasoning=ThinkingLevel.HIGH)
        result = complete_simple("anthropic/claude-sonnet-4-5", context, options)
        print(result.thinking_text)  # The reasoning
        print(result.text)           # The answer
    """
    return asyncio.run(acomplete_simple(model, context, options))


async def acomplete_simple(
    model: str,
    context: Context,
    options: SimpleStreamOptions | None = None,
) -> AssistantMessage:
    """Complete with reasoning support (async)."""
    return await _get_provider().acomplete_simple(model, context, options)


def stream_simple(
    model: str,
    context: Context,
    options: SimpleStreamOptions | None = None,
) -> Iterator[AssistantMessageEvent]:
    """Stream with reasoning support (sync).
    
    Example:
        options = SimpleStreamOptions(reasoning=ThinkingLevel.HIGH)
        for event in stream_simple(model, context, options):
            match event.type:
                case "thinking_delta":
                    print(f"[thinking] {event.delta}")
                case "text_delta":
                    print(event.delta, end="")
    """
    return _get_provider().stream_simple(model, context, options)


async def astream_simple(
    model: str,
    context: Context,
    options: SimpleStreamOptions | None = None,
) -> AsyncIterator[AssistantMessageEvent]:
    """Stream with reasoning support (async)."""
    async for event in _get_provider().astream_simple(model, context, options):
        yield event


# === Convenience Functions ===

def quick(
    prompt: str,
    model: str = "anthropic/claude-sonnet-4-5",
    system: str | None = None,
    temperature: float | None = None,
    max_tokens: int = 4096,
    reasoning: ThinkingLevel | None = None,
) -> AssistantMessage:
    """Quick one-liner completion.
    
    Example:
        from pipy_ai import quick
        
        result = quick("What is 2+2?")
        print(result.text)  # "4"
        
        # With reasoning
        result = quick("Solve step by step: 127 * 843", reasoning=ThinkingLevel.HIGH)
        print(result.thinking_text)
        print(result.text)
    """
    ctx = Context(
        system_prompt=system,
        messages=[UserMessage(content=prompt, timestamp=int(time.time() * 1000))],
    )
    options = SimpleStreamOptions(
        temperature=temperature,
        max_tokens=max_tokens,
        reasoning=reasoning,
    )
    return complete_simple(model, ctx, options)


# === Context Builders ===

def user(content: str) -> UserMessage:
    """Create a user message.
    
    Example:
        from pipy_ai import Context, user, complete
        
        ctx = Context(messages=[user("What's the weather?")])
        result = complete("anthropic/claude-sonnet-4-5", ctx)
    """
    return UserMessage(content=content, timestamp=int(time.time() * 1000))


def ctx(
    *messages: UserMessage | AssistantMessage,
    system: str | None = None,
) -> Context:
    """Build a context from messages.
    
    Example:
        from pipy_ai import ctx, user, complete
        
        result = complete("anthropic/claude-sonnet-4-5", ctx(
            user("Hello!"),
            system="You are helpful."
        ))
    """
    return Context(
        system_prompt=system,
        messages=list(messages),
    )
```

---

## Registry Integration (`registry/`)

The models.dev registry powers intelligent model selection and cost tracking:

```python
"""registry/__init__.py - Public registry API."""

from .registry import get_registry, reload_registry, ModelRegistry
from .schema import Model, ModelCost, ModelLimits, ModelCapabilities, ModelModalities
from .sync import sync_models, load_models_cache
from .config import generate_router_config

# === Model Lookup ===

def get_model(name: str) -> Model | None:
    """Get model by name with smart matching.
    
    Args:
        name: Full name "anthropic/claude-sonnet-4-5" or short "claude-sonnet-4-5"
    
    Example:
        model = get_model("anthropic/claude-sonnet-4-5")
        print(f"Context: {model.limits.context}, Cost: ${model.cost.input}/1M")
    """
    return get_registry().get(name)


def get_models(
    provider: str | None = None,
    capability: str | None = None,  # "reasoning", "tool_call", "structured_output"
    modality: str | None = None,    # "image", "audio", "video", "pdf"
    min_context: int | None = None,
    max_cost_input: float | None = None,  # $/1M tokens
) -> list[Model]:
    """Query models with filters.
    
    Examples:
        from pipy_ai import get_models
        
        # All reasoning models
        get_models(capability="reasoning")
        
        # Anthropic models that accept images
        get_models(provider="anthropic", modality="image")
        
        # Cheap models with 100k+ context
        get_models(min_context=100000, max_cost_input=1.0)
    """
    registry = get_registry()
    models = registry.list_all()
    
    if provider:
        models = [m for m in models if m.provider == provider]
    if capability:
        models = [m for m in models if getattr(m.capabilities, capability, False)]
    if modality:
        models = [m for m in models if modality in m.modalities.input]
    if min_context:
        models = [m for m in models if m.limits.context >= min_context]
    if max_cost_input:
        models = [m for m in models if m.cost.input <= max_cost_input]
    
    return models


# === Cost Functions ===

def calculate_cost(model: str | Model, usage: "Usage") -> "Cost":
    """Calculate actual cost from usage after a request.
    
    Example:
        result = await complete(model, context)
        cost = calculate_cost(model, result.usage)
        print(f"Request cost: ${cost.total:.4f}")
    """
    from ..types import Cost
    
    if isinstance(model, str):
        m = get_model(model)
        if not m:
            raise ValueError(f"Unknown model: {model}")
    else:
        m = model
    
    input_cost = (m.cost.input / 1_000_000) * usage.input
    output_cost = (m.cost.output / 1_000_000) * usage.output
    cache_read_cost = (m.cost.cache_read / 1_000_000) * usage.cache_read
    cache_write_cost = (m.cost.cache_write / 1_000_000) * usage.cache_write
    
    return Cost(
        input=input_cost,
        output=output_cost,
        cache_read=cache_read_cost,
        cache_write=cache_write_cost,
        total=input_cost + output_cost + cache_read_cost + cache_write_cost,
    )


def estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int = 0,
    cached_tokens: int = 0,
) -> float:
    """Estimate cost before making a request.
    
    Example:
        # Check cost before expensive request
        est = estimate_cost("anthropic/claude-opus-4", 50000, 8000)
        if est > 1.0:
            print(f"Warning: estimated cost ${est:.2f}")
    """
    m = get_model(model)
    if not m:
        raise ValueError(f"Unknown model: {model}")
    
    input_cost = (input_tokens / 1_000_000) * m.cost.input
    output_cost = (output_tokens / 1_000_000) * m.cost.output
    cache_savings = (cached_tokens / 1_000_000) * (m.cost.input - m.cost.cache_read)
    
    return input_cost + output_cost - cache_savings


__all__ = [
    # Registry
    "get_registry",
    "reload_registry",
    "ModelRegistry",
    # Lookup
    "get_model",
    "get_models",
    # Cost
    "calculate_cost",
    "estimate_cost",
    # Sync
    "sync_models",
    "load_models_cache",
    "generate_router_config",
    # Schema
    "Model",
    "ModelCost",
    "ModelLimits",
    "ModelCapabilities",
    "ModelModalities",
]
```

### Registry Schema (from models.dev)

```python
@dataclass
class ModelCost:
    input: float = 0.0        # $/1M tokens
    output: float = 0.0       # $/1M tokens
    cache_read: float = 0.0   # $/1M tokens (prompt caching)
    cache_write: float = 0.0  # $/1M tokens
    reasoning: float = 0.0    # $/1M tokens (thinking tokens)

@dataclass
class ModelLimits:
    context: int = 0          # Max context window
    output: int = 0           # Max output tokens

@dataclass
class ModelCapabilities:
    reasoning: bool = False        # Extended thinking
    tool_call: bool = False        # Function calling
    structured_output: bool = False # JSON mode
    attachment: bool = False       # File input
    temperature: bool = True       # Temperature control

@dataclass
class ModelModalities:
    input: list[str] = ["text"]   # text, image, audio, video, pdf
    output: list[str] = ["text"]  # text, image

@dataclass
class Model:
    id: str                    # "claude-sonnet-4-5-20251101"
    provider: str              # "anthropic"
    name: str                  # "Claude Sonnet 4.5"
    family: str                # "claude"
    cost: ModelCost
    limits: ModelLimits
    capabilities: ModelCapabilities
    modalities: ModelModalities
    knowledge_cutoff: str      # "2025-04"
    release_date: str          # "2025-01-15"
    status: str                # "", "deprecated", "preview"
    open_weights: bool         # False
```

---

## LiteLLM Provider (`provider.py`)

```python
"""LiteLLM provider emitting granular events."""

import asyncio
import json
import time
from pathlib import Path

from litellm import Router
import yaml

from .types import (
    Context,
    UserMessage,
    AssistantMessage,
    ToolResultMessage,
    TextContent,
    ThinkingContent,
    ToolCall,
    ImageContent,
    Usage,
    Cost,
    StopReason,
    StreamOptions,
    SimpleStreamOptions,
    ThinkingLevel,
    ThinkingBudgets,
)
from .stream import (
    AssistantMessageEventStream,
    StartEvent,
    TextStartEvent,
    TextDeltaEvent,
    TextEndEvent,
    ThinkingStartEvent,
    ThinkingDeltaEvent,
    ThinkingEndEvent,
    ToolCallStartEvent,
    ToolCallDeltaEvent,
    ToolCallEndEvent,
    DoneEvent,
    ErrorEvent,
)

# Default data directory
DATA_DIR = Path.home() / ".pipy"

# Thinking budgets by level
DEFAULT_BUDGETS = ThinkingBudgets(
    minimal=1024,
    low=2048,
    medium=8192,
    high=16384,
)


class LiteLLMProvider:
    """LiteLLM-backed provider with granular streaming events.
    
    Uses LiteLLM Router for model routing and the models.dev registry
    for model metadata.
    
    Config is loaded from:
        1. Explicit config_path argument
        2. ~/.pipy/router.yaml (generated by `pipy config`)
        3. Falls back to direct model names if no config
    """
    
    def __init__(self, config_path: str | Path | None = None):
        self._router: Router | None = None
        self._config_path = Path(config_path) if config_path else None
    
    def _get_router(self) -> Router:
        """Get or create the LiteLLM Router."""
        if self._router is not None:
            return self._router
        
        # Find config file
        config_path = self._config_path or DATA_DIR / "router.yaml"
        
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
            self._router = Router(model_list=config.get("model_list", []))
        else:
            # No config - use direct model names (requires env vars for API keys)
            self._router = Router(model_list=[])
        
        return self._router
    
    def _convert_messages(self, context: Context) -> list[dict]:
        """Convert Context to LiteLLM message format."""
        messages = []
        
        if context.system_prompt:
            messages.append({"role": "system", "content": context.system_prompt})
        
        for msg in context.messages:
            if isinstance(msg, UserMessage):
                if isinstance(msg.content, str):
                    messages.append({"role": "user", "content": msg.content})
                else:
                    # Handle multimodal content (text + images)
                    content_parts = []
                    for part in msg.content:
                        if isinstance(part, TextContent):
                            content_parts.append({"type": "text", "text": part.text})
                        elif isinstance(part, ImageContent):
                            content_parts.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{part.mime_type};base64,{part.data}"
                                }
                            })
                    messages.append({"role": "user", "content": content_parts})
            
            elif isinstance(msg, AssistantMessage):
                text_parts = [c.text for c in msg.content if isinstance(c, TextContent)]
                tool_calls = [c for c in msg.content if isinstance(c, ToolCall)]
                
                msg_dict = {"role": "assistant"}
                if text_parts:
                    msg_dict["content"] = "\n".join(text_parts)
                if tool_calls:
                    msg_dict["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments),
                            }
                        }
                        for tc in tool_calls
                    ]
                messages.append(msg_dict)
            
            elif isinstance(msg, ToolResultMessage):
                content = "\n".join(
                    c.text for c in msg.content if isinstance(c, TextContent)
                )
                messages.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "content": content,
                })
        
        return messages
    
    def _convert_tools(self, tools: list | None) -> list[dict] | None:
        """Convert Tool list to LiteLLM/OpenAI function format."""
        if not tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                }
            }
            for t in tools
        ]
    
    def _map_reasoning_effort(self, level: ThinkingLevel) -> str:
        """Map ThinkingLevel to LiteLLM reasoning_effort parameter."""
        # LiteLLM currently supports low/medium/high
        return {
            ThinkingLevel.MINIMAL: "low",
            ThinkingLevel.LOW: "low",
            ThinkingLevel.MEDIUM: "medium",
            ThinkingLevel.HIGH: "high",
            ThinkingLevel.XHIGH: "high",
        }.get(level, "low")
    
    def stream(
        self,
        model: str,
        context: Context,
        options: StreamOptions | None = None,
    ) -> AssistantMessageEventStream:
        """Stream a response with granular events.
        
        Returns immediately with an AssistantMessageEventStream.
        The actual API call runs in a background task.
        """
        event_stream = AssistantMessageEventStream()
        asyncio.create_task(self._stream_impl(event_stream, model, context, options))
        return event_stream
    
    async def _stream_impl(
        self,
        event_stream: AssistantMessageEventStream,
        model: str,
        context: Context,
        options: StreamOptions | None,
    ) -> None:
        """Internal streaming implementation."""
        options = options or StreamOptions()
        
        # Initialize partial message that gets updated as we stream
        partial = AssistantMessage(
            role="assistant",
            content=[],
            api="litellm",
            provider=model.split("/")[0] if "/" in model else "unknown",
            model=model,
            timestamp=int(time.time() * 1000),
        )
        
        try:
            router = self._get_router()
            messages = self._convert_messages(context)
            tools = self._convert_tools(context.tools)
            
            # Build request kwargs
            kwargs = {
                "model": model,
                "messages": messages,
                "stream": True,
            }
            if options.max_tokens:
                kwargs["max_tokens"] = options.max_tokens
            if options.temperature is not None:
                kwargs["temperature"] = options.temperature
            if tools:
                kwargs["tools"] = tools
            if options.api_key:
                kwargs["api_key"] = options.api_key
            
            # Emit start event
            event_stream.push(StartEvent(partial=partial))
            
            # State tracking
            text_started = False
            text_content: list[str] = []
            thinking_started = False
            thinking_content: list[str] = []
            current_tool_call: dict | None = None
            tool_arg_buffer = ""
            
            # Stream from LiteLLM
            response = await router.acompletion(**kwargs)
            
            async for chunk in response:
                choice = chunk.choices[0]
                delta = choice.delta
                
                # === Text content ===
                if delta.content:
                    if not text_started:
                        text_started = True
                        partial.content.append(TextContent(text=""))
                        event_stream.push(TextStartEvent(
                            content_index=len(partial.content) - 1,
                            partial=partial,
                        ))
                    
                    idx = len(partial.content) - 1
                    text_content.append(delta.content)
                    partial.content[idx].text = "".join(text_content)
                    
                    event_stream.push(TextDeltaEvent(
                        content_index=idx,
                        delta=delta.content,
                        partial=partial,
                    ))
                
                # === Thinking/reasoning content ===
                reasoning = getattr(delta, "reasoning_content", None)
                if reasoning:
                    if not thinking_started:
                        thinking_started = True
                        # Insert thinking at the beginning
                        partial.content.insert(0, ThinkingContent(thinking=""))
                        event_stream.push(ThinkingStartEvent(
                            content_index=0,
                            partial=partial,
                        ))
                    
                    thinking_content.append(reasoning)
                    partial.content[0].thinking = "".join(thinking_content)
                    
                    event_stream.push(ThinkingDeltaEvent(
                        content_index=0,
                        delta=reasoning,
                        partial=partial,
                    ))
                
                # === Tool calls ===
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        if tc.function.name:
                            # Finish previous tool call if any
                            if current_tool_call and tool_arg_buffer:
                                current_tool_call["arguments"] = json.loads(tool_arg_buffer)
                                tool_call = ToolCall(
                                    id=current_tool_call["id"],
                                    name=current_tool_call["name"],
                                    arguments=current_tool_call["arguments"],
                                )
                                partial.content.append(tool_call)
                                event_stream.push(ToolCallEndEvent(
                                    content_index=len(partial.content) - 1,
                                    tool_call=tool_call,
                                    partial=partial,
                                ))
                            
                            # Start new tool call
                            current_tool_call = {
                                "id": tc.id,
                                "name": tc.function.name,
                            }
                            tool_arg_buffer = ""
                            event_stream.push(ToolCallStartEvent(
                                content_index=len(partial.content),
                                partial=partial,
                            ))
                        
                        if tc.function.arguments:
                            tool_arg_buffer += tc.function.arguments
                            event_stream.push(ToolCallDeltaEvent(
                                content_index=len(partial.content),
                                delta=tc.function.arguments,
                                partial=partial,
                            ))
            
            # === Finalize content blocks ===
            if text_started:
                event_stream.push(TextEndEvent(
                    content_index=len(partial.content) - 1,
                    content="".join(text_content),
                    partial=partial,
                ))
            
            if thinking_started:
                event_stream.push(ThinkingEndEvent(
                    content_index=0,
                    content="".join(thinking_content),
                    partial=partial,
                ))
            
            if current_tool_call:
                current_tool_call["arguments"] = (
                    json.loads(tool_arg_buffer) if tool_arg_buffer else {}
                )
                tool_call = ToolCall(
                    id=current_tool_call["id"],
                    name=current_tool_call["name"],
                    arguments=current_tool_call["arguments"],
                )
                partial.content.append(tool_call)
                event_stream.push(ToolCallEndEvent(
                    content_index=len(partial.content) - 1,
                    tool_call=tool_call,
                    partial=partial,
                ))
            
            # === Done ===
            finish_reason = chunk.choices[0].finish_reason
            stop_reason = {
                "stop": StopReason.STOP,
                "length": StopReason.LENGTH,
                "tool_calls": StopReason.TOOL_USE,
            }.get(finish_reason, StopReason.STOP)
            
            partial.stop_reason = stop_reason
            event_stream.push(DoneEvent(reason=stop_reason, message=partial))
        
        except Exception as e:
            partial.stop_reason = StopReason.ERROR
            partial.error_message = str(e)
            event_stream.push(ErrorEvent(reason=StopReason.ERROR, error=partial))
    
    def stream_simple(
        self,
        model: str,
        context: Context,
        options: SimpleStreamOptions | None = None,
    ) -> AssistantMessageEventStream:
        """Stream with reasoning level support.
        
        Converts SimpleStreamOptions to provider-specific parameters.
        """
        options = options or SimpleStreamOptions()
        
        # Start with base StreamOptions
        base_options = StreamOptions(
            temperature=options.temperature,
            max_tokens=options.max_tokens,
            cache_retention=options.cache_retention,
            session_id=options.session_id,
            api_key=options.api_key,
        )
        
        # TODO: When reasoning is requested, add reasoning_effort to kwargs
        # This will be passed through to _stream_impl
        
        return self.stream(model, context, base_options)
```

---

## Implementation Plan

### Phase 1: Foundation (Week 1)
1. Create package structure with `pyproject.toml`
2. Implement `types.py` with full type system
3. Implement `stream.py` with `AssistantMessageEventStream`
4. Basic tests for types and stream

### Phase 2: Registry (Week 2)
1. Port `registry/` from animus (standalone, no animus deps)
2. Implement `sync.py` for models.dev integration
3. Implement `config.py` for LiteLLM router config generation
4. CLI commands: `pipy sync`, `pipy models`, `pipy info`

### Phase 3: Provider (Week 3)
1. Implement `provider.py` with `LiteLLMProvider`
2. Granular event emission (text, thinking, tool calls)
3. Full async streaming support
4. Integration tests with mocked LiteLLM

### Phase 4: API & Tools (Week 4)
1. Implement `api.py` with `stream()`, `complete()`, etc.
2. Convenience functions (`quick_complete`, `user`, `context`)
3. Tool calling support
4. Documentation and examples

### Phase 5: Polish & Publish (Week 5)
1. README with examples
2. Full test coverage
3. Type hints validation with mypy
4. Publish to PyPI

---

## Key Differences from pi-mono/ai

| Aspect | pi-mono/ai | pi-ai-litellm |
|--------|------------|---------------|
| **Backend** | Native SDK per provider | LiteLLM unified |
| **Language** | TypeScript | Python |
| **Model DB** | Generated 296KB static code | **models.dev live sync** ✨ |
| **Model Updates** | Requires code release | `animus llm sync-models` |
| **Model Queries** | Basic lookup | Rich filtering (capability, modality, cost) |
| **Cost Tracking** | Manual calculation | Automatic from models.dev pricing |
| **Async** | Native async/await | asyncio |
| **Validation** | TypeBox | JSON Schema / Pydantic |

### Advantages of models.dev Integration

1. **Always Current**: New models available within hours of models.dev update
2. **No Code Changes**: Sync → generate config → use new model
3. **Rich Metadata**: Capabilities, modalities, pricing, knowledge cutoff, release dates
4. **Smart Selection**: Query models by constraints (cost, context, capabilities)
5. **Cost Estimation**: Accurate pricing for budgeting and model selection
6. **Provider Agnostic**: Same metadata schema across all providers

---

## Why LiteLLM + models.dev?

### LiteLLM Benefits
1. **Provider abstraction**: Already handles 100+ providers
2. **Maintenance**: Community maintains provider compatibility
3. **Features**: Caching, rate limiting, fallbacks built-in
4. **Simplicity**: One YAML config for all models
5. **Cost**: No need to maintain native SDK integrations

### models.dev Benefits
1. **Metadata source of truth**: Pricing, limits, capabilities always current
2. **Community maintained**: Models added/updated by the community
3. **Structured data**: Clean JSON API, easy to parse
4. **Provider coverage**: Same providers LiteLLM supports

### The Combination

```
models.dev API ──sync──► models.json ──generate──► litellm_config.yaml
                              │
                              ▼
                        ModelRegistry ──► get_model(), estimate_cost(), select_model()
                              │
                              ▼
                        LiteLLM Router ──► Actual API calls
```

**This is better than pi-mono/ai** because:
- pi-mono/ai has a 296KB generated TypeScript file that requires code changes to update
- We have live sync from models.dev + runtime registry with rich queries
- New models work immediately after `sync-models && generate-config`

The tradeoff is less control over provider-specific features (like Anthropic's exact prompt caching semantics), but LiteLLM exposes most of these through provider-specific params.

---

## CLI (`pipy` command)

The package provides a CLI for registry operations:

```bash
# === Sync & Config ===

# Pull latest models from models.dev
pipy sync
# Output: Fetched 847 models across 42 providers
# Saved to ~/.pipy/models.json

# Generate LiteLLM router config
pipy config
# Output: Generated ~/.pipy/router.yaml

# Sync specific providers only
pipy config --providers anthropic,openai,google

# === Explore Models ===

# List all models
pipy models
# Output: anthropic/claude-opus-4-5, anthropic/claude-sonnet-4-5, ...

# List by provider
pipy models --provider anthropic

# List by capability
pipy models --capability reasoning
pipy models --capability tool_call

# List by modality  
pipy models --modality image
pipy models --modality pdf

# Filter by context window
pipy models --min-context 100000

# === Model Details ===

# Show model info
pipy info anthropic/claude-sonnet-4-5
# Output:
#   Name: Claude Sonnet 4.5
#   Provider: anthropic
#   Context: 200000 tokens
#   Max Output: 16000 tokens
#   Cost: $3.00/1M input, $15.00/1M output
#   Capabilities: reasoning, tool_call, structured_output
#   Modalities: text, image (input) → text (output)
#   Knowledge Cutoff: 2025-04
#   Released: 2025-01-15

# === Cost Estimation ===

# Estimate cost for a request
pipy cost anthropic/claude-sonnet-4-5 --input 10000 --output 2000
# Output: Estimated cost: $0.06 ($0.03 input + $0.03 output)

# Compare costs across models
pipy compare --input 10000 --output 2000
# Output:
#   anthropic/claude-sonnet-4-5: $0.06
#   openai/gpt-4o: $0.04
#   google/gemini-2.0-flash: $0.01
```

### CLI Implementation (`cli/main.py`)

```python
"""pipy CLI - Model registry and config management."""

import argparse
import sys
from pathlib import Path

from ..registry import (
    sync_models,
    get_model,
    get_models,
    estimate_cost,
    generate_router_config,
)

# Default data directory
DATA_DIR = Path.home() / ".pipy"


def cmd_sync(args):
    """Sync models from models.dev."""
    DATA_DIR.mkdir(exist_ok=True)
    data = sync_models(output_path=DATA_DIR / "models.json")
    total = sum(len(p.get("models", {})) for p in data.values())
    print(f"Synced {total} models from {len(data)} providers")


def cmd_config(args):
    """Generate LiteLLM router config."""
    providers = args.providers.split(",") if args.providers else None
    config_path = DATA_DIR / "router.yaml"
    generate_router_config(output_path=config_path, providers=providers)
    print(f"Generated {config_path}")


def cmd_models(args):
    """List models with filters."""
    models = get_models(
        provider=args.provider,
        capability=args.capability,
        modality=args.modality,
        min_context=args.min_context,
    )
    for m in sorted(models, key=lambda x: x.qualified_name):
        print(m.qualified_name)


def cmd_info(args):
    """Show model details."""
    model = get_model(args.model)
    if not model:
        print(f"Model not found: {args.model}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Name: {model.name}")
    print(f"Provider: {model.provider}")
    print(f"Context: {model.limits.context:,} tokens")
    print(f"Max Output: {model.limits.output:,} tokens")
    print(f"Cost: ${model.cost.input:.2f}/1M input, ${model.cost.output:.2f}/1M output")
    
    caps = []
    if model.capabilities.reasoning:
        caps.append("reasoning")
    if model.capabilities.tool_call:
        caps.append("tool_call")
    if model.capabilities.structured_output:
        caps.append("structured_output")
    print(f"Capabilities: {', '.join(caps) or 'none'}")
    
    print(f"Modalities: {', '.join(model.modalities.input)} → {', '.join(model.modalities.output)}")
    if model.knowledge_cutoff:
        print(f"Knowledge Cutoff: {model.knowledge_cutoff}")
    if model.release_date:
        print(f"Released: {model.release_date}")


def cmd_cost(args):
    """Estimate cost for a request."""
    cost = estimate_cost(args.model, args.input, args.output, args.cached or 0)
    print(f"Estimated cost: ${cost:.4f}")


def main():
    parser = argparse.ArgumentParser(prog="pipy", description="pipy-ai: LLM model registry CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # sync
    p_sync = subparsers.add_parser("sync", help="Sync models from models.dev")
    p_sync.set_defaults(func=cmd_sync)
    
    # config
    p_config = subparsers.add_parser("config", help="Generate LiteLLM router config")
    p_config.add_argument("--providers", help="Comma-separated provider list")
    p_config.set_defaults(func=cmd_config)
    
    # models
    p_models = subparsers.add_parser("models", help="List models")
    p_models.add_argument("--provider", help="Filter by provider")
    p_models.add_argument("--capability", help="Filter by capability")
    p_models.add_argument("--modality", help="Filter by input modality")
    p_models.add_argument("--min-context", type=int, help="Minimum context window")
    p_models.set_defaults(func=cmd_models)
    
    # info
    p_info = subparsers.add_parser("info", help="Show model details")
    p_info.add_argument("model", help="Model name")
    p_info.set_defaults(func=cmd_info)
    
    # cost
    p_cost = subparsers.add_parser("cost", help="Estimate request cost")
    p_cost.add_argument("model", help="Model name")
    p_cost.add_argument("--input", type=int, required=True, help="Input tokens")
    p_cost.add_argument("--output", type=int, default=0, help="Output tokens")
    p_cost.add_argument("--cached", type=int, help="Cached tokens")
    p_cost.set_defaults(func=cmd_cost)
    
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
```

---

## Usage Examples (README)

```python
# === Quick Start (sync, Pythonic) ===

from pipy_ai import quick

# One-liner
result = quick("What is the capital of France?")
print(result.text)  # "Paris"

# With reasoning
result = quick("Solve: 127 * 843", reasoning=ThinkingLevel.HIGH)
print(result.thinking_text)  # Step-by-step reasoning
print(result.text)           # "107061"


# === Standard Usage (sync) ===

from pipy_ai import complete, ctx, user

result = complete("anthropic/claude-sonnet-4-5", ctx(
    user("Write a haiku about Python."),
    system="You are a poet."
))
print(result.text)


# === Streaming (sync) ===

from pipy_ai import stream, Context, UserMessage

context = Context(
    system_prompt="You are helpful.",
    messages=[UserMessage(content="Write a short story.")]
)

for event in stream("anthropic/claude-sonnet-4-5", context):
    if event.type == "text_delta":
        print(event.delta, end="", flush=True)
print()


# === Async Variants ===

import asyncio
from pipy_ai import acomplete, astream

async def main():
    # Async complete
    result = await acomplete("anthropic/claude-sonnet-4-5", context)
    
    # Async stream
    async for event in astream("anthropic/claude-sonnet-4-5", context):
        if event.type == "text_delta":
            print(event.delta, end="")

asyncio.run(main())


# === With Reasoning/Thinking ===

from pipy_ai import complete_simple, SimpleStreamOptions, ThinkingLevel

options = SimpleStreamOptions(
    reasoning=ThinkingLevel.HIGH,
    max_tokens=4096,
)

result = complete_simple("anthropic/claude-sonnet-4-5", context, options)
print("Thinking:", result.thinking_text)
print("Answer:", result.text)


# === Tool Calling ===

from pipy_ai import stream, Context, Tool, UserMessage, ToolResultMessage, TextContent

weather_tool = Tool(
    name="get_weather",
    description="Get current weather for a location",
    parameters={
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City name"}
        },
        "required": ["location"]
    }
)

context = Context(
    messages=[UserMessage(content="What's the weather in Tokyo?")],
    tools=[weather_tool]
)

for event in stream("anthropic/claude-sonnet-4-5", context):
    if event.type == "toolcall_end":
        tc = event.tool_call
        print(f"Tool call: {tc.name}({tc.arguments})")
        
        # Execute tool and continue
        tool_result = {"temperature": "22°C", "condition": "Sunny"}
        
        context.messages.append(event.partial)
        context.messages.append(ToolResultMessage(
            tool_call_id=tc.id,
            tool_name=tc.name,
            content=[TextContent(text=str(tool_result))],
        ))
        
        # Continue with tool result
        for event2 in stream("anthropic/claude-sonnet-4-5", context):
            if event2.type == "text_delta":
                print(event2.delta, end="")


# === Model Discovery ===

from pipy_ai import get_models, get_model, estimate_cost

# Find all reasoning models
reasoning_models = get_models(capability="reasoning")
print(f"Found {len(reasoning_models)} reasoning models")

# Find cheap models with vision
vision_models = get_models(modality="image", max_cost_input=1.0)

# Get model details
model = get_model("anthropic/claude-sonnet-4-5")
print(f"{model.name}: ${model.cost.input}/1M input tokens")

# Estimate cost before request
cost = estimate_cost("anthropic/claude-opus-4", input_tokens=50000, output_tokens=8000)
print(f"Estimated cost: ${cost:.2f}")
```

---

## Decisions

| # | Question | Decision |
|---|----------|----------|
| 1 | Package Name | ✅ `pipy-ai` (PyPI), `pipy_ai` (import), `pipy` (CLI) |
| 2 | Sync vs Async | ✅ **Sync-first** with async variants (`complete()` / `acomplete()`) |
| 3 | Types | ✅ **Pydantic** (validation, serialization) |
| 4 | Data Directory | ✅ `~/.pipy/` with `PIPY_DATA_DIR` env override |
| 5 | LiteLLM Version | ✅ **Latest** (no version pinning) |
| 6 | Animus Integration | ✅ **None** - completely standalone library |
| 7 | Caching Strategy | ✅ **Auto-sync** on first use if missing/stale |

### Repository Location

```
~/src/witt3rd/pipy/ai/       # Standalone repo, not part of animus
```

### API Pattern (Sync-first)

```python
from pipy_ai import complete, acomplete, stream, astream

# Sync (default, Pythonic)
result = complete("anthropic/claude-sonnet-4-5", context)

# Async variant
result = await acomplete("anthropic/claude-sonnet-4-5", context)

# Streaming
for event in stream(model, context):
    ...

# Async streaming  
async for event in astream(model, context):
    ...
```
