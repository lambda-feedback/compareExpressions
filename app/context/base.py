"""The `Context` that specialises the evaluation function for one kind of response (symbolic or physical quantity)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from lambdafeedback.criteria import CriteriaGraph
from lambdafeedback.slr_parsing import SLRParser

from app.preview.common import Result
from app.result import EvaluationResult
from app.types import Parameters


@dataclass(frozen=True)
class Context:
    # Previews the response, as the preview function would
    expression_preview: Callable[[str, Parameters], Result]
    # Builds the parser for the criteria from the parsed reserved expressions
    generate_criteria_parser: Callable[[Mapping[str, Mapping[str, Any]]], SLRParser]
    # `(name, expression, parameters)`: the expression string, ready to be parsed
    expression_preprocess: Callable[[str, str, Parameters], str]
    # `(name, expression, parsing_parameters, evaluation_result)`: the parsed expression
    expression_parse: Callable[[str, str, Any, EvaluationResult], Any]
    # Parameters used when they are not given
    default_parameters: Mapping[str, Any]
    # Criteria used when none are given
    default_criteria: tuple[str, ...]
    # Builds the criteria graph for each parsed criterion
    feedback_procedure_generator: Callable[[Parameters], dict[str, CriteriaGraph]]
    # `(parameters, unsplittable_symbols=...)`: the parsing parameters passed to `expression_parse`
    parsing_parameters_generator: Callable[..., Any]
