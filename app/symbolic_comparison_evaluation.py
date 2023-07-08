from sympy.parsing.sympy_parser import T as parser_transformations
from sympy import Equality, latex, pi, Symbol

from .expression_utilities import (
    substitute_input_symbols,
    parse_expression,
    create_sympy_parsing_params,
    create_expression_set,
    convert_absolute_notation
)

from .slr_parsing_utilities import SLR_Parser, catch_undefined, infix, create_node, operate, join

from .evaluation_response_utilities import EvaluationResponse
from .feedback.symbolic_comparison import internal as symbolic_comparison_internal_messages


criteria_operations = {
    "not": lambda x, p: not check_criterion(x[0], p),
}

def generate_criteria_parser():
    start_symbol = "START"
    end_symbol = "END"
    null_symbol = "NULL"

    token_list = [
        (start_symbol,   start_symbol),
        (end_symbol,     end_symbol),
        (null_symbol,    null_symbol),
        (" *BOOL *",     "BOOL"),
        (" *\* *",       "PRODUCT"),
        (" */ *",        "DIVISION"),
        (" *\+ *",       "PLUS"),
        (" *- *",        "MINUS"),
        ("\( *",         "START_DELIMITER"),
        (" *\)",         "END_DELIMITER"),
        (" *= *",        "EQUALITY"),
        ("response",     "EXPR"),
        ("answer",       "EXPR"),
        ("EXPR",         "EXPR", catch_undefined),
    ]
    token_list += [(" *"+x+" *", " "+x+" ") for x in criteria_operations.keys()]

    productions = [
        ("START",    "BOOL", create_node),
        ("BOOL",     "not(BOOL)", operate(1)),
        ("BOOL",     "EXPR=EXPR", infix),
        ("EXPR",     "-EXPR", join),
        ("EXPR",     "EXPR-EXPR", infix),
        ("EXPR",     "EXPR+EXPR", infix),
        ("EXPR",     "EXPR*EXPR", infix),
        ("EXPR",     "EXPR/EXPR", infix),
    ]

    return SLR_Parser(token_list, productions, start_symbol, end_symbol, null_symbol)

def check_criterion(criterion, parameters_dict):
    label = criterion.label.strip()
    parsing_params = parameters_dict["parsing_params"]
    reserved_expressions = parameters_dict["reserved_expressions"]
    if label == "EQUALITY":
        lhs = criterion.children[0].content_string()
        rhs = criterion.children[1].content_string()
        parsing_params = parameters_dict["parsing_params"]
        criterion_expression = (parse_expression(lhs, parsing_params)) - (parse_expression(rhs, parsing_params))
        result = bool(criterion_expression.subs(reserved_expressions).simplify() == 0)
    elif label in criteria_operations.keys():
        result = criteria_operations[label](criterion.children, parameters_dict)
    return result

def create_criteria_list(criteria_string, criteria_parser, parsing_params):
    criteria_string_list = [criterion.strip() for criterion in criteria_string.split(",")]
    criteria_tokens = []
    criteria_parsed = []
    for criterion in criteria_string_list:
        try:
            criterion_tokens = criteria_parser.scan(criterion)
            criteria_tokens.append(criterion_tokens)
            criteria_parsed.append(criteria_parser.parse(criterion_tokens)[0])
        except Exception as e:
            print(e)
            raise Exception("Cannot parse criteria: `"+criterion+"`.") from e
    return criteria_tokens, criteria_parsed

def evaluation_function(response, answer, params, include_test_data=False) -> dict:
    """
    Function used to symbolically compare two expressions.
    """

    eval_response = EvaluationResponse()
    eval_response.is_correct = False

    # This code handles the plus_minus and minus_plus operators
    # actual symbolic comparison is done in check_equality
    if "multiple_answers_criteria" not in params.keys():
        params.update({"multiple_answers_criteria": "all"})

    response_list = create_expression_set(response, params)
    answer_list = create_expression_set(answer, params)

    if len(response_list) == 1 and len(answer_list) == 1:
        eval_response = symbolic_comparison(response, answer, params, eval_response)
    else:
        matches = {"responses": [False]*len(response_list), "answers": [False]*len(answer_list)}
        interp = []
        for i, response in enumerate(response_list):
            result = None
            for j, answer in enumerate(answer_list):
                result = symbolic_comparison(response, answer, params, eval_response)
                if result["is_correct"]:
                    matches["responses"][i] = True
                    matches["answers"][j] = True
            if len(interp) == 0:
                interp = result["response_latex"]
                interp_sympy = result["response_simplified"]
            else:
                interp += result["response_latex"]
                interp_sympy += ", " + result["response_simplified"]
        if params["multiple_answers_criteria"] == "all":
            is_correct = all(matches["responses"]) and all(matches["answers"])
            if is_correct is False:
                eval_response.add_feedback(symbolic_comparison_internal_messages["MULTIPLE_ANSWER_FAIL_ALL"])
        elif params["multiple_answers_criteria"] == "all_responses":
            is_correct = all(matches["responses"])
            if is_correct is False:
                eval_response.add_feedback(symbolic_comparison_internal_messages["MULTIPLE_ANSWER_FAIL_RESPONSE"])
        elif params["multiple_answers_criteria"] == "all_answers":
            is_correct = all(matches["answers"])
            if is_correct is False:
                eval_response.add_feedback(symbolic_comparison_internal_messages["MULTIPLE_ANSWER_FAIL_ANSWERS"])
        else:
            raise SyntaxWarning(f"Unknown multiple_answers_criteria: {params['multiple_answers_critera']}")
        eval_response.is_correct = is_correct
        if len(interp) > 1:
            response_latex = "\\left\\{"+",".join(interp)+"\\right\\}"
        else:
            response_latex = interp
        eval_response.latex = response_latex

    return eval_response


