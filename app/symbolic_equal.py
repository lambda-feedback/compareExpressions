from sympy.parsing.sympy_parser import T as parser_transformations
from sympy.parsing.sympy_parser import parse_expr, split_symbols_custom
from sympy import Equality, simplify, latex, pi, Symbol


from .expression_utilities import (
    substitute_input_symbols,
    parse_expression,
    create_sympy_parsing_params,
    substitute,
    create_expression_set,
    convert_absolute_notation
)
from .evaluation_response_utilities import EvaluationResponse
from .feedback.symbolic_comparison import internal as symbolic_comparison_internal_messages

def evaluation_function(response, answer, params, eval_response = EvaluationResponse()) -> dict:

    """
    Function used to symbolically compare two expressions.
    """

    # This code handles the plus_minus and minus_plus operators
    # actual symbolic comparison is done in check_equality
    if "multiple_answers_criteria" not in params.keys():
        params.update({"multiple_answers_criteria": "all"})

    response_list = create_expression_set(response, params)
    answer_list = create_expression_set(answer, params)

    if len(response_list) == 1 and len(answer_list) == 1:
        return check_equality(response, answer, params, eval_response)
    else:
        matches = { "responses": [False]*len(response_list), "answers": [False]*len(answer_list)}
        interp = []
        for i, response in enumerate(response_list):
            result = None
            for j, answer in enumerate(answer_list):
                result = check_equality(response, answer, params, eval_response)
                if result["is_correct"]:
                    matches["responses"][i] = True
                    matches["answers"][j] = True
            if len(interp) == 0:
                interp = result["response_latex"]
            else:
                interp += result["response_latex"]
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

def find_matching_parenthesis(string,index):
    depth = 0
    for k in range(index,len(string)):
        if string[k] == '(':
            depth += 1
            continue
        if string[k] == ')':
            depth += -1
            if depth == 0:
                return k
    return -1

def check_equality(response, answer, params, eval_response) -> dict:

    if not isinstance(answer,str):
        raise Exception("No answer was given.")
    if not isinstance(response,str):
        eval_response.is_correct = False
        eval_response.add_feedback(("NO_RESPONSE",symbolic_comparison_internal_messages["NO_RESPONSE"]))
        return eval_response

    answer = answer.strip()
    response = response.strip()
    if len(answer) == 0:
        raise Exception("No answer was given.")
    if len(response) == 0:
        eval_response.is_correct = False
        eval_response.add_feedback(("NO_RESPONSE",symbolic_comparison_internal_messages["NO_RESPONSE"]))
        return eval_response

    answer, response = substitute_input_symbols([answer, response],params)
    parsing_params = create_sympy_parsing_params(params)
    parsing_params.update({"rationalise": True, "simplify": True})
    parsing_params["extra_transformations"] = parser_transformations[9] # Add conversion of equal signs

    # Converting absolute value notation to a form that SymPy accepts
    response, response_feedback = convert_absolute_notation(response, "response")
    if response_feedback is not None:
        eval_response.add_feedback(response_feedback)
    answer, answer_feedback = convert_absolute_notation(answer, "answer")
    if answer_feedback is not None:
        raise SyntaxWarning(answer_feedback[1],answer_feedback[0])

    if params.get("strict_syntax",True):
        if "^" in response:
            eval_response.add_feedback(("NOTATION_WARNING",symbolic_comparison_internal_messages["NOTATION_WARNING"]))

    # Safely try to parse answer and response into symbolic expressions
    try:
        res = parse_expression(response, parsing_params)
    except Exception as e:
        eval_response.is_correct = False
        eval_response.add_feedback(("PARSE_ERROR",symbolic_comparison_internal_messages["PARSE_ERROR"](response)))
        return eval_response

    try:
        ans = parse_expression(answer, parsing_params)
    except Exception as e:
        raise Exception("SymPy was unable to parse the answer.") from e

    # Add how res was interpreted to the response
    eval_response.latex = latex(res)
    eval_response.simplified = str(res)

    if (not isinstance(res,Equality)) and isinstance(ans,Equality):
        eval_response.is_correct = False
        tag = "EXPRESSION_NOT_EQUALITY"
        eval_response.add_feedback((tag,symbolic_comparison_internal_messages[tag]))
        return eval_response

    if isinstance(res,Equality) and (not isinstance(ans,Equality)):
        eval_response.is_correct = False
        tag = "EQUALITY_NOT_EXPRESSION"
        eval_response.add_feedback((tag,symbolic_comparison_internal_messages[tag]))
        return eval_response

    # TODO: Remove when criteria for checking proportionality is implemented
    if isinstance(res,Equality) and isinstance(ans,Equality):
        eval_response.is_correct = ((res.args[0]-res.args[1])/(ans.args[0]-ans.args[1])).simplify().is_constant()
        return eval_response

    error_below_atol = False
    error_below_rtol = False

    if params.get("numerical",False) or params.get("rtol",False) or params.get("atol",False):
        # REMARK: 'pi' should be a reserve symbols but is sometimes not treated as one, possibly because of input symbols
        # The two lines below this comments fixes the issue but a more robust solution should be found for cases where there
        # are other reserved symbols.
        ans = ans.subs(Symbol('pi'),float(pi))
        res = res.subs(Symbol('pi'),float(pi))
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
            eval_response.add_feedback((tag,symbolic_comparison_internal_messages[tag]))
            return eval_response

    is_correct = bool((res - ans).simplify() == 0)
    eval_response.is_correct = is_correct
    return eval_response