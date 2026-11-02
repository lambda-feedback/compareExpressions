"""The `EvaluationParameters` that the contexts use to build and run the criteria graphs."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import Any

from lambdafeedback.slr_parsing import ExprNode

from app.result import EvaluationResult


@dataclass(frozen=True)
class EvaluationParameters:
    # The reserved expressions as strings, by group: `{"learner": {"response": ...}, "task": {"answer": ...}}`
    reserved_expressions_strings: Mapping[str, Mapping[str, str]]
    # The parsed reserved expressions by name (both groups together), as returned by the context's `expression_parse`
    reserved_expressions: Mapping[str, Any]
    # The parsed criteria by their content string
    criteria: Mapping[str, ExprNode]
    # Labels of the evaluation nodes that skip straight to the end of their graph
    disabled_evaluation_nodes: Collection[str]
    # The parsing parameters made by the context's `parsing_parameters_generator`
    parsing_parameters: Any
    # Holds the feedback that is returned
    evaluation_result: EvaluationResult
    # "all", "all_responses" or "all_answers": which elements must match when the response or answer is a set
    multiple_answers_criteria: str
    # Whether to compare numerically when symbolic comparison fails
    numerical: bool
    # The tolerances as given in the request (0 if not given)
    atol: float
    rtol: float
    # The number of significant figures or decimal places the response must be written to (None if not given)
    sig_figs: int | None
    dp: int | None
    # Custom feedback strings by tag
    custom_feedback: Mapping[str, Any]