def symbolic_comparison(response, answer, params, eval_response) -> dict:

    if not isinstance(answer, str):
        raise Exception("No answer was given.")
    if not isinstance(response, str):
        eval_response.is_correct = False
        eval_response.add_feedback(("NO_RESPONSE", symbolic_comparison_internal_messages["NO_RESPONSE"]))
        return eval_response

    answer = answer.strip()
    response = response.strip()
    if len(answer) == 0:
        raise Exception("No answer was given.")
    if len(response) == 0:
        eval_response.is_correct = False
        eval_response.add_feedback(("NO_RESPONSE", symbolic_comparison_internal_messages["NO_RESPONSE"]))
        return eval_response

    answer, response = substitute_input_symbols([answer, response], params)
    parsing_params = create_sympy_parsing_params(params)
    parsing_params.update({"rationalise": True, "simplify": True})
    parsing_params["extra_transformations"] = parser_transformations[9]  # Add conversion of equal signs

    # Converting absolute value notation to a form that SymPy accepts
    response, response_feedback = convert_absolute_notation(response, "response")
    if response_feedback is not None:
        eval_response.add_feedback(response_feedback)
    answer, answer_feedback = convert_absolute_notation(answer, "answer")
    if answer_feedback is not None:
        raise SyntaxWarning(answer_feedback[1], answer_feedback[0])

    if params.get("strict_syntax", True):
        if "^" in response:
            eval_response.add_feedback(("NOTATION_WARNING", symbolic_comparison_internal_messages["NOTATION_WARNING"]))

    # Safely try to parse answer and response into symbolic expressions
    try:
        res = parse_expression(response, parsing_params)
    except Exception as e:
        eval_response.is_correct = False
        eval_response.add_feedback(("PARSE_ERROR", symbolic_comparison_internal_messages["PARSE_ERROR"](response)))
        return eval_response

    try:
        ans = parse_expression(answer, parsing_params)
    except Exception as e:
        raise Exception("SymPy was unable to parse the answer.") from e

    criteria_parser = generate_criteria_parser()
    parsing_params["unsplittable_symbols"] += ("response","answer")
    reserved_expressions = [("response", res), ("answer", ans)]
    criteria_tokens, criteria_parsed = create_criteria_list(params.get("criteria","answer=response"), criteria_parser, parsing_params)

    # Add how res was interpreted to the response
    eval_response.latex = latex(res)
    eval_response.simplified = str(res)

    if (not isinstance(res, Equality)) and isinstance(ans, Equality):
        eval_response.is_correct = False
        tag = "EXPRESSION_NOT_EQUALITY"
        eval_response.add_feedback((tag, symbolic_comparison_internal_messages[tag]))
        return eval_response

    if isinstance(res, Equality) and (not isinstance(ans, Equality)):
        eval_response.is_correct = False
        tag = "EQUALITY_NOT_EXPRESSION"
        eval_response.add_feedback((tag, symbolic_comparison_internal_messages[tag]))
        return eval_response

    # TODO: Remove when criteria for checking proportionality is implemented
    if isinstance(res, Equality) and isinstance(ans, Equality):
        eval_response.is_correct = ((res.args[0]-res.args[1])/(ans.args[0]-ans.args[1])).simplify().is_constant()
        return eval_response

    error_below_atol = False
    error_below_rtol = False

    if params.get("numerical", False) or params.get("rtol", False) or params.get("atol", False):
        # REMARK: 'pi' should be a reserved symbol but it is sometimes not treated as one, possibly because of input symbols.
        # The two lines below this comments fixes the issue but a more robust solution should be found for cases where there
        # are other reserved symbols.
        ans = ans.subs(Symbol('pi'), float(pi))
        res = res.subs(Symbol('pi'), float(pi))
        if res.is_constant() and ans.is_constant():
            if "atol" in params.keys():
                error_below_atol = bool(abs(float(ans-res)) < float(params["atol"]))
            else:
                error_below_atol = True
            if "rtol" in params.keys():
                rtol = float(params["rtol"])
                error_below_rtol = bool(float(abs(((ans-res)/ans).simplify())) < rtol)
            else:
                error_below_rtol = True
        if error_below_atol and error_below_rtol:
            eval_response.is_correct = True
            tag = "WITHIN_TOLERANCE"
            eval_response.add_feedback((tag, symbolic_comparison_internal_messages[tag]))
            return eval_response

    #is_correct = bool((res - ans).simplify() == 0)
    is_correct = True
    parameters_dict = {
        "parsing_params": parsing_params,
        "reserved_expressions": reserved_expressions,
    }
    for criterion in criteria_parsed:
        is_correct = is_correct and check_criterion(criterion, parameters_dict)
    eval_response.is_correct = is_correct
    return eval_response
