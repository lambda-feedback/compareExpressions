

def parse_error_warning(x):
    return f"`{x}` could not be parsed as a valid mathematical expression. Ensure that correct notation is used, that the expression is unambiguous and that all parentheses are closed."

def evaluation_function(response, answer, params, include_test_data = False) -> dict:
    try:

        # Added this to make it possible to run both the file directly both from the main directory and from the app directory
        import sys
        sys.path.append(".")
        
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
        #from strict_si_syntax import strict_SI_parsing
        from slr_strict_si_syntax import SLR_strict_SI_parsing as strict_SI_parsing
        from slr_strict_si_syntax import criteria as strict_SI_criteria

        """
        Function that allows for various types of comparison of various kinds of expressions.
        Supported input parameters:
        strict_SI_syntax:
            - if set to True, use a function dimensional analysis functionality.
        """
        eval_response = EvaluationResponse()
    
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
    
        if params.get(
            "strict_SI_syntax", False
        ):  # NOTE: this is the only mode that is supported right now
            # The expected forms of the response are:
            #       NUMBER UNIT_EXPRESSION
            #       MATHEMATICAL_EXPRESSION UNIT_EXPRESSION
            # strict_SI_parsing returns a Quantity object.
            # For this file the relevant content of the quantity object is the messages and the passed criteria.
            ans_parsed, ans_latex = strict_SI_parsing(answer)
            res_parsed, res_latex = strict_SI_parsing(response)
    
            # Collects messages from parsing the response, these needs to be returned as feedback later
            eval_response.add_feedback("\n".join([x[1] for x in res_parsed.messages]))
    
            # Computes the desired tolerance used for numerical computations based on the formatting of the answer
            if ans_parsed.passed("NUMBER_VALUE"):
                rtol = parameters.get(
                    "rtol",
                    compute_relative_tolerance_from_significant_decimals(
                        ans_parsed.value.content_string()
                    ),
                )
    
            # Convert answer to standard units
            ans_converted_value = None
            ans_converted_unit = None
            if ans_parsed.passed("HAS_UNIT"):
                ans_converted_unit = ans_parsed.unit.content_string()
                substitutions = list(conversion_to_base_si_units_dictionary.values())
                ans_symbolic_unit = substitute(ans_converted_unit,substitutions)
                try:
                    ans_converted_unit = parse_expression(ans_converted_unit, parsing_params)
                    ans_converted_unit_factor = ans_converted_unit.subs({name: 1 for name in [x[0] for x in list_of_SI_base_unit_dimensions]}).simplify()
                    ans_converted_unit = (ans_converted_unit/ans_converted_unit_factor).simplify()
                except Exception as e:
                    raise Exception("SymPy was unable to parse the answer unit") from e
            if ans_parsed.passed("HAS_VALUE"):
                ans_converted_value = ans_parsed.value.content_string()
            if ans_parsed.passed("FULL_QUANTITY"):
                ans_converted_value = "("+ans_converted_value+")*("+str(ans_converted_unit_factor)+")"
    
            # Convert response to standard units
            res_converted_value = None
            res_converted_unit = None
            if res_parsed.passed("HAS_UNIT"):
                res_converted_unit = res_parsed.unit.content_string()
                substitutions = list(conversion_to_base_si_units_dictionary.values())
                res_symbolic_unit = substitute(res_converted_unit,substitutions)
                try:
                    res_converted_unit = parse_expression(res_converted_unit, parsing_params)
                    res_converted_unit_factor = ans_converted_unit.subs({name: 1 for name in [x[0] for x in list_of_SI_base_unit_dimensions]}).simplify()
                    res_converted_unit = (res_converted_unit/res_converted_unit_factor).simplify()
                except Exception as e:
                    raise Exception("SymPy was unable to parse the response unit") from e
            if res_parsed.passed("HAS_VALUE"):
                res_converted_value = res_parsed.value.content_string()
            if res_parsed.passed("FULL_QUANTITY"):
                res_converted_value = "("+res_converted_value+")*("+str(res_converted_unit_factor)+")"
    
            response_latex = []
    
            if res_parsed.passed("HAS_VALUE"):
                #TODO redesign symbolicEqual so that it can easily return latex version of input
                value_comparison_response = symbolicEqual(res_converted_value,"0",params)
                #TODO Update symbolicEqual to use new evaluationResponse system
                #response_latex += [value_comparison_response.response_latex]
                response_latex += value_comparison_response.get("response_latex","")
            if res_latex != None and len(res_latex) > 0:
                response_latex += [res_latex]
            eval_response.response_latex = " ".join(response_latex)
    
            # Compare answer and response value
            if ans_parsed.passed("HAS_VALUE") and res_parsed.passed("HAS_VALUE"):
                value_comparison_response = symbolicEqual(res_converted_value,ans_converted_value,params)
                eval_response.is_correct = eval_response.is_correct and value_comparison_response.is_correct
                #TODO Update symbolicEqual to use new evaluationResponse system
                #response_latex += [value_comparison_response.response_latex]
                response_latex += value_comparison_response.get("response_latex","")
            elif ans_parsed.passed("HAS_VALUE") and not res_parsed.passed("HAS_VALUE"):
                eval_response.add_feedback(("MISSING_VALUE","The response is missing a value."))
                eval_response.is_correct = False
            elif not ans_parsed.passed("HAS_VALUE") and res_parsed.passed("HAS_VALUE"):
                eval_response.add_feedback(("UNEXPECTED_VALUE","The response is expected only have unit(s), no value."))
                eval_response.is_correct = False
    
            # Compare answer and response unit
            if ans_parsed.passed("HAS_UNIT") and res_parsed.passed("HAS_UNIT"):
                is_correct = bool((res_converted_unit - ans_converted_unit).simplify() == 0)
                eval_response.is_correct = eval_response.is_correct and is_correct
            elif ans_parsed.passed("HAS_UNIT") and not res_parsed.passed("HAS_UNIT"):
                eval_response.add_feedback(("MISSING_VALUE","The response is missing unit(s)."))
                eval_response.is_correct = False
            elif not ans_parsed.passed("HAS_UNIT") and res_parsed.passed("HAS_UNIT"):
                eval_response.add_feedback(("UNEXPECTED_UNIT","The response is expected only have unit(s), no value."))
                eval_response.is_correct = False
    
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
    
        eval_response.latex = res_latex
        return eval_response.serialise(include_test_data)
    except Exception() as e:
        return {"is_correct": False, "feedback": str(e)}

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
    rtol = 0.5 * 10 ** (-len(significant_characters))
    return rtol

    return