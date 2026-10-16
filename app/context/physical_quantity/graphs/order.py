from __future__ import annotations

from typing import Any

from lambdafeedback.criteria import CriteriaGraph, ReachedCriteria
from lambdafeedback.slr_parsing import ExprNode

from app.context.graph_helpers import attach_terminal_criterion, outcome_graph, outcome_tag
from app.context.physical_quantity.comparison import comparison_function, parse_criterion_sides
from app.evaluation_parameters import EvaluationParameters
from app.feedback.physical_quantity import feedback_string_generators as physical_quantity_feedback_string_generators


def comparison_base_graph(
    criterion: ExprNode, parameters: EvaluationParameters, comparison_operator: str, label: str | None = None
) -> CriteriaGraph:
    reserved_expressions = parameters.reserved_expressions.items()

    if label is None:
        label = criterion.content_string()

    inputs = criterion.children
    _, _, lhs, rhs = parse_criterion_sides(criterion, parameters)

    stardard_forms = [(key, expr.standard_value*expr.standard_unit) for (key, expr) in reserved_expressions]
    compare = comparison_function(comparison_operator)

    def compare_evaluate(_response: Any) -> ReachedCriteria:
        return outcome_tag(label, compare(lhs, rhs, stardard_forms) is True)

    graph, END = outcome_graph(
        label,
        summary=f"Is {inputs[0]} {comparison_operator} {inputs[1]}?",
        details=f"checks if {inputs[0]} {comparison_operator} {inputs[1]}.",
        evaluate=compare_evaluate
    )
    attach_terminal_criterion(
        graph,
        label,
        label+"_TRUE",
        END,
        summary=f"{inputs[0]} {comparison_operator} {inputs[1]} is true.",
        details=f"{inputs[0]} {comparison_operator} {inputs[1]} is true.",
        feedback_string_generator=physical_quantity_feedback_string_generators["COMPARISON"]("TRUE")
    )
    attach_terminal_criterion(
        graph,
        label,
        label+"_FALSE",
        END,
        summary=f"{inputs[0]} {comparison_operator} {inputs[1]} is false.",
        details=f"{inputs[0]} {comparison_operator} {inputs[1]} is false.",
        feedback_string_generator=physical_quantity_feedback_string_generators["COMPARISON"]("FALSE")
    )
    # TODO: Consider adding node for cases where comparison cannot be done / cannot be determined

    return graph


def greater_than_node(criterion: ExprNode, parameters: EvaluationParameters, label: str | None = None) -> CriteriaGraph:
    return comparison_base_graph(criterion, parameters, comparison_operator=">", label=label)


def greater_than_or_equal_node(criterion: ExprNode, parameters: EvaluationParameters, label: str | None = None) -> CriteriaGraph:
    # TODO: Add nodes for the equal case
    return comparison_base_graph(criterion, parameters, comparison_operator=">=", label=label)


def less_than_node(criterion: ExprNode, parameters: EvaluationParameters, label: str | None = None) -> CriteriaGraph:
    return comparison_base_graph(criterion, parameters, comparison_operator="<", label=label)


def less_than_or_equal_node(criterion: ExprNode, parameters: EvaluationParameters, label: str | None = None) -> CriteriaGraph:
    # TODO: Add nodes for the equal case
    return comparison_base_graph(criterion, parameters, comparison_operator="<=", label=label)
