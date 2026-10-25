"""Equivalence of inequalities (`x > 5`, `1 < x < 5`) and not-equal relations (`x != 5`) in the answer and response."""

from __future__ import annotations

from enum import Enum

from sympy import And, Basic, GreaterThan, LessThan, Ne, StrictGreaterThan, StrictLessThan, simplify
from sympy.core.relational import Relational

from app.evaluation_parameters import EvaluationParameters

# Order relations (chainable as `1 < x < 5`).
ORDER_RELATIONS = (StrictLessThan, LessThan, StrictGreaterThan, GreaterThan)
# Non-order relations handled by the same machinery but never chained.
RELATIONS = ORDER_RELATIONS + (Ne,)


class InequalityComparison(Enum):
    """The outcome of comparing a response relation to an answer relation; the names are the criteria tag suffixes."""
    TRUE = "equivalent"
    FALSE = "not equivalent, e.g. a zero ratio, a different number of bounds or `!=` against an order operator"
    UNKNOWN = "undecidable, the ratio is not a constant or its sign is unknown"
    WRONG_DIRECTION = "the ratio is a negative constant, so the relations describe opposite regions"
    STRICTNESS_MISMATCH = "the ratio is a positive constant but one relation is strict and the other is not"
    RESPONSE_NOT_INEQUALITY = "the answer is a relation but the response is not"
    ANSWER_NOT_INEQUALITY = "the response is a relation but the answer is not"


def inequality_bounds(expr: Basic) -> list[Relational] | None:
    """
    The list of relation parts if `expr` is a single relation (`x < 5`, `x != 5`) or a conjunction
    of order inequalities (a chained inequality such as `1 < x < 5`), otherwise None.
    """
    if isinstance(expr, RELATIONS):
        return [expr]
    if isinstance(expr, And) and expr.args and all(isinstance(arg, ORDER_RELATIONS) for arg in expr.args):
        return list(expr.args)
    return None


def _constant_ratio(difference_res: Basic, difference_ans: Basic, constants: set[str]) -> Basic | None:
    """`difference_res / difference_ans` simplified, or None if it contains symbols that are not constants."""
    ratio = simplify(difference_res / difference_ans)
    if not {str(s) for s in ratio.free_symbols}.issubset(constants):
        return None
    return ratio


def _compare_not_equal(res: Relational, ans: Relational, constants: set[str]) -> InequalityComparison:
    """
    `f != g` is equivalent to `p != q` when `(f - g) / (p - q)` simplifies to a
    non-zero constant. Direction and strictness do not apply to `!=`.
    """
    difference_res = simplify(res.lhs - res.rhs)
    difference_ans = simplify(ans.lhs - ans.rhs)
    if difference_res == 0 and difference_ans == 0:
        return InequalityComparison.TRUE
    if difference_res == 0 or difference_ans == 0:
        return InequalityComparison.UNKNOWN
    ratio = _constant_ratio(difference_res, difference_ans, constants)
    if ratio is None:
        return InequalityComparison.UNKNOWN
    if ratio.is_zero:
        return InequalityComparison.FALSE
    if ratio.is_positive or ratio.is_negative:
        return InequalityComparison.TRUE
    return InequalityComparison.UNKNOWN


def _normalise(relation: Relational) -> tuple[Basic, str]:
    """`relation` rewritten as `D REL 0` with `REL` either `<` or `<=`, returned as `(D, REL)`."""
    difference = relation.lhs - relation.rhs
    operator = relation.rel_op
    if operator in (">", ">="):
        difference = -difference
        operator = "<" if operator == ">" else "<="
    return simplify(difference), operator


