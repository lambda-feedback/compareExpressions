import re
from typing import TypedDict
from typing_extensions import NotRequired

from sympy import Symbol
from latex2sympy2 import latex2sympy

from copy import deepcopy

from .expression_utilities import (
    default_parameters,
    extract_latex,
    SymbolDict,
    find_matching_parenthesis,
    create_expression_set,
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


def find_placeholder(exp):
    for char in 'abcdfghjkoqrtvwxyzABCDFGHIJKLMNOPQRSTUVWXYZ':
        if char not in exp:
            return char

def preprocess_E(latex_str: str, placeholder: str) -> str:
    """
    Replace all symbols starting with 'E' (including plain 'E') with a
    placeholder, so latex2sympy does not interpret 'E' as Euler's number.
    """
    # Replace E, E_x, ER_2, Efield, etc.
    def repl(match):
        token = match.group(0)
        return placeholder + token[1:]

    # Match E followed by optional subscript or alphanumeric/underscore
    pattern = re.compile(r'(?<![\\a-zA-Z])E([A-Za-z0-9_]*(?:_\{[^}]*\})?)')
    return pattern.sub(repl, latex_str)


def postprocess_E(expr, placeholder):
    """
    Replace all placeholder symbols back to symbols starting with E.
    """
    subs = {}
    for s in expr.free_symbols:
        name = str(s)
        if name.startswith(placeholder):
            new_name = "E" + name[len(placeholder):]
            subs[s] = Symbol(new_name)
    return expr.xreplace(subs)



def parse_latex(response: str, symbols: SymbolDict, simplify: bool, parameters=None) -> str:
    """Parse a LaTeX string to a sympy string while preserving custom symbols.

    Args:
        response (str): The LaTeX expression to parse.
        symbols (SymbolDict): A mapping of sympy symbol strings and LaTeX
            symbol strings.
        simplify (bool): If set to false the preview will attempt to preserve
            the way that the response was written as much as possible. If set
            to True the response will be simplified before the preview string
            is generated.
        parameters (dict): parameters used when generating sympy output when
            the response is written in LaTeX

    Raises:
        ValueError: If the LaTeX string or symbol couldn't be parsed.

    Returns:
        str: The expression in sympy syntax.
    """
    if parameters is not None:
        for (key, value) in default_parameters.items():
            if key not in parameters.keys():
                parameters.update({key: value})
    else:
        parameters = deepcopy(default_parameters)

    substitutions = {}

    pm_placeholder = None
    mp_placeholder = None

    if r"\pm " in response or r"\mp " in response:
        response_set = set()
        for char in 'abcdefghjkoqrtvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ':
            if char not in response and pm_placeholder is None:
                pm_placeholder = char
                substitutions[pm_placeholder] = Symbol(pm_placeholder, commutative=False)
            elif char not in response and mp_placeholder is None:
                mp_placeholder = char
                substitutions[mp_placeholder] = Symbol(mp_placeholder, commutative=False)
            if pm_placeholder is not None and mp_placeholder is not None:
                break
        for expr in create_expression_set(response.replace(r"\pm ", 'plus_minus').replace(r"\mp ", 'minus_plus'), parameters):
            response_set.add(expr)
        response = response_set
    else:
        response_set = {response}

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
            substitutions[latex_symbol] = Symbol(sympy_symbol_str)

    parsed_responses = set()
    for expression in response_set:
        try:
            e_placeholder = find_placeholder(expression)

            expression_preprocessed = preprocess_E(expression, e_placeholder)
            expression_parsed = latex2sympy(expression_preprocessed, substitutions)
            if isinstance(expression_parsed, list):
                expression_parsed = expression_parsed.pop()

            expression_postprocess = postprocess_E(expression_parsed, e_placeholder)
            if simplify is True:
                expression_postprocess = expression_postprocess.simplify()
        except Exception as e:
            raise ValueError(str(e))

        parsed_responses.add(str(expression_postprocess.xreplace(substitutions)))

    if len(parsed_responses) < 2:
        return parsed_responses.pop()
    else:
        return '{'+', '.join(sorted(parsed_responses))+'}'


def sanitise_latex(response):
    response = "".join(response.split())
    response = response.replace('~', ' ')
    wrappers = [r"\mathrm", r"\text"]
    for wrapper in wrappers:
        processed_response = []
        index = 0
        while index < len(response):
            wrapper_start = response.find(wrapper+"{", index)
            if wrapper_start > -1:
                processed_response.append(response[index:wrapper_start])
                wrapper_end = find_matching_parenthesis(response, wrapper_start+1, delimiters=('{', '}'))
                inside_wrapper = response[(wrapper_start+len(wrapper+"{")):wrapper_end]
                processed_response.append(inside_wrapper)
                index = wrapper_end+1
            else:
                processed_response.append(response[index:])
                index = len(response)
        response = "".join(processed_response)
    return response
