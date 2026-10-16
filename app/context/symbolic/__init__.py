from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from typing import Any

from lambdafeedback.criteria import CriteriaGraph, build_criteria_parser
from lambdafeedback.expression_parsing import (
    ExpressionParams,
    SympyParsingConfig,
    parse_expressions,
    preprocess_expression,
)

from app.context.defaults import base_default_parameters
from app.context.symbolic.graphs.equivalence import criterion_equality_node
from app.context.symbolic.graphs.generic import criterion_eval_node
from app.context.symbolic.graphs.substitution import criterion_where_node
from app.context.symbolic.graphs.syntactical_form import criterion_written_as_node
from app.result import EvaluationResult
from app.types import Expression, GraphTemplate, Parameters
from app.preview.symbolic import preview_function


default_parameters = deepcopy(base_default_parameters)


def expression_preprocess(name: str, expr: str, parameters: Parameters) -> str:
    return preprocess_expression(expr, ExpressionParams.from_dict(parameters), name=name)


def expression_parse(name: str, expr: str, parameters: SympyParsingConfig, evaluation_result: EvaluationResult) -> Expression:
    expressions = parse_expressions(expr, parameters)
    return expressions[0] if len(expressions) == 1 else set(expressions)


default_criteria = ["response = answer"]


graph_templates: dict[str, GraphTemplate] = {
    "EQUALITY": criterion_equality_node,
    "WHERE": criterion_where_node,
    "WRITTEN_AS": criterion_written_as_node,
}


def feedback_procedure_generator(parameters_dict: Parameters) -> dict[str, CriteriaGraph]:
    graphs = dict()
    criteria = set(parameters_dict["criteria"].items())
    for (label, criterion) in criteria:
        graph_template = graph_templates.get(criterion.label, criterion_eval_node)
        graphs.update({label: graph_template(criterion, parameters_dict)})
    return graphs


def parsing_parameters_generator(
    params: Parameters, unsplittable_symbols: Iterable[str] = (), symbol_assumptions: Iterable[tuple[str, str]] = ()
) -> SympyParsingConfig:
    return SympyParsingConfig.from_params(ExpressionParams.from_dict(params), unsplittable_symbols, symbol_assumptions)


context: dict[str, Any] = {
    "expression_preview": preview_function,
    "generate_criteria_parser": build_criteria_parser,
    "expression_preprocess": expression_preprocess,
    "expression_parse": expression_parse,
    "default_parameters": default_parameters,
    "default_criteria": default_criteria,
    "feedback_procedure_generator": feedback_procedure_generator,
    "parsing_parameters_generator": parsing_parameters_generator,
}
