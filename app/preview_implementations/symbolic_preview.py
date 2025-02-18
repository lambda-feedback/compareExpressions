from sympy.parsing.sympy_parser import T as parser_transformations
from ..utility.expression_utilities import (
    default_parameters,
    convert_absolute_notation,
    create_expression_set,
    create_sympy_parsing_params,
    parse_expression,
    substitute_input_symbols,
    SymbolDict,
    sympy_symbols,
    sympy_to_latex,
    preprocess_expression,
)
from ..utility.preview_utilities import (
    Params,
    Preview,
    Result,
    parse_latex
)
from ..feedback.symbolic import feedback_generators as symbolic_feedback_string_generators


def parse_symbolic(response: str, params):
    symbolic_comparison_internal_messages = symbolic_feedback_string_generators["INTERNAL"]
    response_list_in = create_expression_set(response, params)
    response_list_out = []
    feedback = []
    for response in response_list_in:
        response = substitute_input_symbols([response.strip()], params)[0]

        # Converting absolute value notation to a form that SymPy accepts
        response, response_feedback = convert_absolute_notation(response, "response")
        if response_feedback is not None:
            feedback.append(response_feedback)
        response_list_out.append(response)

    parsing_params = create_sympy_parsing_params(params)
    parsing_params["extra_transformations"] = parser_transformations[9]  # Add conversion of equal signs
    parsing_params["symbol_dict"].update(sympy_symbols(params.get("symbols", {})))
    result_sympy_expression = []
    for response in response_list_out:
        # Safely try to parse answer and response into symbolic expressions
        try:
            if "atol" in params.keys():
                parsing_params.update({"atol": params["atol"]})
            if "rtol" in params.keys():
                parsing_params.update({"rtol": params["rtol"]})
            res = parse_expression(response, parsing_params)
        except Exception as exc:
            raise SyntaxError(symbolic_comparison_internal_messages("PARSE_ERROR")({"response": response})) from exc
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
    for (key, value) in default_parameters.items():
        if key not in params.keys():
            params.update({key: value})

    original_response = response

    symbols: SymbolDict = params.get("symbols", {})

    if not response:
        return Result(preview=Preview(latex="", sympy=""))

    response_list = response.split("=")
    response_latex = []
    response_sympy = []

    for response in response_list:
        try:
            if params.get("is_latex", False) is True:
                sympy_out = [parse_latex(response, symbols, params.get("simplify", False))]
                latex_out = [response]
            else:
                params.update({"rationalise": False})
                _, response, _ = preprocess_expression("response", response, params)
                expression_list, _ = parse_symbolic(response, params)

                parsing_params = create_sympy_parsing_params(params)
                printing_symbols = dict()
                for key in parsing_params["symbol_dict"].keys():
                    if key in symbols.keys():
                        printing_symbols.update({key: symbols[key]["latex"]})

                latex_out = []
                sympy_out = []
                for expression in expression_list:
                    latex_out.append(sympy_to_latex(expression, symbols, settings={"mul_symbol": r" \cdot "}))
                    sympy_out.append(str(expression))

            if len(sympy_out) == 1:
                sympy_out = sympy_out[0]
            sympy_out = str(sympy_out)

            if len(latex_out) > 1:
                latex_out = "\\left\\{"+",~".join(latex_out)+"\\right\\}"
            else:
                latex_out = latex_out[0]

        except SyntaxError as exc:
            raise ValueError(f"Failed to parse SymPy expression: {original_response}") from exc
        except ValueError as exc:
            raise ValueError(f"Failed to parse LaTeX expression: {original_response}") from exc

        response_latex.append(latex_out)
        response_sympy.append(sympy_out)

    return Result(preview=Preview(latex="=".join(response_latex), sympy="=".join(response_sympy)))
