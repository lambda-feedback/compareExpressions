from copy import deepcopy
from sympy import Add, Pow, Mul, Equality, pi, im, I, N
from sympy import re as real_part

from ..utility.expression_utilities import (
    default_parameters,
    parse_expression,
    create_sympy_parsing_params,
    preprocess_expression,
)

from ..preview_implementations.symbolic_preview import preview_function
from ..feedback.symbolic import feedback_generators as symbolic_feedback_string_generators

from ..utility.syntactical_comparison_utilities import patterns as syntactical_forms
from ..utility.syntactical_comparison_utilities import generate_arbitrary_number_pattern_matcher

from ..utility.criteria_parsing import generate_criteria_parser
from ..utility.criteria_graph_utilities import CriteriaGraph


def expression_preprocess(name, expr, parameters):
    return preprocess_expression(name, expr, parameters)


def expression_parse(name, expr, parameters, evaluation_result):
    return parse_expression(expr, parameters)


default_criteria = ["response = answer"]


def check_criterion(criterion, parameters_dict, generate_feedback=True):
    label = criterion.label.strip()
    parsing_params = deepcopy(parameters_dict["parsing_parameters"])
    parsing_params.update({"simplify": False})
    if label in {"EQUALITY", "WRITTEN_AS"}:
        result = check_equality(criterion, parameters_dict)
    elif label == "ORDER":
        result = check_order(criterion, parameters_dict)
    elif label == "CONTAINS":
        result = check_contains_symbol(criterion, parameters_dict)
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
    else:
        raise Exception(label)
    return result


def create_expressions_for_comparison(criterion, parameters_dict, local_substitutions=[]):
    parsing_params = deepcopy(parameters_dict["parsing_parameters"])
    reserved_expressions = list(parameters_dict["reserved_expressions"].items())
    parsing_params.update(
        {
            "simplify": False,
            "evaluate": False,
            "unsplittable_symbols": parsing_params["unsplittable_symbols"]+list((parameters_dict["reserved_expressions"].keys())),
        }
    )
    lhs = criterion.children[0].content_string()
    rhs = criterion.children[1].content_string()
    lhs_expr = parse_expression(lhs, parsing_params).subs(local_substitutions).subs(reserved_expressions).subs(local_substitutions)
    rhs_expr = parse_expression(rhs, parsing_params).subs(local_substitutions).subs(reserved_expressions).subs(local_substitutions)
    if parsing_params.get("complexNumbers", False):
        simplified_lhs_expr = lhs_expr.cancel().simplify()
        simplified_rhs_expr = rhs_expr.cancel().simplify()
        if (im(lhs_expr) != 0) or (im(lhs_expr) != 0):
            lhs_expr = real_part(simplified_lhs_expr) + I*im(simplified_lhs_expr)
            rhs_expr = real_part(simplified_rhs_expr) + I*im(simplified_rhs_expr)
    return lhs_expr, rhs_expr


def do_comparison(comparison_symbol, expression):
    comparisons = {
        "=": lambda expr: bool(expression.cancel().simplify().simplify() == 0),
        ">": lambda expr: bool(expression.cancel().simplify().simplify() > 0),
        ">=": lambda expr: bool(expression.cancel().simplify().simplify() >= 0),
        "<": lambda expr: bool(expression.cancel().simplify().simplify() < 0),
        "<=": lambda expr: bool(expression.cancel().simplify().simplify() <= 0),
    }
    comparison = comparisons[comparison_symbol.strip()]
    result = comparison(expression)
    return result


def check_equality(criterion, parameters_dict, local_substitutions=[]):
    lhs_expr, rhs_expr = create_expressions_for_comparison(criterion, parameters_dict, local_substitutions)
    result = do_comparison(criterion.content, lhs_expr-rhs_expr)

    # TODO: Make numerical comparison its own context
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
            res = N(replace_pi(lhs_expr))
            ans = N(replace_pi(rhs_expr))
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
            elif error_below_atol is True and error_below_rtol is True:
                result = True

    return result


