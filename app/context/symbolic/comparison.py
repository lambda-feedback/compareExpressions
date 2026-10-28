from __future__ import annotations

from collections.abc import Iterable

from sympy import Basic, Equality, im, I
from sympy import re as real_part
from sympy.core.relational import Relational
from sympy.logic.boolalg import BooleanAtom

from lambdafeedback.criteria import where_substitutions
from lambdafeedback.expression_parsing import SympyParsingConfig, parse_expression
from lambdafeedback.slr_parsing import ExprNode

from app.context.operators import COMPARISON_OPERATORS
from app.context.symbolic.numerical import compare_numerically
from app.evaluation_parameters import EvaluationParameters
from app.types import SubstitutionList, Substitutions


def unsimplified_with_unsplittable(parsing_params: SympyParsingConfig, symbols: Iterable[str]) -> SympyParsingConfig:
    """`parsing_params` without simplification, with `symbols` also read as single symbols."""
    return parsing_params.replace(
        simplify=False,
        extra_unsplittable_symbols=parsing_params.extra_unsplittable_symbols + tuple(symbols),
    )


def parse_where_substitutions(subs_node: ExprNode, parsing_params: SympyParsingConfig) -> SubstitutionList:
    """`[(name, expression), ...]` for each substitution in the substitution part of a WHERE criterion."""
    return [(name, parse_expression(expr, parsing_params)) for name, expr in where_substitutions(subs_node)]


def check_criterion(criterion: ExprNode, parameters: EvaluationParameters) -> bool | None:
    label = criterion.label.strip()
    if label in {"EQUALITY", "WRITTEN_AS"}:
        result = check_equality(criterion, parameters)
    elif label == "ORDER":
        result = check_order(criterion, parameters)
    elif label == "CONTAINS":
        result = check_contains_symbol(criterion, parameters)
    elif label == "PROPORTIONAL_TO":
        result = check_proportionality(criterion, parameters)
    else:
        raise Exception(label)
    return result


def create_expressions_for_comparison(
    criterion: ExprNode, parameters: EvaluationParameters, local_substitutions: Substitutions = ()
) -> tuple[Basic, Basic]:
    reserved_expressions = list(parameters.reserved_expressions.items())
    parsing_params = unsimplified_with_unsplittable(parameters.parsing_parameters, parameters.reserved_expressions.keys())
    lhs = criterion.children[0].content_string()
    rhs = criterion.children[1].content_string()
    lhs_expr = parse_expression(lhs, parsing_params).subs(local_substitutions).subs(reserved_expressions).subs(local_substitutions)
    rhs_expr = parse_expression(rhs, parsing_params).subs(local_substitutions).subs(reserved_expressions).subs(local_substitutions)
    if parsing_params.params.complex_numbers:
        simplified_lhs_expr = lhs_expr.cancel().simplify()
        simplified_rhs_expr = rhs_expr.cancel().simplify()
        if (im(lhs_expr) != 0) or (im(lhs_expr) != 0):
            lhs_expr = real_part(simplified_lhs_expr) + I * im(simplified_lhs_expr)
            rhs_expr = real_part(simplified_rhs_expr) + I * im(simplified_rhs_expr)
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


def is_inequality_or_boolean(expr: object) -> bool:
    # Inequalities (e.g. 8 < 9) and booleans (e.g. 5 < 1.43 evaluated to False) are not supported
    # and cannot be subtracted, so they cannot be compared like other expressions.
    # NOTE: Not checking for Boolean, since Symbol is a subclass of Boolean.
    return isinstance(expr, (Relational, BooleanAtom)) and not isinstance(expr, Equality)


def check_equality(
    criterion: ExprNode, parameters: EvaluationParameters, local_substitutions: Substitutions = ()
) -> bool | None:
    lhs_expr, rhs_expr = create_expressions_for_comparison(criterion, parameters, local_substitutions)
    if isinstance(lhs_expr, Equality) and not isinstance(rhs_expr, Equality):
        return False
    elif not isinstance(lhs_expr, Equality) and isinstance(rhs_expr, Equality):
        return False
    elif is_inequality_or_boolean(lhs_expr) or is_inequality_or_boolean(rhs_expr):
        return False

    try:
        either_is_infinite = lhs_expr.is_infinite or rhs_expr.is_infinite
    except (KeyError, TypeError):
        either_is_infinite = False
    if either_is_infinite:
        result = do_comparison_infinite(criterion.content, lhs_expr, rhs_expr)
    else:
        result = do_comparison(criterion.content, lhs_expr - rhs_expr)
    if result is not False:
        return result

    # There are some types of expression, e.g. those containing hyperbolic trigonometric functions, that can behave
    # unpredictably when simplification is applied. For that reason we check several different combinations of
    # simplifications here in order to reduce the likelihood of false negatives.
    # Each side is simplified only once a retry needs it.
    simplified_rhs_expr = rhs_expr.simplify()
    result = do_comparison(criterion.content, lhs_expr - simplified_rhs_expr)
    if result is not False:
        return result

    simplified_lhs_expr = lhs_expr.simplify()
    result = do_comparison(criterion.content, simplified_lhs_expr - rhs_expr)
    if result is not False:
        return result

    result = do_comparison(criterion.content, simplified_lhs_expr - simplified_rhs_expr)
    if result is not False:
        return result

    return compare_numerically(lhs_expr, rhs_expr, parameters)


def check_order(criterion: ExprNode, parameters: EvaluationParameters) -> bool | None:
    lhs_expr, rhs_expr = create_expressions_for_comparison(criterion, parameters)
    result = do_comparison(criterion.content, lhs_expr - rhs_expr)
    return result


def check_proportionality(criterion: ExprNode, parameters: EvaluationParameters) -> bool | None:
    lhs_expr, rhs_expr = create_expressions_for_comparison(criterion, parameters)
    result = None
    if lhs_expr.cancel().simplify().simplify() != 0:
        result = (rhs_expr / lhs_expr).cancel().simplify()
    elif rhs_expr.cancel().simplify().simplify() != 0:
        result = (lhs_expr / rhs_expr).cancel().simplify()
    if result == 0 or result is None:
        result = False
    else:
        result = result.is_constant()
    return result


def check_contains_symbol(criterion: ExprNode, parameters: EvaluationParameters) -> bool:
    lhs_expr, rhs_expr = create_expressions_for_comparison(criterion, parameters)
    result = rhs_expr in lhs_expr.atoms()
    return result
