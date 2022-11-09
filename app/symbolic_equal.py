from sympy.parsing.sympy_parser import T as parser_transformations
from sympy.parsing.sympy_parser import parse_expr, split_symbols_custom
from sympy import Equality

try:
    from .expression_utilities import preprocess_expression, parse_expression, create_sympy_parsing_params, substitute
except ImportError:
    from expression_utilities import preprocess_expression, parse_expression, create_sympy_parsing_params, substitute

parse_error_warning = lambda x: f"`{x}` could not be parsed as a valid mathematical expression. Ensure that correct codes for input symbols are used, correct notation is used, that the expression is unambiguous and that all parentheses are closed."

def evaluation_function(response, answer, params) -> dict:

    """
    Function used to symbolically compare two expressions.
    """

    # This code handles the plus_minus and minus_plus operators
    # actual symbolic comparison is done in check_equality
    if "multiple_answers_criteria" not in params.keys():
        params.update({"multiple_answers_criteria": "all"})

    if "plus_minus" in params.keys():
        answer = answer.replace(params["plus_minus"],"plus_minus")
        response = response.replace(params["plus_minus"],"plus_minus")

    if "minus_plus" in params.keys():
        answer = answer.replace(params["minus_plus"],"minus_plus")
        response = response.replace(params["minus_plus"],"minus_plus")

    if ("plus_minus" not in response+answer) and ("minus_plus" not in response+answer):
        return check_equality(response, answer, params)
    else:
        response_set = set()
        if ("plus_minus" in response) or ("minus_plus" in response):
            response_set.add(response.replace("plus_minus","+").replace("minus_plus","-"))
            response_set.add(response.replace("plus_minus","-").replace("minus_plus","+"))
        else:
            response_set.add(response)
        response_list = list(response_set)
        answer_set = set()
        if ("plus_minus" in answer) or ("minus_plus" in answer):
            answer_set.add(answer.replace("plus_minus","+").replace("minus_plus","-"))
            answer_set.add(answer.replace("plus_minus","-").replace("minus_plus","+"))
        else:
            answer_set.add(answer)
        answer_list = list(answer_set)
        matches = { "responses": [False]*len(response_list), "answers": [False]*len(answer_list)}
        interp = ""
        for i, response in enumerate(response_list):
            result = None
            for j, answer in enumerate(answer_list):
                result = check_equality(response, answer, params)
                if result["is_correct"]:
                    matches["responses"][i] = True
                    matches["answers"][j] = True
            if interp == "":
                interp = result["response_latex"]
            else:
                interp += ", "+result["response_latex"]
        if params["multiple_answers_criteria"] == "all":
            is_correct = all(matches["responses"]) and all(matches["answers"])
        elif params["multiple_answers_criteria"] == "all_responses":
            is_correct = all(matches["responses"])
        elif params["multiple_answers_criteria"] == "all_answers":
            is_correct = all(matches["answers"])
        else:
            raise SyntaxWarning(f"Unknown multiple_answers_criteria: {params['multiple_answers_critera']}")
        return {"is_correct": is_correct, "response_latex": interp}

def RecpTrig(expr):
    """
    Reciprocal Trig Functions -> Turn sec, csc, cot into sin form
    
    Parameters
    ----------
    expr : SymPy expression, might have sec, csc, cot

    Returns
    -------
    expr : Updated expression

    Tests
    -----
    Checks if '1+tan(x)**2 + y = sec(x)**2 + y', as this solves the issue
    with sec(x)
    """
    from sympy import sec, csc, cot, sin
    if expr.has(sec) or expr.has(csc) or expr.has(cot):
        expr = expr.rewrite(sin)
    return expr


def Decimals(expr):
    """
    Decimals -> Turn into rational form
    Otherwise x/2 not seen as equal to x*0.5
    
    Parameters
    ----------
    expr : Input expression, might have decimals

    Returns
    -------
    expr : Updated expression
    
    Tests
    -----
    Checks if x*0.5 = x/2
    """
    from sympy import nsimplify
    expr = nsimplify(expr)
    return expr


