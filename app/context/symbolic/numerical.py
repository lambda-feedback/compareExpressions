from __future__ import annotations

import math

from sympy import Basic, pi, N

from lambdafeedback.expression_parsing import read_written_number, round_to_decimal_places, round_to_significant_figures

from app.context.tolerance import values_within_tolerance
from app.evaluation_parameters import EvaluationParameters


# REMARK: 'pi' should be a reserved symbol but it is sometimes not treated as one, possibly because of input symbols.
# Replacing it by name fixes the issue but a more robust solution should be found for cases where there
# are other reserved symbols.
def replace_pi(expr: Basic) -> Basic:
    pi_symbol = pi
    for s in expr.free_symbols:
        if str(s) == 'pi':
            pi_symbol = s
    return expr.subs(pi_symbol, float(pi))


def _rounded_values_equal(rounded_response: float, rounded_answer: float) -> bool:
    # Allows for the last bit of the rounded float, e.g. when 0.1 + 0.2 is rounded
    return abs(rounded_response - rounded_answer) <= math.ulp(abs(rounded_answer))


def sig_figs_match(response_string: str, response_value: float, answer_value: float, sig_figs: int) -> bool:
    """
    Whether `response_string`, as written, is the answer to exactly `sig_figs` significant figures:
    it is a plain number, its value rounds to the same value as the answer, and it is written to `sig_figs`
    significant figures (`response_value`, a float, has lost the trailing zeros that count).
    A zero response is not checked for precision.
    """
    written = read_written_number(response_string)
    if written is None:
        return False

    rounded_answer = round_to_significant_figures(answer_value, sig_figs)
    rounded_response = round_to_significant_figures(response_value, sig_figs)
    numeric_correct = _rounded_values_equal(rounded_response, rounded_answer)

    precision_correct = response_value == 0 or written.significant_figures == sig_figs

    return numeric_correct and precision_correct


def decimal_places_match(response_string: str, response_value: float, answer_value: float, decimal_places: int) -> bool:
    """
    Whether `response_string`, as written, is the answer to exactly `decimal_places` decimal places:
    it is a plain number, its value rounds to the same value as the answer, and it is written to
    `decimal_places` decimal places.
    """
    written = read_written_number(response_string)
    if written is None:
        return False

    rounded_answer = float(round_to_decimal_places(answer_value, decimal_places))
    rounded_response = float(round_to_decimal_places(response_value, decimal_places))
    numeric_correct = _rounded_values_equal(rounded_response, rounded_answer)

    # Unlike sig_figs_match, a zero response is checked too: "0" has 0 decimal places and "0.00" has 2
    precision_correct = written.decimal_places == decimal_places

    return numeric_correct and precision_correct


def matches_written_precision(
    response_expr: Basic, answer_expr: Basic, response_string: str, parameters: EvaluationParameters
) -> bool:
    """
    Whether the response, written as `response_string`, is the answer to the `sig_figs` significant figures
    or `dp` decimal places in `parameters` (one of them is set). False if either side is not a number.
    """
    try:
        response_value = float(N(replace_pi(response_expr)))
        answer_value = float(N(replace_pi(answer_expr)))
    except TypeError:
        return False

    if parameters.sig_figs is not None:
        return sig_figs_match(response_string, response_value, answer_value, parameters.sig_figs)
    elif parameters.dp is not None:
        return decimal_places_match(response_string, response_value, answer_value, parameters.dp)
    return False


def compare_numerically(lhs_expr: Basic, rhs_expr: Basic, parameters: EvaluationParameters) -> bool:
    """
    Compares `lhs_expr` and `rhs_expr` numerically using the `atol` and `rtol` parameters.

    Returns False if numerical comparison is not enabled (`numerical` is not set and neither
    `atol` nor `rtol` is positive), otherwise whether the difference is within the tolerances.
    """
    if not (parameters.numerical
            or float(parameters.rtol) > 0
            or float(parameters.atol) > 0):
        return False

    # NOTE: This code assumes that the left hand side is the response and the right hand side is the answer
    # Separates LHS and RHS, parses and evaluates them
    res = N(replace_pi(lhs_expr))
    ans = N(replace_pi(rhs_expr))
    return values_within_tolerance(res, ans, float(parameters.rtol), float(parameters.atol))
