from __future__ import annotations

from typing import Any

from sympy import Equality

from lambdafeedback.criteria import CriteriaGraph, Evaluate, OutputNode, ReachedCriteria
from lambdafeedback.expression_parsing import parse_expression
from lambdafeedback.slr_parsing import ExprNode

from app.context.graph_helpers import attach_terminal_criterion, outcome_tag
from app.context.symbolic.comparison import check_equality, unsimplified_with_unsplittable
from app.context.symbolic.graphs.set_equivalence import add_set_equivalence_nodes, as_sets
from app.evaluation_parameters import EvaluationParameters
from app.feedback.symbolic import feedback_generators as symbolic_feedback_string_generators


def _equality_equivalence(label: str, parameters: EvaluationParameters) -> Evaluate:
    def equality_equivalence(_response: Any) -> ReachedCriteria:
        result = False
        res = parameters.reserved_expressions["response"]
        ans = parameters.reserved_expressions["answer"]

        if (not isinstance(res, Equality)) and isinstance(ans, Equality):
            return {
                label + "_EXPRESSION_NOT_EQUALITY": None
            }

        if isinstance(res, Equality) and (not isinstance(ans, Equality)):
            return {
                label + "_EQUALITY_NOT_EXPRESSION": None
            }

        # TODO: Remove when criteria for checking proportionality is implemented
        if isinstance(res, Equality) and isinstance(ans, Equality):
            res_difference = (res.args[0] - res.args[1]).simplify()
            if res_difference == 0:
                symbols_in_equality_ratio = (ans.args[0] - ans.args[1]).simplify().free_symbols
            elif (ans.args[0] - ans.args[1]).simplify() == 0:
                symbols_in_equality_ratio = res_difference.free_symbols
            else:
                symbols_in_equality_ratio = ((res.args[0] - res.args[1]) / (ans.args[0] - ans.args[1])).simplify().free_symbols
            result = {str(s) for s in symbols_in_equality_ratio}.issubset(parameters.parsing_parameters.constants)
        return outcome_tag(label, result is True)
    return equality_equivalence


def _same_symbols(label: str, lhs: str, rhs: str, parameters: EvaluationParameters) -> Evaluate:
    def same_symbols(_response: Any) -> ReachedCriteria:
        local_substitutions = list(parameters.reserved_expressions.items())
        parsing_params = unsimplified_with_unsplittable(parameters.parsing_parameters, parameters.reserved_expressions.keys())
        lsym = parse_expression(lhs, parsing_params).subs(local_substitutions)
        rsym = parse_expression(rhs, parsing_params).subs(local_substitutions)
        result = lsym.free_symbols == rsym.free_symbols
        return outcome_tag(label + "_SAME_SYMBOLS", result is True)
    return same_symbols


def add_equality_equivalence_nodes(
    graph: CriteriaGraph, END: OutputNode, parameters: EvaluationParameters, label: str, lhs: str, rhs: str
) -> None:
    """Adds the nodes that check if the equalities `lhs` and `rhs` are equivalent to `graph`."""
    graph.add_evaluation_node(
        label,
        summary=label,
        details="Checks if " + str(lhs) + " is equivalent to " + str(rhs) + ".",
        evaluate=_equality_equivalence(label, parameters)
    )
    attach_terminal_criterion(
        graph,
        label,
        label + "_UNKNOWN",
        END,
        summary="Cannot determine if " + str(lhs) + " is equivalent to " + str(rhs),
        details="Cannot determine if " + str(lhs) + " is equivalent to " + str(rhs) + ".",
        feedback_string_generator=symbolic_feedback_string_generators["INTERNAL"]("EQUALITY_EQUIVALENCE_UNKNOWN")
    )
    attach_terminal_criterion(
        graph,
        label,
        label + "_TRUE",
        END,
        summary=str(lhs) + " is equivalent to " + str(rhs),
        details=str(lhs) + " is equivalent to " + str(rhs) + ".",
        feedback_string_generator=symbolic_feedback_string_generators["INTERNAL"]("EQUALITIES_EQUIVALENT")
    )
    attach_terminal_criterion(
        graph,
        label,
        label + "_FALSE",
        END,
        summary=str(lhs) + " is not equivalent to " + str(rhs),
        details=str(lhs) + " is not equivalent to " + str(rhs) + ".",
        feedback_string_generator=symbolic_feedback_string_generators["INTERNAL"]("EQUALITIES_NOT_EQUIVALENT")
    )
    attach_terminal_criterion(
        graph,
        label,
        label + "_EXPRESSION_NOT_EQUALITY",
        END,
        summary=str(lhs) + " is an expression, not an equality.",
        details=str(lhs) + " is an expression, not an equality.",
        feedback_string_generator=symbolic_feedback_string_generators["INTERNAL"]("EXPRESSION_NOT_EQUALITY")
    )
    attach_terminal_criterion(
        graph,
        label,
        label + "_EQUALITY_NOT_EXPRESSION",
        END,
        summary=str(lhs) + " is an equality, not an expression.",
        details=str(lhs) + " is an equality, not an expression.",
        feedback_string_generator=symbolic_feedback_string_generators["INTERNAL"]("EQUALITY_NOT_EXPRESSION")
    )


