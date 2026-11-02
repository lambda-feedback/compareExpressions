"""Equivalence of equalities (`x = y`) and chained equalities (`x = y = z`) in the answer and response."""

from __future__ import annotations

from enum import Enum
from itertools import permutations

from sympy import And, Basic, Equality, Matrix, Symbol, linear_eq_to_matrix

from app.evaluation_parameters import EvaluationParameters

# Chains longer than this are not searched exhaustively; see `_compare_chained_equalities`.
MAX_CHAINED_EQUALITY_PARTS = 8


class EqualityComparison(Enum):
    """The outcome of comparing a response equality to an answer equality; the names are the criteria tag suffixes."""
    TRUE = "equivalent"
    FALSE = "not equivalent"
    UNKNOWN = "undecidable, a chain too long to search"
    EXPRESSION_NOT_EQUALITY = "the answer is an equality but the response is not"
    EQUALITY_NOT_EXPRESSION = "the response is an equality but the answer is not"
    CHAIN_NOT_EQUALITY = "the response is a chained equality but the answer is a single equality"
    EQUALITY_NOT_CHAIN = "the response is a single equality but the answer is a chained equality"


def equality_parts(expr: Basic) -> list[Equality] | None:
    """
    The list of equality parts if `expr` is a single equality (`x = y`) or a chained equality
    (`x = y = z`, parsed as a conjunction of the equalities between adjacent operands), otherwise None.
    Disjoint from `inequality_bounds`, which never matches a conjunction of equalities.
    """
    if isinstance(expr, Equality):
        return [expr]
    if isinstance(expr, And) and expr.args and all(isinstance(arg, Equality) for arg in expr.args):
        return list(expr.args)
    return None


def is_equality_chain(expr: Basic) -> bool:
    """True if `expr` is a chained equality (`x = y = z`), not a single equality."""
    return isinstance(expr, And) and equality_parts(expr) is not None


def _compare_single_equality(res_eq: Equality, ans_eq: Equality, constants: set[str]) -> bool:
    """
    Check whether two equalities describe the same relation, i.e. whether their
    residuals (`lhs - rhs`) differ only by a constant factor. Where one residual
    simplifies to zero the other is examined on its own, since the ratio would be
    a division by zero.
    """
    res_difference = (res_eq.args[0] - res_eq.args[1]).simplify()
    ans_difference = (ans_eq.args[0] - ans_eq.args[1]).simplify()
    if res_difference == 0:
        symbols_in_equality_ratio = ans_difference.free_symbols
    elif ans_difference == 0:
        symbols_in_equality_ratio = res_difference.free_symbols
    else:
        equality_ratio = (res_eq.args[0] - res_eq.args[1]) / (ans_eq.args[0] - ans_eq.args[1])
        symbols_in_equality_ratio = equality_ratio.simplify().free_symbols
    return {str(s) for s in symbols_in_equality_ratio}.issubset(constants)


def _chain_residuals(parts: list[Equality]) -> list[Basic]:
    return [part.args[0] - part.args[1] for part in parts]


def _augmented_matrix(residuals: list[Basic], symbols: list[Symbol]) -> Matrix | None:
    """
    The coefficient matrix of `residuals` in `symbols` augmented with the
    constant terms, or None if any residual is not affine in `symbols` or if the
    coefficients are not purely numeric.
    """
    try:
        coefficients, constant_terms = linear_eq_to_matrix(residuals, symbols)
    except ValueError:
        return None
    matrix = coefficients.row_join(constant_terms)
    if matrix.free_symbols:
        return None
    return matrix


def _compare_chained_equalities_by_solution_set(res_parts: list[Equality], ans_parts: list[Equality]) -> bool | None:
    """
    Compare two chained equalities by the solution set of the system their parts
    describe. A chain asserts that all of its operands are equal to one another,
    so the order in which the parts are written carries no meaning and the
    adjacent differences of a permuted chain are different expressions that
    nonetheless constrain exactly the same values: `y = x = z` gives `y - x` and
    `x - z` where `x = y = z` gives `x - y` and `y - z`, and each pair spans the
    other. Two affine systems have the same solution set exactly when their
    augmented matrices have equal rank and stacking them adds no rank.

    Returns None when the residuals are not affine with numeric coefficients, in
    which case the caller falls back to comparing the parts pairwise.
    """
    res_residuals = _chain_residuals(res_parts)
    ans_residuals = _chain_residuals(ans_parts)
    symbols = sorted(set().union(*[residual.free_symbols for residual in res_residuals + ans_residuals]), key=str)
    res_matrix = _augmented_matrix(res_residuals, symbols)
    ans_matrix = _augmented_matrix(ans_residuals, symbols)
    if res_matrix is None or ans_matrix is None:
        return None
    res_rank = res_matrix.rank()
    ans_rank = ans_matrix.rank()
    return res_rank == ans_rank == res_matrix.col_join(ans_matrix).rank()


def _compare_chained_equalities(res_parts: list[Equality], ans_parts: list[Equality], constants: set[str]) -> bool | None:
    """
    Compare two chained equalities (`x = y = z`). Affine chains are compared by
    solution set; anything else (for instance a chain scaled by a symbolic
    constant, whose coefficients are not numeric) falls back to matching the
    parts one-to-one with the same constant-ratio test used for a single
    equality. Returns None for non-affine chains too long to search
    exhaustively.
    """
    result = _compare_chained_equalities_by_solution_set(res_parts, ans_parts)
    if result is not None:
        return result
    if len(res_parts) != len(ans_parts):
        return False
    if len(res_parts) > MAX_CHAINED_EQUALITY_PARTS:
        return None
    for permuted_ans_parts in permutations(ans_parts):
        if all(
            _compare_single_equality(res_part, ans_part, constants)
            for res_part, ans_part in zip(res_parts, permuted_ans_parts)
        ):
            return True
    return False


def check_equality_equivalence(res: Basic, ans: Basic, parameters: EvaluationParameters) -> EqualityComparison:
    """
    Check whether the response equality `res` is equivalent to the answer
    equality `ans`. Both may be a single `sympy` equality (`x = y`) or a chained
    equality (`x = y = z`, parsed as an `And` of the equalities between adjacent
    operands); a chain is compared to another chain by solution set.
    """
    res_parts = equality_parts(res)
    ans_parts = equality_parts(ans)
    if res_parts is None and ans_parts is None:
        return EqualityComparison.FALSE
    if res_parts is None:
        return EqualityComparison.EXPRESSION_NOT_EQUALITY
    if ans_parts is None:
        return EqualityComparison.EQUALITY_NOT_EXPRESSION

    constants = set(parameters.parsing_parameters.constants)

    if len(res_parts) == 1 and len(ans_parts) == 1:
        if _compare_single_equality(res_parts[0], ans_parts[0], constants):
            return EqualityComparison.TRUE
        return EqualityComparison.FALSE

    # A chain is compared by solution set, which already accounts for a differing
    # number of parts, so the counts only choose the feedback tag. A degenerate
    # chain that states no more than a single equality (`x = y = y`) therefore
    # still matches that equality.
    result = _compare_chained_equalities(res_parts, ans_parts, constants)
    if result is True:
        return EqualityComparison.TRUE
    if result is None:
        return EqualityComparison.UNKNOWN
    if len(res_parts) > len(ans_parts):
        return EqualityComparison.CHAIN_NOT_EQUALITY
    if len(res_parts) < len(ans_parts):
        return EqualityComparison.EQUALITY_NOT_CHAIN
    return EqualityComparison.FALSE
