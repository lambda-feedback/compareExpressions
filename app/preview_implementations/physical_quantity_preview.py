from ..utility.expression_utilities import (
    find_matching_parenthesis,
    parse_expression,
    SymbolDict,
    sympy_to_latex,
)

from ..utility.preview_utilities import (
    Params,
    Preview,
    Result,
    parse_latex,
    sanitise_latex,
)

from ..utility.physical_quantity_utilities import SLR_quantity_parser as quantity_parser
from ..utility.physical_quantity_utilities import SLR_quantity_parsing as quantity_parsing


def fix_exponents(response):
    processed_response = []
    exponents_notation = ['^', '**']
    for notation in exponents_notation:
        index = 0
        while index < len(response):
            exponent_start = response.find(notation, index)
            if exponent_start > -1:
                processed_response.append(response[index:exponent_start])
                exponent_start += len(notation)
                processed_response.append("**")
                exponent_end = find_matching_parenthesis(response, exponent_start, delimiters=('{', '}'))
                if exponent_end > 0:
                    inside_exponent = '('+response[(exponent_start+len(notation)):exponent_end]+')'
                    processed_response.append(inside_exponent)
                    index = exponent_end+1
                else:
                    index = exponent_start
            else:
                processed_response.append(response[index:])
                break
        response = "".join(processed_response)
        processed_response = []
    return response


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

    latex_out = ""
    sympy_out = ""

    parser = quantity_parser(params)

    try:
        if params.get("is_latex", False):
            response = sanitise_latex(response)
            response = fix_exponents(response)
            res_parsed = quantity_parsing(response, params, parser, "response")
            value = res_parsed.value
            unit = res_parsed.unit
            value_latex = ""
            if value is not None:
                value_string = parse_latex(value.content_string(), symbols, params.get("simplify", False))
                params.update({"is_latex": False})
                value = parse_expression(value_string, params)
                value_latex = sympy_to_latex(value, symbols)
            separator_latex = ""
            separator_sympy = ""
            if value is not None and unit is not None:
                separator_latex = "~"
                separator_sympy = " "
            unit_latex = res_parsed.unit_latex_string if unit is not None else ""
            latex_out = value_latex+separator_latex+unit_latex
            value_sympy = str(value)
            unit_sympy = res_parsed.unit.content_string() if unit is not None else ""
            sympy_out = value_sympy+separator_sympy+unit_sympy
        else:
            res_parsed = quantity_parsing(response, params, parser, "response")
            latex_out = res_parsed.latex_string
            sympy_out = response

    except SyntaxError as e:
        raise Exception("Failed to parse Sympy expression") from e
    except ValueError as e:
        raise Exception("Failed to parse LaTeX expression") from e

    return Result(preview=Preview(latex=latex_out, sympy=sympy_out))
