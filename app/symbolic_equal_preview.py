import re
from typing import Dict, List, TypedDict

import sympy
from latex2sympy2 import latex2sympy
from sympy.parsing import parse_expr
from sympy.printing.latex import LatexPrinter
from typing_extensions import NotRequired

from sympy import latex
from sympy.parsing.sympy_parser import T as parser_transformations
from .expression_utilities import (
    substitute_input_symbols,
    parse_expression,
    create_sympy_parsing_params,
    create_expression_set,
    convert_absolute_notation,
    find_matching_parenthesis
)
from .feedback.symbolic_comparison import internal as symbolic_comparison_internal_messages

class Symbol(TypedDict):
    latex: str
    aliases: List[str]


SymbolDict = Dict[str, Symbol]
symbol_latex_re = re.compile(
    r"(?P<start>\\\(|\$\$|\$)(?P<latex>.*?)(?P<end>\\\)|\$\$|\$)"
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


def sympy_symbols(symbols: SymbolDict) -> Dict[str, sympy.Symbol]:
    """Create a mapping of local variables for parsing sympy expressions.

    Args:
        symbols (SymbolDict): A dictionary of sympy symbol strings to LaTeX
        symbol strings.

    Note:
        Only the sympy string is used in this function.

    Returns:
        Dict[str, sympy.Symbol]: A dictionary of sympy symbol strings to sympy
        Symbol objects.
    """
    return {k: sympy.Symbol(k) for k in symbols}


def extract_latex(symbol: str) -> str:
    """Returns the latex portion of a symbol string.

    Note:
        Only the first matched expression is returned.

    Args:
        symbol (str): The string to extract latex from.

    Returns:
        str: The latex string.
    """
    if (match := symbol_latex_re.search(symbol)) is None:
        return symbol

    return match.group("latex")


def latex_symbols(symbols: SymbolDict) -> Dict[sympy.Symbol, str]:
    """Create a mapping between custom Symbol objects and LaTeX symbol strings.
    Used when parsing a sympy Expression to a LaTeX string.

    Args:
        symbols (SymbolDict): A dictionary of sympy symbol strings to LaTeX
        symbol strings.

    Returns:
        Dict[sympy.Symbol, str]: A dictionary of sympy Symbol objects to LaTeX
        strings.
    """
    return {
        sympy.Symbol(k): extract_latex(v["latex"])
        for (k, v) in symbols.items()
    }


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

    for sympy_symbol_str in symbols:
        symbol_str = symbols[sympy_symbol_str]["latex"]
        latex_symbol_str = extract_latex(symbol_str)

        try:
            latex_symbol = latex2sympy(latex_symbol_str)
        except Exception:
            raise ValueError(
                f"Couldn't parse latex symbol {latex_symbol_str} "
                f"to sympy symbol."
            )

        substitutions[latex_symbol] = sympy.Symbol(sympy_symbol_str)

    try:
        expression = latex2sympy(response, substitutions)

        if isinstance(expression, list):
            expression = expression.pop()

        return str(expression.xreplace(substitutions))  # type: ignore

    except Exception as e:
        raise ValueError(str(e))

def parse_symbolic(response: str, params):
    response_list = create_expression_set(response, params)
    result_sympy_expression = []
    result_latex = []
    feedback = []
    for response in response_list:
        response = response.strip()
        response = substitute_input_symbols([response],params)
    parsing_params = create_sympy_parsing_params(params)
    parsing_params["extra_transformations"] = parser_transformations[9] # Add conversion of equal signs

    if "symbol_assumptions" in params.keys():
        symbol_assumptions_strings = params["symbol_assumptions"]
        symbol_assumptions = []
        index = symbol_assumptions_strings.find("(")
        while index > -1:
            index_match = find_matching_parenthesis(symbol_assumptions_strings,index)
            try:
                symbol_assumption = eval(symbol_assumptions_strings[index+1:index_match])
                symbol_assumptions.append(symbol_assumption)
            except (SyntaxError, TypeError) as e:
                raise Exception("List of symbol assumptions not written correctly.")
            index = symbol_assumptions_strings.find('(',index_match+1)
        for sym, ass in symbol_assumptions:
            try:
                parsing_params["symbol_dict"].update({sym: eval("Symbol('"+sym+"',"+ass+"=True)")})
            except Exception as e:
               raise Exception(f"Assumption {ass} for symbol {sym} caused a problem.")


    # Converting absolute value notation to a form that SymPy accepts
    response, response_feedback = convert_absolute_notation(response, "response")
    if response_feedback is not None:
        feedback.append(response_feedback)

    for response in response_list:
        # Safely try to parse answer and response into symbolic expressions
        try:
            if "atol" in params.keys():
                parsing_params.update({"atol": params["atol"]})
            if "rtol" in params.keys():
                parsing_params.update({"rtol": params["rtol"]})
            res = parse_expression(response, parsing_params)
        except Exception as exc:
            raise SyntaxError(symbolic_comparison_internal_messages["PARSE_ERROR"](response)) from exc
        result_sympy_expression.append(res)

    return result_sympy_expression, feedback


def preview_function(response: str, params: Params) -> Result:
    """
    Function used to preview a student response.
    ---
    The handler function passes three arguments to preview_function():

    - `response` which are the answers provided by the student.
    - `params` which are any extra parameters that may be useful,
        e.g., error tolerances.

    The output of this function is what is returned as the API response
    and therefore must be JSON-encodable. It must also conform to the
    response schema.

    Any standard python library may be used, as well as any package
    available on pip (provided it is added to requirements.txt).

    The way you wish to structure you code (all in this function, or
    split into many) is entirely up to you.
    """
    symbols: SymbolDict = params.get("symbols", {})

    if not response:
        return Result(preview=Preview(latex="", sympy=""))

    try:
        if params.get("is_latex", False):
            response = parse_latex(response, symbols)

#            equation = parse_expr(
#                response,
#                evaluate=False,
#                local_dict=sympy_symbols(symbols),
#                transformations="all",
#            )

        params.update({"rationalise": False})
        expression_list, _ = parse_symbolic(response, params)

        latex_out = []
        sympy_out = []
        for expression in expression_list:
            if params.get("simplify", False):
                expression = sympy.simplify(expression)
            latex_out.append(
                LatexPrinter({"symbol_names": latex_symbols(symbols)}).doprint(expression)
            )
            sympy_out.append(str(expression))

        if len(sympy_out) == 1:
            sympy_out = sympy_out[0]
        sympy_out = str(sympy_out)

        if len(latex_out) > 1:
            latex_out = "\\left\\{"+",~".join(latex_out)+"\\right\\}"
        else:
            latex_out = latex_out[0]

    except SyntaxError as e:
        raise ValueError("Failed to parse Sympy expression") from e
    except ValueError as e:
        raise ValueError("Failed to parse LaTeX expression") from e

    return Result(preview=Preview(latex=latex_out, sympy=sympy_out))
