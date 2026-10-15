from sympy import Equality, im, I
from sympy import re as real_part

from lambdafeedback.expression_parsing import parse_expression

from .numerical import compare_numerically


def unsimplified_with_unsplittable(parsing_params, symbols):
    """`parsing_params` without simplification, with `symbols` also read as single symbols."""
    return parsing_params.replace(
        simplify=False,
        extra_unsplittable_symbols=parsing_params.extra_unsplittable_symbols+tuple(symbols),
    )


def where_substitution_nodes(subs_node):
    """The individual substitutions in the substitution part of a WHERE criterion."""
    if subs_node.label == "EQUALITY":
        return [subs_node]
    elif subs_node.label == "SEPARATOR":
        return subs_node.children
    return subs_node


def parse_where_substitutions(subs_node, parsing_params):
    """`[(name, expression), ...]` for each substitution in the substitution part of a WHERE criterion."""
    local_subs = []
    for sub in where_substitution_nodes(subs_node):
        name = sub.children[0].content_string()
        expr = parse_expression(sub.children[1].content_string(), parsing_params)
        local_subs.append((name, expr))
    return local_subs


def check_criterion(criterion, parameters_dict, generate_feedback=True):
    label = criterion.label.strip()
    parsing_params = parameters_dict["parsing_parameters"].replace(simplify=False)
    if label in {"EQUALITY", "WRITTEN_AS"}:
        result = check_equality(criterion, parameters_dict)
    elif label == "ORDER":
        result = check_order(criterion, parameters_dict)
    elif label == "CONTAINS":
        result = check_contains_symbol(criterion, parameters_dict)
    elif label == "PROPORTIONAL_TO":
        result = check_proportionality(criterion, parameters_dict)
    elif label == "WHERE":
        crit = criterion.children[0]
        local_subs = parse_where_substitutions(criterion.children[1], parsing_params)
        result = check_criterion(crit, {**parameters_dict, **{"local_substitutions": local_subs}}, generate_feedback)
    else:
        raise Exception(label)
    return result


def create_expressions_for_comparison(criterion, parameters_dict, local_substitutions=[]):
    parsing_params = parameters_dict["parsing_parameters"]
    reserved_expressions = list(parameters_dict["reserved_expressions"].items())
    parsing_params = unsimplified_with_unsplittable(parsing_params, parameters_dict["reserved_expressions"].keys())
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


def do_comparison_infinite(comparison_symbol, lhs_expr, rhs_expr):
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


def do_comparison(comparison_symbol, expression):
    comparisons = {
        "=": lambda expr: bool(expression.cancel().simplify().simplify() == 0),
        ">": lambda expr: bool(expression.cancel().simplify().simplify() > 0),
        ">=": lambda expr: bool(expression.cancel().simplify().simplify() >= 0),
        "<": lambda expr: bool(expression.cancel().simplify().simplify() < 0),
        "<=": lambda expr: bool(expression.cancel().simplify().simplify() <= 0),
    }
    comparison = comparisons[comparison_symbol.strip()]
    try:
        result = comparison(expression)
    except Exception:
        result = None
    return result


def check_equality(criterion, parameters_dict, local_substitutions=[]):
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
    differences_to_retry = (
        lambda: lhs_expr-rhs_expr.simplify(),
        lambda: lhs_expr.simplify()-rhs_expr,
        lambda: lhs_expr.simplify()-rhs_expr.simplify(),
    )
    for difference in differences_to_retry:
        if result is not False:
            break
        result = do_comparison(criterion.content, difference())

    if result is False:
        result = compare_numerically(lhs_expr, rhs_expr, parameters_dict)

    return result


def check_order(criterion, parameters_dict, local_substitutions=[]):
    lhs_expr, rhs_expr = create_expressions_for_comparison(criterion, parameters_dict, local_substitutions)
    result = do_comparison(criterion.content, lhs_expr-rhs_expr)
    return result


def check_proportionality(criterion, parameters_dict, local_substitutions=[]):
    lhs_expr, rhs_expr = create_expressions_for_comparison(criterion, parameters_dict, local_substitutions)
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


def check_contains_symbol(criterion, parameters_dict, local_substitutions=[]):
    lhs_expr, rhs_expr = create_expressions_for_comparison(criterion, parameters_dict, local_substitutions)
    result = rhs_expr in lhs_expr.atoms()
    return result
