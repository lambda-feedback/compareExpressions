from sympy.printing.latex import LatexPrinter
from sympy.parsing.sympy_parser import T as parser_transformations
from .expression_utilities import (
    extract_latex,
    convert_absolute_notation,
    create_expression_set,
    create_sympy_parsing_params,
    latex_symbols,
    parse_expression,
    substitute_input_symbols,
    SymbolDict,
    sympy_symbols,
)

from .preview_utilities import (
    Params,
    Preview,
    Result,
    extract_latex,
    parse_latex
)

from .slr_quantity import SLR_quantity_parser
from .slr_quantity import SLR_quantity_parsing as quantity_parsing

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

    try:
        if params.get("is_latex", False):
            response = parse_latex(response, symbols)

        quantity_parser = SLR_quantity_parser(params)
        res_parsed = quantity_parsing(response, params, quantity_parser, "response")

        latex_out = res_parsed.latex_string
        sympy_out = response

    except SyntaxError as e:
        raise ValueError("Failed to parse Sympy expression") from e
    except ValueError as e:
        raise ValueError("Failed to parse LaTeX expression") from e

    return Result(preview=Preview(latex=latex_out, sympy=sympy_out))
