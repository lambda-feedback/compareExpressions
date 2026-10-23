from __future__ import annotations

from typing import Any, TypedDict

from sympy import Basic

from lambdafeedback.criteria import CriteriaGraph, OutputNode, ReachedCriteria, where_substitutions
from lambdafeedback.expression_parsing import parse_expression
from lambdafeedback.slr_parsing import ExprNode

from app.context.graph_helpers import attach_terminal_criterion, outcome_graph, outcome_tag
from app.context.symbolic.comparison import check_equality, parse_where_substitutions
from app.context.symbolic.variations import one_addition_to_subtraction, one_exponent_flip, one_swap_addition_and_multiplication
from app.evaluation_parameters import EvaluationParameters
from app.types import Substitutions
from app.feedback.symbolic import feedback_generators as symbolic_feedback_string_generators


def _expression_to_vary(expression: ExprNode) -> ExprNode | None:
    """The side of `expression` opposite `response`, or None if neither side is exactly `response`."""
    expression_to_vary = None
    if expression.children[0].content_string().strip() == "response":
        expression_to_vary = expression.children[1]
    elif expression.children[1].content_string().strip() == "response":
        expression_to_vary = expression.children[0]
    if expression_to_vary is not None and "response" in expression_to_vary.content_string():
        expression_to_vary = None
    return expression_to_vary


class VariationGroup(TypedDict):
    variations: list[Basic]
    summary: str


def _variation_groups(criterion: ExprNode, expression_to_vary: Basic) -> dict[str, VariationGroup]:
    expression_string = criterion.children[0].content_string()
    return {
        "ONE_ADDITION_TO_SUBTRACTION": {
            "variations": one_addition_to_subtraction(expression_to_vary),
            "summary": expression_string + " if one addition is changed to a subtraction or vice versa.",
        },
        "ONE_EXPONENT_FLIP": {
            "variations": one_exponent_flip(expression_to_vary),
            "summary": expression_string + " is true if one exponent has its sign changed.",
        },
        "ONE_SWAP_ADDITION_AND_MULTIPLICATION": {
            "variations": one_swap_addition_and_multiplication(expression_to_vary),
            "summary": expression_string + " is true if one addition is replaced with a multiplication or vice versa.",
        }
    }


def _variation_details(variations: list[Basic]) -> str:
    return "The following expressions are checked: " + ", ".join([str(e) for e in variations])


def _group_values(
    expression_to_vary: Basic, variation_groups: dict[str, VariationGroup], local_subs: Substitutions
) -> tuple[dict[str, set[Basic]], dict[str, set[str]]]:
    """
    Groups `expression_to_vary` and its variations by their value after `local_subs` are applied.
    Returns the expressions for each value, and the variation groups that produce each value.
    """
    unvaried_value = expression_to_vary.subs(local_subs)
    value_key = str(unvaried_value.simplify())
    values_and_expressions = {value_key: set([expression_to_vary])}
    values_and_variations_group = {value_key: set(["UNKNOWN"])}
    for (group_label, info) in variation_groups.items():
        for variation in info["variations"]:
            value = variation.subs(local_subs).simplify()
            value_key = str(value)
            values_and_expressions.setdefault(value_key, set()).add(variation)
            if value != unvaried_value:
                values_and_variations_group.setdefault(value_key, set()).add(group_label)
    return values_and_expressions, values_and_variations_group


