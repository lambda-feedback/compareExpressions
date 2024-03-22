from sympy.parsing.sympy_parser import T as parser_transformations
from sympy import Abs, Equality, latex, pi, Symbol
from sympy.printing.latex import LatexPrinter

from .expression_utilities import (
    substitute_input_symbols,
    parse_expression,
    create_sympy_parsing_params,
    create_expression_set,
    convert_absolute_notation,
    latex_symbols,
)

from .slr_parsing_utilities import SLR_Parser, catch_undefined, infix, create_node, operate, join, group, proceed, append_last

from .evaluation_response_utilities import EvaluationResponse
from .feedback.symbolic_comparison import internal as symbolic_comparison_internal_messages
from .feedback.symbolic_comparison import criteria as symbolic_comparison_criteria
from .feedback.symbolic_comparison import equivalences as reference_criteria_strings

from .criteria_graph_utilities import CriteriaGraph

criteria_operations = {
    "not": lambda x, p: not check_criterion(x[0], p, generate_feedback=False),
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
        (" *= *",        "EQUALITY"),
        ("\( *",         "START_DELIMITER"),
        (" *\)",         "END_DELIMITER"),
        (" *; *",        "SEPARATOR"),
        ("response",     "EXPR"),
        (" *where *",    "WHERE"),
        ("answer",       "EXPR"),
        ("EQUAL",        "EQUAL"),
        ("EQUALS",       "EQUALS"),
        ("EXPR",         "EXPR", catch_undefined),
    ]
    token_list += [(" *"+x+" *", " "+x+" ") for x in criteria_operations.keys()]

    productions = [
        ("START", "BOOL", create_node),
        ("BOOL",  "not(BOOL)", operate(1)),
        ("BOOL",  "EQUAL", proceed),
        ("EQUAL",  "EQUAL where EQUAL", infix),
        ("EQUAL",  "EQUAL where EQUALS", infix),
        ("EQUALS", "EQUAL;EQUAL", infix),
        ("EQUALS", "EQUALS;EQUAL", append_last),
        ("EQUAL", "EXPR=EXPR", infix),
        ("EXPR",  "-EXPR", join),
        ("EXPR",  "EXPR-EXPR", infix),
        ("EXPR",  "EXPR+EXPR", infix),
        ("EXPR",  "EXPR*EXPR", infix),
        ("EXPR",  "EXPREXPR", join),
        ("EXPR",  "EXPR/EXPR", infix),
        ("EXPR",  "(EXPR)", join),
    ]

    return SLR_Parser(token_list, productions, start_symbol, end_symbol, null_symbol)

def check_criterion(criterion, parameters_dict, generate_feedback=True):
    label = criterion.label.strip()
    parsing_params = parameters_dict["parsing_params"]
    reserved_expressions = parameters_dict["reserved_expressions"]
    local_substitutions = parameters_dict.get("local_substitutions",[])
    reference_criteria_strings = parameters_dict["reference_criteria_strings"]
    eval_response = parameters_dict["eval_response"]
    parsing_params = {key: value for (key,value) in parameters_dict["parsing_params"].items()}
    parsing_params.update({"simplify": False})
    symbolic_comparison_criteria = parameters_dict["symbolic_comparison_criteria"]
    if label == "EQUALITY":
        lhs = criterion.children[0].content_string()
        rhs = criterion.children[1].content_string()
        criterion_expression = (parse_expression(lhs, parsing_params)) - (parse_expression(rhs, parsing_params))
        result = bool(criterion_expression.subs(reserved_expressions).subs(local_substitutions).cancel().simplify().simplify() == 0)
        for (reference_tag, reference_strings) in reference_criteria_strings.items():
            if reference_tag in eval_response.get_tags():
                continue
            if "".join(str(criterion_expression).split()) in reference_strings and generate_feedback is True:
                feedback = symbolic_comparison_criteria[reference_tag].feedback[result]([])
                eval_response.add_feedback((reference_tag, feedback))
                break
    elif label == "WHERE":
        crit = criterion.children[0]
        subs = criterion.children[1]
        local_subs = []
        if subs.label == "EQUALITY":
            subs = [subs]
        elif subs.label == "SEPARATOR":
            subs = subs.children
        for sub in subs:
            name = sub.children[0].content_string()
            expr = parse_expression(sub.children[1].content_string(), parsing_params)
            local_subs.append((name, expr))
        result = check_criterion(crit, {**parameters_dict, **{"local_substitutions": local_subs}}, generate_feedback)
    elif label in criteria_operations.keys():
        result = criteria_operations[label](criterion.children, parameters_dict)
    return result

def criterion_eval_node(criterion, parameters_dict, generate_feedback=True):
    def evaluation_node_internal(response):
        result = check_criterion(criterion, parameters_dict, generate_feedback)
        label = criterion.content_string()
        if result:
            return {label+"_TRUE"}
        else:
            return {label+"_FALSE"}
    label = criterion.content_string()
    graph = CriteriaGraph(label)
    END = CriteriaGraph.END
    graph.add_node(END)
    graph.add_evaluation_node(label, summary=label, details="Checks if "+label+" is true.", evaluate=evaluation_node_internal)
    graph.attach(label, label+"_TRUE", summary="True", details=label+" is true.")
    graph.attach(label+"_TRUE", END.label)
    graph.attach(label, label+"_FALSE", summary="True", details=label+" is false.")
    graph.attach(label+"_FALSE", END.label)
    return graph