def check_order(criterion, parameters_dict, local_substitutions=[]):
    lhs_expr, rhs_expr = create_expressions_for_comparison(criterion, parameters_dict, local_substitutions)
    result = do_comparison(criterion.content, lhs_expr-rhs_expr)
    return result


def check_contains_symbol(criterion, parameters_dict, local_substitutions=[]):
    lhs_expr, rhs_expr = create_expressions_for_comparison(criterion, parameters_dict, local_substitutions)
    result = rhs_expr in lhs_expr.atoms()
    return result


def find_coords_for_node_type(expression, node_type):
    stack = [(expression, tuple())]
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


def criterion_equality_node(criterion, parameters_dict, label=None):
    if label is None:
        label = criterion.content_string()

    def mathematical_equivalence(unused_input):
        result = check_equality(criterion, parameters_dict)
        if result is True:
            return {
                label+"_TRUE": None
            }
        else:
            return {
                label+"_FALSE": None
            }

    def set_equivalence(unused_input):
        matches = {"responses": [False]*len(response_list), "answers": [False]*len(answer_list)}
        for i, response in enumerate(response_list):
            result = None
            for j, answer in enumerate(answer_list):
                current_pair = [("response", response), ("answer", answer)]
                result = check_equality(criterion, parameters_dict, local_substitutions=current_pair)
                if result is True:
                    matches["responses"][i] = True
                    matches["answers"][j] = True
        if parameters_dict["multiple_answers_criteria"] == "all":
            is_correct = all(matches["responses"]) and all(matches["answers"])
            if is_correct is False:
                return {
                    label+"_MULTIPLE_ANSWER_FAIL_ALL": None
                }
        elif parameters_dict["multiple_answers_criteria"] == "all_responses":
            is_correct = all(matches["responses"])
            if is_correct is False:
                return {
                    label+"_MULTIPLE_ANSWER_FAIL_RESPONSE": None
                }
        elif parameters_dict["multiple_answers_criteria"] == "all_answers":
            is_correct = all(matches["answers"])
            if is_correct is False:
                return {
                    label+"_MULTIPLE_ANSWER_FAIL_ANSWER": None
                }
        else:
            raise SyntaxWarning(f"Unknown multiple_answers_criteria: {parameters_dict['multiple_answers_critera']}")
        return {
            label+"_TRUE": None
        }

    def equality_equivalence(unused_input):
        result = False
        res = parameters_dict["reserved_expressions"]["response"]
        ans = parameters_dict["reserved_expressions"]["answer"]

        if (not isinstance(res, Equality)) and isinstance(ans, Equality):
            return {
                label+"_EXPRESSION_NOT_EQUALITY": None
            }

        if isinstance(res, Equality) and (not isinstance(ans, Equality)):
            return {
                label+"_EQUALITY_NOT_EXPRESSION": None
            }

        # TODO: Remove when criteria for checking proportionality is implemented
        if isinstance(res, Equality) and isinstance(ans, Equality):
            symbols_in_equality_ratio = ((res.args[0]-res.args[1])/(ans.args[0]-ans.args[1])).simplify().free_symbols
            result = {str(s) for s in symbols_in_equality_ratio}.issubset(parameters_dict["parsing_parameters"]["constants"])
        if result is True:
            return {
                label+"_TRUE": None
            }
        else:
            return {
                label+"_FALSE": None
            }

    graph = CriteriaGraph(label)
    END = CriteriaGraph.END
    graph.add_node(END)
    lhs = criterion.children[0].content_string()
    rhs = criterion.children[1].content_string()

    def same_symbols(unused_input):
        parsing_params = deepcopy(parameters_dict["parsing_parameters"])
        local_substitutions = list(parameters_dict["reserved_expressions"].items())
        parsing_params.update(
            {
                "simplify": False,
                "unsplittable_symbols": parsing_params["unsplittable_symbols"]+list((parameters_dict["reserved_expressions"].keys())),
            }
        )
        lsym = parse_expression(lhs, parsing_params).subs(local_substitutions)
        rsym = parse_expression(rhs, parsing_params).subs(local_substitutions)
        result = lsym.free_symbols == rsym.free_symbols
        if result is True:
            return {
                label+"_SAME_SYMBOLS"+"_TRUE": None
            }
        else:
            return {
                label+"_SAME_SYMBOLS"+"_FALSE": None
            }

    use_set_equivalence = False
    response_list = parameters_dict["reserved_expressions"]["response"]
    answer_list = parameters_dict["reserved_expressions"]["answer"]
    if isinstance(response_list, set) and isinstance(answer_list, set):
        use_set_equivalence = True
    elif isinstance(response_list, set) and not isinstance(answer_list, set):
        use_set_equivalence = True
        answer_list = set([answer_list])
    elif not isinstance(response_list, set) and isinstance(answer_list, set):
        use_set_equivalence = True
        response_list = set([response_list])

    res = parameters_dict["reserved_expressions"]["response"]
    ans = parameters_dict["reserved_expressions"]["answer"]
    use_equality_equivalence = isinstance(res, Equality) or isinstance(ans, Equality)

    # TODO: Make checking set quivalence its own context that calls symbolic comparisons instead
    if use_set_equivalence is True:
        graph.add_evaluation_node(
            label,
            summary=label,
            details="Checks if "+str(lhs)+"="+str(rhs)+".",
            evaluate=set_equivalence
        )
        graph.attach(
            label,
            label+"_TRUE",
            summary=str(lhs)+"="+str(rhs),
            details=str(lhs)+" is equal to "+str(rhs)+".",
            feedback_string_generator=symbolic_feedback_string_generators["response=answer"]("TRUE")
        )
        graph.attach(
            label,
            label+"_MULTIPLE_ANSWER_FAIL_ALL",
            summary=str(lhs)+" is not equal to "+str(rhs),
            details="At least one answer or response was incorrect.",
            feedback_string_generator=symbolic_feedback_string_generators["INTERNAL"]("MULTIPLE_ANSWER_FAIL_ALL")
        )
        graph.attach(label+"_MULTIPLE_ANSWER_FAIL_ALL", END.label)
        graph.attach(
            label,
            label+"_MULTIPLE_ANSWER_FAIL_RESPONSE",
            summary="Unexpected element in response.",
            details="At least one response was incorrect.",
            feedback_string_generator=symbolic_feedback_string_generators["INTERNAL"]("MULTIPLE_ANSWER_FAIL_RESPONSE")
        )
        graph.attach(label+"_MULTIPLE_ANSWER_FAIL_RESPONSE", END.label)
        graph.attach(
            label,
            label+"_MULTIPLE_ANSWER_FAIL_ANSWER",
            summary="Missing element in response",
            details="At least one answer is missing in the response.",
            feedback_string_generator=symbolic_feedback_string_generators["INTERNAL"]("MULTIPLE_ANSWER_FAIL_ANSWER")
        )
        graph.attach(label+"_MULTIPLE_ANSWER_FAIL_ANSWER", END.label)
    elif use_equality_equivalence is True:
        graph.add_evaluation_node(
            label,
            summary=label,
            details="Checks if "+str(lhs)+" is equivalent to "+str(rhs)+".",
            evaluate=equality_equivalence
        )
        graph.attach(
            label,
            label+"_TRUE",
            summary=str(lhs)+" is equivalent to "+str(rhs),
            details=str(lhs)+" is equivalent to "+str(rhs)+".",
            feedback_string_generator=symbolic_feedback_string_generators["INTERNAL"]("EQUALITIES_EQUIVALENT")
        )
        graph.attach(label+"_TRUE", END.label)
        graph.attach(
            label,
            label+"_FALSE",
            summary=str(lhs)+" is not equivalent to "+str(rhs),
            details=str(lhs)+" is not equivalent to "+str(rhs)+".",
            feedback_string_generator=symbolic_feedback_string_generators["INTERNAL"]("EQUALITIES_NOT_EQUIVALENT")
        )
        graph.attach(label+"_FALSE", END.label)
        graph.attach(
            label,
            label+"_EXPRESSION_NOT_EQUALITY",
            summary=str(lhs)+" is an expression, not an equality.",
            details=str(lhs)+" is an expression, not an equality.",
            feedback_string_generator=symbolic_feedback_string_generators["INTERNAL"]("EXPRESSION_NOT_EQUALITY")
        )
        graph.attach(label+"_EXPRESSION_NOT_EQUALITY", END.label)
        graph.attach(
            label,
            label+"_EQUALITY_NOT_EXPRESSION",
            summary=str(lhs)+" is an equality, not an expression.",
            details=str(lhs)+" is an equality, not an expression.",
            feedback_string_generator=symbolic_feedback_string_generators["INTERNAL"]("EQUALITY_NOT_EXPRESSION")
        )
        graph.attach(label+"_EQUALITY_NOT_EXPRESSION", END.label)
    else:
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
            feedback_string_generator=symbolic_feedback_string_generators["response=answer"]("TRUE")
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
            feedback_string_generator=symbolic_feedback_string_generators["SAME_SYMBOLS"]("TRUE")
        )
        graph.attach(label+"_SAME_SYMBOLS"+"_TRUE", END.label)
        graph.attach(
            label+"_SAME_SYMBOLS",
            label+"_SAME_SYMBOLS"+"_FALSE",
            summary=str(lhs)+" does not have the same symbols as "+str(rhs),
            details=str(lhs)+" does note have the same (free) symbols as "+str(rhs)+".",
            feedback_string_generator=symbolic_feedback_string_generators["SAME_SYMBOLS"]("FALSE")
        )
        graph.attach(label+"_SAME_SYMBOLS"+"_FALSE", END.label)
        graph.attach(
            label,
            label+"_FALSE",
            summary=str(lhs)+"=\\="+str(rhs),
            details=str(lhs)+" is not equal to"+str(rhs)+".",
            feedback_string_generator=symbolic_feedback_string_generators["response=answer"]("FALSE")
        )
        graph.attach(label+"_FALSE", END.label)
    return graph


