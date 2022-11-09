from sympy.parsing.sympy_parser import parse_expr, split_symbols_custom
from sympy.parsing.sympy_parser import T as parser_transformations
from sympy import simplify, latex, Matrix, Symbol

try:
    from .static_unit_conversion_arrays import unit_dictionary, names_of_prefixes_units_and_dimensions
    from .expression_utilities import preprocess_expression, parse_expression, create_sympy_parsing_params, substitute
    from .symbolic_equal import evaluation_function as symbolic_equal
    from .strict_si_syntax import strict_SI_parsing
except ImportError:
    from static_unit_conversion_arrays import unit_dictionary, names_of_prefixes_units_and_dimensions
    from expression_utilities import preprocess_expression, parse_expression, create_sympy_parsing_params, substitute
    from symbolic_equal import evaluation_function as symbolic_equal
    from strict_si_syntax import strict_SI_parsing

parse_error_warning = lambda x: f"`{x}` could not be parsed as a valid mathematical expression. Ensure that correct notation is used, that the expression is unambiguous and that all parentheses are closed."

def evaluation_function(response, answer, params) -> dict:
    """
    Function that provides some basic dimensional analysis functionality.
    """
    default_rtol = 1e-12
    if "substitutions" in params.keys():
        unsplittable_symbols = tuple()
    else:
        unsplittable_symbols = names_of_prefixes_units_and_dimensions

    parameters = {"comparison": "expression", "strict_syntax": True}
    parameters.update(params)

    answer, response = preprocess_expression([answer, response],parameters)
    parsing_params = create_sympy_parsing_params(parameters, unsplittable_symbols=unsplittable_symbols)

    if params.get("strict_SI_syntax",False):
        ans_parsed = strict_SI_parsing(answer)
        res_parsed = strict_SI_parsing(response)

        remark = "\n".join(res_parsed.messages)

        if ans_parsed.passed("NUMBER_VALUE"):
            rtol = parameters.get("rtol",compute_relative_tolerance_from_significant_decimals(ans_parsed.value()))

        expression = ""
        if res_parsed.passed("HAS_VALUE"):
            expression += "("+res_parsed.value()+")"
        if res_parsed.passed("HAS_UNIT"):
            joiner = "*" if len(expression) > 0 else ""
            expression += joiner+"("+res_parsed.unit()+")"
        try:
            res = parse_expression(expression,parsing_params)
        except Exception as e:
            separator = "" if len(remark) == 0 else "\n"
            return {"is_correct": False, "feedback": parse_error_warning(response)+separator+remark}

        expression = ""
        if ans_parsed.passed("HAS_VALUE"):
            expression += "("+ans_parsed.value()+")"
        if ans_parsed.passed("HAS_UNIT"):
            joiner = "*" if len(expression) > 0 else ""
            expression += joiner+"("+ans_parsed.unit()+")"
        try:
            ans = parse_expression(expression,parsing_params)
        except Exception as e:
            raise Exception(f"SymPy was unable to parse the answer {answer}") from e

        interp = {"response_latex": res_parsed.print_latex()}

        result = {"is_correct": False}

        equal_up_to_multiplication = bool(simplify(res/ans).is_constant() and res != 0)
        error_below_atol = False
        error_below_rtol = False
        if equal_up_to_multiplication:
            if ans.free_symbols == res.free_symbols:
                for symbol in ans.free_symbols:
                    ans = ans.subs(symbol,1)
                    res = res.subs(symbol,1)
            if "atol" in parameters.keys():
                error_below_atol = bool(abs(float(ans-res)) < float(parameters["atol"]))
            else:
                error_below_atol = True
            if "rtol" in parameters.keys():
                rtol = float(parameters["rtol"])
                error_below_rtol = bool(float(abs(((ans-res)/ans).simplify())) < rtol)
            else:
                if "atol" in parameters.keys():
                    error_below_rtol = True
                else:
                    error_below_rtol = bool(float(abs(((ans-res)/ans).simplify())) < default_rtol)
        if error_below_atol and error_below_rtol:
            result["is_correct"] = True

    tested_criteria = ["FULL_QUANTITY","NO_UNIT","ONLY_UNIT","NUMBER_VALUE","EXPR_VALUE"]
    feedback = []
    for criterion in tested_criteria:
        if res_parsed.passed(criterion):
            feedback += [res_parsed.feedback(criterion)]

    feedback = {"feedback": "\n".join(feedback+[remark])}

    return {**result, **interp, **feedback}

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
    rtol = 0.5*10**(-len(significant_characters))
    return rtol