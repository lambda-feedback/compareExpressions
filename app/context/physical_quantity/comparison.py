from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from sympy import Basic, Symbol

from lambdafeedback.expression_parsing import parse_expression
from lambdafeedback.slr_parsing import ExprNode
from lambdafeedback.units import parse_quantity as parse_physical_quantity

from app.context.operators import COMPARISON_OPERATORS
from app.context.physical_quantity.parsing import ParsedQuantity, parsed_quantity
from app.evaluation_parameters import EvaluationParameters
from app.types import Substitutions

NONE_PLACEHOLDER = Symbol('NONE_PLACEHOLDER')


@dataclass(frozen=True)
class CriterionSides:
    """The left- and right-hand sides of a criterion, and the quantities that the sides are written in terms of."""
    lhs_string: str
    rhs_string: str
    lhs: Basic
    rhs: Basic
    # The response, the answer and any quantity written out in the criterion (e.g. `2 m`), by the
    # symbol that stands for them in `lhs` and `rhs`
    quantities: Mapping[str, ParsedQuantity]


def parse_criterion_sides(criterion: ExprNode, parameters: EvaluationParameters) -> CriterionSides:
    """The sides of `criterion`, where a side written out as a quantity is parsed with its units."""
    parsing_params = parameters.parsing_parameters["sympy"].replace(simplify=False)
    quantities = dict(parameters.reserved_expressions)
    sides = []
    for (name, node) in zip(("criterion_lhs", "criterion_rhs"), criterion.children):
        if node.label == "INPUT":
            quantity = parse_physical_quantity(node.content_string(), parameters.parsing_parameters["quantity"], name)
            quantities[name] = parsed_quantity(quantity)
            sides.append(Symbol(name))
        else:
            sides.append(parse_expression(node.content_string(), parsing_params))
    return CriterionSides(
        lhs_string=criterion.children[0].content_string(),
        rhs_string=criterion.children[1].content_string(),
        lhs=sides[0],
        rhs=sides[1],
        quantities=quantities,
    )


def _substitute(lhs: Basic, rhs: Basic, substitutions: Substitutions) -> tuple[Basic, Basic]:
    """`lhs` and `rhs` with `substitutions` applied, where substitutions by None use a placeholder symbol instead."""
    local_substitutions = [(key, NONE_PLACEHOLDER) if expr is None else (key, expr) for (key, expr) in substitutions]
    return lhs.subs(local_substitutions), rhs.subs(local_substitutions)


def comparison_function(comparison_operator: str) -> Callable[[Basic, Basic, Substitutions], bool | None]:
    comparison = COMPARISON_OPERATORS[comparison_operator]

    def comparison_function_inner(lhs: Basic, rhs: Basic, substitutions: Substitutions) -> bool | None:
        expr0, expr1 = _substitute(lhs, rhs, substitutions)
        try:
            return bool(comparison((expr0 - expr1).cancel().simplify().simplify(), 0))
        except TypeError:
            # The difference still contains symbols, so sympy cannot determine the truth value
            return None
    return comparison_function_inner


def is_proportional(lhs: Basic, rhs: Basic, substitutions: Substitutions) -> tuple[bool | None, float | None]:
    expr0, expr1 = _substitute(lhs, rhs, substitutions)
    if expr0.cancel().simplify().simplify() != 0:
        ratio = (expr0 / expr1).cancel().simplify()
        result = ratio.is_constant()
    elif expr0.cancel().simplify().simplify() != 0:
        ratio = (expr1 / expr0).cancel().simplify()
        result = ratio.is_constant()
    else:
        result = False
    if result is True:
        ratio = float(ratio)
    else:
        ratio = None
    return result, ratio