def _compare_single_inequality(res: Relational, ans: Relational, constants: set[str]) -> InequalityComparison:
    """
    Compare one response relation to one answer relation.

    For order operators each side `f REL g` is rewritten as `D REL 0` (all terms
    moved to one side) and normalised to `<` or `<=` by negating `D` when the
    operator is `>` or `>=`; the two are equivalent when `D_res / D_ans`
    simplifies to a positive constant and the normalised operators match. `!=` is
    delegated to `_compare_not_equal`; `!=` against an order operator is never
    equivalent.
    """
    res_is_not_equal = res.rel_op == "!="
    ans_is_not_equal = ans.rel_op == "!="
    if res_is_not_equal != ans_is_not_equal:
        return InequalityComparison.FALSE
    if res_is_not_equal and ans_is_not_equal:
        return _compare_not_equal(res, ans, constants)

    try:
        difference_res, operator_res = _normalise(res)
        difference_ans, operator_ans = _normalise(ans)
    except TypeError:
        return InequalityComparison.UNKNOWN

    # `difference` is `lhs - rhs`, so it is zero when an inequality compares an
    # expression to itself, e.g. `x <= x`. Such an inequality is always true (or
    # always false for `<` / `>`), and a zero `difference_ans` would make the
    # ratio below a division by zero, so handle these cases up front.
    if difference_res == 0 and difference_ans == 0:
        if operator_res == operator_ans:
            return InequalityComparison.TRUE
        return InequalityComparison.STRICTNESS_MISMATCH
    if difference_res == 0 or difference_ans == 0:
        return InequalityComparison.UNKNOWN

    ratio = _constant_ratio(difference_res, difference_ans, constants)
    if ratio is None:
        return InequalityComparison.UNKNOWN
    if ratio.is_zero:
        return InequalityComparison.FALSE
    if ratio.is_positive:
        if operator_res == operator_ans:
            return InequalityComparison.TRUE
        return InequalityComparison.STRICTNESS_MISMATCH
    if ratio.is_negative:
        return InequalityComparison.WRONG_DIRECTION
    return InequalityComparison.UNKNOWN


def _compare_chained_inequalities(
    res_bounds: list[Relational], ans_bounds: list[Relational], constants: set[str]
) -> InequalityComparison:
    """
    Compare two chained inequalities (`1 < x < 5`) bound by bound. The response's
    two bound inequalities are matched against the answer's two in either pairing;
    equivalent only when some pairing makes both bounds equivalent.
    """
    res_lower, res_upper = res_bounds
    saw_unknown = False
    saw_strictness = False
    for ans_first, ans_second in ((ans_bounds[0], ans_bounds[1]), (ans_bounds[1], ans_bounds[0])):
        first = _compare_single_inequality(res_lower, ans_first, constants)
        second = _compare_single_inequality(res_upper, ans_second, constants)
        if first is InequalityComparison.TRUE and second is InequalityComparison.TRUE:
            return InequalityComparison.TRUE
        if first is InequalityComparison.UNKNOWN or second is InequalityComparison.UNKNOWN:
            saw_unknown = True
        elif {first, second} <= {InequalityComparison.TRUE, InequalityComparison.STRICTNESS_MISMATCH}:
            saw_strictness = True
    if saw_strictness:
        return InequalityComparison.STRICTNESS_MISMATCH
    if saw_unknown:
        return InequalityComparison.UNKNOWN
    return InequalityComparison.FALSE


def check_inequality_equivalence(res: Basic, ans: Basic, parameters: EvaluationParameters) -> InequalityComparison:
    """
    Check whether the response relation `res` is equivalent to the answer
    relation `ans`. Both may be a single `sympy` relation (an order operator or
    `!=`) or a two-part chained order inequality (`1 < x < 5`, parsed as an `And`
    of two relations); a chain is compared to another chain bound by bound, and a
    chain is never equivalent to a single relation.
    """
    res_bounds = inequality_bounds(res)
    ans_bounds = inequality_bounds(ans)
    if res_bounds is None and ans_bounds is None:
        return InequalityComparison.FALSE
    if res_bounds is None:
        return InequalityComparison.RESPONSE_NOT_INEQUALITY
    if ans_bounds is None:
        return InequalityComparison.ANSWER_NOT_INEQUALITY
    if len(res_bounds) != len(ans_bounds):
        return InequalityComparison.FALSE

    constants = set(parameters.parsing_parameters.constants)

    if len(res_bounds) == 1:
        return _compare_single_inequality(res_bounds[0], ans_bounds[0], constants)
    return _compare_chained_inequalities(res_bounds, ans_bounds, constants)
