"""Written forms of numbers for "written as" criteria (moved out of lambdafeedback.expression_parsing)."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from lambdafeedback.expression_parsing import (
    is_complex_number_on_cartesian_form,
    is_complex_number_on_exponential_form,
    is_number,
)


@dataclass(frozen=True)
class SyntacticalPattern:
    """A written form of numbers, for "written as" criteria.

    ``summary``/``details`` render descriptions from the criterion node (whose
    two children are the compared expressions) and the parameters.
    """

    matcher: Callable[[str], bool]
    name: str
    summary: Callable[[Any, Any], str]
    details: Callable[[Any, Any], str]


def _both(criterion: Any) -> str:
    return f"{criterion.children[0].content_string()} and {criterion.children[1].content_string()}"


PATTERNS: dict[str, SyntacticalPattern] = {
    "NUMBER": SyntacticalPattern(
        matcher=is_number,
        name="simplified number",
        summary=lambda criterion, parameters: f"{_both(criterion)} are both numbers written in simplified form.",
        details=lambda criterion, parameters: f"{_both(criterion)} are both numbers written in simplified form.",
    ),
    "CARTESIAN": SyntacticalPattern(
        matcher=is_complex_number_on_cartesian_form,
        name="cartesian",
        summary=lambda criterion, parameters: f"{_both(criterion)} are both complex numbers written in cartesian form",
        details=lambda criterion, parameters: (
            f"{_both(criterion)} are both complex numbers written in cartesian form, i.e. $a+bi$."
        ),
    ),
    "EXPONENTIAL": SyntacticalPattern(
        matcher=is_complex_number_on_exponential_form,
        name="exponential",
        summary=lambda criterion, parameters: (
            f"{_both(criterion)} are both complex numbers written in exponential form"
        ),
        details=lambda criterion, parameters: (
            f"{_both(criterion)} are both complex numbers written in exponential form, i.e. $a exp(bi)$."
        ),
    ),
}