def create_criteria_list(criteria_string, criteria_parser, parsing_params):
    criteria_string_list = []
    delims = [
        ("(", ")"),
        ("[", "]"),
        ("{", "}"),
    ]
    depth = {delim: 0 for delim in delims}
    delim_key = {delim[0]: delim for delim in delims}
    delim_key.update({delim[1]: delim for delim in delims})
    criterion_start = 0
    for n, c in enumerate(criteria_string):
        if c in [delim[0] for delim in delims]:
            depth[delim_key[c]] += 1
        if c in [delim[1] for delim in delims]:
            depth[delim_key[c]] -= 1
        if c == "," and all([d == 0 for d in depth.values()]):
            criteria_string_list.append(criteria_string[criterion_start:n].strip())
            criterion_start = n+1
    criteria_string_list.append(criteria_string[criterion_start:].strip())
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
    return criteria_parsed

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
                eval_response.add_feedback(("MULTIPLE_ANSWER_FAIL_ALL",symbolic_comparison_internal_messages["MULTIPLE_ANSWER_FAIL_ALL"]))
        elif params["multiple_answers_criteria"] == "all_responses":
            is_correct = all(matches["responses"])
            if is_correct is False:
                eval_response.add_feedback(("MULTIPLE_ANSWER_FAIL_RESPONSE",symbolic_comparison_internal_messages["MULTIPLE_ANSWER_FAIL_RESPONSE"]))
        elif params["multiple_answers_criteria"] == "all_answers":
            is_correct = all(matches["answers"])
            if is_correct is False:
                eval_response.add_feedback(("MULTIPLE_ANSWER_FAIL_RESPONSE",symbolic_comparison_internal_messages["MULTIPLE_ANSWER_FAIL_ANSWERS"]))
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
            eval_response.add_feedback(("NOTATION_WARNING_EXPONENT", symbolic_comparison_internal_messages["NOTATION_WARNING_EXPONENT"]))
        if "!" in response:
            eval_response.add_feedback(("NOTATION_WARNING_FACTORIAL", symbolic_comparison_internal_messages["NOTATION_WARNING_FACTORIAL"]))

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
        raise Exception(f"SymPy was unable to parse the answer: {answer}.") from e

    criteria_parser = generate_criteria_parser()
    parsing_params["unsplittable_symbols"] += ("response", "answer", "where")
    reserved_expressions = [("response", res), ("answer", ans)]
    criteria_string = substitute_input_symbols(params.get("criteria", "answer=response"), params)[0]
    criteria_parsed = create_criteria_list(criteria_string, criteria_parser, parsing_params)

    # Add how res was interpreted to the response
    # eval_response.latex = latex(res)
    symbols = params.get("symbols", {})
    eval_response.latex = LatexPrinter({"symbol_names": latex_symbols(symbols), "mul_symbol": r" \cdot "}).doprint(res)
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

    is_correct = True
    parameters_dict = {
        "parsing_params": parsing_params,
        "reserved_expressions": reserved_expressions,
        "reference_criteria_strings": reference_criteria_strings,
        "symbolic_comparison_criteria": symbolic_comparison_criteria,
        "eval_response": eval_response,
    }
    criteria_feedback = set()
    for criterion in criteria_parsed:
        main_criteria = criterion.content_string()+"_TRUE"
        criteria_feedback = criteria_feedback.union(criterion_eval_node(criterion, parameters_dict).generate_feedback(response, main_criteria))
        #is_correct = is_correct and check_criterion(criterion, parameters_dict)
        is_correct = is_correct and main_criteria in criteria_feedback
    eval_response.is_correct = is_correct

    error_below_atol = None
    error_below_rtol = None

    if eval_response.is_correct is False:
        if params.get("numerical", False) or float(params.get("rtol", 0)) > 0 or float(params.get("atol", 0)) > 0:
            # REMARK: 'pi' should be a reserved symbol but it is sometimes not treated as one, possibly because of input symbols.
            # The two lines below this comments fixes the issue but a more robust solution should be found for cases where there
            # are other reserved symbols.
            def replace_pi(expr):
                pi_symbol = pi
                for s in expr.free_symbols:
                    if str(s) == 'pi':
                        pi_symbol = s
                return expr.subs(pi_symbol, float(pi))
            ans = replace_pi(ans)
            res = replace_pi(res)
            if float(params.get("atol", 0)) > 0:
                try:
                    absolute_error = abs(float(ans-res))
                    error_below_atol = bool(absolute_error < float(params["atol"]))
                except TypeError:
                    error_below_atol = None
            else:
                error_below_atol = True
            if float(params.get("rtol", 0)) > 0:
                try:
                    relative_error = abs(float((ans-res)/ans))
                    error_below_rtol = bool(relative_error < float(params["rtol"]))
                except TypeError:
                    error_below_rtol = None
            else:
                error_below_rtol = True
            if error_below_atol is None or error_below_rtol is None:
                eval_response.is_correct = False
                tag = "NOT_NUMERICAL"
                eval_response.add_feedback((tag, symbolic_comparison_internal_messages[tag]))
            elif error_below_atol is True and error_below_rtol is True:
                eval_response.is_correct = True
                tag = "WITHIN_TOLERANCE"
                eval_response.add_feedback((tag, symbolic_comparison_internal_messages[tag]))

    return eval_response
