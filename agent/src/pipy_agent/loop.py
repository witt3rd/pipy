"""Agent loop implementation using pipy-ai for LLM calls."""

from typing import AsyncIterator

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
    AbortError,
    ToolCall,
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
                system_prompt,
                messages,
                tools,
                config,
                signal,
                convert_to_llm,
                transform_context,
                get_api_key,
            )
            for event in events:
                yield event
            new_messages.append(assistant_msg)

            if assistant_msg.stop_reason in ("error", "aborted"):
                yield TurnEndEvent(message=assistant_msg, tool_results=[])
                yield AgentEndEvent(messages=new_messages)
                return

            # Execute tool calls
            tool_calls = [c for c in assistant_msg.content if isinstance(c, ToolCall)]
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
        resolved = get_api_key(config.model.split("/")[0])
        # Handle both sync and async
        if hasattr(resolved, "__await__"):
            resolved = await resolved
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
        thinking_budgets=config.thinking_budgets,
        max_retry_delay_ms=config.max_retry_delay_ms or 60000,
    )

    # Stream from pipy-ai
    partial: AssistantMessage | None = None
    started = False

    try:
        async for event in astream(config.model, context, options):
            if signal and signal.aborted:
                raise AbortError("Aborted")

            if event.type == "start":
                partial = event.partial
                messages.append(partial)
                started = True
                events.append(MessageStartEvent(message=partial))

            elif event.type in (
                "text_delta",
                "thinking_delta",
                "toolcall_delta",
                "text_start",
                "text_end",
                "thinking_start",
                "thinking_end",
                "toolcall_start",
                "toolcall_end",
            ):
                if partial:
                    partial = event.partial
                    messages[-1] = partial
                    events.append(
                        MessageUpdateEvent(
                            message=partial,
                            assistant_event=event,
                        )
                    )

            elif event.type == "done":
                final = event.message
                if started:
                    messages[-1] = final
                else:
                    messages.append(final)
                    events.append(MessageStartEvent(message=final))
                events.append(MessageEndEvent(message=final))
                return final, events

            elif event.type == "error":
                final = event.error
                if started:
                    messages[-1] = final
                else:
                    messages.append(final)
                    events.append(MessageStartEvent(message=final))
                events.append(MessageEndEvent(message=final))
                return final, events

    except AbortError:
        # Create aborted message
        final = AssistantMessage(
            content=[TextContent(text="Aborted")],
            stop_reason="aborted",
        )
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
    tool_calls = [c for c in assistant_msg.content if isinstance(c, ToolCall)]

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
                for skip in tool_calls[i + 1 :]:
                    yield ToolExecutionStartEvent(
                        tool_call_id=skip.id,
                        tool_name=skip.name,
                        args=skip.arguments,
                    )
                    skip_result = AgentToolResult(content=[TextContent(text="Skipped")])
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
