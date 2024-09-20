from sympy.parsing.sympy_parser import T as parser_transformations
from sympy import Abs, Equality, latex, pi, Symbol, Add, Pow, Mul,N
from sympy.printing.latex import LatexPrinter
from copy import deepcopy
import re

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
from .feedback.symbolic_comparison import feedback_generators as symbolic_feedback_generators
from .feedback.symbolic_comparison import equivalences as reference_criteria_strings

from .syntactical_comparison_utilities import patterns as syntactical_forms
from .syntactical_comparison_utilities import is_number as syntactical_is_number
from .syntactical_comparison_utilities import response_and_answer_on_same_form
from .syntactical_comparison_utilities import attach_form_criteria

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
    reserved_expressions = list(parameters_dict["reserved_expressions"].items())
    local_substitutions = parameters_dict.get("local_substitutions",[])
    reference_criteria_strings = parameters_dict["reference_criteria_strings"]
    eval_response = parameters_dict["eval_response"]
    parsing_params = {key: value for (key,value) in parameters_dict["parsing_params"].items()}
    parsing_params.update({"simplify": False})
    symbolic_comparison_criteria = parameters_dict["symbolic_comparison_criteria"]
    if label == "EQUALITY":
        result = check_equality(criterion, parameters_dict)
        lhs = criterion.children[0].content_string()
        rhs = criterion.children[1].content_string()
        criterion_expression = (parse_expression(lhs, parsing_params)) - (parse_expression(rhs, parsing_params))
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

def check_equality(criterion, parameters_dict):
    
    reserved_expressions = list(parameters_dict["reserved_expressions"].items())
    local_substitutions = parameters_dict.get("local_substitutions",[])
    parsing_params = {key: value for (key,value) in parameters_dict["parsing_params"].items()}
    parsing_params.update({"simplify": False})
    
    #Define atol and rtol
    
    #Gets the LHS and RHS of the equation
    
    lhs = criterion.children[0].content_string()
    rhs = criterion.children[1].content_string()
    
 #LHS is response
 #RHS is answer
    
    #Parses into a mathematical expression - the numerical value needs to be extracted
    expression = (parse_expression(lhs, parsing_params)) - (parse_expression(rhs, parsing_params))
    result = bool(expression.subs(reserved_expressions).subs(local_substitutions).cancel().simplify().simplify() == 0)

    if result is False:
        error_below_rtol = None
        error_below_atol = None
        if parameters_dict.get("numerical", False) or float(parameters_dict.get("rtol", 0)) > 0 or float(parameters_dict.get("atol", 0)) > 0:

            # REMARK: 'pi' should be a reserved symbol but it is sometimes not treated as one, possibly because of input symbols.
            # The two lines below this comments fixes the issue but a more robust solution should be found for cases where there
            # are other reserved symbols.
            def replace_pi(expr):
                pi_symbol = pi
                for s in expr.free_symbols:
                    if str(s) == 'pi':
                        pi_symbol = s
                return expr.subs(pi_symbol, float(pi))

            # NOTE: This code assumes that the left hand side is the response and the right hand side is the answer
            # Separates LHS and RHS, parses and evaluates them
            res = N(replace_pi(parse_expression(lhs, parsing_params).subs(reserved_expressions).subs(local_substitutions)))
            ans = N(replace_pi(parse_expression(rhs, parsing_params).subs(reserved_expressions).subs(local_substitutions)))

            if float(parameters_dict.get("atol", 0)) > 0:
                try:
                    absolute_error = abs(float(ans-res))
                    error_below_atol = bool(absolute_error < float(parameters_dict["atol"]))
                except TypeError:
                    error_below_atol = None
            else:
                error_below_atol = True
            if float(parameters_dict.get("rtol", 0)) > 0:
                try:
                    relative_error = abs(float((ans-res)/ans))
                    error_below_rtol = bool(relative_error < float(parameters_dict["rtol"]))
                except TypeError:
                    error_below_rtol = None
            else:
                error_below_rtol = True
            if error_below_atol is None or error_below_rtol is None:
                result = False
                # TODO: The code below for supplying the right tag will be moved elsewhere in the code in the future
                """
                eval_response.is_correct = False
                tag = "NOT_NUMERICAL"
                eval_response.add_feedback((tag, symbolic_comparison_internal_messages[tag]))
                """
            elif error_below_atol is True and error_below_rtol is True:
                result = True
                # TODO: The code below for supplying the right tag will be moved elsewhere in the code in the future
                """
                eval_response.is_correct = True
                tag = "WITHIN_TOLERANCE"
                eval_response.add_feedback((tag, symbolic_comparison_internal_messages[tag]))
                """

    
    return result

