"""Textual TUI for pipy-coding-agent.

Provides a full-featured terminal UI with:
- StatusBar showing model/thinking/cwd
- ChatArea with streaming responses and tool call widgets
- PiEditor with @file and /command autocomplete
- Ctrl+C abort support
"""

from __future__ import annotations

import asyncio
import re
import time
from pathlib import Path
from typing import Any

from pipy_tui import (
    CombinedProvider,
    FilePathProvider,
    PiEditor,
    SlashCommand,
    SlashCommandProvider,
)
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Markdown, Static

from .agent import AgentSession

# Maximum file size to include via @file (256 KB)
MAX_FILE_SIZE = 256 * 1024

# Throttle interval for streaming text updates (seconds)
STREAM_THROTTLE = 0.05


# =============================================================================
# @file Reference Parsing
# =============================================================================


def parse_at_references(text: str, cwd: Path) -> tuple[str, str]:
    """Parse @file references from user text.

    Supports @path and @"path with spaces" syntax.

    Returns:
        (clean_text, file_context_xml) where file_context_xml contains
        <file> tags with contents, and clean_text has refs removed.
    """
    pattern = r'@"([^"]+)"|@(\S+)'
    refs: list[str] = []
    file_parts: list[str] = []

    for match in re.finditer(pattern, text):
        quoted, unquoted = match.groups()
        ref_path = quoted or unquoted
        refs.append(match.group(0))

        full_path = (cwd / ref_path).resolve()
        if not full_path.exists():
            file_parts.append(f'<file name="{ref_path}" error="File not found" />')
            continue
        if full_path.is_dir():
            file_parts.append(f'<file name="{ref_path}" error="Is a directory" />')
            continue
        try:
            size = full_path.stat().st_size
            if size > MAX_FILE_SIZE:
                file_parts.append(
                    f'<file name="{ref_path}" error="File too large ({size} bytes)" />'
                )
                continue
            content = full_path.read_text(encoding="utf-8", errors="replace")
            file_parts.append(f'<file name="{ref_path}">\n{content}\n</file>')
        except Exception as e:
            file_parts.append(f'<file name="{ref_path}" error="{e}" />')

    # Remove refs from display text
    clean = text
    for ref in refs:
        clean = clean.replace(ref, "").strip()

    file_context = "\n\n".join(file_parts) if file_parts else ""
    return clean, file_context


# =============================================================================
# Textual Messages (bridge agent events into Textual)
# =============================================================================


class AgentStreamStart(Message):
    """Agent started streaming a response."""


class AgentTextDelta(Message):
    """Streaming text delta from assistant."""

    def __init__(self, delta: str, full_text: str) -> None:
        self.delta = delta
        self.full_text = full_text
        super().__init__()


class AgentThinkingDelta(Message):
    """Streaming thinking delta."""

    def __init__(self, delta: str) -> None:
        self.delta = delta
        super().__init__()


class AgentToolStart(Message):
    """Tool execution started."""

    def __init__(self, tool_call_id: str, name: str, args: dict[str, Any]) -> None:
        self.tool_call_id = tool_call_id
        self.name = name
        self.args = args
        super().__init__()


class AgentToolEnd(Message):
    """Tool execution ended."""

    def __init__(self, tool_call_id: str, name: str, result: str, is_error: bool = False) -> None:
        self.tool_call_id = tool_call_id
        self.name = name
        self.result = result
        self.is_error = is_error
        super().__init__()


class AgentStreamEnd(Message):
    """Agent finished streaming."""

    def __init__(self, response: str, tool_calls: int) -> None:
        self.response = response
        self.tool_calls = tool_calls
        super().__init__()


class AgentError(Message):
    """Agent encountered an error."""

    def __init__(self, error: str) -> None:
        self.error = error
        super().__init__()


# =============================================================================
# Widgets
# =============================================================================


class StatusBar(Static):
    """Top status bar showing model, thinking level, and cwd."""

    model_name: reactive[str] = reactive("")
    thinking: reactive[str] = reactive("")
    cwd_path: reactive[str] = reactive("")

    def render(self) -> str:
        parts = []
        if self.model_name:
            parts.append(f"Model: {self.model_name}")
        if self.thinking:
            parts.append(f"Thinking: {self.thinking}")
        if self.cwd_path:
            parts.append(f"CWD: {self.cwd_path}")
        return " | ".join(parts) if parts else "pipy-coding-agent"

    DEFAULT_CSS = """
    StatusBar {
        dock: top;
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 1;
    }
    """


