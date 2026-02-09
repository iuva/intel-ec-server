import asyncio
import time
import sys
import os
from unittest.mock import MagicMock

# Add service root to path
service_root = os.path.abspath(os.path.join(os.getcwd(), "services/host-service"))
sys.path.insert(0, service_root)

# Mock shared modules to avoid dependency issues (like missing redis)
shared_mock = MagicMock()
loguru_config_mock = MagicMock()
logger_mock = MagicMock()
loguru_config_mock.get_logger.return_value = logger_mock

# Setup mocks in sys.modules
sys.modules["shared"] = shared_mock
sys.modules["shared.common"] = shared_mock
sys.modules["shared.common.loguru_config"] = loguru_config_mock

print("Mocked shared.common.loguru_config to bypass dependencies.")

try:
    from app.utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError, CircuitBreakerState
except ImportError as e:
    print(f"Import failed: {e}")
    # Try alternate structure failure fallback
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from app.utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError, CircuitBreakerState


async def test_circuit_breaker_logic():
    print("Starting Circuit Breaker Test...")
    # Setup
    threshold = 5
    window = 2.0  # short window for testing
    recovery = 2.0  # short recovery for testing
    cb = CircuitBreaker(failure_threshold=threshold, failure_window=window, recovery_timeout=recovery)

    async def succeeding_func():
        return "success"

    async def failing_func():
        raise ValueError("failed")

    # 1. Normal calls pass
    print("1. Testing normal calls...")
    assert await cb.call(succeeding_func) == "success"
    assert cb.state == CircuitBreakerState.CLOSED
    print("   Passed.")

    # 2. Accumulate failures
    print("2. Testing failure accumulation...")
    for i in range(threshold - 1):
        try:
            await cb.call(failing_func)
        except ValueError:
            pass
        assert cb.state == CircuitBreakerState.CLOSED
        assert len(cb.failure_timestamps) == i + 1
    print("   Passed.")

    # 3. Trigger Open
    print("3. Testing circuit open...")
    try:
        await cb.call(failing_func)
    except ValueError:
        pass

    assert cb.state == CircuitBreakerState.OPEN
    assert cb.opened_at > 0
    print("   Passed (Circuit is OPEN).")

    # 4. Call while Open -> CircuitBreakerOpenError
    print("4. Testing rejection while open...")
    try:
        await cb.call(succeeding_func)
        print("   FAILED: Should have raised CircuitBreakerOpenError")
    except CircuitBreakerOpenError:
        print("   Passed (Caught CircuitBreakerOpenError).")
    except Exception as e:
        print(f"   FAILED: Caught wrong exception {type(e)}")

    # 5. Wait for recovery
    print(f"5. Waiting {recovery + 0.1}s for recovery...")
    await asyncio.sleep(recovery + 0.1)

    # 6. Half-Open transition on next call
    print("6. Testing Half-Open transition...")
    assert await cb.call(succeeding_func) == "success"
    assert cb.state == CircuitBreakerState.CLOSED
    assert len(cb.failure_timestamps) == 0
    print("   Passed (Circuit Closed).")

    # 7. Test window expiration logic
    print("7. Testing window expiration...")
    # Fail 4 times
    for _ in range(threshold - 1):
        try:
            await cb.call(failing_func)
        except ValueError:
            pass

    # Wait for window to pass
    print(f"   Waiting {window + 0.1}s for window expiration...")
    await asyncio.sleep(window + 0.1)

    # Fail 5th time (but 1st failure was long ago)
    try:
        await cb.call(failing_func)
    except ValueError:
        pass

    assert cb.state == CircuitBreakerState.CLOSED
    print("   Passed (Circuit remained CLOSED due to window expiration).")

    print("All tests passed!")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test_circuit_breaker_logic())
