"""Helpers for building the `CriteriaGraph`s shared by the symbolic and physical quantity contexts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from lambdafeedback.criteria import CriteriaGraph, Evaluate, FeedbackStringGenerator, OutputNode, ReachedCriteria


def outcome_tag(label: str, result: bool | None, inputs: Mapping[str, Any] | None = None) -> ReachedCriteria:
    """`{label+"_TRUE": inputs}` if `result` is True, `label+"_FALSE"` if it is False, otherwise `label+"_UNKNOWN"`."""
    if result is True:
        return {label+"_TRUE": inputs}
    elif result is False:
        return {label+"_FALSE": inputs}
    else:
        return {label+"_UNKNOWN": inputs}


def outcome_graph(label: str, summary: str, details: str, evaluate: Evaluate) -> tuple[CriteriaGraph, OutputNode]:
    """A new graph `label` with an end node and a single evaluation node `label`, ready for its outcomes to be attached."""
    graph = CriteriaGraph(label)
    end = graph.add_end_node()
    graph.add_evaluation_node(label, summary=summary, details=details, evaluate=evaluate)
    return graph, end


def attach_terminal_criterion(
    graph: CriteriaGraph,
    evaluation_label: str,
    label: str,
    end: OutputNode,
    summary: str,
    details: str,
    feedback_string_generator: FeedbackStringGenerator | None = None,
) -> None:
    """Attaches a new criterion `label` to `evaluation_label` and connects it to the `end` node."""
    graph.attach_new_criterion(
        evaluation_label,
        label,
        summary=summary,
        details=details,
        feedback_string_generator=feedback_string_generator
    )
    graph.attach(label, end.label)