class StreamingResponse(Static):
    """Widget that displays streaming text, finalized as Markdown."""

    DEFAULT_CSS = """
    StreamingResponse {
        padding: 0 1;
        margin: 0 0 0 2;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__("", **kwargs)
        self._text = ""
        self._last_update = 0.0
        self._pending_delta = ""

    def append_text(self, delta: str) -> None:
        """Append streaming text with throttling."""
        self._text += delta
        self._pending_delta += delta
        now = time.monotonic()
        if now - self._last_update >= STREAM_THROTTLE:
            self._flush()

    def _flush(self) -> None:
        """Flush pending text to display."""
        if self._pending_delta:
            self.update(self._text)
            self._pending_delta = ""
            self._last_update = time.monotonic()

    def finalize(self) -> None:
        """Finalize: flush remaining text."""
        self._flush()

    @property
    def full_text(self) -> str:
        return self._text


class ToolCallWidget(Static):
    """Widget showing a tool call and its result."""

    DEFAULT_CSS = """
    ToolCallWidget {
        padding: 0 1;
        margin: 0 0 0 2;
        color: $text-muted;
    }
    """

    def __init__(self, tool_call_id: str, name: str, args: dict[str, Any], **kwargs) -> None:
        self._tool_call_id = tool_call_id
        self._name = name
        self._args = args
        self._result: str | None = None
        self._is_error = False
        super().__init__(self._render_content(), **kwargs)

    def _render_content(self) -> str:
        # Format args concisely
        args_str = ""
        if self._args:
            arg_parts = []
            for k, v in self._args.items():
                val = str(v)
                if len(val) > 60:
                    val = val[:57] + "..."
                arg_parts.append(f"{k}={val}")
            args_str = ", ".join(arg_parts)

        if self._result is None:
            return f"[{self._name}] {args_str} ..."
        elif self._is_error:
            result_preview = self._result[:100] + ("..." if len(self._result) > 100 else "")
            return f"[{self._name}] {args_str} -> ERROR: {result_preview}"
        else:
            result_preview = self._result[:100] + ("..." if len(self._result) > 100 else "")
            return f"[{self._name}] {args_str} -> {result_preview}"

    def set_result(self, result: str, is_error: bool = False) -> None:
        self._result = result
        self._is_error = is_error
        self.update(self._render_content())


class UserMessageWidget(Static):
    """Displays a user message."""

    DEFAULT_CSS = """
    UserMessageWidget {
        padding: 0 1;
        margin: 1 0 0 0;
        color: $accent;
    }
    """


class SystemMessageWidget(Static):
    """Displays system/info messages."""

    DEFAULT_CSS = """
    SystemMessageWidget {
        padding: 0 1;
        margin: 0 0 0 2;
        color: $text-muted;
    }
    """


class ChatArea(VerticalScroll):
    """Scrollable area containing chat messages."""

    DEFAULT_CSS = """
    ChatArea {
        height: 1fr;
        padding: 0 1;
    }
    """

    def add_user_message(self, text: str) -> None:
        widget = UserMessageWidget(f"> {text}")
        self.mount(widget)
        self.scroll_end(animate=False)

    def add_system_message(self, text: str) -> None:
        widget = SystemMessageWidget(text)
        self.mount(widget)
        self.scroll_end(animate=False)

    def add_streaming_response(self) -> StreamingResponse:
        widget = StreamingResponse()
        self.mount(widget)
        self.scroll_end(animate=False)
        return widget

    def add_tool_call(self, tool_call_id: str, name: str, args: dict[str, Any]) -> ToolCallWidget:
        widget = ToolCallWidget(tool_call_id, name, args)
        self.mount(widget)
        self.scroll_end(animate=False)
        return widget

    def finalize_response(self, streaming_widget: StreamingResponse) -> None:
        """Replace streaming widget with finalized Markdown."""
        text = streaming_widget.full_text
        streaming_widget.finalize()
        if text:
            md = Markdown(text)
            streaming_widget.replace(md)
        self.scroll_end(animate=False)


# =============================================================================
# Main App
# =============================================================================


class PipyApp(App):
    """Textual TUI for pipy-coding-agent."""

    TITLE = "pipy-coding-agent"

    CSS = """
    Screen {
        layout: vertical;
    }

    #status-line {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }

    PiEditor {
        dock: bottom;
        min-height: 3;
        max-height: 12;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "interrupt", "Interrupt/Quit", show=False, priority=True),
    ]

    def __init__(
        self,
        session: AgentSession,
        verbose: bool = False,
        slash_commands: dict | None = None,
        handle_slash_command_fn=None,
    ) -> None:
        super().__init__()
        self.session = session
        self.verbose = verbose
        self._slash_commands = slash_commands or {}
        self._handle_slash_command_fn = handle_slash_command_fn
        self._is_streaming = False
        self._current_streaming: StreamingResponse | None = None
        self._tool_widgets: dict[str, ToolCallWidget] = {}
        self._unsubscribe: Any = None
        self._response_text = ""
        self._tool_call_count = 0

    def compose(self) -> ComposeResult:
        # Build slash command list for autocomplete
        slash_cmds = [
            SlashCommand(name=name, description=info.get("description", ""))
            for name, info in self._slash_commands.items()
        ]

        provider = CombinedProvider(
            [
                SlashCommandProvider(slash_cmds),
                FilePathProvider(self.session.cwd),
            ]
        )

        yield StatusBar(id="status-bar")
        yield ChatArea(id="chat-area")
        yield Static("Ready", id="status-line")
        yield PiEditor(
            placeholder="Type a message... (@ for files, / for commands)",
            autocomplete=provider,
            id="editor",
        )

    def on_mount(self) -> None:
        # Set status bar info
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.model_name = self.session.model.model_id
        status_bar.thinking = self.session.thinking_level
        status_bar.cwd_path = str(self.session.cwd)

        # Subscribe to session events
        self._unsubscribe = self.session.on_event(self._on_agent_event)

        # Focus the editor
        self.query_one("#editor", PiEditor).focus()

    def on_unmount(self) -> None:
        if self._unsubscribe:
            self._unsubscribe()

    # === Event Bridge (agent events -> Textual messages) ===

    def _on_agent_event(self, event_type: str, data: Any) -> None:
        """Bridge agent events into Textual messages.

        This runs on the asyncio thread, so we use call_from_thread
        to safely post messages to the Textual event loop.
        """
        try:
            if event_type == "turn_start":
                self.post_message(AgentStreamStart())
            elif event_type == "message_update":
                if hasattr(data, "assistant_event"):
                    ae = data.assistant_event
                    ae_type = getattr(ae, "type", "")
                    if ae_type == "text_delta":
                        full = ""
                        if hasattr(ae, "partial") and ae.partial:
                            from pipy_agent import TextContent

                            for block in ae.partial.content:
                                if isinstance(block, TextContent):
                                    full = block.text
                                    break
                        self.post_message(AgentTextDelta(ae.delta, full))
                    elif ae_type == "thinking_delta":
                        self.post_message(AgentThinkingDelta(ae.delta))
            elif event_type == "tool_execution_start":
                self.post_message(
                    AgentToolStart(
                        data.tool_call_id,
                        data.tool_name,
                        getattr(data, "args", {}),
                    )
                )
            elif event_type == "tool_execution_end":
                result_text = ""
                if data.result and data.result.content:
                    from pipy_agent import TextContent

                    for block in data.result.content:
                        if isinstance(block, TextContent):
                            result_text = block.text
                            break
                self.post_message(
                    AgentToolEnd(
                        data.tool_call_id,
                        data.tool_name,
                        result_text,
                        data.is_error,
                    )
                )
            elif event_type == "turn_end":
                pass
            elif event_type == "error":
                error_msg = str(data) if data else "Unknown error"
                self.post_message(AgentError(error_msg))
        except Exception:
            pass  # Don't crash the event bridge

    # === Textual Message Handlers ===

    @on(AgentStreamStart)
    def on_stream_start(self, event: AgentStreamStart) -> None:
        chat = self.query_one("#chat-area", ChatArea)
        self._current_streaming = chat.add_streaming_response()
        self._response_text = ""
        self._tool_call_count = 0
        self._tool_widgets.clear()

    @on(AgentTextDelta)
    def on_text_delta(self, event: AgentTextDelta) -> None:
        if self._current_streaming:
            self._current_streaming.append_text(event.delta)
            self._response_text = event.full_text
            # Auto-scroll
            chat = self.query_one("#chat-area", ChatArea)
            chat.scroll_end(animate=False)

    @on(AgentThinkingDelta)
    def on_thinking_delta(self, event: AgentThinkingDelta) -> None:
        status = self.query_one("#status-line", Static)
        status.update("Thinking...")

    @on(AgentToolStart)
    def on_tool_start(self, event: AgentToolStart) -> None:
        chat = self.query_one("#chat-area", ChatArea)
        widget = chat.add_tool_call(event.tool_call_id, event.name, event.args)
        self._tool_widgets[event.tool_call_id] = widget
        self._tool_call_count += 1
        status = self.query_one("#status-line", Static)
        status.update(f"Running tool: {event.name}...")

    @on(AgentToolEnd)
    def on_tool_end(self, event: AgentToolEnd) -> None:
        widget = self._tool_widgets.get(event.tool_call_id)
        if widget:
            widget.set_result(event.result, event.is_error)
        status = self.query_one("#status-line", Static)
        status.update(f"{self._tool_call_count} tool call(s)")

    @on(AgentStreamEnd)
    def on_stream_end(self, event: AgentStreamEnd) -> None:
        if self._current_streaming:
            chat = self.query_one("#chat-area", ChatArea)
            chat.finalize_response(self._current_streaming)
            self._current_streaming = None

        self._is_streaming = False
        editor = self.query_one("#editor", PiEditor)
        editor.disabled = False
        editor.focus()

        # Update status
        status = self.query_one("#status-line", Static)
        parts = ["Ready"]
        if event.tool_calls > 0:
            parts.append(f"{event.tool_calls} tool call(s)")
        status.update(" | ".join(parts))

    @on(AgentError)
    def on_agent_error(self, event: AgentError) -> None:
        chat = self.query_one("#chat-area", ChatArea)
        chat.add_system_message(f"Error: {event.error}")
        self._is_streaming = False
        editor = self.query_one("#editor", PiEditor)
        editor.disabled = False
        editor.focus()
        status = self.query_one("#status-line", Static)
        status.update("Error occurred")

    # === User Input ===

    @on(PiEditor.Submitted)
    def on_editor_submitted(self, event: PiEditor.Submitted) -> None:
        text = event.text.strip()
        if not text:
            return

        # Add to editor history
        editor = self.query_one("#editor", PiEditor)
        editor.add_to_history(text)

        # Check for slash commands
        if text.startswith("/"):
            self._handle_slash(text)
            return

        # Parse @file references
        clean_text, file_context = parse_at_references(text, self.session.cwd)

        # Display user message
        chat = self.query_one("#chat-area", ChatArea)
        chat.add_user_message(text)

        # Build the actual prompt with file context
        prompt = clean_text
        if file_context:
            prompt = f"{file_context}\n\n{clean_text}"

        # Disable editor during streaming
        editor.disabled = True
        self._is_streaming = True

        status = self.query_one("#status-line", Static)
        status.update(f"Sending to {self.session.model.model_id}...")

        # Run prompt as worker
        self._run_prompt(prompt)

    @work(exclusive=True, thread=False)
    async def _run_prompt(self, prompt: str) -> None:
        """Run the agent prompt as a Textual worker."""
        try:
            result = await self.session.aprompt(prompt)
            self.post_message(AgentStreamEnd(result.response, result.tool_calls))
        except Exception as e:
            self.post_message(AgentError(str(e)))

    def _handle_slash(self, text: str) -> None:
        """Handle slash command input."""
        chat = self.query_one("#chat-area", ChatArea)

        parts = text[1:].split(maxsplit=1)
        cmd_name = parts[0].lower()
        cmd_args = parts[1] if len(parts) > 1 else ""

        if cmd_name in ("quit", "exit"):
            self.exit()
            return

        if cmd_name in ("login", "logout"):
            chat.add_system_message(
                f"/{cmd_name} requires terminal input. "
                "Use --no-tui mode: pipy-coding-agent --no-tui"
            )
            return

        if cmd_name not in self._slash_commands:
            chat.add_system_message(f"Unknown command: /{cmd_name}. Type /help for commands.")
            return

        # Execute the slash command, capturing print output
        cmd_info = self._slash_commands[cmd_name]
        import contextlib
        import io

        f = io.StringIO()
        try:
            with contextlib.redirect_stdout(f):
                result = cmd_info["func"](self.session, cmd_args)
                # Handle async commands
                if asyncio.iscoroutine(result):
                    # Can't easily run async slash commands in TUI context
                    chat.add_system_message(
                        f"/{cmd_name} requires terminal mode. "
                        "Use --no-tui mode: pipy-coding-agent --no-tui"
                    )
                    return

            output = f.getvalue().strip()
            if output:
                chat.add_system_message(output)

            # Update status bar if model/thinking changed
            status_bar = self.query_one("#status-bar", StatusBar)
            status_bar.model_name = self.session.model.model_id
            status_bar.thinking = self.session.thinking_level

            if result is False:
                self.exit()
        except Exception as e:
            chat.add_system_message(f"Error running /{cmd_name}: {e}")

    # === Interrupt ===

    def action_interrupt(self) -> None:
        """Handle Ctrl+C: abort streaming if active, else quit."""
        if self._is_streaming:
            self.session.abort()
            self._is_streaming = False

            if self._current_streaming:
                chat = self.query_one("#chat-area", ChatArea)
                chat.finalize_response(self._current_streaming)
                self._current_streaming = None

            chat = self.query_one("#chat-area", ChatArea)
            chat.add_system_message("Aborted.")

            editor = self.query_one("#editor", PiEditor)
            editor.disabled = False
            editor.focus()

            status = self.query_one("#status-line", Static)
            status.update("Aborted")
        else:
            self.exit()


def run_tui(
    session: AgentSession,
    verbose: bool = False,
    slash_commands: dict | None = None,
    handle_slash_command_fn=None,
) -> None:
    """Launch the TUI application."""
    app = PipyApp(
        session=session,
        verbose=verbose,
        slash_commands=slash_commands,
        handle_slash_command_fn=handle_slash_command_fn,
    )
    app.run()