def criterion_eval_node(criterion, parameters_dict, generate_feedback=True):
    def evaluation_node_internal(unused_input):
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
    graph.attach(
        label,
        label+"_TRUE",
        summary="True",
        details=label+" is true.",
        feedback_string_generator=symbolic_feedback_generators["GENERIC"]("TRUE")
    )
    graph.attach(label+"_TRUE", END.label)
    graph.attach(
        label,
        label+"_FALSE",
        summary="True",
        details=label+" is false.",
        feedback_string_generator=symbolic_feedback_generators["GENERIC"]("FALSE")
    )
    graph.attach(label+"_FALSE", END.label)
    return graph


#Not the issue
def criterion_equality_node(criterion, parameters_dict, label=None):
    if label is None:
        label = criterion.content_string()

    def mathematical_equivalence(unused_input):
        result = check_equality(criterion, parameters_dict)
        if result is True:
            return {label+"_TRUE"}
        else:
            return {label+"_FALSE"}
    graph = CriteriaGraph(label)
    END = CriteriaGraph.END
    graph.add_node(END)
    lhs = criterion.children[0].content_string()
    rhs = criterion.children[1].content_string()

    def syntactical_equivalence(unused_input):
        result = parameters_dict["original_input"]["answer"] == parameters_dict["original_input"]["response"]
        if result is True:
            return {label+"_SYNTACTICAL_EQUIVALENCE"+"_TRUE"}
        else:
            return {label+"_SYNTACTICAL_EQUIVALENCE"+"_FALSE"}

    def same_symbols(unused_input):
        local_substitutions = parameters_dict.get("local_substitutions",[])
        reserved_expressions = list(parameters_dict["reserved_expressions"].items())
        parsing_params = {key: value for (key,value) in parameters_dict["parsing_params"].items()}
        parsing_params.update({"simplify": False})
        for k, item in enumerate(reserved_expressions):
            if item[0] == "answer":
                reserved_expressions[k] = ("answer", parameters_dict["reserved_expressions"]["answer_original"])
            elif item[0] == "response":
                reserved_expressions[k] = ("response", parameters_dict["reserved_expressions"]["response_original"])
        lsym = parse_expression(lhs, parsing_params).subs(reserved_expressions).subs(local_substitutions)
        rsym = parse_expression(rhs, parsing_params).subs(reserved_expressions).subs(local_substitutions)
        result = lsym.free_symbols == rsym.free_symbols
        if result is True:
            return {label+"_SAME_SYMBOLS"+"_TRUE"}
        else:
            return {label+"_SAME_SYMBOLS"+"_FALSE"}

    # Check for mathematical equivalence
    graph.add_evaluation_node(
        label,
        summary=label,
        details="Checks if "+str(lhs)+"="+str(rhs)+".",
        evaluate=mathematical_equivalence
    )
    graph.attach(
        label,
        label+"_TRUE",
        summary=str(lhs)+"="+str(rhs),
        details=str(lhs)+" is equal to "+str(rhs)+".",
        feedback_string_generator=symbolic_feedback_generators["response=answer"]("TRUE")
    )

    graph.attach(
        label+"_TRUE",
        label+"_SAME_SYMBOLS",
        summary=str(lhs)+" has the same symbols as "+str(rhs),
        details=str(lhs)+" has the same (free) symbols as "+str(rhs)+".",
        evaluate=same_symbols
    )
    graph.attach(
        label+"_SAME_SYMBOLS",
        label+"_SAME_SYMBOLS"+"_TRUE",
        summary=str(lhs)+" has the same symbols as "+str(rhs),
        details=str(lhs)+" has the same (free) symbols as "+str(rhs)+".",
        feedback_string_generator=symbolic_feedback_generators["SAME_SYMBOLS"]("TRUE")
    )
    graph.attach(label+"_SAME_SYMBOLS"+"_TRUE", END.label)
    graph.attach(
        label+"_SAME_SYMBOLS",
        label+"_SAME_SYMBOLS"+"_FALSE",
        summary=str(lhs)+" does not have the same symbols as "+str(rhs),
        details=str(lhs)+" does note have the same (free) symbols as "+str(rhs)+".",
        feedback_string_generator=symbolic_feedback_generators["SAME_SYMBOLS"]("FALSE")
    )
    graph.attach(label+"_SAME_SYMBOLS"+"_FALSE", END.label)

    graph.attach(
        label,
        label+"_FALSE",
        summary=str(lhs)+"=\\="+str(rhs),
        details=str(lhs)+" is not equal to"+str(rhs)+".",
        feedback_string_generator=symbolic_feedback_generators["response=answer"]("FALSE")
    )

    if parameters_dict["syntactical_comparison"] is True:
        if set([lhs, rhs]) == set(["response", "answer"]):
            has_recognisable_form = syntactical_is_number(parameters_dict["original_input"]["answer"])
            for form_label in syntactical_forms.keys():
                has_recognisable_form = has_recognisable_form or syntactical_forms[form_label]["matcher"](parameters_dict["original_input"]["answer"])
            if has_recognisable_form is True:

                graph.attach(
                    label+"_TRUE",
                    label+"_SYNTACTICAL_EQUIVALENCE",
                    summary="response is written like answer",
                    details="Checks if "+str(lhs)+" is written exactly the same as "+str(rhs)+".",
                    evaluate=syntactical_equivalence
                )
                graph.attach(
                    label+"_SYNTACTICAL_EQUIVALENCE",
                    label+"_SYNTACTICAL_EQUIVALENCE"+"_TRUE",
                    summary="response is written like answer",
                    details=""+str(lhs)+" is written exactly the same as "+str(rhs)+".",
                    feedback_string_generator=symbolic_feedback_generators["SYNTACTICAL_EQUIVALENCE"]("TRUE")
                )
                graph.attach(
                    label+"_SYNTACTICAL_EQUIVALENCE"+"_TRUE",
                    END.label
                )
                graph.attach(
                    label+"_SYNTACTICAL_EQUIVALENCE",
                    label+"_SYNTACTICAL_EQUIVALENCE"+"_FALSE",
                    summary="response is not written like answer", details=""+str(lhs)+" is not written exactly the same as "+str(rhs)+".",
                    feedback_string_generator=symbolic_feedback_generators["SYNTACTICAL_EQUIVALENCE"]("FALSE")
                )
                graph.attach(label+"_SYNTACTICAL_EQUIVALENCE"+"_FALSE", END.label)

                graph.attach(
                    label+"_TRUE",
                    label+"_SAME_FORM",
                    summary=str(lhs)+" is written in the same form as "+str(rhs),
                    details=str(lhs)+" is written in the same form as "+str(rhs)+".",
                    evaluate=response_and_answer_on_same_form(label+"_SAME_FORM", parameters_dict)
                )

                for form_label in syntactical_forms.keys():
                    if syntactical_forms[form_label]["matcher"](parameters_dict["original_input"]["answer"]) is True:
                        attach_form_criteria(graph, label+"_SAME_FORM", criterion, parameters_dict, form_label)

                graph.attach(
                    label+"_SAME_FORM",
                    label+"_SAME_FORM"+"_UNKNOWN",
                    summary="Cannot determine if "+str(lhs)+" and "+str(rhs)+" are written on the same form",
                    details="Cannot determine if "+str(lhs)+" and "+str(rhs)+" are written on the same form.",
                    feedback_string_generator=symbolic_feedback_generators["SAME_FORM"]("UNKNOWN"),
                )

                graph.attach(label+"_SAME_FORM"+"_UNKNOWN", END.label)

                graph.attach(label+"_FALSE", label+"_SAME_FORM")
    else:
        graph.attach(label+"_FALSE", END.label)
    return graph

