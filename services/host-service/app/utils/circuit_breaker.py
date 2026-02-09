"""
Circuit Breaker Implementation
"""

import time
import asyncio
from enum import Enum
from typing import Callable, Any
from collections import deque

from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


class CircuitBreakerState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open"""

    pass


class CircuitBreaker:
    """
    Circuit Breaker implementation based on failure count and time window.

    Rules:
    1. If failed {failure_threshold} times consecutively within {failure_window} seconds, open the circuit.
    2. After {recovery_timeout} seconds in OPEN state, transition to HALF_OPEN.
    3. In HALF_OPEN state, allow one request. If successful, close circuit. If failed, open circuit again.
    """

    def __init__(self, failure_threshold: int = 5, failure_window: float = 30.0, recovery_timeout: float = 60.0):
        """
        Initialize Circuit Breaker

        Args:
            failure_threshold: Number of consecutive failures to trigger open state
            failure_window: Time window in seconds to count failures
            recovery_timeout: Time in seconds to wait before trying to recover
        """
        self.failure_threshold = failure_threshold
        self.failure_window = failure_window
        self.recovery_timeout = recovery_timeout

        self.state = CircuitBreakerState.CLOSED
        # Store timestamps of consecutive failures
        self.failure_timestamps: deque = deque(maxlen=failure_threshold)
        self.opened_at = 0.0

        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection
        """
        await self._before_call()

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            # Re-raise CircuitBreakerOpenError immediately without counting as failure
            if isinstance(e, CircuitBreakerOpenError):
                raise e

            await self._on_failure()
            raise e

    async def _before_call(self):
        """Check status before calling"""
        async with self._lock:
            current_time = time.time()

            if self.state == CircuitBreakerState.OPEN:
                if current_time - self.opened_at > self.recovery_timeout:
                    self._transition_to_half_open()
                else:
                    logger.warning(
                        "Circuit breaker is OPEN",
                        extra={
                            "state": self.state.value,
                            "opened_at": self.opened_at,
                            "retry_after": round(self.recovery_timeout - (current_time - self.opened_at), 2),
                        },
                    )
                    raise CircuitBreakerOpenError("Circuit breaker is OPEN")

            # In HALF_OPEN, we proceed.

    async def _on_success(self):
        """Handle success"""
        async with self._lock:
            if self.state == CircuitBreakerState.HALF_OPEN:
                self._transition_to_closed()
            elif self.state == CircuitBreakerState.CLOSED:
                # Reset failure count on any success in CLOSED state ensures we only count consecutive failures
                if self.failure_timestamps:
                    self.failure_timestamps.clear()

    async def _on_failure(self):
        """Handle failure"""
        async with self._lock:
            current_time = time.time()

            if self.state == CircuitBreakerState.HALF_OPEN:
                # Failed in HALF_OPEN -> Go back to OPEN
                self._transition_to_open()
                return

            if self.state == CircuitBreakerState.CLOSED:
                self.failure_timestamps.append(current_time)

                # Check if threshold reached
                if len(self.failure_timestamps) >= self.failure_threshold:
                    first_failure = self.failure_timestamps[0]

                    # Check if within window
                    if current_time - first_failure <= self.failure_window:
                        self._transition_to_open()
                    else:
                        # Failures span more than 30s.
                        # Since it's a sliding window of *last* 5 consecutive failures,
                        # we keep them in buffer.
                        pass

    def _transition_to_open(self):
        self.state = CircuitBreakerState.OPEN
        self.opened_at = time.time()
        self.failure_timestamps.clear()

        logger.warning(
            "Circuit breaker transitioned to OPEN state",
            extra={
                "threshold": self.failure_threshold,
                "window": self.failure_window,
                "recovery_timeout": self.recovery_timeout,
            },
        )

    def _transition_to_half_open(self):
        self.state = CircuitBreakerState.HALF_OPEN
        logger.info("Circuit breaker transitioned to HALF_OPEN state")

    def _transition_to_closed(self):
        self.state = CircuitBreakerState.CLOSED
        self.failure_timestamps.clear()
        self.opened_at = 0.0
        logger.info("Circuit breaker transitioned to CLOSED state")
