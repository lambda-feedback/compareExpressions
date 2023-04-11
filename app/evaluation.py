from app.expression_utilities import (
    preprocess_expression,
    parse_expression,
    create_sympy_parsing_params
)
from app.evaluation_response_utilities import EvaluationResponse
from app.symbolic_equal import evaluation_function as symbolicEqual
from app.slr_quantity import SLR_quantity_parsing as quantity_parsing
from app.slr_quantity import SLR_quantity_parser as quantity_parser
# from app.slr_quantity import criteria as strict_SI_criteria
from app.parsers import SLR_implicit_multiplication_convention_parser
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
        all_units = set_of_SI_prefixes | set_of_SI_base_unit_dimensions | set_of_derived_SI_units_in_SI_base_units | set_of_common_units_in_SI | set_of_very_common_units_in_SI
        unsplittable_symbols = [x[0] for x in all_units]

    parameters = {"comparison": "expression", "strict_syntax": True}
    parameters.update(params)

    answer, response = preprocess_expression([answer, response], parameters)
    parsing_params = create_sympy_parsing_params(
        parameters, unsplittable_symbols=unsplittable_symbols
    )

    if parameters.get("physical_quantity", False):
        eval_response.is_correct = True
        # NOTE: this is the only mode that is supported right now
        # The expected forms of the response are:
        #       NUMBER UNIT_EXPRESSION
        #       MATHEMATICAL_EXPRESSION UNIT_EXPRESSION
        # strict_SI_parsing returns a Quantity object.
        # For this file the relevant content of the quantity object is the messages and the passed criteria.
        units_string = parameters.get("units_string", "SI")
        strictness = parameters.get("strictness", "strict")
        try:
            ans_parsed, ans_latex = quantity_parsing(answer, units_string=units_string, strictness=strictness)
        except Exception as e:
            raise Exception("Could not parse quantity expression") from e

        try:
            res_parsed, res_latex = quantity_parsing(response, units_string=units_string, strictness=strictness)
        except Exception as e:
            eval_response.add_feedback(("PARSE_EXCEPTION", str(e)))
            eval_response.is_correct = False
            return eval_response.serialise(include_test_data)

        # Collects messages from parsing the response, these needs to be returned as feedback later
        for message in res_parsed.messages:
            eval_response.add_feedback(message)

        # Computes the desired tolerance used for numerical computations based on the formatting of the answer
        if ans_parsed.passed("NUMBER_VALUE"):
            parameters["rtol"] = parameters.get(
                "rtol",
                compute_relative_tolerance_from_significant_decimals(
                    ans_parsed.value.content_string()
                ),
            )

        def expand_units(node):
            parser = quantity_parser(units_string, strictness)
            if node.label == "UNIT" and len(node.children) == 0:
                expanded_unit_content = conversion_to_base_si_units[node.content]
                node = parser.parse(parser.scan(expanded_unit_content))[0]
            for k, child in enumerate(node.children):
                node.children[k] = expand_units(child)
            return node

        def convert_to_standard_unit(q):
            q_converted_value = q.value.content_string() if q.value is not None else None
            q_converted_unit = None
            if q.unit is not None:
                q_converted_unit = q.unit.copy()
                q_converted_unit = expand_units(q_converted_unit)
                q_converted_unit = q_converted_unit.content_string()
                q_converted_unit = parse_expression(q_converted_unit, parsing_params)
            if q.passed("FULL_QUANTITY"):
                try:
                    q_converted_unit_factor = q_converted_unit.subs({name: 1 for name in [x[0] for x in set_of_SI_base_unit_dimensions]}).simplify()
                    q_converted_unit = (q_converted_unit/q_converted_unit_factor).simplify()
                except Exception as e:
                    raise Exception("SymPy was unable to parse the answer unit") from e
                q_converted_value = "("+str(q_converted_value)+")*("+str(q_converted_unit_factor)+")"
            return q_converted_value, q_converted_unit

        ans_converted_value, ans_converted_unit = convert_to_standard_unit(ans_parsed)
        res_converted_value, res_converted_unit = convert_to_standard_unit(res_parsed)

        response_latex = []

        if res_parsed.passed("HAS_VALUE"):
            # TODO redesign symbolicEqual so that it can easily return latex version of input
            if ans_parsed.passed("NUMBER_VALUE") and not res_parsed.passed("NUMBER_VALUE"):
                preview_parameters = {**parameters}
                del preview_parameters["rtol"]
                value_comparison_response = symbolicEqual(res_parsed.value.original_string(), "0", preview_parameters)
            else:
                value_comparison_response = symbolicEqual(res_parsed.value.original_string(), "0", parameters)
            # TODO Update symbolicEqual to use new evaluationResponse system
            # response_latex += [value_comparison_response.response_latex]
            response_latex += [value_comparison_response.get("response_latex", "")]
        if res_latex is not None and len(res_latex) > 0:
            if len(response_latex) > 0:
                response_latex += ["~"]
            response_latex += [res_latex]
        eval_response.latex = "".join(response_latex)

        def compare_response_and_answer(comp_tag, action, not_res_tag, not_res_message, not_ans_tag, not_ans_message):
            if res_parsed.passed(comp_tag) and ans_parsed.passed(comp_tag):
                eval_response.is_correct = eval_response.is_correct and action()
            elif not res_parsed.passed(comp_tag) and ans_parsed.passed(comp_tag):
                eval_response.add_feedback((not_res_tag, not_res_message))
                eval_response.is_correct = False
            elif res_parsed.passed(comp_tag) and not ans_parsed.passed(comp_tag):
                eval_response.add_feedback((not_ans_tag, not_ans_message))
                eval_response.is_correct = False

        compare_response_and_answer(
            "HAS_VALUE", lambda: symbolic_comparison(res_converted_value, ans_converted_value, parameters)["is_correct"],
            "MISSING_VALUE", "The response is missing a value.",
            "UNEXPECTED_VALUE", "The response is expected only have unit(s), no value."
        )

        compare_response_and_answer(
            "HAS_UNIT", lambda: bool((res_converted_unit - ans_converted_unit).simplify() == 0),
            "MISSING_UNIT", "The response is missing unit(s).",
            "UNEXPECTED_UNIT", "The response is expected only have unit(s), no value."
        )

        # TODO: Comparison of units in way that allows for constructive feedback

        for criterion in res_parsed.passed_dict.keys():
            eval_response.add_feedback((criterion,  res_parsed.passed(criterion)))
    else:
        eval_response.is_correct = symbolic_comparison(response, answer, parameters)["is_correct"]

    return eval_response.serialise(include_test_data)


def symbolic_comparison(response, answer, parameters):
    convention = parameters.get("convention", None)
    if convention is not None:
        parser = SLR_implicit_multiplication_convention_parser(convention)
        response = parser.parse(parser.scan(response))[0].content_string()
        answer = parser.parse(parser.scan(answer))[0].content_string()
    value_comparison_response = symbolicEqual(response, answer, parameters)
    return value_comparison_response


def compute_relative_tolerance_from_significant_decimals(string):
    rtol = None
    string = string.strip()
    separators = "e*^ "
    separator_indices = []
    for separator in separators:
        if separator in string:
            separator_indices.append(string.index(separator))
        else:
            separator_indices.append(len(string))
    index = min(separator_indices)
    significant_characters = string[0:index].replace(".", "")
    index = 0
    for c in significant_characters:
        if c in "-0":
            index += 1
        else:
            break
    significant_characters = significant_characters[index:]
    rtol = 5*10**(-len(significant_characters))
    return rtol

    return
