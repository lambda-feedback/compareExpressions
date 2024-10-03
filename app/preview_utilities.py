from typing import TypedDict
from typing_extensions import NotRequired

import sympy
from latex2sympy2 import latex2sympy

from .expression_utilities import (
    extract_latex,
    SymbolDict,
    find_matching_parenthesis,
)

class Params(TypedDict):
    is_latex: bool
    simplify: NotRequired[bool]
    symbols: NotRequired[SymbolDict]


class Preview(TypedDict):
    latex: str
    sympy: str
    feedback: str


class Result(TypedDict):
    preview: Preview


def parse_latex(response: str, symbols: SymbolDict) -> str:
    """Parse a LaTeX string to a sympy string while preserving custom symbols.

    Args:
        response (str): The LaTeX expression to parse.
        symbols (SymbolDict): A mapping of sympy symbol strings and LaTeX
        symbol strings.

    Raises:
        ValueError: If the LaTeX string or symbol couldn't be parsed.

    Returns:
        str: The expression in sympy syntax.
    """
    substitutions = {}

    pm_placeholder = None
    mp_placeholder = None

    if r"\pm " in response or r"\mp " in response:
        for char in 'abcdefghjkoqrtvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ':
            if char not in response and pm_placeholder is None:
                pm_placeholder = char
            elif char not in response and mp_placeholder is None:
                mp_placeholder = char
            if pm_placeholder is not None and mp_placeholder is not None:
                break

    if pm_placeholder is not None:
        response = response.replace(r"\pm ", pm_placeholder)
    if mp_placeholder is not None:
        response = response.replace(r"\mp ", mp_placeholder)

    for sympy_symbol_str in symbols:
        symbol_str = symbols[sympy_symbol_str]["latex"]
        latex_symbol_str = extract_latex(symbol_str)

        if "\pm" not in symbol_str and "\mp" not in symbol_str:
            try:
                latex_symbol = latex2sympy(latex_symbol_str)
            except Exception:
                raise ValueError(
                    f"Couldn't parse latex symbol {latex_symbol_str} "
                    f"to sympy symbol."
                )
            substitutions[latex_symbol] = sympy.Symbol(sympy_symbol_str)

    substitutions.update({r"\pm ": pm_placeholder, r"\mp ": mp_placeholder})

    try:
        expression = latex2sympy(response, substitutions)
        if isinstance(expression, list):
            expression = expression.pop()
    except Exception as e:
        raise ValueError(str(e))

    result_str = str(expression.xreplace(substitutions))
    for ph in [(pm_placeholder, "plus_minus"), (mp_placeholder, "minus_plus")]:
        if ph[0] is not None:
            result_str = result_str.replace("*"+ph[0]+"*", " "+ph[1]+" ")
            result_str = result_str.replace(ph[0]+"*", " "+ph[1]+" ")
            result_str = result_str.replace("*"+ph[0], " "+ph[1]+" ")
            result_str = result_str.replace(ph[0], " "+ph[1]+" ")

    return result_str


def sanitise_latex(response):
    response = "".join(response.split())
    response = response.replace('~',' ')
    wrappers = [r"\mathrm",r"\text"]
    for wrapper in wrappers:
        processed_response = []
        index = 0
        while index < len(response):
            wrapper_start = response.find(wrapper+"{", index)
            if wrapper_start > -1:
                processed_response.append(response[index:wrapper_start])
                wrapper_end = find_matching_parenthesis(response, wrapper_start+1, delimiters=('{','}'))
                inside_wrapper = response[(wrapper_start+len(wrapper+"{")):wrapper_end]
                processed_response.append(inside_wrapper)
                index = wrapper_end+1
            else:
                processed_response.append(response[index:])
                index = len(response)
        response = "".join(processed_response)
    return response