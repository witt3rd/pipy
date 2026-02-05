"""LiteLLM provider with granular streaming events."""

import json
import logging
import time
from collections.abc import AsyncIterator, Iterator

from litellm import acompletion, completion

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
    Context,
    ImageContent,
    SimpleStreamOptions,
    StopReason,
    StreamOptions,
    TextContent,
    ThinkingContent,
    ThinkingLevel,
    ToolCall,
    ToolResultMessage,
    UserMessage,
)

logger = logging.getLogger(__name__)


def supports_xhigh(model: str) -> bool:
    """Check if a model supports xhigh thinking level.

    Currently only certain OpenAI models (gpt-5.2 variants) support this.
    Matches upstream: model.id.includes("gpt-5.2")
    """
    return "gpt-5.2" in model


class LiteLLMProvider:
    """LiteLLM-backed provider with sync-first API."""

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
                    content_parts = []
                    for part in msg.content:
                        if isinstance(part, TextContent):
                            content_parts.append({"type": "text", "text": part.text})
                        elif isinstance(part, ImageContent):
                            content_parts.append(
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{part.mime_type};base64,{part.data}"
                                    },
                                }
                            )
                    messages.append({"role": "user", "content": content_parts})

            elif isinstance(msg, AssistantMessage):
                text_parts = [c.text for c in msg.content if isinstance(c, TextContent)]
                tool_calls = [c for c in msg.content if isinstance(c, ToolCall)]

                msg_dict: dict = {"role": "assistant"}
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
                            },
                        }
                        for tc in tool_calls
                    ]
                messages.append(msg_dict)

            elif isinstance(msg, ToolResultMessage):
                content = "\n".join(c.text for c in msg.content if isinstance(c, TextContent))
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": msg.tool_call_id,
                        "content": content,
                    }
                )

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
                },
            }
            for t in tools
        ]

    def _build_kwargs(
        self,
        model: str,
        messages: list[dict],
        options: StreamOptions | None,
        tools: list[dict] | None = None,
        stream: bool = False,
    ) -> dict:
        """Build kwargs for litellm completion call."""
        options = options or StreamOptions()

        kwargs = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }

        if options.max_tokens:
            kwargs["max_tokens"] = options.max_tokens
        if options.temperature is not None:
            kwargs["temperature"] = options.temperature
        if tools:
            kwargs["tools"] = tools
        if options.api_key:
            if options.api_key.startswith("sk-ant-oat"):
                # Anthropic OAuth token — must be passed via Authorization header.
                # LiteLLM's validate_environment detects "Bearer sk-ant-oat..." and
                # sets the required OAuth beta headers automatically.
                kwargs["extra_headers"] = {
                    **(options.headers or {}),
                    "authorization": f"Bearer {options.api_key}",
                }
                # api_key still needed so litellm doesn't reject for missing key
                kwargs["api_key"] = options.api_key
            else:
                kwargs["api_key"] = options.api_key
        if options.headers and "extra_headers" not in kwargs:
            kwargs["extra_headers"] = options.headers
        # session_id can be passed via headers for providers that support cache affinity
        # e.g., headers={"x-session-id": session_id} or provider-specific header names
        if options.session_id and not options.headers:
            kwargs["extra_headers"] = {"x-session-id": options.session_id}
        elif options.session_id and options.headers:
            kwargs["extra_headers"] = {**options.headers, "x-session-id": options.session_id}

        # Handle reasoning/thinking level from SimpleStreamOptions
        if isinstance(options, SimpleStreamOptions) and options.reasoning:
            level = options.reasoning
            if level != ThinkingLevel.OFF:
                # LiteLLM passes reasoning_effort to OpenAI models
                # Maps: low, medium, high (xhigh -> high unless model supports it)
                effort = level.value
                if effort == "xhigh" and not supports_xhigh(model):
                    effort = "high"  # xhigh only supported by gpt-5.2 models
                elif effort == "minimal":
                    effort = "low"  # minimal -> low for broader compatibility
                kwargs["reasoning_effort"] = effort

                # For Anthropic models, also set thinking budget if specified
                # LiteLLM passes this through as the 'thinking' parameter
                if options.thinking_budgets:
                    budgets = options.thinking_budgets
                    budget_map = {
                        ThinkingLevel.MINIMAL: budgets.minimal,
                        ThinkingLevel.LOW: budgets.low,
                        ThinkingLevel.MEDIUM: budgets.medium,
                        ThinkingLevel.HIGH: budgets.high,
                        ThinkingLevel.XHIGH: budgets.high,  # Use high budget for xhigh
                    }
                    budget_tokens = budget_map.get(level, budgets.medium)
                    kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget_tokens}

        return kwargs

    def _create_partial(self, model: str) -> AssistantMessage:
        """Create initial partial AssistantMessage."""
        provider = model.split("/")[0] if "/" in model else "unknown"
        return AssistantMessage(
            role="assistant",
            content=[],
            api="litellm",
            provider=provider,
            model=model,
            timestamp=int(time.time() * 1000),
        )

    # === Sync API ===

    def complete(
        self,
        model: str,
        context: Context,
        options: StreamOptions | None = None,
    ) -> AssistantMessage:
        """Sync completion (blocking)."""
        messages = self._convert_messages(context)
        tools = self._convert_tools(context.tools)
        kwargs = self._build_kwargs(model, messages, options, tools, stream=False)

        try:
            response = completion(**kwargs)
            msg = response.choices[0].message

            # Build AssistantMessage
            partial = self._create_partial(model)

            # Add text content
            if msg.content:
                partial.content.append(TextContent(text=msg.content))

            # Add tool calls
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    partial.content.append(
                        ToolCall(
                            id=tc.id,
                            name=tc.function.name,
                            arguments=json.loads(tc.function.arguments or "{}"),
                        )
                    )

            # Set stop reason
            finish_reason = response.choices[0].finish_reason
            partial.stop_reason = {
                "stop": StopReason.STOP,
                "length": StopReason.LENGTH,
                "tool_calls": StopReason.TOOL_USE,
                "sensitive": StopReason.SENSITIVE,
            }.get(finish_reason, StopReason.STOP)

            # Set usage
            if response.usage:
                partial.usage.input = response.usage.prompt_tokens or 0
                partial.usage.output = response.usage.completion_tokens or 0
                partial.usage.total_tokens = response.usage.total_tokens or 0

            return partial

        except Exception as e:
            partial = self._create_partial(model)
            partial.stop_reason = StopReason.ERROR
            partial.error_message = str(e)
            return partial

    def stream(
        self,
        model: str,
        context: Context,
        options: StreamOptions | None = None,
    ) -> Iterator[AssistantMessageEvent]:
        """Sync streaming (blocking iterator)."""
        messages = self._convert_messages(context)
        tools = self._convert_tools(context.tools)
        kwargs = self._build_kwargs(model, messages, options, tools, stream=True)

        partial = self._create_partial(model)

        try:
            response = completion(**kwargs)

            yield StartEvent(partial=partial)

            text_started = False
            text_content: list[str] = []
            thinking_started = False
            thinking_content: list[str] = []
            current_tool_call: dict | None = None
            tool_arg_buffer = ""

            for chunk in response:
                choice = chunk.choices[0]
                delta = choice.delta

                # Text content
                if delta.content:
                    if not text_started:
                        text_started = True
                        partial.content.append(TextContent(text=""))
                        yield TextStartEvent(
                            content_index=len(partial.content) - 1,
                            partial=partial,
                        )

                    idx = len(partial.content) - 1
                    text_content.append(delta.content)
                    partial.content[idx].text = "".join(text_content)

                    yield TextDeltaEvent(
                        content_index=idx,
                        delta=delta.content,
                        partial=partial,
                    )

                # Thinking/reasoning content
                reasoning = getattr(delta, "reasoning_content", None)
                if reasoning:
                    if not thinking_started:
                        thinking_started = True
                        partial.content.insert(0, ThinkingContent(thinking=""))
                        yield ThinkingStartEvent(
                            content_index=0,
                            partial=partial,
                        )

                    thinking_content.append(reasoning)
                    partial.content[0].thinking = "".join(thinking_content)

                    yield ThinkingDeltaEvent(
                        content_index=0,
                        delta=reasoning,
                        partial=partial,
                    )

                # Tool calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        if tc.function and tc.function.name:
                            if current_tool_call and tool_arg_buffer:
                                current_tool_call["arguments"] = json.loads(tool_arg_buffer)
                                tool_call = ToolCall(
                                    id=current_tool_call["id"],
                                    name=current_tool_call["name"],
                                    arguments=current_tool_call["arguments"],
                                )
                                partial.content.append(tool_call)
                                yield ToolCallEndEvent(
                                    content_index=len(partial.content) - 1,
                                    tool_call=tool_call,
                                    partial=partial,
                                )

                            current_tool_call = {
                                "id": tc.id,
                                "name": tc.function.name,
                            }
                            tool_arg_buffer = ""
                            yield ToolCallStartEvent(
                                content_index=len(partial.content),
                                partial=partial,
                            )

                        if tc.function and tc.function.arguments:
                            tool_arg_buffer += tc.function.arguments
                            yield ToolCallDeltaEvent(
                                content_index=len(partial.content),
                                delta=tc.function.arguments,
                                partial=partial,
                            )

            # Finalize
            if text_started:
                yield TextEndEvent(
                    content_index=len(partial.content) - 1,
                    content="".join(text_content),
                    partial=partial,
                )

            if thinking_started:
                yield ThinkingEndEvent(
                    content_index=0,
                    content="".join(thinking_content),
                    partial=partial,
                )

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
                yield ToolCallEndEvent(
                    content_index=len(partial.content) - 1,
                    tool_call=tool_call,
                    partial=partial,
                )

            # Done
            finish_reason = chunk.choices[0].finish_reason if chunk.choices else "stop"
            stop_reason = {
                "stop": StopReason.STOP,
                "length": StopReason.LENGTH,
                "tool_calls": StopReason.TOOL_USE,
                "sensitive": StopReason.SENSITIVE,
            }.get(finish_reason, StopReason.STOP)

            partial.stop_reason = stop_reason
            yield DoneEvent(reason=stop_reason, message=partial)

        except Exception as e:
            partial.stop_reason = StopReason.ERROR
            partial.error_message = str(e)
            yield ErrorEvent(reason=StopReason.ERROR, error=partial)

    # === Async API ===

    async def acomplete(
        self,
        model: str,
        context: Context,
        options: StreamOptions | None = None,
    ) -> AssistantMessage:
        """Async completion."""
        messages = self._convert_messages(context)
        tools = self._convert_tools(context.tools)
        kwargs = self._build_kwargs(model, messages, options, tools, stream=False)

        try:
            response = await acompletion(**kwargs)
            msg = response.choices[0].message

            partial = self._create_partial(model)

            if msg.content:
                partial.content.append(TextContent(text=msg.content))

            if msg.tool_calls:
                for tc in msg.tool_calls:
                    partial.content.append(
                        ToolCall(
                            id=tc.id,
                            name=tc.function.name,
                            arguments=json.loads(tc.function.arguments or "{}"),
                        )
                    )

            finish_reason = response.choices[0].finish_reason
            partial.stop_reason = {
                "stop": StopReason.STOP,
                "length": StopReason.LENGTH,
                "tool_calls": StopReason.TOOL_USE,
                "sensitive": StopReason.SENSITIVE,
            }.get(finish_reason, StopReason.STOP)

            if response.usage:
                partial.usage.input = response.usage.prompt_tokens or 0
                partial.usage.output = response.usage.completion_tokens or 0
                partial.usage.total_tokens = response.usage.total_tokens or 0

            return partial

        except Exception as e:
            partial = self._create_partial(model)
            partial.stop_reason = StopReason.ERROR
            partial.error_message = str(e)
            return partial

    async def astream(
        self,
        model: str,
        context: Context,
        options: StreamOptions | None = None,
    ) -> AsyncIterator[AssistantMessageEvent]:
        """Async streaming."""
        messages = self._convert_messages(context)
        tools = self._convert_tools(context.tools)
        kwargs = self._build_kwargs(model, messages, options, tools, stream=True)

        partial = self._create_partial(model)

        try:
            response = await acompletion(**kwargs)

            yield StartEvent(partial=partial)

            text_started = False
            text_content: list[str] = []
            thinking_started = False
            thinking_content: list[str] = []
            current_tool_call: dict | None = None
            tool_arg_buffer = ""

            async for chunk in response:
                choice = chunk.choices[0]
                delta = choice.delta

                if delta.content:
                    if not text_started:
                        text_started = True
                        partial.content.append(TextContent(text=""))
                        yield TextStartEvent(
                            content_index=len(partial.content) - 1,
                            partial=partial,
                        )

                    idx = len(partial.content) - 1
                    text_content.append(delta.content)
                    partial.content[idx].text = "".join(text_content)

                    yield TextDeltaEvent(
                        content_index=idx,
                        delta=delta.content,
                        partial=partial,
                    )

                reasoning = getattr(delta, "reasoning_content", None)
                if reasoning:
                    if not thinking_started:
                        thinking_started = True
                        partial.content.insert(0, ThinkingContent(thinking=""))
                        yield ThinkingStartEvent(
                            content_index=0,
                            partial=partial,
                        )

                    thinking_content.append(reasoning)
                    partial.content[0].thinking = "".join(thinking_content)

                    yield ThinkingDeltaEvent(
                        content_index=0,
                        delta=reasoning,
                        partial=partial,
                    )

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        if tc.function and tc.function.name:
                            if current_tool_call and tool_arg_buffer:
                                current_tool_call["arguments"] = json.loads(tool_arg_buffer)
                                tool_call = ToolCall(
                                    id=current_tool_call["id"],
                                    name=current_tool_call["name"],
                                    arguments=current_tool_call["arguments"],
                                )
                                partial.content.append(tool_call)
                                yield ToolCallEndEvent(
                                    content_index=len(partial.content) - 1,
                                    tool_call=tool_call,
                                    partial=partial,
                                )

                            current_tool_call = {
                                "id": tc.id,
                                "name": tc.function.name,
                            }
                            tool_arg_buffer = ""
                            yield ToolCallStartEvent(
                                content_index=len(partial.content),
                                partial=partial,
                            )

                        if tc.function and tc.function.arguments:
                            tool_arg_buffer += tc.function.arguments
                            yield ToolCallDeltaEvent(
                                content_index=len(partial.content),
                                delta=tc.function.arguments,
                                partial=partial,
                            )

            if text_started:
                yield TextEndEvent(
                    content_index=len(partial.content) - 1,
                    content="".join(text_content),
                    partial=partial,
                )

            if thinking_started:
                yield ThinkingEndEvent(
                    content_index=0,
                    content="".join(thinking_content),
                    partial=partial,
                )

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
                yield ToolCallEndEvent(
                    content_index=len(partial.content) - 1,
                    tool_call=tool_call,
                    partial=partial,
                )

            finish_reason = chunk.choices[0].finish_reason if chunk.choices else "stop"
            stop_reason = {
                "stop": StopReason.STOP,
                "length": StopReason.LENGTH,
                "tool_calls": StopReason.TOOL_USE,
                "sensitive": StopReason.SENSITIVE,
            }.get(finish_reason, StopReason.STOP)

            partial.stop_reason = stop_reason
            yield DoneEvent(reason=stop_reason, message=partial)

        except Exception as e:
            partial.stop_reason = StopReason.ERROR
            partial.error_message = str(e)
            yield ErrorEvent(reason=StopReason.ERROR, error=partial)

    # === Simple variants ===

    def complete_simple(
        self,
        model: str,
        context: Context,
        options: SimpleStreamOptions | None = None,
    ) -> AssistantMessage:
        """Sync completion with reasoning support."""
        return self.complete(model, context, options)

    def stream_simple(
        self,
        model: str,
        context: Context,
        options: SimpleStreamOptions | None = None,
    ) -> Iterator[AssistantMessageEvent]:
        """Sync streaming with reasoning support."""
        return self.stream(model, context, options)

    async def acomplete_simple(
        self,
        model: str,
        context: Context,
        options: SimpleStreamOptions | None = None,
    ) -> AssistantMessage:
        """Async completion with reasoning support."""
        return await self.acomplete(model, context, options)

    async def astream_simple(
        self,
        model: str,
        context: Context,
        options: SimpleStreamOptions | None = None,
    ) -> AsyncIterator[AssistantMessageEvent]:
        """Async streaming with reasoning support."""
        async for event in self.astream(model, context, options):
            yield event
