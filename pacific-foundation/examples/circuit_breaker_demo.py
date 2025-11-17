"""
Demo for ncm_foundation.core.messaging.circuit_breaker.CircuitBreaker
Run with: PYTHONPATH=src python examples/circuit_breaker_demo.py
"""

import asyncio
import importlib.util
import logging
import os
import random
import sys
import time

"""
Prefer importing CircuitBreaker as a normal package module when the package
is available on PYTHONPATH or installed. If the package isn't importable
(for example when running the example directly from the repository), fall
back to loading the module by file path so the demo remains self-contained.
"""

try:
    # Preferred: package import (works when running with PYTHONPATH=src or
    # after `pip install -e .` from the project root)
    from ncm_foundation.core.messaging.circuit_breaker import (
        CircuitBreaker,
        CircuitState,
    )
except Exception:
    # Fallback: load by file path so the demo can be executed directly from
    # the repo without installing the package or adding PYTHONPATH.
    HERE = os.path.dirname(os.path.dirname(__file__))  # project root
    CIRCUIT_PATH = os.path.join(
        HERE, "src", "ncm_foundation", "core", "messaging", "circuit_breaker.py"
    )

    spec = importlib.util.spec_from_file_location("circuit_breaker", CIRCUIT_PATH)
    cb_mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = cb_mod
    spec.loader.exec_module(cb_mod)

    CircuitBreaker = cb_mod.CircuitBreaker
    CircuitState = cb_mod.CircuitState

# Simple logger for demo output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("demo")


async def flaky_operation(success_rate=0.5, delay=0.1):
    """Simulate an async operation that fails sometimes."""
    await asyncio.sleep(delay)
    if random.random() > success_rate:
        raise RuntimeError("simulated transient error")
    return "ok"


async def main():
    cb = CircuitBreaker(
        failure_threshold=3, recovery_timeout=2.0, expected_exception=RuntimeError
    )

    print("Starting demo: will call flaky_operation repeatedly")

    for i in range(12):
        try:
            result = await cb.call(flaky_operation, success_rate=0.4, delay=0.05)
            print(f"Call {i}: success -> {result} | state={cb.get_state().value}")
        except Exception as e:
            print(f"Call {i}: failed -> {e} | state={cb.get_state().value}")

        # show transition waiting behavior when OPEN
        if cb.get_state() == CircuitState.OPEN:
            print(
                "Circuit is OPEN; waiting before next attempt to allow recovery timeout to pass"
            )
            # wait a bit less than recovery timeout to show blocked behavior
            time.sleep(1.0)

        # small pause between calls
        await asyncio.sleep(0.1)

    # wait long enough for recovery timeout, then attempt a call to go to HALF_OPEN
    print("Waiting for recovery timeout + small buffer to allow reset attempt...")
    await asyncio.sleep(2.5)

    try:
        result = await cb.call(flaky_operation, success_rate=1.0, delay=0.01)
        print(f"Post-timeout call: success -> {result} | state={cb.get_state().value}")
    except Exception as e:
        print(f"Post-timeout call: failed -> {e} | state={cb.get_state().value}")

    # demonstrate manual reset
    cb.reset()
    print(f"After manual reset: state={cb.get_state().value}")


if __name__ == "__main__":
    asyncio.run(main())