def find_coords_for_node_type(expression, node_type):
    stack = [(expression, tuple() )]
    node_coords = []
    while len(stack) > 0:
        (expr, coord) = stack.pop()
        if isinstance(expr, node_type):
            node_coords.append(coord)
        for (k, arg) in enumerate(expr.args):
            stack.append((arg, coord+(k,)))
    return node_coords

def replace_node_variations(expression, type_of_node, replacement_function):
    variations = []
    list_of_coords = find_coords_for_node_type(expression, type_of_node)
    for coords in list_of_coords:
        nodes = [expression]
        for coord in coords:
            nodes.append(nodes[-1].args[coord])
        for k in range(0, len(nodes[-1].args)):
            variation = replacement_function(nodes[-1], k)
            for (node, coord) in reversed(list(zip(nodes, coords))):
                new_args = node.args[0:coord]+(variation,)+node.args[coord+1:]
                variation = type(node)(*new_args)
            variations.append(variation)
    return variations

def one_addition_to_subtraction(expression):
    def addition_to_subtraction(node, k):
        return node - 2*node.args[k]
    variations = replace_node_variations(expression, Add, addition_to_subtraction)
    return variations

def one_swap_addition_and_multiplication(expression):
    def addition_to_multiplication(node, k):
        return node - node.args[k-1] - node.args[k] + node.args[k-1] * node.args[k]
    def multiplication_to_addition(node, k):
        return node - 2*node.args[k]
    variations = replace_node_variations(expression, Add, addition_to_multiplication)
    variations += replace_node_variations(expression, Mul, addition_to_multiplication)
    return variations

