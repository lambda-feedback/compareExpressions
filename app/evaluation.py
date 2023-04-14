from app.expression_utilities import (
    preprocess_expression,
    parse_expression,
    create_sympy_parsing_params
)
from app.evaluation_response_utilities import EvaluationResponse
from app.comparison_utilities import symbolic_comparison, compute_relative_tolerance_from_significant_decimals
from app.slr_quantity import quantity_comparison
from app.unit_system_conversions import set_of_SI_prefixes, set_of_SI_base_unit_dimensions, set_of_derived_SI_units_in_SI_base_units, set_of_common_units_in_SI, set_of_very_common_units_in_SI, conversion_to_base_si_units


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

    answer, response = preprocess_expression([answer, response], parameters)
    parsing_params = create_sympy_parsing_params(
        parameters, unsplittable_symbols=unsplittable_symbols
    )

    if parameters.get("physical_quantity", False):
        eval_response = quantity_comparison(response, answer, parameters, parsing_params, eval_response)
    else:
        eval_response.is_correct = symbolic_comparison(response, answer, parameters)["is_correct"]

    return eval_response.serialise(include_test_data)
