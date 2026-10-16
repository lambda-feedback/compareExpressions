"""Type aliases shared by the contexts."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, TypeAlias

from lambdafeedback.criteria import CriteriaGraph
from lambdafeedback.slr_parsing import ExprNode
from sympy import Basic

# The evaluation parameters passed to the contexts.
# CONSIDER: Replace with a dataclass so that the available parameters are explicit.
Parameters: TypeAlias = Mapping[str, Any]

# A parsed physical quantity, as returned by `physical_quantity.parsing.parse_quantity`.
# CONSIDER: Replace with a dataclass.
QuantityDict: TypeAlias = dict[str, Any]

# A parsed response or answer: one expression, or a set of them for a list of answers.
Expression: TypeAlias = Basic | set[Basic]

# Substitutions as passed to sympy's `subs`.
Substitutions: TypeAlias = list[tuple[str, Any]]

# Builds the criteria graph for a criterion.
GraphTemplate: TypeAlias = Callable[[ExprNode, Parameters], CriteriaGraph]
