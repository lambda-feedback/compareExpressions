from sympy import Symbol


def _substitute(lhs, rhs, substitutions):
    """`lhs` and `rhs` with `substitutions` applied, where substitutions by None use a placeholder symbol instead."""
    none_placeholder = Symbol('NONE_PLACEHOLDER')
    local_substitutions = [(key, none_placeholder) if expr is None else (key, expr) for (key, expr) in substitutions]
    return lhs.subs(local_substitutions), rhs.subs(local_substitutions)


def comparison_function(comparison_operator):
    comparison_type_dictionary = {
        "=": lambda a, b: bool(a == b),
        ">": lambda a, b: bool(a > b),
        "<": lambda a, b: bool(a < b),
        ">=": lambda a, b: bool(a >= b),
        "<=": lambda a, b: bool(a <= b),
    }
    comparison = comparison_type_dictionary[comparison_operator]

    def comparison_function_inner(lhs, rhs, substitutions):
        expr0, expr1 = _substitute(lhs, rhs, substitutions)
        result = comparison((expr0-expr1).cancel().simplify().simplify(), 0)
        return result
    return comparison_function_inner


def is_proportional(lhs, rhs, substitutions):
    expr0, expr1 = _substitute(lhs, rhs, substitutions)
    if expr0.cancel().simplify().simplify() != 0:
        result = (expr0/expr1).cancel().simplify().is_constant()
        ratio = expr0/expr1
    elif expr0.cancel().simplify().simplify() != 0:
        result = (expr1/expr0).cancel().simplify().is_constant()
        ratio = expr1/expr0
    else:
        result = False
    if result is True:
        ratio = float(ratio.cancel().simplify())
    else:
        ratio = None
    return result, ratio
