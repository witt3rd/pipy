"""Agent session - combines agent with session management."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal

from pipy_agent import Agent, AgentEvent, agent_loop
from pipy_ai import UserMessage, AssistantMessage

from ..session import SessionManager, build_session_context
from ..settings import SettingsManager, CompactionSettings
from ..resources import DefaultResourceLoader
from ..prompt import build_system_prompt, BuildSystemPromptOptions
from ..compaction import (
    should_compact,
    prepare_compaction,
    compact,
    estimate_context_tokens,
    CompactionResult,
)
from ..tools import create_coding_tools
from .model_resolver import ModelResolver, ResolvedModel, resolve_model


# Event types
AgentSessionEvent = Literal[
    "turn_start",
    "turn_end",
    "message",
    "tool_call",
    "tool_result",
    "thinking",
    "text",
    "error",
    "compaction_start",
    "compaction_end",
]


@dataclass
class PromptOptions:
    """Options for prompting the agent."""

    images: list[str] = field(default_factory=list)
    """Image paths or URLs to include."""

    no_tools: bool = False
    """Disable tool use for this prompt."""

    thinking_level: str | None = None
    """Override thinking level for this prompt."""


@dataclass
class PromptResult:
    """Result from prompting the agent."""

    response: str
    """Final text response."""

    tool_calls: int
    """Number of tool calls made."""

    tokens_used: int
    """Tokens used in this turn."""

    compacted: bool
    """Whether compaction occurred."""


@dataclass
class AgentSessionConfig:
    """Configuration for agent session."""

    cwd: str | Path | None = None
    """Working directory."""

    model: str = "sonnet"
    """Model name or alias."""

    thinking_level: str = "medium"
    """Default thinking level."""

    system_prompt: str | None = None
    """Custom system prompt."""

    tools: list[Any] | None = None
    """Custom tools (defaults to coding tools)."""

    auto_compact: bool = True
    """Enable automatic compaction."""

    persist_session: bool = True
    """Persist session to disk."""


class AgentSession:
    """
    High-level agent session combining:
    - Agent execution (pipy-agent)
    - Session persistence (session manager)
    - Resource loading (skills, prompts, context)
    - Compaction (context management)
    - System prompt building

    This is the main entry point for running the coding agent.
    """

    def __init__(self, config: AgentSessionConfig | None = None):
        """
        Initialize agent session.

        Args:
            config: Session configuration
        """
        self._config = config or AgentSessionConfig()
        self._cwd = Path(self._config.cwd) if self._config.cwd else Path.cwd()

        # Initialize components
        self._model_resolver = ModelResolver()
        self._resolved_model = self._model_resolver.resolve(self._config.model)

        self._settings = SettingsManager(cwd=self._cwd)
        self._session = SessionManager(cwd=self._cwd) if self._config.persist_session else None
        self._resources = DefaultResourceLoader(cwd=self._cwd)

        # Build tools
        self._tools = self._config.tools or create_coding_tools(cwd=str(self._cwd))

        # Build system prompt
        self._system_prompt = self._build_system_prompt()

        # Create agent
        self._agent = Agent(
            model=self._resolved_model.model_id,
            system_prompt=self._system_prompt,
            tools=self._tools,
        )

        # Event listeners
        self._listeners: list[Callable[[AgentSessionEvent, Any], None]] = []

        # State
        self._thinking_level = self._config.thinking_level
        self._turn_count = 0

    def _build_system_prompt(self) -> str:
        """Build system prompt from resources and config."""
        if self._config.system_prompt:
            return self._config.system_prompt

        options = BuildSystemPromptOptions(
            cwd=self._cwd,
            context_files=self._resources.get_context_files(),
            skills=self._resources.get_skills().skills,
            selected_tools=[t.name for t in self._tools] if self._tools else None,
        )
        return build_system_prompt(options)

    @property
    def model(self) -> ResolvedModel:
        """Get resolved model."""
        return self._resolved_model

    @property
    def cwd(self) -> Path:
        """Get working directory."""
        return self._cwd

    @property
    def system_prompt(self) -> str:
        """Get current system prompt."""
        return self._system_prompt

    @property
    def thinking_level(self) -> str:
        """Get current thinking level."""
        return self._thinking_level

    def set_model(self, model: str) -> None:
        """Change the model."""
        self._resolved_model = self._model_resolver.resolve(model)
        self._agent = Agent(
            model=self._resolved_model.model_id,
            system_prompt=self._system_prompt,
            tools=self._tools,
        )

    def set_thinking_level(self, level: str) -> None:
        """Change thinking level."""
        self._thinking_level = level

    def on_event(self, listener: Callable[[AgentSessionEvent, Any], None]) -> None:
        """Add event listener."""
        self._listeners.append(listener)

    def _emit(self, event: AgentSessionEvent, data: Any = None) -> None:
        """Emit event to listeners."""
        for listener in self._listeners:
            listener(event, data)

    def prompt(
        self,
        message: str,
        options: PromptOptions | None = None,
    ) -> PromptResult:
        """
        Send a prompt to the agent and get response.

        Args:
            message: User message
            options: Prompt options

        Returns:
            PromptResult with response and metadata
        """
        options = options or PromptOptions()
        self._turn_count += 1
        self._emit("turn_start", {"turn": self._turn_count})

        # Build user message
        user_msg = UserMessage(role="user", content=message)

        # Get conversation history from session
        messages = []
        if self._session:
            context = build_session_context(self._session.get_branch())
            messages = context.messages

        messages.append(user_msg)

        # Check if compaction needed
        compacted = False
        if self._config.auto_compact and self._session:
            compaction_settings = self._settings.get_compaction_settings()
            context_tokens = estimate_context_tokens(messages).tokens

            if should_compact(
                context_tokens,
                self._resolved_model.context_window,
                compaction_settings,
            ):
                self._emit("compaction_start", {})
                # Would run compaction here in full implementation
                compacted = True
                self._emit("compaction_end", {"compacted": compacted})

        # Run agent
        tool_calls = 0
        response_text = ""

        def on_event(event: AgentEvent) -> None:
            nonlocal tool_calls, response_text
            self._emit(event.type, event)

            if event.type == "tool_call":
                tool_calls += 1
            elif event.type == "text":
                response_text += event.text

        # Execute agent loop
        result = agent_loop(
            self._agent,
            messages,
            on_event=on_event,
        )

        # Save to session
        if self._session:
            self._session.add_message(user_msg)
            if result:
                self._session.add_message(result)

        self._emit("turn_end", {"turn": self._turn_count})

        # Extract response
        if result:
            for block in result.content:
                if hasattr(block, "type") and block.type == "text":
                    response_text = block.text
                    break

        return PromptResult(
            response=response_text,
            tool_calls=tool_calls,
            tokens_used=result.usage.input + result.usage.output if result and result.usage else 0,
            compacted=compacted,
        )

    def get_messages(self) -> list[Any]:
        """Get conversation messages."""
        if self._session:
            context = build_session_context(self._session.get_branch())
            return context.messages
        return []

    def clear(self) -> None:
        """Clear conversation history."""
        if self._session:
            self._session.clear()

    def export_html(self) -> str:
        """Export session to HTML."""
        # Placeholder - would implement full HTML export
        return "<html><body>Session export not implemented</body></html>"
