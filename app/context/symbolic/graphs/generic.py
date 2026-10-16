from __future__ import annotations

from typing import Any

from lambdafeedback.criteria import CriteriaGraph, ReachedCriteria
from lambdafeedback.slr_parsing import ExprNode

from app.context.graph_helpers import attach_terminal_criterion, outcome_graph, outcome_tag
from app.context.symbolic.comparison import check_criterion
from app.types import Parameters
from app.feedback.symbolic import feedback_generators as symbolic_feedback_string_generators


def criterion_eval_node(criterion: ExprNode, parameters_dict: Parameters) -> CriteriaGraph:
    feedback_string_generator_inputs = {'criterion': criterion}
    label = criterion.content_string()

    def evaluation_node_internal(_response: Any) -> ReachedCriteria:
        result = check_criterion(criterion, parameters_dict)
        return outcome_tag(label, result, feedback_string_generator_inputs)

    graph, END = outcome_graph(label, summary=label, details="Checks if "+label+" is true.", evaluate=evaluation_node_internal)
    attach_terminal_criterion(
        graph,
        label,
        label+"_TRUE",
        END,
        summary="True",
        details=label+" is true.",
        feedback_string_generator=symbolic_feedback_string_generators["GENERIC"]("TRUE")
    )
    attach_terminal_criterion(
        graph,
        label,
        label+"_FALSE",
        END,
        summary="True",
        details=label+" is false.",
        feedback_string_generator=symbolic_feedback_string_generators["GENERIC"]("FALSE")
    )
    attach_terminal_criterion(
        graph,
        label,
        label+"_UNKNOWN",
        END,
        summary="True",
        details=label+" is false.",
        feedback_string_generator=symbolic_feedback_string_generators["GENERIC"]("FALSE")
    )
    return graph
