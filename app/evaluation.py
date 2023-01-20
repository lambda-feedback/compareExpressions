import sys

try:
    from static_unit_conversion_arrays import (
        names_of_prefixes_units_and_dimensions,
        conversion_to_base_si_units_dictionary,
        list_of_SI_base_unit_dimensions,
    )
    from expression_utilities import (
        preprocess_expression,
        parse_expression,
        create_sympy_parsing_params,
        substitute,
    )
    from evaluation_response_utilities import EvaluationResponse
    from symbolic_equal import evaluation_function as symbolicEqual
    from slr_strict_si_syntax import SLR_strict_SI_parsing as strict_SI_parsing
    from slr_strict_si_syntax import criteria as strict_SI_criteria
    from demo_stuff import SLR_polynomial_parsing as polynomial_parsing
except ImportError:
    from .static_unit_conversion_arrays import (
        names_of_prefixes_units_and_dimensions,
        conversion_to_base_si_units_dictionary,
        list_of_SI_base_unit_dimensions,
    )
    from .expression_utilities import (
        preprocess_expression,
        parse_expression,
        create_sympy_parsing_params,
        substitute,
    )
    from .evaluation_response_utilities import EvaluationResponse
    from .symbolic_equal import evaluation_function as symbolicEqual
    from .slr_strict_si_syntax import SLR_strict_SI_parsing as strict_SI_parsing
    from .slr_strict_si_syntax import criteria as strict_SI_criteria
    from .demo_stuff import SLR_polynomial_parsing as polynomial_parsing

