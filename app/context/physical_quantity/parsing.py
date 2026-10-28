from __future__ import annotations

from dataclasses import dataclass

from sympy import Basic

from lambdafeedback.expression_parsing import parse_expression
from lambdafeedback.physical_quantities import PhysicalQuantity, parse_quantity as parse_physical_quantity

from app.types import Expression, Parameters
from app.feedback.physical_quantity import reverted_unit_feedback
from app.result import EvaluationResult


@dataclass(frozen=True)
class ParsedQuantity:
    """A physical quantity together with the forms of its value and unit used by the criteria."""
    quantity: PhysicalQuantity
    # The value with the unit's factor applied: one expression, a set for several values, or None if there is no value
    standard_value: Expression | None
    # The value and unit as written, or None if missing
    original_value: Basic | None
    original_unit: Basic | None

    @property
    def standard_unit(self) -> Basic | None:
        """The unit in SI base units, without its factor."""
        return self.quantity.standard_unit

    @property
    def dimension(self) -> Basic:
        return self.quantity.dimension


def parse_quantity(name: str, expr: str, parameters: Parameters, evaluation_result: EvaluationResult) -> ParsedQuantity:
    quantity = parse_physical_quantity(expr, parameters["quantity"], name)
    for index, reverted in enumerate(quantity.reverted_units):
        evaluation_result.add_feedback(f"{name}_REVERTED_UNIT_{index}", reverted_unit_feedback(reverted))
    standard_value: Expression | None
    if quantity.standard_values is None:
        standard_value = None
    elif len(quantity.standard_values) == 1:
        standard_value = quantity.standard_values[0]
    else:
        standard_value = set(quantity.standard_values)
    value = parse_expression(quantity.value.content_string(), quantity.parsing_config) if quantity.value is not None else None
    unit = parse_expression(quantity.unit.content_string(), quantity.parsing_config) if quantity.unit is not None else None
    return ParsedQuantity(quantity=quantity, standard_value=standard_value, original_value=value, original_unit=unit)
