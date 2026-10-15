from copy import deepcopy

from lambdafeedback.expression_parsing import (
    ExpressionParams,
    SympyParsingConfig,
    parse_expressions,
    preprocess_expression,
)

from ...preview.symbolic import preview_function
from ..defaults import base_default_parameters
from .graphs.equivalence import criterion_equality_node
from .graphs.generic import criterion_eval_node
from .graphs.substitution import criterion_where_node
from .graphs.syntactical_form import criterion_written_as_node

from lambdafeedback.criteria import build_criteria_parser


default_parameters = deepcopy(base_default_parameters)


def expression_preprocess(name, expr, parameters):
    return preprocess_expression(expr, ExpressionParams.from_dict(parameters), name=name)


def expression_parse(name, expr, parameters, evaluation_result):
    expressions = parse_expressions(expr, parameters)
    return expressions[0] if len(expressions) == 1 else set(expressions)


default_criteria = ["response = answer"]


graph_templates = {
    "EQUALITY": criterion_equality_node,
    "WHERE": criterion_where_node,
    "WRITTEN_AS": criterion_written_as_node,
}


def feedback_procedure_generator(parameters_dict):
    graphs = dict()
    criteria = set(parameters_dict["criteria"].items())
    for (label, criterion) in criteria:
        graph_template = graph_templates.get(criterion.label, criterion_eval_node)
        graphs.update({label: graph_template(criterion, parameters_dict)})
    return graphs


def parsing_parameters_generator(params, unsplittable_symbols=tuple(), symbol_assumptions=tuple()):
    return SympyParsingConfig.from_params(ExpressionParams.from_dict(params), unsplittable_symbols, symbol_assumptions)


context = {
    "expression_preview": preview_function,
    "generate_criteria_parser": build_criteria_parser,
    "expression_preprocess": expression_preprocess,
    "expression_parse": expression_parse,
    "default_parameters": default_parameters,
    "default_criteria": default_criteria,
    "feedback_procedure_generator": feedback_procedure_generator,
    "parsing_parameters_generator": parsing_parameters_generator,
}
