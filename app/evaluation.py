from .expression_utilities import (
    substitute_input_symbols,
    create_sympy_parsing_params
)
from .evaluation_response_utilities import EvaluationResponse
from .symbolic_comparison_evaluation import evaluation_function as symbolic_comparison
from .slr_quantity import quantity_comparison
from .unit_system_conversions import set_of_SI_prefixes, set_of_SI_base_unit_dimensions
from .preview import preview_function


def evaluation_function(response, answer, params, include_test_data=False) -> dict:
    """
    Function that allows for various types of comparison of various kinds of expressions.
    Supported input parameters:
    strict_SI_syntax:
        - if set to True, use basic dimensional analysis functionality.
    """

    eval_response = EvaluationResponse()
    eval_response.is_correct = False

    if "substitutions" in params.keys():
        unsplittable_symbols = tuple()
    else:
        all_units = set_of_SI_prefixes | set_of_SI_base_unit_dimensions
        unsplittable_symbols = [x[0] for x in all_units]

    parameters = {"comparison": "expression", "strict_syntax": True}
    parameters.update(params)

    if params.get("is_latex",False):
        preview_result = preview_function(response, params)["preview"]["sympy"]

    answer, response = substitute_input_symbols([answer, response], parameters)
    parsing_params = create_sympy_parsing_params(
        parameters, unsplittable_symbols=unsplittable_symbols
    )

    if parameters.get("physical_quantity", False) is True:
        eval_response = quantity_comparison(response, answer, parameters, parsing_params, eval_response)
    else:
        eval_response = symbolic_comparison(response, answer, parameters, eval_response)

    return eval_response.serialise(include_test_data)
