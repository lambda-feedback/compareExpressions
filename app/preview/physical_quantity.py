"""Previewing a quantity response: LaTeX and SymPy renderings of value and unit."""

from __future__ import annotations

import tokenize
from collections.abc import Mapping
from typing import Any

from lambdafeedback.expression_parsing import (
    SympyParsingConfig,
    find_matching_parenthesis,
    parse_expression,
    parse_latex,
    sanitise_latex,
    sympy_to_latex,
)
from lambdafeedback.physical_quantities import (
    QuantityError,
    QuantityParams,
    QuantityParseError,
    parse_quantity,
    preprocess_quantity,
)

from app.preview.common import Preview, Result


def fix_exponents(response: str) -> str:
    """Rewrite LaTeX exponents ``^{...}`` / ``**{...}`` as ``**(...)``.

    Only a brace directly after the exponent operator is unwrapped; other
    exponents (``x^2``) just get ``**``.
    """
    for notation in ("^", "**"):
        processed = []
        index = 0
        while index < len(response):
            exponent_start = response.find(notation, index)
            if exponent_start < 0:
                processed.append(response[index:])
                break
            processed.append(response[index:exponent_start] + "**")
            index = exponent_start + len(notation)
            if response.startswith("{", index):
                exponent_end = find_matching_parenthesis(response, index, delimiters=("{", "}"))
                if exponent_end > 0:
                    processed.append("(" + response[index + 1:exponent_end] + ")")
                    index = exponent_end + 1
        response = "".join(processed)
    return response


def preview_function(response: str, params: QuantityParams | Mapping[str, Any]) -> Result:
    """Preview a quantity response as LaTeX and SymPy syntax.

    ``params`` may be :class:`QuantityParams` or evaluation-function
    parameters. Raises :class:`QuantityParseError` if the response can't be
    read as a quantity.
    """
    params = params if isinstance(params, QuantityParams) else QuantityParams.from_dict(params)
    if not response:
        return Result(preview=Preview(latex="", sympy=""))

    try:
        if params.is_latex:
            response = fix_exponents(sanitise_latex(response))
            quantity = parse_quantity(response, params)
            value, unit = quantity.value, quantity.unit
            value_latex = value_sympy = ""
            if value is not None:
                value_string = parse_latex(value.content_string(), params.symbols, params.simplify)
                value_expr = parse_expression(value_string, SympyParsingConfig.from_params(params))
                value_latex = sympy_to_latex(value_expr, params.symbols)
                value_sympy = str(value_expr)
            separators = ("~", " ") if value is not None and unit is not None else ("", "")
            unit_latex = quantity.unit_latex if unit is not None else ""
            unit_sympy = unit.content_string() if unit is not None else ""
            latex_out = value_latex + separators[0] + (unit_latex or "")
            sympy_out = value_sympy + separators[1] + unit_sympy
        else:
            preprocessed = preprocess_quantity(response, params, name="response")
            latex_out = parse_quantity(preprocessed, params).latex
            sympy_out = response
    except QuantityError:
        raise
    except (SyntaxError, tokenize.TokenError) as e:
        raise QuantityParseError("Failed to parse Sympy expression") from e
    except ValueError as e:
        raise QuantityParseError("Failed to parse LaTeX expression") from e

    return Result(preview=Preview(latex=latex_out, sympy=sympy_out))