def evaluation_function(response, answer, params, include_test_data = False) -> dict:
    """
    Function that allows for various types of comparison of various kinds of expressions.
    Supported input parameters:
    strict_SI_syntax:
        - if set to True, use a function dimensional analysis functionality.
    """
    eval_response = EvaluationResponse()
    eval_response.is_correct = True

    default_rtol = 1e-12
    if "substitutions" in params.keys():
        unsplittable_symbols = tuple()
    else:
        unsplittable_symbols = names_of_prefixes_units_and_dimensions

    parameters = {"comparison": "expression", "strict_syntax": True}
    parameters.update(params)

    answer, response = preprocess_expression([answer, response], parameters)
    parsing_params = create_sympy_parsing_params(
        parameters, unsplittable_symbols=unsplittable_symbols
    )

    debugging_messages = []

    if parameters.get(
        "strict_SI_syntax", False
    ):  # NOTE: this is the only mode that is supported right now
        # The expected forms of the response are:
        #       NUMBER UNIT_EXPRESSION
        #       MATHEMATICAL_EXPRESSION UNIT_EXPRESSION
        # strict_SI_parsing returns a Quantity object.
        # For this file the relevant content of the quantity object is the messages and the passed criteria.
        try:
            ans_parsed, ans_latex = strict_SI_parsing(answer)
        except Exception as e:
            raise Exception("Could not parse quantity expression") from e

        try:
            res_parsed, res_latex = strict_SI_parsing(response)
        except Exception as e:
            eval_response.add_feedback(("PARSE_EXCEPTION",str(e)))
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

        def convert_to_standard_unit(q):
            q_converted_value = q.value.content_string() if q.value != None else None
            q_converted_unit = parse_expression(q.unit.content_string(), parsing_params) if q.unit != None else None
            if q.passed("FULL_QUANTITY"):
                q_converted_unit = q.unit.content_string()
                substitutions = list(conversion_to_base_si_units_dictionary.items())
                q_converted_unit = substitute(q_converted_unit,substitutions)
                try:
                    q_converted_unit = parse_expression(q_converted_unit, parsing_params)
                    q_converted_unit_factor = q_converted_unit.subs({name: 1 for name in [x[0] for x in list_of_SI_base_unit_dimensions]}).simplify()
                    q_converted_unit = (q_converted_unit/q_converted_unit_factor).simplify()
                except Exception as e:
                    raise Exception("SymPy was unable to parse the answer unit") from e
                q_converted_value = "("+str(q_converted_value)+")*("+str(q_converted_unit_factor)+")"
            return q_converted_value, q_converted_unit

        ans_converted_value, ans_converted_unit = convert_to_standard_unit(ans_parsed)
        res_converted_value, res_converted_unit = convert_to_standard_unit(res_parsed)

        response_latex = []

        if res_parsed.passed("HAS_VALUE"):
            #TODO redesign symbolicEqual so that it can easily return latex version of input
            if ans_parsed.passed("NUMBER_VALUE") and not res_parsed.passed("NUMBER_VALUE"):
                preview_parameters = {**parameters}
                del preview_parameters["rtol"]
                value_comparison_response = symbolicEqual(res_parsed.value.original_string(),"0",preview_parameters)
            else:
                value_comparison_response = symbolicEqual(res_parsed.value.original_string(),"0",parameters)
            #TODO Update symbolicEqual to use new evaluationResponse system
            #response_latex += [value_comparison_response.response_latex]
            response_latex += [value_comparison_response.get("response_latex","")]
        if res_latex != None and len(res_latex) > 0:
            if len(response_latex) > 0:
                response_latex += ["~"]
            response_latex += [res_latex]
        eval_response.latex = "".join(response_latex)

        def compare_response_and_answer(comp_tag,action,not_res_tag,not_res_message,not_ans_tag,not_ans_message):
            if res_parsed.passed(comp_tag) and ans_parsed.passed(comp_tag):
                eval_response.is_correct = eval_response.is_correct and action()
            elif not res_parsed.passed(comp_tag) and ans_parsed.passed(comp_tag):
                eval_response.add_feedback((not_res_tag,not_res_message))
                eval_response.is_correct = False
            elif res_parsed.passed(comp_tag) and not ans_parsed.passed(comp_tag):
                eval_response.add_feedback((not_ans_tag,not_ans_message))
                eval_response.is_correct = False

        def action_HAS_VALUE():
            value_comparison_response = symbolicEqual(res_converted_value,ans_converted_value,parameters)
            return value_comparison_response["is_correct"]

        compare_response_and_answer(\
            "HAS_VALUE", action_HAS_VALUE,\
            "MISSING_VALUE", "The response is missing a value.",\
            "UNEXPECTED_VALUE","The response is expected only have unit(s), no value."
        )

        compare_response_and_answer(\
            "HAS_UNIT", lambda: bool((res_converted_unit - ans_converted_unit).simplify() == 0),\
            "MISSING_UNIT", "The response is missing unit(s).",\
            "UNEXPECTED_UNIT","The response is expected only have unit(s), no value."
        )

        #TODO: Comparison of units in way that allows for constructive feedback

        # Check some of the criteria and creates corresponding feedback
        tested_criteria = [
            "FULL_QUANTITY",
            "NO_UNIT",
            "ONLY_UNIT",
            "NUMBER_VALUE",
            "EXPR_VALUE",
        ]
        feedback = []
        for criterion in tested_criteria:
            if res_parsed.passed(criterion) != None:
                eval_response.add_feedback((criterion,res_parsed.passed(criterion)))
    elif parameters.get("demo_stuff", "") == "polynomial":
        try:
            try:
                ans_parsed = polynomial_parsing(answer)
            except Exception as e:
                raise Exception("Answer is not a polynomial") from e
    
            try:
                res_parsed = polynomial_parsing(response)
            except Exception as e:
                eval_response.add_feedback(("PARSE_EXCEPTION","Response could not be parsed as a polynomial written on standard form."))
                eval_response.is_correct = False
                return eval_response.serialise(include_test_data)
    
            # Safely try to parse answer and response into symbolic expressions
            try:
                res = parse_expression(res_parsed.content_string(), parsing_params)
            except Exception as e:
                eval_response.add_feedback(("PARSE_EXCEPTION","Sympy could not parse response."))
                eval_response.is_correct = False
                return eval_response.serialise(include_test_data)
    
            try:
                ans = parse_expression(answer, parsing_params)
            except Exception as e:
                raise Exception("SymPy was unable to parse the answer.",) from e
    
            # Add how res was interpreted to the response
            from sympy import latex
            eval_response.latex = latex(res)
    
            missed_points = []
            x_values = parameters.get("x_values",None)
            if x_values != None:
                for val in x_values:
                    debugging_messages.append(res_parsed.content_string().replace('x','('+val+')'))
                    res_val = parse_expression(res_parsed.content_string().replace('x','('+val+')'), parsing_params).simplify()
                    ans_val = parse_expression(ans_parsed.content_string().replace('x','('+val+')'), parsing_params).simplify()
                    if bool((res_val - ans_val).simplify() != 0):
                        missed_points.append((val,str(ans_val)))
            else:
                raise Exception("Missing values for x.")
            if len(missed_points) > 0:
                eval_response.is_correct = False
                eval_response.add_feedback(("WRONG_POLYNOMIAL","The polynomial given in the response does not pass through the following points: "+", ".join([str(p) for p in missed_points])))
                return eval_response.serialise(include_test_data)
        except Exception as e:
            raise Exception("Error on line: "+str(sys.exc_info()[-1].tb_lineno)+" : "+" ".join(debugging_messages)) from e

    return eval_response.serialise(include_test_data)

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
    significant_characters = string[0:index].replace(".","")
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