def _add_identify_reason_nodes(graph: CriteriaGraph, END: OutputNode, label: str, criterion: ExprNode, expression: ExprNode,
                               variation_groups: dict[str, VariationGroup], values_and_expressions: dict[str, set[Basic]],
                               values_and_variations_group: dict[str, set[str]], response_value: Basic) -> None:
    """Adds the nodes that try to identify which variation of the expression the response matches."""
    def identify_reason(_response: Any) -> ReachedCriteria:
        reasons = {
            label + "_" + group_label: {'criterion': criterion} for group_label in values_and_variations_group.get(str(response_value), {"UNKNOWN"})
        }
        return reasons
    graph.attach_new_evaluation(
        label + "_FALSE",
        label + "_IDENTIFY_REASON",
        summary="Identify reason.",
        details="Attempt to identify why the response is incorrect.",
        evaluate=identify_reason
    )
    attach_terminal_criterion(
        graph,
        label + "_IDENTIFY_REASON",
        label + "_UNKNOWN",
        END,
        summary="Unknown reason",
        details="No candidates for how the response was computed were found.",
        feedback_string_generator=symbolic_feedback_string_generators["IDENTIFY_REASON"]("UNKNOWN")
    )

    def get_candidates(_response: Any) -> ReachedCriteria:
        candidates = {
            label + "_RESPONSE_CANDIDATES_" + group_label: {'criterion': criterion} for group_label in values_and_variations_group[str(response_value)]
        }
        return candidates

    for (group_label, group_info) in variation_groups.items():
        graph.attach_new_criterion(
            label + "_IDENTIFY_REASON",
            label + "_" + group_label,
            summary=group_info["summary"],
            details=_variation_details(group_info["variations"]),
            feedback_string_generator=symbolic_feedback_string_generators["IDENTIFY_REASON"]("UNKNOWN")
        )
        graph.attach_new_evaluation(
            label + "_" + group_label,
            label + "_GET_CANDIDATES_" + group_label,
            summary ="Get candidate responses that satisfy " + expression.content_string(),
            details ="Get candidate responses that satisfy " + expression.content_string(),
            evaluate=get_candidates
        )

    for (value, expressions) in values_and_expressions.items():
        expressions_string = ", ".join([str(e) for e in expressions])
        for group_label in values_and_variations_group[value]:
            if group_label != "UNKNOWN":
                group_candidates_eval = graph.evaluations[label + "_GET_CANDIDATES_" + group_label]
                if label + "_RESPONSE_CANDIDATES_" + group_label not in [edge.target.label for edge in group_candidates_eval.outgoing]:
                    attach_terminal_criterion(
                        graph,
                        label + "_GET_CANDIDATES_" + group_label,
                        label + "_RESPONSE_CANDIDATES_" + group_label,
                        END,
                        summary ="response = " + str(value),
                        details ="Response candidates: " + expressions_string
                    )


def criterion_where_node(criterion: ExprNode, parameters: EvaluationParameters, label: str | None = None) -> CriteriaGraph:
    parsing_params = parameters.parsing_parameters
    expression = criterion.children[0]
    subs = where_substitutions(criterion.children[1])
    local_subs = parse_where_substitutions(criterion.children[1], parsing_params)
    if label is None:
        label = criterion.content_string()

    def expression_check(_response: Any) -> ReachedCriteria:
        result = check_equality(expression, parameters, local_substitutions=local_subs)
        return outcome_tag(label, result is True)

    subs_string = ", ".join(name + " = " + expr for name, expr in subs)
    graph, END = outcome_graph(
        label,
        summary=label,
        details ="Checks if " + expression.content_string() + " where " + subs_string + ".",
        evaluate=expression_check
    )
    attach_terminal_criterion(
        graph,
        label,
        label + "_TRUE",
        END,
        summary =expression.content_string() + " where " + subs_string,
        details =expression.content_string() + " where " + subs_string + "is true.",
        feedback_string_generator=symbolic_feedback_string_generators["response=answer_where"]("TRUE")
    )
    graph.attach_new_criterion(
        label,
        label + "_FALSE",
        summary ="not " + expression.content_string(),
        details =expression.content_string() + " is not true when " + subs_string + ".",
        feedback_string_generator=symbolic_feedback_string_generators["response=answer_where"]("FALSE")
    )

    expression_to_vary = _expression_to_vary(expression)
    if expression_to_vary is None:
        return graph

    reserved_expressions = list(parameters.reserved_expressions.items())
    response_value = parameters.reserved_expressions["response"].subs(local_subs)
    expression_to_vary = parse_expression(expression_to_vary.content_string(), parsing_params).subs(reserved_expressions)
    variation_groups = _variation_groups(criterion, expression_to_vary)
    values_and_expressions, values_and_variations_group = _group_values(expression_to_vary, variation_groups, local_subs)
    if len(values_and_expressions) > 1:
        _add_identify_reason_nodes(
            graph, END, label, criterion, expression, variation_groups,
            values_and_expressions, values_and_variations_group, response_value
        )
    return graph
