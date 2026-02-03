"""Event types for streaming responses."""

from pydantic import BaseModel

from .types import AssistantMessage, StopReason, ToolCall

# === Event Types ===


class StartEvent(BaseModel):
    """Stream started."""

    type: str = "start"
    partial: AssistantMessage


class TextStartEvent(BaseModel):
    """Text content block started."""

    type: str = "text_start"
    content_index: int = 0
    partial: AssistantMessage


class TextDeltaEvent(BaseModel):
    """Text content delta."""

    type: str = "text_delta"
    content_index: int = 0
    delta: str = ""
    partial: AssistantMessage


class TextEndEvent(BaseModel):
    """Text content block ended."""

    type: str = "text_end"
    content_index: int = 0
    content: str = ""
    partial: AssistantMessage


class ThinkingStartEvent(BaseModel):
    """Thinking content block started."""

    type: str = "thinking_start"
    content_index: int = 0
    partial: AssistantMessage


class ThinkingDeltaEvent(BaseModel):
    """Thinking content delta."""

    type: str = "thinking_delta"
    content_index: int = 0
    delta: str = ""
    partial: AssistantMessage


class ThinkingEndEvent(BaseModel):
    """Thinking content block ended."""

    type: str = "thinking_end"
    content_index: int = 0
    content: str = ""
    partial: AssistantMessage


class ToolCallStartEvent(BaseModel):
    """Tool call started."""

    type: str = "toolcall_start"
    content_index: int = 0
    partial: AssistantMessage


class ToolCallDeltaEvent(BaseModel):
    """Tool call arguments delta."""

    type: str = "toolcall_delta"
    content_index: int = 0
    delta: str = ""
    partial: AssistantMessage


class ToolCallEndEvent(BaseModel):
    """Tool call ended."""

    type: str = "toolcall_end"
    content_index: int = 0
    tool_call: ToolCall
    partial: AssistantMessage


class DoneEvent(BaseModel):
    """Stream completed successfully."""

    type: str = "done"
    reason: StopReason = StopReason.STOP
    message: AssistantMessage


class ErrorEvent(BaseModel):
    """Stream ended with error."""

    type: str = "error"
    reason: StopReason = StopReason.ERROR
    error: AssistantMessage


# Union type for all events
AssistantMessageEvent = (
    StartEvent
    | TextStartEvent
    | TextDeltaEvent
    | TextEndEvent
    | ThinkingStartEvent
    | ThinkingDeltaEvent
    | ThinkingEndEvent
    | ToolCallStartEvent
    | ToolCallDeltaEvent
    | ToolCallEndEvent
    | DoneEvent
    | ErrorEvent
)