def one_exponent_flip(expression):
    def exponent_flip(node, k):
        return node**(-1)
    variations = replace_node_variations(expression, Pow, exponent_flip)
    return variations

#3rd in chain: returns part of the criterion graph

def criterion_where_node(criterion, parameters_dict, label=None):
    parsing_params = parameters_dict["parsing_params"]
    expression = criterion.children[0]
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
    if label is None:
        label = criterion.content_string()
    local_parameters = {**parameters_dict}
    if "local_substitutions" in local_parameters.keys():
        local_parameters["local_substitutions"] += local_subs
    else:
        local_parameters.update({"local_substitutions": local_subs})
    def create_expression_check(crit):
        def expression_check(unused_input):
            result = check_equality(crit, local_parameters)
            if result is True:
                return {label+"_TRUE"}
            else:
                return {label+"_FALSE"}
        return expression_check

    graph = CriteriaGraph(label)
    END = CriteriaGraph.END
    graph.add_node(END)
    graph.add_evaluation_node(
        label,
        summary=label,
        details="Checks if "+expression.content_string()+" where "+", ".join([s.content_string() for s in subs])+".",
        evaluate=create_expression_check(expression)
    )
    graph.attach(
        label,
        label+"_TRUE",
        summary=expression.content_string()+" where "+", ".join([s.content_string() for s in subs]),
        details=expression.content_string()+" where "+", ".join([s.content_string() for s in subs])+"is true.",
        feedback_string_generator=symbolic_feedback_generators["response=answer_where"]("TRUE")
    )
    graph.attach(label+"_TRUE", END.label)
    graph.attach(
        label,
        label+"_FALSE",
        summary="not "+expression.content_string(),
        details=expression.content_string()+" is not true when "+", ".join([s.content_string() for s in subs])+".",
        feedback_string_generator=symbolic_feedback_generators["response=answer_where"]("FALSE")
    )

    reserved_expressions = list(parameters_dict["reserved_expressions"].items())
    response = parameters_dict["reserved_expressions"]["response"]
    expression_to_vary = None
    if "response" in expression.children[0].content_string().strip():
        expression_to_vary = expression.children[1]
    elif "response" in expression.children[1].content_string().strip():
        expression_to_vary = expression.children[0]
    if expression_to_vary is not None and "response" in expression_to_vary.content_string():
        expression_to_vary = None
    if expression_to_vary is not None:
        response_value = response.subs(local_subs)
        expression_to_vary = parse_expression(expression_to_vary.content_string(), parsing_params).subs(reserved_expressions)
        variation_groups = {
            "ONE_ADDITION_TO_SUBTRACTION": {
                "variations": one_addition_to_subtraction(expression_to_vary),
                "summary": lambda expression, variations: criterion.children[0].content_string()+" if one addition is changed to a subtraction or vice versa.",
                "details": lambda expression, variations: "The following expressions are checked: "+", ".join([str(e) for e in variations]),
            },
            "ONE_EXPONENT_FLIP": {
                "variations": one_exponent_flip(expression_to_vary),
                "summary": lambda expression, variations: criterion.children[0].content_string()+" is true if one exponent has its sign changed.",
                "details": lambda expression, variations: "The following expressions are checked: "+", ".join([str(e) for e in variations]),
            },
            "ONE_SWAP_ADDITION_AND_MULTIPLICATION": {
                "variations": one_swap_addition_and_multiplication(expression_to_vary),
                "summary": lambda expression, variations: criterion.children[0].content_string()+" is true if one addition is replaced with a multiplication or vice versa.",
                "details": lambda expression, variations: "The following expressions are checked: "+", ".join([str(e) for e in variations]),
            }
        }
        reference_value = expression_to_vary.subs(local_subs)
        values_and_expressions = {reference_value: set([expression_to_vary])}
        values_and_variations_group = {reference_value: set(["UNDETECTABLE"])}
        undetectable_variations = set()
        for (group_label, info) in variation_groups.items():
            for variation in info["variations"]:
                value = variation.subs(local_subs)
                values_and_expressions.update({value: values_and_expressions.get(value, set()).union(set([variation]))})
                if value == reference_value:
                    undetectable_variations.add(variation)
                else:
                    values_and_variations_group.update({value: values_and_variations_group.get(value, set()).union(set([group_label]))})
        if len(values_and_expressions) > 1:
            def identify_reason(unused_input):
                reasons = {label+"_"+group_label for group_label in values_and_variations_group.get(response_value, {"UNKNOWN"})}
                return reasons
            graph.attach(
                label+"_FALSE",
                label+"_IDENTIFY_REASON",
                summary="Identify reason.",
                details="Attempt to identify why the response is incorrect.",
                evaluate=identify_reason
            )
            graph.attach(
                label+"_IDENTIFY_REASON",
                label+"_UNKNOWN",
                summary="Unknown reason",
                details="No candidates for how the response was computed were found.",
                feedback_string_generator=symbolic_feedback_generators["IDENTIFY_REASON"]("UNKNOWN")
            )
            graph.attach(label+"_UNKNOWN", END.label)

            def get_candidates(unused_input):
                candidates = set(["response candidates "+", ".join([str(e) for e in values_and_expressions[response_value]])])
                return candidates
            for (group_label, group_info) in variation_groups.items():
                graph.attach(
                    label+"_IDENTIFY_REASON",
                    label+"_"+group_label,
                    summary=group_info["summary"](expression_to_vary, group_info["variations"]),
                    details=group_info["details"](expression_to_vary, group_info["variations"]),
                    feedback_string_generator=symbolic_feedback_generators["IDENTIFY_REASON"]("UNKNOWN")
                )
                graph.attach(
                    label+"_"+group_label,
                    label+"_GET_CANDIDATES_"+group_label,
                    summary="Get candidate responses that satisfy "+expression.content_string(),
                    details="Get candidate responses that satisfy "+expression.content_string(),
                    evaluate=get_candidates
                )

            for (value, expressions) in values_and_expressions.items():
                expressions_string = ", ".join([str(e) for e in expressions])
                for group_label in values_and_variations_group[value]:
                    if group_label != "UNDETECTABLE":
                        graph.attach(
                            label+"_GET_CANDIDATES_"+group_label,
                            "response candidates "+expressions_string,
                            summary="response = "+str(value),
                            details="Response candidates: "+expressions_string
                        )
    return graph

