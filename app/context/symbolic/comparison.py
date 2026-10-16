from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from typing import Any

from sympy import Basic, Equality, im, I
from sympy import re as real_part

from lambdafeedback.expression_parsing import SympyParsingConfig, parse_expression
from lambdafeedback.slr_parsing import ExprNode

from app.context.operators import COMPARISON_OPERATORS
from app.context.symbolic.numerical import compare_numerically
from app.context.types import Parameters, Substitutions


def unsimplified_with_unsplittable(parsing_params: SympyParsingConfig, symbols: Iterable[str]) -> SympyParsingConfig:
    """`parsing_params` without simplification, with `symbols` also read as single symbols."""
    return parsing_params.replace(
        simplify=False,
        extra_unsplittable_symbols=parsing_params.extra_unsplittable_symbols+tuple(symbols),
    )


def where_substitution_nodes(subs_node: ExprNode) -> list[ExprNode]:
    """The individual substitutions in the substitution part of a WHERE criterion."""
    if subs_node.label == "EQUALITY":
        return [subs_node]
    elif subs_node.label == "SEPARATOR":
        return subs_node.children
    return subs_node  # type: ignore[return-value]  # Bug 6 in the bug report: should be a list or raise


def parse_where_substitutions(subs_node: ExprNode, parsing_params: SympyParsingConfig) -> Substitutions:
    """`[(name, expression), ...]` for each substitution in the substitution part of a WHERE criterion."""
    local_subs = []
    for sub in where_substitution_nodes(subs_node):
        name = sub.children[0].content_string()
        expr = parse_expression(sub.children[1].content_string(), parsing_params)
        local_subs.append((name, expr))
    return local_subs


def check_criterion(criterion: ExprNode, parameters_dict: Parameters) -> bool | None:
    label = criterion.label.strip()
    if label in {"EQUALITY", "WRITTEN_AS"}:
        result = check_equality(criterion, parameters_dict)
    elif label == "ORDER":
        result = check_order(criterion, parameters_dict)
    elif label == "CONTAINS":
        result = check_contains_symbol(criterion, parameters_dict)
    elif label == "PROPORTIONAL_TO":
        result = check_proportionality(criterion, parameters_dict)
    else:
        raise Exception(label)
    return result


def create_expressions_for_comparison(
    criterion: ExprNode, parameters_dict: Parameters, local_substitutions: Sequence[tuple[str, Any]] = ()
) -> tuple[Basic, Basic]:
    reserved_expressions = list(parameters_dict["reserved_expressions"].items())
    parsing_params = unsimplified_with_unsplittable(parameters_dict["parsing_parameters"], parameters_dict["reserved_expressions"].keys())
    lhs = criterion.children[0].content_string()
    rhs = criterion.children[1].content_string()
    lhs_expr = parse_expression(lhs, parsing_params).subs(local_substitutions).subs(reserved_expressions).subs(local_substitutions)
    rhs_expr = parse_expression(rhs, parsing_params).subs(local_substitutions).subs(reserved_expressions).subs(local_substitutions)
    if parsing_params.params.complex_numbers:
        simplified_lhs_expr = lhs_expr.cancel().simplify()
        simplified_rhs_expr = rhs_expr.cancel().simplify()
        if (im(lhs_expr) != 0) or (im(lhs_expr) != 0):
            lhs_expr = real_part(simplified_lhs_expr) + I*im(simplified_lhs_expr)
            rhs_expr = real_part(simplified_rhs_expr) + I*im(simplified_rhs_expr)
    return lhs_expr, rhs_expr


def do_comparison_infinite(comparison_symbol: str, lhs_expr: Basic, rhs_expr: Basic) -> bool | None:
    # When either side is infinite, subtracting (e.g. oo - oo) yields nan, making
    # the subtraction-based do_comparison unreliable. Compare the sides directly instead.
    direct_comparisons = {
        "=": lhs_expr == rhs_expr,
        ">": lhs_expr > rhs_expr,
        ">=": lhs_expr >= rhs_expr,
        "<": lhs_expr < rhs_expr,
        "<=": lhs_expr <= rhs_expr,
    }
    try:
        return bool(direct_comparisons[comparison_symbol.strip()])
    except Exception:
        return None


def do_comparison(comparison_symbol: str, expression: Basic) -> bool | None:
    comparison = COMPARISON_OPERATORS[comparison_symbol.strip()]
    result: bool | None
    try:
        result = bool(comparison(expression.cancel().simplify().simplify(), 0))
    except Exception:
        result = None
    return result


def check_equality(
    criterion: ExprNode, parameters_dict: Parameters, local_substitutions: Sequence[tuple[str, Any]] = ()
) -> bool | None:
    lhs_expr, rhs_expr = create_expressions_for_comparison(criterion, parameters_dict, local_substitutions)
    if isinstance(lhs_expr, Equality) and not isinstance(rhs_expr, Equality):
        return False
    elif not isinstance(lhs_expr, Equality) and isinstance(rhs_expr, Equality):
        return False

    try:
        either_is_infinite = lhs_expr.is_infinite or rhs_expr.is_infinite
    except (KeyError, TypeError):
        either_is_infinite = False
    if either_is_infinite:
        result = do_comparison_infinite(criterion.content, lhs_expr, rhs_expr)
    else:
        result = do_comparison(criterion.content, lhs_expr-rhs_expr)

    # There are some types of expression, e.g. those containing hyperbolic trigonometric functions, that can behave
    # unpredictably when simplification is applied. For that reason we check several different combinations of
    # simplifications here in order to reduce the likelihood of false negatives.
    # Each side is simplified at most once, and only if a retry needs it
    simplified: dict[str, Basic] = {}

    def simplified_side(side: str, expr: Basic) -> Basic:
        if side not in simplified:
            simplified[side] = expr.simplify()
        return simplified[side]

    differences_to_retry: tuple[Callable[[], Basic], ...] = (
        lambda: lhs_expr-simplified_side("rhs", rhs_expr),
        lambda: simplified_side("lhs", lhs_expr)-rhs_expr,
        lambda: simplified_side("lhs", lhs_expr)-simplified_side("rhs", rhs_expr),
    )
    for difference in differences_to_retry:
        if result is not False:
            break
        result = do_comparison(criterion.content, difference())

    if result is False:
        result = compare_numerically(lhs_expr, rhs_expr, parameters_dict)

    return result


def check_order(criterion: ExprNode, parameters_dict: Parameters) -> bool | None:
    lhs_expr, rhs_expr = create_expressions_for_comparison(criterion, parameters_dict)
    result = do_comparison(criterion.content, lhs_expr-rhs_expr)
    return result


def check_proportionality(criterion: ExprNode, parameters_dict: Parameters) -> bool | None:
    lhs_expr, rhs_expr = create_expressions_for_comparison(criterion, parameters_dict)
    result = None
    if lhs_expr.cancel().simplify().simplify() != 0:
        result = (rhs_expr/lhs_expr).cancel().simplify()
    elif rhs_expr.cancel().simplify().simplify() != 0:
        result = (lhs_expr/rhs_expr).cancel().simplify()
    if result == 0 or result is None:
        result = False
    else:
        result = result.is_constant()
    return result


def check_contains_symbol(criterion: ExprNode, parameters_dict: Parameters) -> bool:
    lhs_expr, rhs_expr = create_expressions_for_comparison(criterion, parameters_dict)
    result = rhs_expr in lhs_expr.atoms()
    return result