def add_mathematical_equivalence_nodes(
    graph: CriteriaGraph, END: OutputNode, criterion: ExprNode, parameters: EvaluationParameters, label: str, lhs: str, rhs: str
) -> None:
    """
    Adds the nodes that check if `lhs` and `rhs` are mathematically equal to `graph`,
    and if they are, whether they have the same symbols.
    """
    def mathematical_equivalence(_response: Any) -> ReachedCriteria:
        return outcome_tag(label, check_equality(criterion, parameters))

    graph.add_evaluation_node(
        label,
        summary=label,
        details="Checks if " + str(lhs) + "=" + str(rhs) + ".",
        evaluate=mathematical_equivalence
    )
    graph.attach_new_criterion(
        label,
        label + "_TRUE",
        summary=str(lhs) + "=" + str(rhs),
        details=str(lhs) + " is equal to " + str(rhs) + ".",
        feedback_string_generator=symbolic_feedback_string_generators["response=answer"]("TRUE")
    )
    graph.attach_new_evaluation(
        label + "_TRUE",
        label + "_SAME_SYMBOLS",
        summary=str(lhs) + " has the same symbols as " + str(rhs),
        details=str(lhs) + " has the same (free) symbols as " + str(rhs) + ".",
        evaluate=_same_symbols(label, lhs, rhs, parameters)
    )
    attach_terminal_criterion(
        graph,
        label + "_SAME_SYMBOLS",
        label + "_SAME_SYMBOLS" + "_TRUE",
        END,
        summary=str(lhs) + " has the same symbols as " + str(rhs),
        details=str(lhs) + " has the same (free) symbols as " + str(rhs) + ".",
        feedback_string_generator=symbolic_feedback_string_generators["SAME_SYMBOLS"]("TRUE")
    )
    attach_terminal_criterion(
        graph,
        label + "_SAME_SYMBOLS",
        label + "_SAME_SYMBOLS" + "_FALSE",
        END,
        summary=str(lhs) + " does not have the same symbols as " + str(rhs),
        details=str(lhs) + " does note have the same (free) symbols as " + str(rhs) + ".",
        feedback_string_generator=symbolic_feedback_string_generators["SAME_SYMBOLS"]("FALSE")
    )
    attach_terminal_criterion(
        graph,
        label,
        label + "_FALSE",
        END,
        summary=str(lhs) + "=\\=" + str(rhs),
        details=str(lhs) + " is not equal to" + str(rhs) + ".",
        feedback_string_generator=symbolic_feedback_string_generators["response=answer"]("FALSE")
    )
    attach_terminal_criterion(
        graph,
        label,
        label + "_UNKNOWN",
        END,
        summary="Cannot detrmine if " + str(lhs) + "=" + str(rhs),
        details="Cannot detrmine if " + str(lhs) + " is equal to " + str(rhs) + ".",
        feedback_string_generator=symbolic_feedback_string_generators["response=answer"]("UNKNOWN")
    )


def criterion_equality_node(criterion: ExprNode, parameters: EvaluationParameters, label: str | None = None) -> CriteriaGraph:
    if label is None:
        label = criterion.content_string()

    graph = CriteriaGraph(label)
    END = graph.add_end_node()
    lhs = criterion.children[0].content_string()
    rhs = criterion.children[1].content_string()

    res = parameters.reserved_expressions["response"]
    ans = parameters.reserved_expressions["answer"]
    use_set_equivalence, response_list, answer_list = as_sets(res, ans)

    if use_set_equivalence is True:
        add_set_equivalence_nodes(graph, END, criterion, parameters, label, lhs, rhs, response_list, answer_list)
    elif isinstance(res, Equality) or isinstance(ans, Equality):
        add_equality_equivalence_nodes(graph, END, parameters, label, lhs, rhs)
    else:
        add_mathematical_equivalence_nodes(graph, END, criterion, parameters, label, lhs, rhs)
    return graph
