# flow/utils/circuit_breaker.py
"""
Circuit Breaker for the workflow nodes' external HTTP calls.

States:
  CLOSED    — normal operation, calls go through normally.
  OPEN      — circuit open, calls blocked. Waits for recovery_timeout.
  HALF_OPEN — test mode: allows one call; if it fails → OPEN, if ok → CLOSED.

Usage:
    from flow.utils.circuit_breaker import get_circuit_breaker

    breaker = get_circuit_breaker("api.example.com")
    result = await breaker.call(some_async_func, arg1, arg2)
"""
import asyncio
import time
from typing import Any, Callable
from flow.utils.logger import get_logger

logger = get_logger(__name__)


class CircuitOpenError(RuntimeError):
    """Raised when the circuit is OPEN and the call is blocked."""
    pass


class CircuitBreaker:
    CLOSED    = "closed"
    OPEN      = "open"
    HALF_OPEN = "half_open"

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
    ):
        self.name              = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout  = recovery_timeout
        self.success_threshold = success_threshold

        self._state           = self.CLOSED
        self._failure_count   = 0
        self._success_count   = 0
        self._opened_at: float | None = None
        self._lock            = asyncio.Lock()

    @property
    def state(self) -> str:
        return self._state

    async def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Runs `func` under circuit breaker protection.
        func may be sync or async; sync functions are run in a separate
        thread via asyncio.to_thread so as not to block the event loop.
        """
        async with self._lock:
            if self._state == self.OPEN:
                elapsed = time.monotonic() - (self._opened_at or 0)
                if elapsed >= self.recovery_timeout:
                    self._state         = self.HALF_OPEN
                    self._success_count = 0
                    logger.info("Circuit '%s' → HALF_OPEN após %.0fs", self.name, elapsed)
                else:
                    remaining = self.recovery_timeout - elapsed
                    raise CircuitOpenError(
                        f"Serviço '{self.name}' temporariamente indisponível. "
                        f"Nova tentativa em {remaining:.0f}s."
                    )

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = await asyncio.to_thread(func, *args, **kwargs)
        except CircuitOpenError:
            raise
        except Exception as exc:
            await self._on_failure(exc)
            raise

        await self._on_success()
        return result

    async def _on_failure(self, exc: Exception) -> None:
        async with self._lock:
            self._failure_count += 1
            if self._state == self.HALF_OPEN:
                self._state      = self.OPEN
                self._opened_at  = time.monotonic()
                logger.warning(
                    "Circuit '%s' → OPEN (falhou em HALF_OPEN): %s", self.name, exc
                )
            elif self._failure_count >= self.failure_threshold:
                self._state      = self.OPEN
                self._opened_at  = time.monotonic()
                logger.warning(
                    "Circuit '%s' → OPEN após %d falhas consecutivas: %s",
                    self.name, self._failure_count, exc,
                )

    async def _on_success(self) -> None:
        async with self._lock:
            if self._state == self.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._state         = self.CLOSED
                    self._failure_count = 0
                    logger.info(
                        "Circuit '%s' → CLOSED após %d sucessos",
                        self.name, self._success_count,
                    )
            elif self._state == self.CLOSED:
                # Gradual decay of failures on success
                self._failure_count = max(0, self._failure_count - 1)


# ── Global registry (per worker process) ──────────────────────────────────────

_registry: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    success_threshold: int = 2,
) -> CircuitBreaker:
    """Returns (or creates) a CircuitBreaker shared by name."""
    if name not in _registry:
        _registry[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            success_threshold=success_threshold,
        )
    return _registry[name]