def Absolute(res, ans):
    """
    Accept || as another form of writing modulus of an expression. 
    Function makes the input parseable by SymPy, SymPy only accepts Abs()
    REMARK: this function cannot handle nested || and will raise a 
    SyntaxWarning if more than two | are present in the answer or the 
    response

    Parameters
    ----------
    res : string
        Reponse Input from Teacher, might have ||
    ans : string
        Answer Input from Student, might have ||

    Returns
    -------
    res : string
        Updated response input
    ans : string
        Updated answer input
        
    Tests
    -----
    Checks if Abs(x)+y = |x|+y
    Checks if giving |x+|y|| sends back a warning in the feedback
    Checks if giving |x|+|y| as answer raises an Exception

    """

    # positions of the || values
    n_res = res.count('|')
    if n_res == 2:
        res = list(res)
        res[res.index("|")] = "Abs("
        res[res.index("|")] = ")"
        res = "".join(res)
    elif n_res > 0:
        res_start_abs_pos = []
        res_end_abs_pos = []
        res_ambiguous_abs_pos = []
        
        if res[0] == "|":
            res_start_abs_pos.append(0)
        for i in range(1,len(res)-1):
            if res[i] == "|":
                if (res[i-1].isalnum() or res[i-1] in "()[]{}") and not (res[i+1].isalnum() or res[i+1] in "()[]{}"):
                    res_end_abs_pos.append(i)
                elif (res[i+1].isalnum() or res[i+1] in "()[]{}") and not (res[i-1].isalnum() or res[i-1] in "()[]{}"):
                    res_start_abs_pos.append(i)
                else:
                    res_ambiguous_abs_pos.append(i)
        if res[-1] == "|":
            res_end_abs_pos.append(len(res)-1)
        res = list(res)
        for i in res_start_abs_pos:
            res[i] = "Abs("
        for i in res_end_abs_pos:
            res[i] = ")"
        k = 0
        prev_ambiguous = -1
        for i in res_ambiguous_abs_pos:
            prev_start = -1
            for j in res_start_abs_pos:
                if j < i:
                    prev_start = j
                else:
                    break
            prev_end = -1
            for j in res_end_abs_pos:
                if j < i:
                    prev_end = j
                else:
                    break
            if max(prev_start,prev_end,prev_ambiguous) == prev_end:
                if res[i-1].isalnum():
                    res[i] = "*Abs("
                else:
                    res[i] = "Abs("
            elif max(prev_start,prev_end,prev_ambiguous) == prev_ambiguous:
                if k % 2 == 0:
                    if res[i-1].isalnum():
                        res[i] = "*Abs("
                    else:
                        res[i] = "Abs("
                else:
                    res[i] = ")"
                k += 1
            else:
                res[i] = ")"
            prev_ambiguous = i
        res = "".join(res)

    n_ans = ans.count('|')
    if n_ans == 2:
        ans = list(ans)
        ans[ans.index("|")] = "Abs("
        ans[ans.index("|")] = ")"
        ans = "".join(ans)
    elif n_ans > 0:
        ans_start_abs_pos = []
        ans_end_abs_pos = []
        ans_ambiguous_abs_pos = []
        
        if ans[0] == "|":
            ans_start_abs_pos.append(0)
        for i in range(1,len(ans)-1):
            if ans[i] == "|":
                if (ans[i-1].isalnum() or ans[i-1] in "()[]{}") and not (ans[i+1].isalnum() or ans[i+1] in "()[]{}"):
                    ans_end_abs_pos.append(i)
                elif (ans[i+1].isalnum() or ans[i+1] in "()[]{}") and not (ans[i-1].isalnum() or ans[i-1] in "()[]{}"):
                    ans_start_abs_pos.append(i)
                else:
                    ans_ambiguous_abs_pos.append(i)
        if ans[-1] == "|":
            ans_end_abs_pos.append(len(ans)-1)
        ans = list(ans)
        for i in ans_start_abs_pos:
            ans[i] = "Abs("
        for i in ans_end_abs_pos:
            ans[i] = ")"
        ans = "".join(ans)

    # Response
    ambiguity_warning_answer = "Notation in answer might be ambiguous, use Abs(.) instead of |.|"
    ambiguity_warning_response = "Notation in response might be ambiguous, use Abs(.) instead of |.|"

    remark = ""
    if n_ans > 2 and len(ans_ambiguous_abs_pos) > 0:
        raise SyntaxWarning(ambiguity_warning_answer,"ambiguityWith|")
    if n_res > 2 and len(res_ambiguous_abs_pos) > 0:
        remark = ambiguity_warning_response

    return res, ans, remark