def criterion_written_as_node(criterion, parameters_dict, label=None):
    if label is None:
        label = criterion.content_string()

    def written_as_known_form(string, name):
        def find_form(unused_input):
            forms = set()
            for form_label in syntactical_forms.keys():
                if syntactical_forms[form_label]["matcher"](string) is True:
                    forms.add(form_label)
            if len(forms) > 0:
                return {name+"_WRITTEN_AS_"+form_label: None for form_label in forms}
            else:
                return {name+"_WRITTEN_AS_UNKNOWN": None}
        return find_form

    def compare_to_form(string, form_label):
        def inner(unused_input):
            result = dict()
            if syntactical_forms[form_label]["matcher"](string) is True:
                result.update({label+"_TRUE": None})
            else:
                result.update({label+"_FALSE": None})
            return result
        return inner

    graph = CriteriaGraph(label)
    END = CriteriaGraph.END
    graph.add_node(END)

    lhs = criterion.children[0].content_string()
    rhs = criterion.children[1].content_string()

    if set([lhs, rhs]) == set(["response", "answer"]):

        # TODO: Make a version that can compare the forms of any two reserved expressions
        answer = parameters_dict["reserved_expressions_strings"]["task"]["answer"]
        response = parameters_dict["reserved_expressions_strings"]["learner"]["response"]

        def response_written_as_answer(unused_input):
            matcher = generate_arbitrary_number_pattern_matcher(answer)
            if matcher(response):
                return {label+"_TRUE": None}
            else:
                return {label+"_FALSE": None}

        graph.add_evaluation_node(
            str(rhs)+"_WRITTEN_AS_KNOWN_FORM",
            summary=label,
            details=f"Checks if {rhs} is written in a known form.",
            evaluate=written_as_known_form(answer, rhs)
        )
        graph.attach(
            str(rhs)+"_WRITTEN_AS_KNOWN_FORM",
            str(rhs)+"_WRITTEN_AS_UNKNOWN",
            summary=str(rhs)+" is not written in a known form.",
            details=str(rhs)+" is not written in a known form.",
            feedback_string_generator=symbolic_feedback_string_generators["WRITTEN_AS"]("UNKNOWN")
        )
        graph.attach(
            str(rhs)+"_WRITTEN_AS_UNKNOWN",
            label,
            summary="Is "+str(lhs)+" written in the same form as "+str(rhs)+".",
            details="Checks if "+str(lhs)+" is written in the same form as "+str(rhs)+".",
            evaluate=response_written_as_answer,
            sufficiencies={str(rhs)+"_WRITTEN_AS_UNKNOWN"}
        )
        graph.attach(
            label,
            label+"_TRUE",
            summary=str(rhs)+" written in the same form as "+str(rhs)+".",
            details=str(rhs)+" written in the same form as "+str(rhs)+".",
            feedback_string_generator=symbolic_feedback_string_generators["SYNTACTICAL_EQUIVALENCE"]("TRUE")
        )
        graph.attach(
            label,
            label+"_FALSE",
            summary=str(rhs)+" written in the same form as "+str(rhs)+".",
            details=str(rhs)+" written in the same form as "+str(rhs)+".",
            feedback_string_generator=symbolic_feedback_string_generators["SYNTACTICAL_EQUIVALENCE"]("FALSE")
        )

        for form_label in syntactical_forms.keys():
            graph.attach(
                str(rhs)+"_WRITTEN_AS_KNOWN_FORM",
                str(rhs)+"_WRITTEN_AS_"+form_label,
                summary=str(rhs)+" in written in "+syntactical_forms[form_label]["name"]+" form.",
                details=str(rhs)+" in written in "+syntactical_forms[form_label]["name"]+" form.",
                feedback_string_generator=symbolic_feedback_string_generators["WRITTEN_AS"](form_label),
            )
            graph.attach(
                str(rhs)+"_WRITTEN_AS_"+form_label,
                str(lhs)+"_COMPARE_FORM_TO_"+form_label,
                summary="Is "+str(lhs)+" written in "+syntactical_forms[form_label]["name"]+" form.",
                details="Checks if "+str(lhs)+" is written in "+syntactical_forms[form_label]["name"]+" form.",
                evaluate=compare_to_form(response, form_label),
                sufficiencies={str(rhs)+"_WRITTEN_AS_"+form_label}
            )
            graph.attach(str(lhs)+"_COMPARE_FORM_TO_"+form_label, label+"_TRUE")
            graph.attach(str(lhs)+"_COMPARE_FORM_TO_"+form_label, label+"_FALSE")
    return graph


