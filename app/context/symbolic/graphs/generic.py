from lambdafeedback.criteria import CriteriaGraph

from ....feedback.symbolic import feedback_generators as symbolic_feedback_string_generators
from ...graph_helpers import attach_terminal_criterion, outcome_tag
from ..comparison import check_criterion


def criterion_eval_node(criterion, parameters_dict):
    feedback_string_generator_inputs = {'criterion': criterion}
    label = criterion.content_string()

    def evaluation_node_internal(unused_input):
        result = check_criterion(criterion, parameters_dict)
        return outcome_tag(label, result, feedback_string_generator_inputs)

    graph = CriteriaGraph(label)
    END = graph.add_end_node()
    graph.add_evaluation_node(label, summary=label, details="Checks if "+label+" is true.", evaluate=evaluation_node_internal)
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
