"""
    Time budgets for SymPy work that can run practically forever.

    Simplifying can build huge exact numbers: `simplify` calls `logcombine`,
    which writes the coefficient of `-10**8*log(10)/pi` into the logarithm as
    `log(10**(-10**8))`, a number of a hundred million digits. A budget
    interrupts such work with SIGALRM, so the request still gets a grade
    instead of running into the Lambda timeout.

    Budgets nest: the timer is set for the earliest deadline, and each budget
    only stops the work for its own expiry, so an outer budget's expiry
    passes through inner ones. Off the main thread, where signals can't be
    handled, a budget does nothing.
"""
import signal
import threading
import time
from contextlib import contextmanager

REQUEST_BUDGET = 60
"""Seconds for evaluating one request, well within the 120 s Lambda timeout."""

COMPARISON_BUDGET = 5
"""Seconds for one symbolic comparison (or simplification) before falling back."""


class TimeBudgetExceeded(BaseException):
    """
        Raised when `budget` expires. A `BaseException`, so the `except Exception`
        around many SymPy calls doesn't swallow it.
    """
    def __init__(self, budget):
        super().__init__(f"Time budget of {budget.seconds} s exceeded.")
        self.budget = budget


class Budget:
    def __init__(self, seconds):
        self.seconds = seconds
        self.deadline = time.monotonic() + seconds
        self.exceeded = False


_active = []  # budgets in force, outermost first


def _arm_timer():
    if len(_active) > 0:
        earliest = min(budget.deadline for budget in _active)
        signal.setitimer(signal.ITIMER_REAL, max(earliest - time.monotonic(), 1e-3))
    else:
        signal.setitimer(signal.ITIMER_REAL, 0)


def _expire(signum, frame):
    if len(_active) == 0:
        return
    earliest = min(_active, key=lambda budget: budget.deadline)
    if earliest.deadline > time.monotonic() + 0.01:
        # The budget the timer was set for has ended since; wait for the next one
        _arm_timer()
        return
    raise TimeBudgetExceeded(earliest)


@contextmanager
def time_budget(seconds):
    """
        Stop the work in the `with` block after `seconds`. Yields a `Budget`
        whose `exceeded` is set if it was stopped; the block's own assignments
        after that point are skipped.
    """
    budget = Budget(seconds)
    if threading.current_thread() is not threading.main_thread():
        yield budget
        return
    previous_handler = None
    if len(_active) == 0:
        previous_handler = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, _expire)
    _active.append(budget)
    _arm_timer()
    try:
        yield budget
    except TimeBudgetExceeded as e:
        if e.budget is not budget:
            raise
        budget.exceeded = True
    finally:
        _active.remove(budget)
        _arm_timer()
        if len(_active) == 0:
            signal.signal(signal.SIGALRM, signal.SIG_DFL if previous_handler is None else previous_handler)


def request_budget():
    return time_budget(REQUEST_BUDGET)


def comparison_budget():
    return time_budget(COMPARISON_BUDGET)