def criterion_where_node(criterion, parameters_dict, label=None):
    parsing_params = parameters_dict["parsing_parameters"]
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

    def create_expression_check(crit):
        def expression_check(unused_input):
            result = check_equality(crit, parameters_dict, local_substitutions=local_subs)
            if result is True:
                return {
                    label+"_TRUE": None
                }
            else:
                return {
                    label+"_FALSE": None
                }
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
        feedback_string_generator=symbolic_feedback_string_generators["response=answer_where"]("TRUE")
    )
    graph.attach(label+"_TRUE", END.label)
    graph.attach(
        label,
        label+"_FALSE",
        summary="not "+expression.content_string(),
        details=expression.content_string()+" is not true when "+", ".join([s.content_string() for s in subs])+".",
        feedback_string_generator=symbolic_feedback_string_generators["response=answer_where"]("FALSE")
    )

    reserved_expressions = list(parameters_dict["reserved_expressions"].items())
    response = parameters_dict["reserved_expressions"]["response"]
    expression_to_vary = None
    if expression.children[0].content_string().strip() == "response":
        expression_to_vary = expression.children[1]
    elif expression.children[1].content_string().strip() == "response":
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
        value = expression_to_vary.subs(local_subs).simplify()
        values_and_expressions = {str(value): set([expression_to_vary])}
        values_and_variations_group = {str(value): set(["UNKNOWN"])}
        for (group_label, info) in variation_groups.items():
            for variation in info["variations"]:
                value = variation.subs(local_subs).simplify()
                values_and_expressions.update({str(value): values_and_expressions.get(str(value), set()).union(set([variation]))})
                if value != expression_to_vary.subs(local_subs):
                    values_and_variations_group.update({str(value): values_and_variations_group.get(str(value), set()).union(set([group_label]))})
        if len(values_and_expressions) > 1:
            def identify_reason(unused_input):
                reasons = {
                    label+"_"+group_label: {'criterion': criterion} for group_label in values_and_variations_group.get(str(response_value), {"UNKNOWN"})
                }
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
                feedback_string_generator=symbolic_feedback_string_generators["IDENTIFY_REASON"]("UNKNOWN")
            )
            graph.attach(label+"_UNKNOWN", END.label)

            def get_candidates(unused_input):
                candidates = {
                    label+"_RESPONSE_CANDIDATES_"+group_label: {'criterion': criterion} for group_label in values_and_variations_group[str(response_value)]
                }
                return candidates

            for (group_label, group_info) in variation_groups.items():
                graph.attach(
                    label+"_IDENTIFY_REASON",
                    label+"_"+group_label,
                    summary=group_info["summary"](expression_to_vary, group_info["variations"]),
                    details=group_info["details"](expression_to_vary, group_info["variations"]),
                    feedback_string_generator=symbolic_feedback_string_generators["IDENTIFY_REASON"]("UNKNOWN")
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
                    if group_label != "UNKNOWN":
                        group_candidates_eval = graph.evaluations[label+"_GET_CANDIDATES_"+group_label]
                        if label+"_RESPONSE_CANDIDATES_"+group_label not in [edge.target.label for edge in group_candidates_eval.outgoing]:
                            graph.attach(
                                label+"_GET_CANDIDATES_"+group_label,
                                label+"_RESPONSE_CANDIDATES_"+group_label,
                                summary="response = "+str(value),
                                details="Response candidates: "+expressions_string
                            )
                            graph.attach(
                                label+"_RESPONSE_CANDIDATES_"+group_label,
                                END.label
                            )
    return graph


def criterion_eval_node(criterion, parameters_dict, generate_feedback=True):
    feedback_string_generator_inputs = {'criterion': criterion}

    def evaluation_node_internal(unused_input):
        result = check_criterion(criterion, parameters_dict, generate_feedback)
        label = criterion.content_string()
        if result:
            return {
                label+"_TRUE": feedback_string_generator_inputs
            }
        else:
            return {
                label+"_FALSE": feedback_string_generator_inputs
            }
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
        feedback_string_generator=symbolic_feedback_string_generators["GENERIC"]("TRUE")
    )
    graph.attach(label+"_TRUE", END.label)
    graph.attach(
        label,
        label+"_FALSE",
        summary="True",
        details=label+" is false.",
        feedback_string_generator=symbolic_feedback_string_generators["GENERIC"]("FALSE")
    )
    graph.attach(label+"_FALSE", END.label)
    return graph


