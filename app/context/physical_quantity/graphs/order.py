from lambdafeedback.criteria import CriteriaGraph

from ....feedback.physical_quantity import feedback_string_generators as physical_quantity_feedback_string_generators
from ...graph_helpers import attach_terminal_criterion, outcome_tag
from ..comparison import comparison_function, parse_criterion_sides


def comparison_base_graph(criterion, parameters, comparison_operator="=", label=None):
    graph = CriteriaGraph(label)
    END = graph.add_end_node()
    reserved_expressions = parameters["reserved_expressions"].items()

    if label is None:
        label = criterion.content_string()

    inputs = criterion.children
    _, _, lhs, rhs = parse_criterion_sides(criterion, parameters)

    stardard_forms = [(key, expr["standard"]["value"]*expr["standard"]["unit"]) for (key, expr) in reserved_expressions]
    compare = comparison_function(comparison_operator)

    def compare_evaluate(unused_input):
        return outcome_tag(label, compare(lhs, rhs, stardard_forms) is True)

    graph.add_evaluation_node(
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


def greater_than_node(criterion, parameters, label=None):
    return comparison_base_graph(criterion, parameters, comparison_operator=">", label=label)


def greater_than_or_equal_node(criterion, parameters, label=None):
    # TODO: Add nodes for the equal case
    return comparison_base_graph(criterion, parameters, comparison_operator=">=", label=label)


def less_than_node(criterion, parameters, label=None):
    return comparison_base_graph(criterion, parameters, comparison_operator="<", label=label)


def less_than_or_equal_node(criterion, parameters, label=None):
    # TODO: Add nodes for the equal case
    return comparison_base_graph(criterion, parameters, comparison_operator="<=", label=label)
