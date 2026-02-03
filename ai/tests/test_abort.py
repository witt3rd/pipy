"""Tests for abort module."""

import pytest

from pipy_ai import AbortController, AbortError, AbortSignal


class TestAbortSignal:
    def test_initial_state(self):
        signal = AbortSignal()
        assert signal.aborted is False

    def test_cannot_abort_directly(self):
        signal = AbortSignal()
        # _abort is internal, but signal has no public abort method
        assert not hasattr(signal, "abort") or not callable(getattr(signal, "abort", None))

    def test_throw_if_aborted_when_not_aborted(self):
        signal = AbortSignal()
        signal.throw_if_aborted()  # Should not raise

    def test_throw_if_aborted_when_aborted(self):
        controller = AbortController()
        controller.abort()
        with pytest.raises(AbortError):
            controller.signal.throw_if_aborted()


class TestAbortController:
    def test_creates_signal(self):
        controller = AbortController()
        assert isinstance(controller.signal, AbortSignal)
        assert controller.signal.aborted is False

    def test_abort_sets_signal(self):
        controller = AbortController()
        controller.abort()
        assert controller.signal.aborted is True

    def test_abort_is_idempotent(self):
        controller = AbortController()
        controller.abort()
        controller.abort()
        assert controller.signal.aborted is True


class TestAbortCallbacks:
    def test_callback_called_on_abort(self):
        controller = AbortController()
        called = []

        controller.signal.on_abort(lambda: called.append(1))
        assert called == []

        controller.abort()
        assert called == [1]

    def test_callback_called_immediately_if_already_aborted(self):
        controller = AbortController()
        controller.abort()

        called = []
        controller.signal.on_abort(lambda: called.append(1))
        assert called == [1]

    def test_multiple_callbacks(self):
        controller = AbortController()
        called = []

        controller.signal.on_abort(lambda: called.append(1))
        controller.signal.on_abort(lambda: called.append(2))
        controller.signal.on_abort(lambda: called.append(3))

        controller.abort()
        assert called == [1, 2, 3]

    def test_unsubscribe(self):
        controller = AbortController()
        called = []

        unsub = controller.signal.on_abort(lambda: called.append(1))
        unsub()

        controller.abort()
        assert called == []

    def test_callback_error_doesnt_stop_others(self):
        controller = AbortController()
        called = []

        controller.signal.on_abort(lambda: called.append(1))
        controller.signal.on_abort(lambda: (_ for _ in ()).throw(Exception("oops")))
        controller.signal.on_abort(lambda: called.append(3))

        controller.abort()  # Should not raise
        assert 1 in called
        assert 3 in called


class TestThinkingLevelOff:
    def test_thinking_level_has_off(self):
        from pipy_ai import ThinkingLevel

        assert ThinkingLevel.OFF == "off"
        assert ThinkingLevel.OFF.value == "off"
