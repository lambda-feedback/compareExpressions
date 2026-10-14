import signal
import threading
import time

import pytest

from ..time_budget import time_budget


def busy(seconds):
    """Python-level work (SIGALRM is handled between bytecodes, like during SymPy's loops)."""
    end = time.monotonic()+seconds
    count = 0
    while time.monotonic() < end:
        count += 1
    return count


def test_work_within_budget_finishes():
    with time_budget(1) as budget:
        result = busy(0.01)
    assert result > 0
    assert budget.exceeded is False


def test_expired_budget_stops_work():
    result = None
    start = time.monotonic()
    with time_budget(0.1) as budget:
        result = busy(5)
    assert result is None
    assert budget.exceeded is True
    assert time.monotonic()-start < 1


def test_expired_budget_is_not_swallowed_by_except_exception():
    with time_budget(0.1) as budget:
        try:
            busy(5)
        except Exception:
            pytest.fail("TimeBudgetExceeded was caught as an Exception")
    assert budget.exceeded is True


def test_inner_budget_expires_inside_outer():
    with time_budget(5) as outer:
        with time_budget(0.1) as inner:
            busy(5)
        busy(0.01)
    assert inner.exceeded is True
    assert outer.exceeded is False


def test_outer_budget_expiry_passes_through_inner():
    with time_budget(0.1) as outer:
        with time_budget(5) as inner:
            busy(5)
        pytest.fail("work after the inner budget ran after the outer budget expired")
    assert outer.exceeded is True
    assert inner.exceeded is False


def test_timer_and_handler_are_restored():
    def handler(signum, frame):
        pass
    previous = signal.signal(signal.SIGALRM, handler)
    try:
        with time_budget(0.1):
            busy(5)
        assert signal.getsignal(signal.SIGALRM) is handler
        assert signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)
    finally:
        signal.signal(signal.SIGALRM, previous)


def test_budget_does_nothing_off_the_main_thread():
    outcome = {}

    def work():
        with time_budget(0.01) as budget:
            outcome["result"] = busy(0.1)
        outcome["exceeded"] = budget.exceeded

    thread = threading.Thread(target=work)
    thread.start()
    thread.join()
    assert outcome == {"result": outcome["result"], "exceeded": False}
    assert signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)
