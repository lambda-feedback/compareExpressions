from __future__ import annotations

from lambdafeedback.expression_parsing import parse_expression
from lambdafeedback.units import parse_quantity as parse_physical_quantity

from app.types import Parameters, QuantityDict
from app.feedback.physical_quantity import reverted_unit_feedback
from app.result import EvaluationResult


def parse_quantity(name: str, expr: str, parameters: Parameters, evaluation_result: EvaluationResult) -> QuantityDict:
    quantity = parse_physical_quantity(expr, parameters["quantity"], name)
    for index, reverted in enumerate(quantity.reverted_units):
        evaluation_result.add_feedback(f"{name}_REVERTED_UNIT_{index}", reverted_unit_feedback(reverted))
    if quantity.standard_values is None:
        standard_value = None
    elif len(quantity.standard_values) == 1:
        standard_value = quantity.standard_values[0]
    else:
        standard_value = set(quantity.standard_values)
    value = parse_expression(quantity.value.content_string(), quantity.parsing_config) if quantity.value is not None else None
    unit = parse_expression(quantity.unit.content_string(), quantity.parsing_config) if quantity.unit is not None else None
    quantity_dict = {
        "quantity": quantity,
        "standard": {
            "value": standard_value,
            "unit": quantity.standard_unit
        },
        "dimension": quantity.dimension,
        "original": {
            "value": value,
            "unit": unit
        },
    }
    return quantity_dict