def feedback_procedure_generator(parameters_dict):
    graphs = dict()
    criteria = set(parameters_dict["criteria"].items())
    for (label, criterion) in criteria:
        graph_templates = {
            "EQUALITY": criterion_equality_node,
            "WHERE": criterion_where_node,
            "WRITTEN_AS": criterion_written_as_node,
        }
        graph_template = graph_templates.get(criterion.label, criterion_eval_node)
        graph = graph_template(criterion, parameters_dict)
        for evaluation in graph.evaluations.values():
            if evaluation.label in parameters_dict.get("disabled_evaluation_nodes", set()):
                evaluation.replacement = CriteriaGraph.END
        graphs.update({label: graph})
    return graphs


def feedback_string_generator(tags, graph, parameters_dict):
    strings = dict()
    for tag in tags:
        # feedback_string = graph.criteria[tag].feedback_string_generator(inputs)
        feedback_string = "PLACEHOLDER"
        if feedback_string is not None:
            strings.update({tag: feedback_string})
    return


context = {
    "expression_preview": preview_function,
    "generate_criteria_parser": generate_criteria_parser,
    "generate_feedback": generate_criteria_parser,
    "expression_preprocess": expression_preprocess,
    "expression_parse": expression_parse,
    "default_parameters": default_parameters,
    "default_criteria": default_criteria,
    "feedback_procedure_generator": feedback_procedure_generator,
    "feedback_string_generator": feedback_string_generator,
    "parsing_parameters_generator": create_sympy_parsing_params,
}
