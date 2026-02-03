"""Abort signal and controller for async cancellation."""

from collections.abc import Callable


class AbortSignal:
    """Signal for cooperative cancellation of async operations.

    Similar to JavaScript's AbortSignal / Python's asyncio.Event,
    but with a callback mechanism for cleanup.

    Example:
        controller = AbortController()

        async def long_operation(signal: AbortSignal):
            while not signal.aborted:
                await do_work()
                if signal.aborted:
                    break

        # Start operation
        task = asyncio.create_task(long_operation(controller.signal))

        # Cancel it
        controller.abort()
    """

    def __init__(self):
        self._aborted = False
        self._callbacks: list[Callable[[], None]] = []

    @property
    def aborted(self) -> bool:
        """True if abort() has been called."""
        return self._aborted

    def _abort(self) -> None:
        """Internal: called by AbortController."""
        if self._aborted:
            return
        self._aborted = True
        for cb in self._callbacks:
            try:
                cb()
            except Exception:
                pass  # Don't let callback errors propagate

    def on_abort(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Register a callback to run when aborted.

        If already aborted, callback runs immediately.
        Returns an unsubscribe function.

        Example:
            def cleanup():
                print("Cancelled!")

            unsubscribe = signal.on_abort(cleanup)
            # Later: unsubscribe()
        """
        if self._aborted:
            callback()
        else:
            self._callbacks.append(callback)

        def unsubscribe():
            if callback in self._callbacks:
                self._callbacks.remove(callback)

        return unsubscribe

    def throw_if_aborted(self) -> None:
        """Raise AbortError if aborted.

        Useful for checking at await points:
            signal.throw_if_aborted()
            await some_operation()
        """
        if self._aborted:
            raise AbortError("Operation was aborted")


class AbortController:
    """Controller that creates and triggers an AbortSignal.

    Example:
        controller = AbortController()

        # Pass signal to operations
        await fetch(url, signal=controller.signal)

        # Cancel all operations using this signal
        controller.abort()
    """

    def __init__(self):
        self._signal = AbortSignal()

    @property
    def signal(self) -> AbortSignal:
        """The AbortSignal controlled by this controller."""
        return self._signal

    def abort(self) -> None:
        """Abort all operations using this controller's signal."""
        self._signal._abort()


class AbortError(Exception):
    """Raised when an operation is aborted."""

    pass
