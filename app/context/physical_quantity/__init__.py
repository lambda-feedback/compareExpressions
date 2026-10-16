from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from types import MappingProxyType
from typing import Any

from lambdafeedback.criteria import CriteriaGraph
from lambdafeedback.expression_parsing import ExpressionParams, SympyParsingConfig
from lambdafeedback.units import QuantityParams, preprocess_quantity

from app.context.base import Context
from app.context.defaults import base_default_parameters
from app.context.physical_quantity.criteria_parser import generate_criteria_parser
from app.context.physical_quantity.graphs.match import criterion_match_node
from app.context.physical_quantity.graphs.order import greater_than_node, greater_than_or_equal_node, less_than_node, less_than_or_equal_node
from app.context.physical_quantity.parsing import parse_quantity
from app.types import GraphTemplate, Parameters
from app.preview.physical_quantity import preview_function


def expression_preprocess(name: str, expr: str, parameters: Parameters) -> str:
    return preprocess_quantity(expr, QuantityParams.from_dict(parameters), name=name)


graph_templates: dict[str, GraphTemplate] = {
    "matches": criterion_match_node,
    ">": greater_than_node,
    ">=": greater_than_or_equal_node,
    "<": less_than_node,
    "<=": less_than_or_equal_node,
}


def feedback_procedure_generator(parameters_dict: Parameters) -> dict[str, CriteriaGraph]:
    graphs = dict()
    for (label, criterion) in parameters_dict["criteria"].items():
        graph_template = graph_templates.get(criterion.label.strip(), criterion_match_node)
        graphs.update({label: graph_template(criterion, parameters_dict)})
    return graphs


# The evaluation parameters that affect how quantities are read. Other parameters
# (e.g. `symbols`, `units_string` and `is_latex`) have never applied when reading
# the response and answer as quantities during evaluation, only in the preview.
QUANTITY_PARSING_PARAMETERS = (
    "complexNumbers",
    "convention",
    "elementary_functions",
    "rationalise",
    "reserved_keywords",
    "simplify",
    "strict_syntax",
    "strictness",
)


def parsing_parameters_generator(
    params: Parameters, unsplittable_symbols: Iterable[str] = (), symbol_assumptions: Iterable[tuple[str, str]] = ()
) -> dict[str, Any]:
    return {
        "sympy": SympyParsingConfig.from_params(ExpressionParams.from_dict(params)),
        "quantity": QuantityParams.from_dict({key: params[key] for key in QUANTITY_PARSING_PARAMETERS if key in params}),
        "rtol": float(params.get("rtol", 0)),
        "atol": float(params.get("atol", 0)),
    }


# CONSIDER: Share these with the preview function implementation (or move preview implementation here)
default_parameters = deepcopy(base_default_parameters)
default_parameters.update(
    {
        "physical_quantity": True,
        "strictness": "natural",
        "units_string": "SI common imperial",
    }
)


default_criteria = ("response matches answer",)


context = Context(
    expression_preview=preview_function,
    generate_criteria_parser=generate_criteria_parser,
    expression_preprocess=expression_preprocess,
    expression_parse=parse_quantity,
    default_parameters=MappingProxyType(default_parameters),
    default_criteria=default_criteria,
    feedback_procedure_generator=feedback_procedure_generator,
    parsing_parameters_generator=parsing_parameters_generator,
)
