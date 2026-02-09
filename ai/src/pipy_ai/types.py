"""Rich type system with Pydantic validation."""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

# === Enums ===


class ThinkingLevel(str, Enum):
    """Reasoning/thinking budget level."""

    OFF = "off"  # No reasoning/thinking
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"


class CacheRetention(str, Enum):
    """Prompt cache retention preference."""

    NONE = "none"
    SHORT = "short"
    LONG = "long"


class StopReason(str, Enum):
    """Why the model stopped generating."""

    STOP = "stop"
    LENGTH = "length"
    TOOL_USE = "toolUse"
    ERROR = "error"
    ABORTED = "aborted"
    SENSITIVE = "sensitive"  # Anthropic: content flagged as sensitive


# === Content Types ===


class TextContent(BaseModel):
    """Text content block."""

    type: Literal["text"] = "text"
    text: str = ""
    text_signature: str | None = None


class ThinkingContent(BaseModel):
    """Thinking/reasoning content block."""

    type: Literal["thinking"] = "thinking"
    thinking: str = ""
    thinking_signature: str | None = None


class ImageContent(BaseModel):
    """Image content block (base64 encoded)."""

    type: Literal["image"] = "image"
    data: str = ""  # Base64 encoded
    mime_type: str = "image/png"


class ToolCall(BaseModel):
    """Tool/function call."""

    type: Literal["toolCall"] = "toolCall"
    id: str = ""
    name: str = ""
    arguments: dict[str, Any] = Field(default_factory=dict)
    thought_signature: str | None = None


# === Messages ===


class UserMessage(BaseModel):
    """User message."""

    role: Literal["user"] = "user"
    content: str | list[TextContent | ImageContent] = ""
    timestamp: int = 0


class AssistantMessage(BaseModel):
    """Assistant response message."""

    role: Literal["assistant"] = "assistant"
    content: list[TextContent | ThinkingContent | ToolCall] = Field(default_factory=list)
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
        return "\n".join(c.text for c in self.content if isinstance(c, TextContent))

    @property
    def thinking_text(self) -> str:
        """Convenience: concatenated thinking content."""
        return "\n".join(c.thinking for c in self.content if isinstance(c, ThinkingContent))

    @property
    def tool_calls(self) -> list[ToolCall]:
        """Convenience: all tool calls."""
        return [c for c in self.content if isinstance(c, ToolCall)]


class ToolResultMessage(BaseModel):
    """Tool result message."""

    role: Literal["toolResult"] = "toolResult"
    tool_call_id: str = ""
    tool_name: str = ""
    content: list[TextContent | ImageContent] = Field(default_factory=list)
    details: Any = None
    is_error: bool = False
    timestamp: int = 0


# Type alias for any message
Message = UserMessage | AssistantMessage | ToolResultMessage


# === Usage & Cost ===


class Cost(BaseModel):
    """Cost breakdown in dollars."""

    input: float = 0.0
    output: float = 0.0
    cache_read: float = 0.0
    cache_write: float = 0.0
    total: float = 0.0


class Usage(BaseModel):
    """Token usage and cost."""

    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write: int = 0
    total_tokens: int = 0
    cost: Cost = Field(default_factory=Cost)


# === Tools ===


class Tool(BaseModel):
    """Tool definition."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema


# === Context ===


class Context(BaseModel):
    """Conversation context."""

    system_prompt: str | None = None
    messages: list[Message] = Field(default_factory=list)
    tools: list[Tool] | None = None


# === Options ===


class ThinkingBudgets(BaseModel):
    """Token budgets for each thinking level."""

    minimal: int = 1024
    low: int = 2048
    medium: int = 8192
    high: int = 16384


class StreamOptions(BaseModel):
    """Options for streaming requests."""

    temperature: float | None = None
    max_tokens: int | None = None
    cache_retention: CacheRetention = CacheRetention.SHORT
    session_id: str | None = None  # Passed via x-session-id header for cache affinity
    headers: dict[str, str] | None = None  # Custom headers (merged with session_id)
    api_key: str | None = None
    api_base: str | None = None
    # Note: max_retry_delay_ms is for API compatibility but LiteLLM handles retries internally
    max_retry_delay_ms: int = 60000


class SimpleStreamOptions(StreamOptions):
    """Options with reasoning level support."""

    reasoning: ThinkingLevel | None = None
    thinking_budgets: ThinkingBudgets | None = None


# Forward reference resolution
AssistantMessage.model_rebuild()