def check_equality(response, answer, params) -> dict:

    from sympy import expand, simplify, trigsimp, radsimp, latex, Symbol
    from sympy import pi

    unsplittable_symbols = tuple()+(params.get("plus_minus","plus_minus"),params.get("minus_plus","minus_plus"))

    if not isinstance(answer,str):
        raise Exception("No answer was given.")
    if not isinstance(response,str):
        return {"is_correct": False, "feedback": "No response submitted."}

    answer = answer.strip()
    response = response.strip()
    if len(answer) == 0:
        raise Exception("No answer was given.")
    if len(response) == 0:
        return {"is_correct": False, "feedback": "No response submitted."}

    answer, response = preprocess_expression([answer, response],params)
    parsing_params = create_sympy_parsing_params(params, unsplittable_symbols=unsplittable_symbols)
    parsing_params["extra_transformations"] = parser_transformations[9] # Add conversion of equal signs

    if "symbol_assumptions" in params.keys():
        symbol_assumptions_strings = params["symbol_assumptions"]
        symbol_assumptions = []
        index = symbol_assumptions_strings.find("(")
        while index > -1:
            index_match = find_matching_parenthesis(symbol_assumptions_strings,index)
            try:
                symbol_assumption = eval(symbol_assumptions_strings[index+1:index_match])
                symbol_assumptions.append(symbol_assumption)
            except (SyntaxError, TypeError) as e:
                raise Exception("List of symbol assumptions not written correctly.")
            index = symbol_assumptions_strings.find('(',index_match+1)
        for sym, ass in symbol_assumptions:
            try:
                parsing_params["symbol_dict"].update({sym: eval("Symbol('"+sym+"',"+ass+"=True)")})
            except Exception as e:
               raise Exception(f"Assumption {ass} for symbol {sym} caused a problem.")


    # Dealing with special cases that aren't accepted by SymPy
    response, answer, remark = Absolute(response, answer)

    if params.get("strict_syntax",True):
        if "^" in response:
            separator = "" if len(remark) == 0 else "\n"
            remark += separator+"Note that `^` cannot be used to denote exponentiation, use `**` instead."

    # Safely try to parse answer and response into symbolic expressions
    try:
        res = parse_expression(response, parsing_params)
    except (SyntaxError, TypeError) as e:
        separator = "" if len(remark) == 0 else "\n"
        return {"is_correct": False, "feedback": parse_error_warning(response)+separator+remark}

    try:
        ans = parse_expression(answer, parsing_params)
    except (SyntaxError, TypeError) as e:
        raise Exception("SymPy was unable to parse the answer."+remark,) from e

    # Add how res was interpreted to the response
    interp = {"response_latex": latex(res)}

    feedback = {}

    separator = "" if len(remark) == 0 else "\n"

    if (not isinstance(res,Equality)) and isinstance(ans,Equality):
        return {
            "is_correct": False,
            "feedback": "The response was an expression but was expected to be an equality."+separator+remark,
            "response_simplified": str(ans),
            **interp
        }
        return

    if isinstance(res,Equality) and (not isinstance(ans,Equality)):
        return {
            "is_correct": False,
            "feedback": "The response was an equality but was expected to be an expression."+separator+remark,
            "response_simplified": str(ans),
            **interp
        }
        return

    if isinstance(res,Equality) and isinstance(ans,Equality):
        is_correct = ((res.args[0]-res.args[1])/(ans.args[0]-ans.args[1])).simplify().is_constant()
        if remark != "":
            feedback = {"feedback": remark}
        return {
            "is_correct": is_correct,
            "response_simplified": str(ans),
            **feedback,
            **interp
        }
        return

    # Dealing with special cases
    try:
        res = RecpTrig(res)
        res = Decimals(res)
    except Exception:
        separator = "" if len(remark) == 0 else "\n"
        return {"is_correct": False, "feedback": parse_error_warning(response)+separator+remark}

    try:
        ans = RecpTrig(ans)
        ans = Decimals(ans)
    except (SyntaxError, TypeError) as e:
        raise Exception("SymPy was unable to parse the answer.") from e


    error_below_atol = False
    error_below_rtol = False
    
    if res.is_constant() and ans.is_constant() and params.get("numerical",False): 

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
        return {
            "is_correct": True,
            "level": "0",
            "feedback": "The response is numerically equal to the answer."+separator+remark,
            **interp
            }

    # Going from the simplest to complex tranformations available in sympy, check equality
    # https://github.com/sympy/sympy/wiki/Faq#why-does-sympy-say-that-two-equal-expressions-are-unequal
    is_correct = bool(res.expand() == ans.expand())
    if is_correct:
        if remark != "":
            feedback = {"feedback": remark}
        return {
            "is_correct": True,
            "level": "1",
            "response_simplified": str(res.simplify()),
            **feedback,
            **interp
        }

    is_correct = bool(res.simplify() == ans.simplify())
    if is_correct:
        if remark != "":
            feedback = {"feedback": remark}
        return {
            "is_correct": True,
            "level": "2",
            "response_simplified": str(res.simplify()),
            **feedback,
            **interp
        }

    # Looks for trig identities
    is_correct = bool(res.trigsimp() == ans.trigsimp())
    if is_correct:
        if remark != "":
            feedback = {"feedback": remark}
        return {
            "is_correct": True,
            "level": "3",
            "response_simplified": str(res.simplify()),
            **feedback,
            **interp
        }

    # General catch-all if above does not work
    is_correct = bool((res.simplify() - ans.simplify()).simplify() == 0)
    if is_correct:
        if remark != "":
            feedback = {"feedback": remark}
        return {
            "is_correct": True,
            "level": "4",
            "response_simplified": str(res.simplify()),
            **feedback,
            **interp
        }

    if remark != "":
        feedback = {"feedback": remark}
    return {"is_correct": False, "response_simplified": str(res), **feedback, **interp}

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
