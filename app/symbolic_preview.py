"""Previewing a learner's response: LaTeX and SymPy renderings of what was typed.

Moved here from ``lambdafeedback.expression_parsing``: rendering a
response for display, and mapping a parse failure to a tag for the learner,
are app-layer concerns.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, NotRequired, TypedDict

from sympy import Basic

from lambdafeedback.expression_parsing import (
    AbsoluteValueNotationError,
    BracketNotationError,
    ExpressionParams,
    ExpressionParsingError,
    SympyParsingConfig,
    convert_absolute_notation,
    create_expression_set,
    parse_expression,
    parse_latex,
    preprocess_expression,
    substitute_input_symbols,
    sympy_to_latex,
)

from .feedback.tags import FeedbackTag, FeedbackTagName


class ExpressionSyntaxError(ExpressionParsingError):
    """A response could not be parsed; ``feedback`` is the tag to show the learner."""

    def __init__(self, feedback: FeedbackTag) -> None:
        super().__init__(f"{feedback.tag}: {dict(feedback.inputs)}")
        self.feedback = feedback


class Preview(TypedDict):
    """Structurally compatible with ``lf_toolkit.preview.Preview`` (whose ``feedback`` is required)."""

    latex: str
    sympy: str
    feedback: NotRequired[str]


class Result(TypedDict):
    """Structurally compatible with ``lf_toolkit.preview.Result``."""

    preview: Preview


def _as_params(params: ExpressionParams | Mapping[str, Any]) -> ExpressionParams:
    return params if isinstance(params, ExpressionParams) else ExpressionParams.from_dict(params)


def parse_symbolic(response: str, params: ExpressionParams) -> tuple[list[Basic | set[Basic]], list[FeedbackTag]]:
    """Parse a (preprocessed) response into SymPy expressions, one per expression it stands for.

    Also returns the feedback raised while converting ``|...|`` notation.
    Raises :class:`ExpressionSyntaxError` (with ``PARSE_ERROR`` feedback)
    when an expression can't be parsed.
    """
    responses = []
    feedback: list[FeedbackTag] = []
    for expression in create_expression_set(response, params):
        expression = substitute_input_symbols(expression.strip(), params)
        try:
            expression = convert_absolute_notation(expression, name="response")
        except AbsoluteValueNotationError as exc:
            feedback.append(FeedbackTag(FeedbackTagName.ABSOLUTE_VALUE_NOTATION_AMBIGUITY, {"name": exc.name}))
            expression = exc.expression
        responses.append(expression)

    config = SympyParsingConfig.from_params(params, unsplittable_symbols=params.symbols)
    parsed = []
    for expression in responses:
        try:
            parsed.append(parse_expression(expression, config))
        except Exception as exc:
            raise ExpressionSyntaxError(FeedbackTag(FeedbackTagName.PARSE_ERROR, {"response": expression})) from exc
    return parsed, feedback


def preview_function(response: str, params: ExpressionParams | Mapping[str, Any]) -> Result:
    """Preview a learner's response as LaTeX and SymPy syntax.

    ``params`` may be :class:`ExpressionParams` or evaluation-function
    parameters. Each side of an ``=`` is previewed separately; a response
    standing for several expressions (``{a, b}``, ``±``) previews as a set.
    Raises :class:`ExpressionParsingError` if the response can't be parsed.
    """
    params = _as_params(params)
    if not response:
        return Result(preview=Preview(latex="", sympy=""))

    latex_parts = []
    sympy_parts = []
    for part in response.split("="):
        try:
            if params.is_latex:
                latex_out = [part]
                sympy_out = [parse_latex(part, params.symbols, params.simplify)]
            else:
                symbolic_params = params.replace(rationalise=False)
                try:
                    preprocessed = preprocess_expression(part, symbolic_params, name="response")
                except (BracketNotationError, AbsoluteValueNotationError) as exc:
                    preprocessed = exc.expression
                expressions, _ = parse_symbolic(preprocessed, symbolic_params)
                latex_out = sorted(
                    sympy_to_latex(expression, params.symbols, settings={"mul_symbol": r" \cdot "})
                    for expression in expressions
                )
                sympy_out = [preprocessed]
        except ExpressionSyntaxError as exc:
            raise ExpressionParsingError(f"Failed to parse SymPy expression: {response}") from exc
        except ValueError as exc:
            raise ExpressionParsingError(f"Failed to parse LaTeX expression: {response}") from exc

        sympy_parts.append(sympy_out[0] if len(sympy_out) == 1 else str(sympy_out))
        latex_parts.append(latex_out[0] if len(latex_out) == 1 else "\\left\\{" + ",~".join(latex_out) + "\\right\\}")

    return Result(preview=Preview(latex="=".join(latex_parts), sympy="=".join(sympy_parts)))
