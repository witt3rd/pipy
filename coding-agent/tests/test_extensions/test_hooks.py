"""Tests for extension hooks."""

import pytest

from pipy_coding_agent.extensions import (
    ExtensionHooks,
    HookType,
)


class TestHookType:
    def test_common_hooks_exist(self):
        """Test that common hooks are defined."""
        expected = [
            "SESSION_START",
            "TURN_START",
            "TURN_END",
            "BEFORE_PROMPT",
            "AFTER_RESPONSE",
        ]

        for name in expected:
            assert hasattr(HookType, name)


class TestExtensionHooks:
    def test_register_handler(self):
        """Test registering a hook handler."""
        hooks = ExtensionHooks()
        handler = lambda: "test"

        hooks.register(HookType.TURN_START, handler)

        handlers = hooks.get_handlers(HookType.TURN_START)
        assert len(handlers) == 1
        assert handlers[0].handler == handler

    def test_register_with_priority(self):
        """Test handlers are sorted by priority."""
        hooks = ExtensionHooks()

        hooks.register(HookType.TURN_START, lambda: 1, priority=10)
        hooks.register(HookType.TURN_START, lambda: 2, priority=20)
        hooks.register(HookType.TURN_START, lambda: 3, priority=5)

        handlers = hooks.get_handlers(HookType.TURN_START)
        # Higher priority first
        assert handlers[0].priority == 20
        assert handlers[1].priority == 10
        assert handlers[2].priority == 5

    def test_register_with_extension_name(self):
        """Test registering with extension name."""
        hooks = ExtensionHooks()

        hooks.register(
            HookType.TURN_START,
            lambda: "test",
            extension_name="my-extension",
        )

        handlers = hooks.get_handlers(HookType.TURN_START)
        assert handlers[0].extension_name == "my-extension"

    def test_unregister_by_handler(self):
        """Test unregistering specific handler."""
        hooks = ExtensionHooks()
        handler1 = lambda: 1
        handler2 = lambda: 2

        hooks.register(HookType.TURN_START, handler1)
        hooks.register(HookType.TURN_START, handler2)

        removed = hooks.unregister(HookType.TURN_START, handler=handler1)

        assert removed == 1
        handlers = hooks.get_handlers(HookType.TURN_START)
        assert len(handlers) == 1
        assert handlers[0].handler == handler2

    def test_unregister_by_extension(self):
        """Test unregistering by extension name."""
        hooks = ExtensionHooks()

        hooks.register(HookType.TURN_START, lambda: 1, extension_name="ext1")
        hooks.register(HookType.TURN_START, lambda: 2, extension_name="ext1")
        hooks.register(HookType.TURN_START, lambda: 3, extension_name="ext2")

        removed = hooks.unregister(HookType.TURN_START, extension_name="ext1")

        assert removed == 2
        handlers = hooks.get_handlers(HookType.TURN_START)
        assert len(handlers) == 1
        assert handlers[0].extension_name == "ext2"

    def test_call_sync(self):
        """Test calling handlers synchronously."""
        hooks = ExtensionHooks()
        results = []

        hooks.register(HookType.TURN_START, lambda x: results.append(x * 2))
        hooks.register(HookType.TURN_START, lambda x: results.append(x * 3))

        hooks.call_sync(HookType.TURN_START, 5)

        assert 10 in results
        assert 15 in results

    def test_call_sync_returns_results(self):
        """Test that call_sync returns handler results."""
        hooks = ExtensionHooks()

        hooks.register(HookType.TURN_START, lambda: "result1")
        hooks.register(HookType.TURN_START, lambda: "result2")

        results = hooks.call_sync(HookType.TURN_START)

        assert "result1" in results
        assert "result2" in results

    def test_call_sync_handles_errors(self):
        """Test that errors don't stop other handlers."""
        hooks = ExtensionHooks()

        def error_handler():
            raise ValueError("Test error")

        hooks.register(HookType.TURN_START, lambda: "before")
        hooks.register(HookType.TURN_START, error_handler)
        hooks.register(HookType.TURN_START, lambda: "after")

        results = hooks.call_sync(HookType.TURN_START)

        assert "before" in results
        assert "after" in results
        assert None in results  # Error handler returns None

    def test_has_handlers(self):
        """Test checking for handlers."""
        hooks = ExtensionHooks()

        assert hooks.has_handlers(HookType.TURN_START) is False

        hooks.register(HookType.TURN_START, lambda: None)

        assert hooks.has_handlers(HookType.TURN_START) is True

    def test_clear_specific_hook(self):
        """Test clearing specific hook."""
        hooks = ExtensionHooks()

        hooks.register(HookType.TURN_START, lambda: 1)
        hooks.register(HookType.TURN_END, lambda: 2)

        hooks.clear(HookType.TURN_START)

        assert hooks.has_handlers(HookType.TURN_START) is False
        assert hooks.has_handlers(HookType.TURN_END) is True

    def test_clear_all(self):
        """Test clearing all hooks."""
        hooks = ExtensionHooks()

        hooks.register(HookType.TURN_START, lambda: 1)
        hooks.register(HookType.TURN_END, lambda: 2)
        hooks.register(HookType.SESSION_START, lambda: 3)

        hooks.clear()

        assert hooks.has_handlers(HookType.TURN_START) is False
        assert hooks.has_handlers(HookType.TURN_END) is False
        assert hooks.has_handlers(HookType.SESSION_START) is False


@pytest.mark.asyncio
class TestExtensionHooksAsync:
    async def test_call_async(self):
        """Test calling handlers asynchronously."""
        hooks = ExtensionHooks()

        async def async_handler(x):
            return x * 2

        def sync_handler(x):
            return x * 3

        hooks.register(HookType.TURN_START, async_handler)
        hooks.register(HookType.TURN_START, sync_handler)

        results = await hooks.call_async(HookType.TURN_START, 5)

        assert 10 in results
        assert 15 in results
