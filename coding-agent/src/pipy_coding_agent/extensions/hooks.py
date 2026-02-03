"""Extension hook system."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable


class HookType(str, Enum):
    """Available hook types."""

    # Session lifecycle
    SESSION_START = "session_start"
    SESSION_END = "session_end"

    # Turn lifecycle
    TURN_START = "turn_start"
    TURN_END = "turn_end"

    # Message processing
    BEFORE_PROMPT = "before_prompt"
    AFTER_RESPONSE = "after_response"

    # Compaction
    BEFORE_COMPACT = "before_compact"
    AFTER_COMPACT = "after_compact"

    # Tool execution
    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"

    # Context
    TRANSFORM_CONTEXT = "transform_context"
    BUILD_SYSTEM_PROMPT = "build_system_prompt"


# Type alias for hook handlers
HookHandler = Callable[..., Any | Awaitable[Any]]


@dataclass
class RegisteredHook:
    """A registered hook handler."""

    hook_type: HookType
    handler: HookHandler
    priority: int = 0
    extension_name: str = ""


class ExtensionHooks:
    """
    Manages extension hooks.

    Allows extensions to register handlers for various lifecycle events.
    Handlers are called in priority order (higher priority first).
    """

    def __init__(self):
        """Initialize hooks manager."""
        self._hooks: dict[HookType, list[RegisteredHook]] = {
            hook_type: [] for hook_type in HookType
        }

    def register(
        self,
        hook_type: HookType,
        handler: HookHandler,
        priority: int = 0,
        extension_name: str = "",
    ) -> None:
        """
        Register a hook handler.

        Args:
            hook_type: Type of hook
            handler: Handler function
            priority: Priority (higher = called first)
            extension_name: Name of registering extension
        """
        registered = RegisteredHook(
            hook_type=hook_type,
            handler=handler,
            priority=priority,
            extension_name=extension_name,
        )
        self._hooks[hook_type].append(registered)
        # Sort by priority (descending)
        self._hooks[hook_type].sort(key=lambda h: -h.priority)

    def unregister(
        self,
        hook_type: HookType,
        handler: HookHandler | None = None,
        extension_name: str | None = None,
    ) -> int:
        """
        Unregister hook handlers.

        Args:
            hook_type: Type of hook
            handler: Specific handler to remove (optional)
            extension_name: Remove all hooks from extension (optional)

        Returns:
            Number of handlers removed
        """
        original_count = len(self._hooks[hook_type])

        if handler:
            self._hooks[hook_type] = [
                h for h in self._hooks[hook_type]
                if h.handler != handler
            ]
        elif extension_name:
            self._hooks[hook_type] = [
                h for h in self._hooks[hook_type]
                if h.extension_name != extension_name
            ]

        return original_count - len(self._hooks[hook_type])

    def get_handlers(self, hook_type: HookType) -> list[RegisteredHook]:
        """Get all handlers for a hook type."""
        return self._hooks[hook_type].copy()

    async def call_async(
        self,
        hook_type: HookType,
        *args: Any,
        **kwargs: Any,
    ) -> list[Any]:
        """
        Call all handlers for a hook (async).

        Args:
            hook_type: Type of hook
            *args: Arguments to pass to handlers
            **kwargs: Keyword arguments to pass to handlers

        Returns:
            List of results from handlers
        """
        import asyncio

        results = []
        for hook in self._hooks[hook_type]:
            try:
                result = hook.handler(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    result = await result
                results.append(result)
            except Exception as e:
                # Log but don't stop other handlers
                print(f"Hook error ({hook.extension_name}): {e}")
                results.append(None)

        return results

    def call_sync(
        self,
        hook_type: HookType,
        *args: Any,
        **kwargs: Any,
    ) -> list[Any]:
        """
        Call all handlers for a hook (sync only).

        Args:
            hook_type: Type of hook
            *args: Arguments to pass to handlers
            **kwargs: Keyword arguments to pass to handlers

        Returns:
            List of results from handlers
        """
        results = []
        for hook in self._hooks[hook_type]:
            try:
                result = hook.handler(*args, **kwargs)
                results.append(result)
            except Exception as e:
                print(f"Hook error ({hook.extension_name}): {e}")
                results.append(None)

        return results

    def has_handlers(self, hook_type: HookType) -> bool:
        """Check if hook type has any handlers."""
        return len(self._hooks[hook_type]) > 0

    def clear(self, hook_type: HookType | None = None) -> None:
        """
        Clear handlers.

        Args:
            hook_type: Specific hook to clear (None = all)
        """
        if hook_type:
            self._hooks[hook_type] = []
        else:
            for ht in HookType:
                self._hooks[ht] = []
