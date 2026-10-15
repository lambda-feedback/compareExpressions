from sympy import Symbol

from lambdafeedback.expression_parsing import parse_expression

from ..operators import COMPARISON_OPERATORS

NONE_PLACEHOLDER = Symbol('NONE_PLACEHOLDER')


def parse_criterion_sides(criterion, parameters):
    """The left- and right-hand sides of `criterion` as strings, and parsed without simplification."""
    parsing_params = parameters["parsing_parameters"]["sympy"].replace(simplify=False)
    lhs_string = criterion.children[0].content_string()
    rhs_string = criterion.children[1].content_string()
    return lhs_string, rhs_string, parse_expression(lhs_string, parsing_params), parse_expression(rhs_string, parsing_params)


def _substitute(lhs, rhs, substitutions):
    """`lhs` and `rhs` with `substitutions` applied, where substitutions by None use a placeholder symbol instead."""
    local_substitutions = [(key, NONE_PLACEHOLDER) if expr is None else (key, expr) for (key, expr) in substitutions]
    return lhs.subs(local_substitutions), rhs.subs(local_substitutions)


def comparison_function(comparison_operator):
    comparison = COMPARISON_OPERATORS[comparison_operator]

    def comparison_function_inner(lhs, rhs, substitutions):
        expr0, expr1 = _substitute(lhs, rhs, substitutions)
        return bool(comparison((expr0-expr1).cancel().simplify().simplify(), 0))
    return comparison_function_inner


def is_proportional(lhs, rhs, substitutions):
    expr0, expr1 = _substitute(lhs, rhs, substitutions)
    if expr0.cancel().simplify().simplify() != 0:
        ratio = (expr0/expr1).cancel().simplify()
        result = ratio.is_constant()
    elif expr0.cancel().simplify().simplify() != 0:
        ratio = (expr1/expr0).cancel().simplify()
        result = ratio.is_constant()
    else:
        result = False
    if result is True:
        ratio = float(ratio)
    else:
        ratio = None
    return result, ratio
