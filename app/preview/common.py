"""Types shared by the symbolic and physical quantity previews."""

from __future__ import annotations

from typing import NotRequired, TypedDict

from lambdafeedback.expression_parsing import ExpressionParsingError

from ..feedback.tags import FeedbackTag


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