def create_criteria_dict(criteria_string, criteria_parser, parsing_params):
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
    criteria_parsed = dict()
    for criterion in criteria_string_list:
        try:
            criterion_tokens = criteria_parser.scan(criterion)
            criterion_parsed = criteria_parser.parse(criterion_tokens)[0]
            criteria_parsed.update({criterion_parsed.content_string(): criterion_parsed})
        except Exception as e:
            print(e)
            raise Exception("Cannot parse criteria: `"+criterion+"`.") from e
    return criteria_parsed


# 2nd in the chain - Creates the evaluation criteria 

def create_criteria_graphs(criteria, params_dict):
    criteria_graphs = {}
    graph_templates = {
        "EQUALITY": criterion_equality_node,
        "WHERE": criterion_where_node
    }

    for (label, criterion) in criteria.items():
        graph_template = graph_templates.get(criterion.label, criterion_eval_node)
        graph = graph_template(criterion, params_dict)
        for evaluation in graph.evaluations.values():
            if evaluation.label in params_dict.get("disabled_evaluation_nodes", set()):
                evaluation.replacement = CriteriaGraph.END
        criteria_graphs.update({label: graph})
    return criteria_graphs

"""
The main function
"""
def evaluation_function(response, answer, params, include_test_data=False) -> dict:
    """
    Function used to symbolically compare two expressions.
    """

    eval_response = EvaluationResponse() #Initiayion
    eval_response.is_correct = False

    # This code handles the plus_minus and minus_plus operators
    # actual symbolic comparison is done in *check_equality*
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
                eval_response.add_feedback(("MULTIPLE_ANSWER_FAIL_ALL", symbolic_comparison_internal_messages["MULTIPLE_ANSWER_FAIL_ALL"]))
        elif params["multiple_answers_criteria"] == "all_responses":
            is_correct = all(matches["responses"])
            if is_correct is False:
                eval_response.add_feedback(("MULTIPLE_ANSWER_FAIL_RESPONSE", symbolic_comparison_internal_messages["MULTIPLE_ANSWER_FAIL_RESPONSE"]))
        elif params["multiple_answers_criteria"] == "all_answers":
            is_correct = all(matches["answers"])
            if is_correct is False:
                eval_response.add_feedback(("MULTIPLE_ANSWER_FAIL_RESPONSE", symbolic_comparison_internal_messages["MULTIPLE_ANSWER_FAIL_ANSWERS"]))
        else:
            raise SyntaxWarning(f"Unknown multiple_answers_criteria: {params['multiple_answers_critera']}")
        eval_response.is_correct = is_correct
        if len(interp) > 1:
            response_latex = "\\left\\{"+",".join(interp)+"\\right\\}"
        else:
            response_latex = interp
        eval_response.latex = response_latex

    return eval_response

