"""Agent class with state management."""

from typing import Callable

from pipy_ai import (
    UserMessage,
    ImageContent,
    TextContent,
    ThinkingLevel,
    ThinkingBudgets,
    AbortController,
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
        thinking_budgets: ThinkingBudgets | None = None,
        max_retry_delay_ms: int | None = None,
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
        self._thinking_budgets = thinking_budgets
        self._max_retry_delay_ms = max_retry_delay_ms

    @property
    def state(self) -> AgentState:
        return self._state

    @property
    def messages(self) -> list[AgentMessage]:
        """Current conversation messages."""
        return self._state.messages

    @property
    def is_streaming(self) -> bool:
        """True if agent is currently processing."""
        return self._state.is_streaming

    @property
    def session_id(self) -> str | None:
        """Session ID for provider caching."""
        return self._session_id

    @session_id.setter
    def session_id(self, value: str | None):
        """Set session ID for provider caching."""
        self._session_id = value

    @property
    def thinking_budgets(self) -> ThinkingBudgets | None:
        """Custom thinking budgets for token-based providers."""
        return self._thinking_budgets

    @thinking_budgets.setter
    def thinking_budgets(self, value: ThinkingBudgets | None):
        """Set custom thinking budgets."""
        self._thinking_budgets = value

    @property
    def max_retry_delay_ms(self) -> int | None:
        """Max delay in ms to wait for server-requested retries."""
        return self._max_retry_delay_ms

    @max_retry_delay_ms.setter
    def max_retry_delay_ms(self, value: int | None):
        """Set max retry delay. Set to 0 to disable the cap."""
        self._max_retry_delay_ms = value

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
        """Subscribe to agent events. Returns unsubscribe function."""
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
        """Abort current execution."""
        if self._abort:
            self._abort.abort()

    def reset(self):
        """Reset agent state."""
        self._state.messages = []
        self._state.is_streaming = False
        self._state.stream_message = None
        self._state.pending_tool_calls = set()
        self._state.error = None
        self.clear_queues()

    # === Prompt ===

    async def prompt(
        self,
        input: str | AgentMessage | list[AgentMessage],
        images: list[ImageContent] | None = None,
    ):
        """Send a prompt to the agent.

        Args:
            input: String prompt, single message, or list of messages
            images: Optional images to attach (only if input is string)
        """
        if self._state.is_streaming:
            raise RuntimeError("Already streaming. Use steer() or wait.")

        if isinstance(input, list):
            msgs = input
        elif isinstance(input, str):
            content: list[TextContent | ImageContent] = [TextContent(text=input)]
            if images:
                content.extend(images)
            msgs = [UserMessage(content=content)]
        else:
            msgs = [input]

        await self._run(msgs)

    async def continue_(self):
        """Continue from current context (for retry after overflow)."""
        if self._state.is_streaming:
            raise RuntimeError("Already streaming.")
        if not self._state.messages:
            raise ValueError("No messages to continue from")
        if self._state.messages[-1].role == "assistant":
            raise ValueError("Cannot continue from assistant message")

        await self._run(None)

    async def _run(self, prompts: list[AgentMessage] | None):
        """Run the agent loop."""
        self._abort = AbortController()
        self._state.is_streaming = True
        self._state.stream_message = None
        self._state.error = None

        config = AgentLoopConfig(
            model=self._state.model,
            reasoning=self._state.thinking_level,
            session_id=self._session_id,
            thinking_budgets=self._thinking_budgets,
            max_retry_delay_ms=self._max_retry_delay_ms,
        )

        try:
            if prompts:
                stream = agent_loop(
                    prompts,
                    system_prompt=self._state.system_prompt,
                    messages=list(self._state.messages),
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
                    messages=list(self._state.messages),
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
            self._state.stream_message = None
            self._state.pending_tool_calls = set()
            self._abort = None

    def _update_state(self, event: AgentEvent):
        """Update internal state based on event."""
        match event.type:
            case "message_start":
                if hasattr(event, "message") and event.message.role == "assistant":
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
        """Get steering messages from queue."""
        if not self._steering_queue:
            return []
        if self._steering_mode == "one-at-a-time":
            return [self._steering_queue.pop(0)]
        msgs = self._steering_queue
        self._steering_queue = []
        return msgs

    async def _get_follow_up(self) -> list[AgentMessage]:
        """Get follow-up messages from queue."""
        if not self._follow_up_queue:
            return []
        if self._follow_up_mode == "one-at-a-time":
            return [self._follow_up_queue.pop(0)]
        msgs = self._follow_up_queue
        self._follow_up_queue = []
        return msgs
