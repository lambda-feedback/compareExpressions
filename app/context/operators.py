"""The comparison operators that criteria can use, by the symbol used in the criteria string."""

import operator

COMPARISON_OPERATORS = {
    "=": operator.eq,
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
}
