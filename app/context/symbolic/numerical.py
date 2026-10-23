from __future__ import annotations

from sympy import Basic, pi, N

from app.evaluation_parameters import EvaluationParameters


def replace_pi(expr: Basic, value: float | Basic = float(pi)) -> Basic:
    # REMARK: 'pi' should be a reserved symbol but it is sometimes not treated as one, possibly because of input symbols.
    # Replacing it with its value fixes the issue but a more robust solution should be found for cases where there
    # are other reserved symbols.
    pi_symbol = pi
    for s in expr.free_symbols:
        if str(s) == 'pi':
            pi_symbol = s
    return expr.subs(pi_symbol, value)


def numerically_equal(lhs_expr: Basic, rhs_expr: Basic) -> bool | None:
    """
    Whether `lhs_expr` and `rhs_expr` are equal when evaluated to 50 digits: compares numbers
    without simplifying them, which can take practically forever (see `app.time_budget`).

    Returns None if either contains symbols other than `pi` or can't be evaluated to a number.
    """
    lhs, rhs = replace_pi(lhs_expr, pi), replace_pi(rhs_expr, pi)
    if lhs.free_symbols or rhs.free_symbols:
        return None
    try:
        difference = abs(complex(N(lhs - rhs, 50)))
        scale = max(1.0, abs(complex(N(lhs, 50))), abs(complex(N(rhs, 50))))
    except (TypeError, ValueError, OverflowError):
        return None
    return bool(difference <= 1e-30 * scale)


def compare_numerically(lhs_expr: Basic, rhs_expr: Basic, parameters: EvaluationParameters) -> bool:
    """
    Compares `lhs_expr` and `rhs_expr` numerically using the `atol` and `rtol` parameters.

    Returns False if numerical comparison is not enabled (`numerical` is not set and neither
    `atol` nor `rtol` is positive), otherwise whether the difference is within both tolerances.
    """
    if not (parameters.numerical
            or float(parameters.rtol) > 0
            or float(parameters.atol) > 0):
        return False

    # NOTE: This code assumes that the left hand side is the response and the right hand side is the answer
    # Separates LHS and RHS, parses and evaluates them
    res = N(replace_pi(lhs_expr))
    ans = N(replace_pi(rhs_expr))
    if float(parameters.atol) > 0:
        try:
            absolute_error = abs(float(ans - res))
            error_below_atol = bool(absolute_error < float(parameters.atol))
        except TypeError:
            error_below_atol = None
    else:
        error_below_atol = True
    if float(parameters.rtol) > 0:
        try:
            relative_error = abs(float((ans - res) / ans))
            error_below_rtol = bool(relative_error < float(parameters.rtol))
        except TypeError:
            error_below_rtol = None
    else:
        error_below_rtol = True
    return error_below_atol is True and error_below_rtol is True