#1st in chain, executes the comparison. Returns the eval response, which includes the T/F and additional info. Evalresponse is a class
def symbolic_comparison(response, answer, params, eval_response) -> dict:

    #Error exceptions


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


    # Makes everything symbolic
    
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
    parsing_params_original = {**parsing_params}
    parsing_params_original.update({"rationalise": False, "simplify": False})
    try:
        res = parse_expression(response, parsing_params)
        res_original = parse_expression(response, parsing_params_original)
    except Exception as e:
        eval_response.is_correct = False
        eval_response.add_feedback(("PARSE_ERROR", symbolic_comparison_internal_messages["PARSE_ERROR"](response)))
        return eval_response

    try:
        ans = parse_expression(answer, parsing_params)
        ans_original = parse_expression(answer, parsing_params_original)
    except Exception as e:
        raise Exception(f"SymPy was unable to parse the answer: {answer}.") from e

    # Add how res was interpreted to the response
    # eval_response.latex = latex(res)
    symbols = params.get("symbols", {})
    eval_response.latex = LatexPrinter({"symbol_names": latex_symbols(symbols), "mul_symbol": r" \cdot "}).doprint(res_original)
    eval_response.simplified = str(res)

    if (not isinstance(res_original, Equality)) and isinstance(ans_original, Equality):
        eval_response.is_correct = False
        tag = "EXPRESSION_NOT_EQUALITY"
        eval_response.add_feedback((tag, symbolic_comparison_internal_messages[tag]))
        return eval_response

    if isinstance(res_original, Equality) and (not isinstance(ans_original, Equality)):
        eval_response.is_correct = False
        tag = "EQUALITY_NOT_EXPRESSION"
        eval_response.add_feedback((tag, symbolic_comparison_internal_messages[tag]))
        return eval_response

    # TODO: Remove when criteria for checking proportionality is implemented
    if isinstance(res_original, Equality) and isinstance(ans_original, Equality):
        eval_response.is_correct = ((res_original.args[0]-res_original.args[1])/(ans_original.args[0]-ans_original.args[1])).simplify().is_constant()
        return eval_response

    # Parse criteria
    criteria_parser = generate_criteria_parser()
    parsing_params["unsplittable_symbols"] += ("response", "answer", "where")
    reserved_expressions = {
        "response": res,
        "answer": ans,
        "response_original": res_original,
        "answer_original": ans_original,
    }
    criteria_string = substitute_input_symbols(params.get("criteria", "response=answer"), params)[0]
    criteria_parsed = create_criteria_dict(criteria_string, criteria_parser, parsing_params)


    # Criteria graphs are the reference


    # Create criteria graphs
    is_correct = True
    parameters_dict = {
        "parsing_params": parsing_params,
        "reserved_expressions": reserved_expressions,
        "reference_criteria_strings": reference_criteria_strings,
        "symbolic_comparison_criteria": symbolic_comparison_criteria,
        "eval_response": eval_response,
        "original_input": {"answer": answer, "response": response},
        "disabled_evaluation_nodes": params.get("disabled_evaluation_nodes", set()),
        "syntactical_comparison": params.get("syntactical_comparison", False),
        "atol": (params.get("atol", 0)),
        "rtol": (params.get("rtol", 0)),
        "numerical": params.get("numerical", False),
        
    }
    criteria_graphs = create_criteria_graphs(criteria_parsed, parameters_dict)

    # Generate feedback from criteria graphs
    criteria_feedback = set()
    for (criterion_identifier, graph) in criteria_graphs.items():
        # TODO: Find better way to identify main criteria for criteria graph
        main_criteria = criterion_identifier+"_TRUE"
        criteria_feedback = criteria_feedback.union(graph.generate_feedback(response, main_criteria))

        # TODO: Implement way to define completeness of task other than "all main criteria satisfied"
        is_correct = is_correct and main_criteria in criteria_feedback
        eval_response.add_criteria_graph(criterion_identifier, graph)

        # Generate feedback strings from found feedback
        # NOTE: Feedback strings are generated for each graph due to the
        #       assumption that some way to return partial feedback
        #       before script has executed completely will be available
        #       in the future
        eval_response.add_feedback_from_tags(criteria_feedback, graph, {"criterion": criteria_parsed[criterion_identifier]})
        result = main_criteria in criteria_feedback
        for item in criteria_feedback:
            eval_response.add_feedback((item, ""))
        for (reference_tag, reference_strings) in reference_criteria_strings.items():
            if reference_tag in eval_response.get_tags():
                continue
            if "".join(criterion_identifier.split()) in reference_strings:
                feedback = symbolic_comparison_criteria[reference_tag].feedback[result]([])
                eval_response.add_feedback((reference_tag, feedback))
                break
    eval_response.is_correct = is_correct

    return eval_response
