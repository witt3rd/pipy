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

__version__ = "0.51.6"

# Types (Pydantic models)
# Abort (cancellation)
from .abort import (
    AbortController,
    AbortError,
    AbortSignal,
)

# API (sync-first)
from .api import (
    # Async variants
    acomplete,
    acomplete_simple,
    astream,
    astream_simple,
    # Sync (primary)
    complete,
    complete_simple,
    ctx,
    quick,
    stream,
    stream_simple,
    # Builders
    user,
)

# Registry (models.dev)
from .provider import supports_xhigh
from .registry import (
    Model,
    ModelCapabilities,
    ModelCost,
    ModelLimits,
    ModelModalities,
    calculate_cost,
    estimate_cost,
    get_model,
    get_models,
    get_registry,
    sync_models,
)


def get_available_models() -> list[str]:
    """Get list of available model IDs from LiteLLM."""
    try:
        import litellm
        return sorted(litellm.model_list or [])
    except Exception:
        # Fallback to common models
        return [
            "anthropic/claude-sonnet-4-20250514",
            "anthropic/claude-3-opus-20240229",
            "anthropic/claude-3.5-haiku-20241022",
            "openai/gpt-4o",
            "openai/gpt-4-turbo",
            "google/gemini-2.0-flash",
        ]

# Events
from .stream import (
    AssistantMessageEvent,
    DoneEvent,
    ErrorEvent,
    StartEvent,
    TextDeltaEvent,
    TextEndEvent,
    TextStartEvent,
    ThinkingDeltaEvent,
    ThinkingEndEvent,
    ThinkingStartEvent,
    ToolCallDeltaEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
)
from .types import (
    AssistantMessage,
    CacheRetention,
    # Context
    Context,
    Cost,
    ImageContent,
    Message,
    SimpleStreamOptions,
    StopReason,
    # Options
    StreamOptions,
    # Content
    TextContent,
    ThinkingBudgets,
    ThinkingContent,
    # Enums
    ThinkingLevel,
    Tool,
    ToolCall,
    ToolResultMessage,
    # Usage
    Usage,
    # Messages
    UserMessage,
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
    # Abort
    "AbortSignal",
    "AbortController",
    "AbortError",
    # Utilities
    "get_available_models",
    "supports_xhigh",
]
