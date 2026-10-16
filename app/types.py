"""Type aliases shared across the evaluation function."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any, TypeAlias

from lambdafeedback.criteria import CriteriaGraph, FeedbackStringGenerator
from lambdafeedback.slr_parsing import ExprNode
from sympy import Basic

# The evaluation parameters passed to the contexts.
# CONSIDER: Replace with a dataclass so that the available parameters are explicit.
Parameters: TypeAlias = Mapping[str, Any]

# A parsed response or answer: one expression, or a set of them for a list of answers.
Expression: TypeAlias = Basic | set[Basic]

# Substitutions as passed to sympy's `subs`, as (name, value) pairs. Use for parameters.
Substitutions: TypeAlias = Iterable[tuple[str, Any]]

# Parsed substitutions, as returned by `parse_where_substitutions`: a list, so it can be used more than once.
SubstitutionList: TypeAlias = list[tuple[str, Basic]]

# Builds the criteria graph for a criterion.
GraphTemplate: TypeAlias = Callable[[ExprNode, Parameters], CriteriaGraph]

# Feedback text generators by group: `generators[group](tag)(inputs)` is the text (or None).
FeedbackGenerators: TypeAlias = dict[str, Callable[[str], FeedbackStringGenerator]]
