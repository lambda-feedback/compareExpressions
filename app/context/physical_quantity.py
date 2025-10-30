# -------
# IMPORTS
# -------

import re
from copy import deepcopy
from ..utility.physical_quantity_utilities import (
    SLR_quantity_parser,
    SLR_quantity_parsing
)
from ..preview_implementations.physical_quantity_preview import preview_function
from ..feedback.physical_quantity import feedback_string_generators as physical_quantity_feedback_string_generators
from ..utility.expression_utilities import default_parameters as symbolic_default_parameters, \
    transform_unicode_greek_symbols, substitute
from ..utility.expression_utilities import (
    substitute_input_symbols,
    create_sympy_parsing_params,
    compute_relative_tolerance_from_significant_decimals,
    parse_expression
)
from ..utility.physical_quantity_utilities import (
    units_sets_dictionary,
    set_of_SI_prefixes,
    set_of_SI_base_unit_dimensions,
    set_of_derived_SI_units_in_SI_base_units,
    set_of_common_units_in_SI,
    set_of_very_common_units_in_SI,
    set_of_imperial_units,
)
from ..utility.slr_parsing_utilities import create_node, infix, operate, catch_undefined, SLR_Parser
from sympy import Symbol

from ..utility.criteria_graph_utilities import CriteriaGraph


def parse_quantity(name, expr, parameters, evaluation_result):
    parser = SLR_quantity_parser(parameters)
    quantity = SLR_quantity_parsing(expr, parameters, parser, name)

    for message in quantity.messages:
        evaluation_result.add_feedback(message)
    if quantity.standard_value is not None:
        standard_value = quantity.standard_value
    else:
        standard_value = None
    if quantity.value is not None:
        value = parse_expression(quantity.value.content_string(), quantity.parsing_params)
    else:
        value = None
    if quantity.standard_unit is not None:
        standard_unit = quantity.standard_unit
    else:
        standard_unit = None
    if quantity.unit is not None:
        unit = parse_expression(quantity.unit.content_string(), quantity.parsing_params)
    else:
        unit = None
    quantity_dict = {
        "quantity": quantity,
        "standard": {
            "value": standard_value,
            "unit": standard_unit
        },
        "dimension": quantity.dimension,
        "original": {
            "value": value,
            "unit": unit
        },
    }
    return quantity_dict


def generate_criteria_parser(reserved_expressions):
    start_symbol = "START"
    end_symbol = "END"
    null_symbol = "NULL"

    criteria_operations = {
        "matches",
        "dimension",
        "=",
        "<=",
        ">=",
        "<",
        ">",
    }

    token_list = [
        (start_symbol,   start_symbol),
        (end_symbol,     end_symbol),
        (null_symbol,    null_symbol),
        (" *BOOL *",     "BOOL"),
        (" *QUANTITY *", "QUANTITY"),
        (" *DIMENSION *", "DIMENSION"),
        ("\( *",         "START_DELIMITER"),
        (" *\)",         "END_DELIMITER"),
        ("response",     "QUANTITY"),
        ("answer",       "QUANTITY"),
        ("INPUT",        "INPUT", catch_undefined),
    ]
    token_list += [(" *"+x+" *", " "+x+" ") for x in criteria_operations]

    productions = [
        ("START",     "BOOL", create_node),
        ("BOOL",      "QUANTITY matches QUANTITY", infix),
        ("BOOL",      "DIMENSION matches DIMENSION", infix),
        ("BOOL",      "QUANTITY=QUANTITY", infix),
        ("BOOL",      "QUANTITY<=QUANTITY", infix),
        ("BOOL",      "QUANTITY>=QUANTITY", infix),
        ("BOOL",      "QUANTITY<QUANTITY", infix),
        ("BOOL",      "QUANTITY>QUANTITY", infix),
        ("QUANTITY",  "INPUT", create_node),
        ("DIMENSION", "dimension(QUANTITY)", operate(1)),
    ]

    return SLR_Parser(token_list, productions, start_symbol, end_symbol, null_symbol)


def comparison_function(comparison_operator):
    none_placeholder = Symbol('NONE_PLACEHOLDER')
    comparison_type_dictionary = {
        "=": lambda a, b: bool(a == b),
        ">": lambda a, b: bool(a > b),
        "<": lambda a, b: bool(a < b),
        ">=": lambda a, b: bool(a >= b),
        "<=": lambda a, b: bool(a <= b),
    }
    comparison = comparison_type_dictionary[comparison_operator]

    def comparison_function_inner(lhs, rhs, substitutions):
        local_substitutions = [(key, none_placeholder) if expr is None else (key, expr) for (key, expr) in substitutions]
        expr0 = lhs.subs(local_substitutions)
        expr1 = rhs.subs(local_substitutions)
        result = comparison((expr0-expr1).cancel().simplify().simplify(), 0)
        return result
    return comparison_function_inner


def comparison_base_graph(criterion, parameters, comparison_operator="=", label=None):
    graph = CriteriaGraph(label)
    END = CriteriaGraph.END
    graph.add_node(END)
    reserved_expressions = parameters["reserved_expressions"].items()
    parsing_params = deepcopy(parameters["parsing_parameters"])
    if parameters.get('atol', 0) == 0 and parameters.get('rtol', 0) == 0:
        ans = parameters["reserved_expressions"]["answer"]["quantity"].value
        if ans is not None:
            rtol = compute_relative_tolerance_from_significant_decimals(ans.content_string())
            parsing_params.update({'rtol': rtol})
    parsing_params.update({"simplify": False, "evaluate": False})

    if label is None:
        label = criterion.content_string()

    inputs = criterion.children
    lhs_string = criterion.children[0].content_string()
    rhs_string = criterion.children[1].content_string()
    lhs = parse_expression(lhs_string, parsing_params)
    rhs = parse_expression(rhs_string, parsing_params)

    stardard_forms = [(key, expr["standard"]["value"]*expr["standard"]["unit"]) for (key, expr) in reserved_expressions]
    compare = comparison_function(comparison_operator)

    def compare_evaluate(unused_input):
        if compare(lhs, rhs, stardard_forms) is True:
            return {label+"_TRUE": None}
        else:
            return {label+"_FALSE": None}

    graph.add_evaluation_node(
        label,
        summary=f"Is {inputs[0]} {comparison_operator} {inputs[1]}?",
        details=f"checks if {inputs[0]} {comparison_operator} {inputs[1]}.",
        evaluate=compare_evaluate
    )
    graph.attach(
        label,
        label+"_TRUE",
        summary=f"{inputs[0]} {comparison_operator} {inputs[1]} is true.",
        details=f"{inputs[0]} {comparison_operator} {inputs[1]} is true.",
        feedback_string_generator=physical_quantity_feedback_string_generators["COMPARISON"]("TRUE")
    )
    graph.attach(label+"_TRUE", END.label)
    graph.attach(
        label,
        label+"_FALSE",
        summary=f"{inputs[0]} {comparison_operator} {inputs[1]} is false.",
        details=f"{inputs[0]} {comparison_operator} {inputs[1]} is false.",
        feedback_string_generator=physical_quantity_feedback_string_generators["COMPARISON"]("FALSE")
    )
    graph.attach(label+"_FALSE", END.label)
    # TODO: Consider adding node for cases where comparison cannot be done / cannot be determined

    return graph


def greater_than_node(criterion, parameters, label=None):
    return comparison_base_graph(criterion, parameters, comparison_operator=">", label=label)


def greater_than_or_equal_node(criterion, parameters, label=None):
    # TODO: Add nodes for the equal case
    graph = comparison_base_graph(criterion, parameters, comparison_operator=">=", label=label)
    return graph


def less_than_node(criterion, parameters, label=None):
    return comparison_base_graph(criterion, parameters, comparison_operator="<", label=label)


def less_than_or_equal_node(criterion, parameters, label=None):
    # TODO: Add nodes for the equal case
    graph = comparison_base_graph(criterion, parameters, comparison_operator=">=", label=label)
    return graph


def criterion_match_node(criterion, parameters, label=None):
    graph = CriteriaGraph(label)
    END = CriteriaGraph.END
    graph.add_node(END)
    reserved_expressions = parameters["reserved_expressions"].items()
    parsing_params = deepcopy(parameters["parsing_parameters"])
    if parameters.get('atol', 0) == 0 and parameters.get('rtol', 0) == 0:
        ans = parameters["reserved_expressions"]["answer"]["quantity"].value
        if ans is not None:
            rtol = compute_relative_tolerance_from_significant_decimals(ans.content_string())
            parsing_params.update({'rtol': rtol})
    parsing_params.update({"simplify": False, "evaluate": False})

    if label is None:
        label = criterion.content_string()

    inputs = criterion.children
    lhs_string = criterion.children[0].content_string()
    rhs_string = criterion.children[1].content_string()
    lhs = parse_expression(lhs_string, parsing_params)
    rhs = parse_expression(rhs_string, parsing_params)

    is_equal = comparison_function("=")

    def is_proportional(lhs, rhs, substitutions):
        none_placeholder = Symbol('NONE_PLACEHOLDER')
        local_substitutions = [(key, none_placeholder) if expr is None else (key, expr) for (key, expr) in substitutions]
        expr0 = lhs.subs(local_substitutions)
        expr1 = rhs.subs(local_substitutions)
        if expr0.cancel().simplify().simplify() != 0:
            result = (expr0/expr1).cancel().simplify().is_constant()
            ratio = expr0/expr1
        elif expr0.cancel().simplify().simplify() != 0:
            result = (expr1/expr0).cancel().simplify().is_constant()
            ratio = expr1/expr0
        else:
            result = False
        if result is True:
            ratio = float(ratio.cancel().simplify())
        else:
            ratio = None
        return result, ratio

    def quantity_match(unused_inputs):
        # TODO: Better system for identifying if we expect the response to have value/unit or not
        if ('answer' in lhs_string and 'response' in rhs_string) or ('response' in lhs_string and 'answer' in rhs_string):
            res_value = parameters["reserved_expressions"]["response"]["original"]["value"]
            ans_value = parameters["reserved_expressions"]["answer"]["original"]["value"]
            res_unit = parameters["reserved_expressions"]["response"]["original"]["unit"]
            ans_unit = parameters["reserved_expressions"]["answer"]["original"]["unit"]
            if res_value is None and ans_value is not None:
                return {label+"_MISSING_VALUE": {"lhs": lhs_string, "rhs": rhs_string}}
            if res_value is not None and ans_value is None:
                return {label+"_UNEXPECTED_VALUE": {"lhs": lhs_string, "rhs": rhs_string}}
            if res_unit is None and ans_unit is not None:
                return {label+"_MISSING_UNIT": {"lhs": lhs_string, "rhs": rhs_string}}
            if res_unit is not None and ans_unit is None:
                return {label+"_UNEXPECTED_UNIT": {"lhs": lhs_string, "rhs": rhs_string}}

        substitutions = [(key, expr["standard"]["value"]) for (key, expr) in reserved_expressions]
        value_match = is_equal(lhs, rhs, substitutions)

        if value_match is False:
            # TODO: better analysis of where `answer` is found in the criteria so that
            #       numerical tolerances can be applied appropriately
            if parsing_params.get('rtol', 0) > 0 or parsing_params.get('atol', 0) > 0:
                if (lhs_string == 'answer' and rhs_string == 'response') or (lhs_string == 'response' and rhs_string == 'answer'):
                    ans = parameters["reserved_expressions"]["answer"]["standard"]["value"].simplify()
                    res = parameters["reserved_expressions"]["response"]["standard"]["value"].simplify()
                if (ans is not None and ans.is_constant()) and (res is not None and res.is_constant()):
                    if parsing_params.get('rtol', 0) > 0 and (ans != 0):
                        value_match = bool(abs(float((ans-res)/ans)) < parsing_params['rtol'])
                    elif parsing_params.get('atol', 0) > 0 or (ans == 0):
                        value_match = bool(abs(float(ans-res)) < parsing_params['atol'])

        substitutions = [(key, expr["standard"]["unit"]) for (key, expr) in reserved_expressions]
        unit_match = is_equal(lhs, rhs, substitutions)

        output_tags = None
        if value_match is True and unit_match is True:
            output_tags = {
                label+"_TRUE": {"lhs": lhs_string, "rhs": rhs_string}
            }
        else:
            output_tags = {
                label+"_FALSE": {"lhs": lhs_string, "rhs": rhs_string}
            }

        return output_tags

    def dimension_match(unused_inputs):
        substitutions = [(key, expr["dimension"]) for (key, expr) in reserved_expressions]
        dimension_match, _ = is_proportional(lhs, rhs, substitutions)

        output_tags = None
        if dimension_match is True:
            output_tags = {
                label+"_DIMENSION_MATCH"+"_TRUE": {"lhs": lhs_string, "rhs": rhs_string}
            }
        else:
            output_tags = {
                label+"_DIMENSION_MATCH"+"_FALSE": {"lhs": lhs_string, "rhs": rhs_string}
            }
        return output_tags

    def unit_comparison(unused_inputs):
        substitutions = [(key, expr["original"]["unit"]) for (key, expr) in reserved_expressions]

        if is_equal(lhs, rhs, substitutions) is True:
            output_tags = {
                label+"_UNIT_COMPARISON"+"_IDENTICAL": None
            }
        else:
            local_substitutions = [(key, expr["quantity"].expanded_unit) for (key, expr) in reserved_expressions]
            result, ratio = is_proportional(lhs, rhs, local_substitutions)
            if result is True and ratio >= 1000:
                output_tags = {
                    label+"_UNIT_COMPARISON"+"_PREFIX_IS_LARGE": None
                }
            elif result is True and ratio <= 1/1000:
                output_tags = {
                    label+"_UNIT_COMPARISON"+"_PREFIX_IS_SMALL": None
                }
            else:
                output_tags = {
                    label+"_UNIT_COMPARISON"+"_SIMILAR": None
                }

        return output_tags

    graph.add_evaluation_node(
        label,
        summary=f"Do the quantities {inputs[0]} and {inputs[1]} match?",
        details=f"Converts {inputs[0]} and {inputs[1]} match to a common set of base units and compares their values.",
        evaluate=quantity_match
    )
    graph.attach(
        label,
        label+"_TRUE",
        summary=f"The quantities {inputs[0]} and {inputs[1]} match.",
        details=f"The quantities {inputs[0]} and {inputs[1]} match.",
        feedback_string_generator=physical_quantity_feedback_string_generators["MATCHES"]("QUANTITY_MATCH")
    )
    graph.attach(
        label,
        label+"_FALSE",
        summary=f"The quantities {inputs[0]} and {inputs[1]} does not match.",
        details=f"The quantities {inputs[0]} and {inputs[1]} does not match.",
        feedback_string_generator=physical_quantity_feedback_string_generators["MATCHES"]("QUANTITY_MISMATCH")
    )
    graph.attach(
        label,
        label+"_MISSING_VALUE",
        summary="The response is missing a value.",
        details="The response is missing a value.",
        feedback_string_generator=physical_quantity_feedback_string_generators["MATCHES"]("MISSING_VALUE")
    )
    graph.attach(label+"_MISSING_VALUE", END.label)
    graph.attach(
        label,
        label+"_UNEXPECTED_VALUE",
        summary="The response is expected only have unit(s), no value.",
        details="The response is expected only have unit(s), no value.",
        feedback_string_generator=physical_quantity_feedback_string_generators["MATCHES"]("UNEXPECTED_VALUE")
    )
    graph.attach(label+"_UNEXPECTED_VALUE", END.label)
    graph.attach(
        label,
        label+"_MISSING_UNIT",
        summary="The response is missing unit(s).",
        details="The response is missing unit(s).",
        feedback_string_generator=physical_quantity_feedback_string_generators["MATCHES"]("MISSING_UNIT")
    )
    graph.attach(label+"_MISSING_UNIT", END.label)
    graph.attach(
        label,
        label+"_UNEXPECTED_UNIT",
        summary="The response is expected to be a value without unit(s).",
        details="The response is expected to be a value without unit(s).",
        feedback_string_generator=physical_quantity_feedback_string_generators["MATCHES"]("UNEXPECTED_UNIT")
    )
    graph.attach(label+"_UNEXPECTED_UNIT", END.label)
    graph.attach(
        label+"_FALSE",
        label+"_DIMENSION_MATCH",
        summary=f"Do the dimensions of {inputs[0]} and {inputs[1]} match?",
        details=f"Do the dimensions of {inputs[0]} and {inputs[1]} match?",
        evaluate=dimension_match
    )
    graph.attach(
        label+"_DIMENSION_MATCH",
        label+"_DIMENSION_MATCH"+"_TRUE",
        summary=f"The quantities {inputs[0]} and {inputs[1]} have the same dimensions.",
        details=f"The quantities {inputs[0]} and {inputs[1]} have the same dimensions.",
        feedback_string_generator=physical_quantity_feedback_string_generators["MATCHES"]("DIMENSION_MATCH")
    )
    graph.attach(
        label+"_DIMENSION_MATCH",
        label+"_DIMENSION_MATCH"+"_FALSE",
        summary=f"The quantities {inputs[0]} and {inputs[1]} have different dimensions.",
        details=f"The quantities {inputs[0]} and {inputs[1]} have different dimensions.",
        feedback_string_generator=physical_quantity_feedback_string_generators["MATCHES"]("DIMENSION_MISMATCH")
    )
    graph.attach(label+"_DIMENSION_MATCH"+"_TRUE", END.label)
    graph.attach(label+"_DIMENSION_MATCH"+"_FALSE", END.label)
    graph.attach(
        label+"_TRUE",
        label+"_UNIT_COMPARISON",
        summary=f"Compares how similar the units of {inputs[0]} and {inputs[1]} are.",
        details=f"Compares how similar the units of {inputs[0]} and {inputs[1]} are.",
        evaluate=unit_comparison
    )
    graph.attach(
        label+"_UNIT_COMPARISON",
        label+"_UNIT_COMPARISON"+"_IDENTICAL",
        summary=f"The units of quantities {inputs[0]} and {inputs[1]} are identical.",
        details=f"The units of quantities {inputs[0]} and {inputs[1]} are identical.",
        feedback_string_generator=physical_quantity_feedback_string_generators["MATCHES"]("UNIT_COMPARISON_IDENTICAL")
    )
    graph.attach(
        label+"_UNIT_COMPARISON",
        label+"_UNIT_COMPARISON"+"_SIMILAR",
        summary=f"The units of quantities {inputs[0]} and {inputs[1]} are similar.",
        details=f"The units of quantities {inputs[0]} and {inputs[1]} are similar.",
        feedback_string_generator=physical_quantity_feedback_string_generators["MATCHES"]("UNIT_COMPARISON_SIMILAR")
    )
    graph.attach(
        label+"_UNIT_COMPARISON",
        label+"_UNIT_COMPARISON"+"_PREFIX_IS_LARGE",
        summary=f"The units of {inputs[0]} are much greater than the units of {inputs[1]}.",
        details=f"The units of {inputs[0]} are at least 1000 times greater than the units of {inputs[1]}.",
        feedback_string_generator=physical_quantity_feedback_string_generators["MATCHES"]("PREFIX_IS_LARGE")
    )
    graph.attach(label+"_UNIT_COMPARISON"+"_PREFIX_IS_LARGE", END.label)
    graph.attach(
        label+"_UNIT_COMPARISON",
        label+"_UNIT_COMPARISON"+"_PREFIX_IS_SMALL",
        summary=f"The units of {inputs[0]} are much smaller than the units of {inputs[1]}.",
        details=f"The units of {inputs[0]} are at least 1000 times smaller than the units of {inputs[1]}.",
        feedback_string_generator=physical_quantity_feedback_string_generators["MATCHES"]("PREFIX_IS_SMALL")
    )
    graph.attach(label+"_UNIT_COMPARISON"+"_PREFIX_IS_SMALL", END.label)

    return graph


def feedback_procedure_generator(parameters_dict):
    graphs = dict()
    for (label, criterion) in parameters_dict["criteria"].items():
        graph_templates = {
            "matches": criterion_match_node,
            ">": greater_than_node,
            ">=": greater_than_or_equal_node,
            "<": less_than_node,
            "<=": less_than_or_equal_node,
        }
        graph_template = graph_templates.get(criterion.label.strip(), criterion_match_node)
        graph = graph_template(criterion, parameters_dict)
        for evaluation in graph.evaluations.values():
            if evaluation.label in parameters_dict.get("disabled_evaluation_nodes", set()):
                evaluation.replacement = CriteriaGraph.END
        graphs.update({label: graph})
    return graphs

def preprocess_unicode(expr):
    unicode_transforms = transform_unicode_greek_symbols(expr)
    expr = substitute(expr, unicode_transforms)
    return expr

def expression_preprocess(name, expr, parameters):
    if parameters.get("strictness", "natural") == "legacy":
        prefix_data = {(p[0], p[1], tuple(), p[3]) for p in set_of_SI_prefixes}
        prefixes = []
        for prefix in prefix_data:
            prefixes = prefixes+[prefix[0]] + list(prefix[-1])
        prefix_short_forms = [prefix[1] for prefix in prefix_data]
        unit_data = set_of_SI_base_unit_dimensions \
            | set_of_derived_SI_units_in_SI_base_units \
            | set_of_common_units_in_SI \
            | set_of_very_common_units_in_SI \
            | set_of_imperial_units
        unit_long_forms = prefixes
        for unit in unit_data:
            unit_long_forms = unit_long_forms+[unit[0]] + list(unit[-2]) + list(unit[-1])
        unit_long_forms = "("+"|".join(unit_long_forms)+")"
        # Rewrite any expression on the form "*UNIT" (but not "**UNIT") as " UNIT"
        # Example: "newton*metre" ---> "newton metre"
        search_string = r"(?<!\*)\* *"+unit_long_forms
        match_content = re.search(search_string, expr[1:])
        while match_content is not None:
            expr = expr[0:match_content.span()[0]+1]+match_content.group().replace("*", " ")+expr[match_content.span()[1]+1:]
            match_content = re.search(search_string, expr[1:])
        prefixes = "("+"|".join(prefixes)+")"
        # Rewrite any expression on the form "PREFIX UNIT" as "PREFIXUNIT"
        # Example: "kilo metre" ---> "kilometre"
        search_string = prefixes+" "+unit_long_forms
        match_content = re.search(search_string, expr)
        while match_content is not None:
            expr = expr[0:match_content.span()[0]]+" "+"".join(match_content.group().split())+expr[match_content.span()[1]:]
            match_content = re.search(search_string, expr)
        unit_short_forms = [u[1] for u in unit_data]
        short_forms = "("+"|".join(list(set(prefix_short_forms+unit_short_forms)))+")"
        # Add space before short forms of prefixes or unit names if they are preceded by numbers or multiplication
        # Example: "100Pa" ---> "100 Pa"
        search_string = r"[0-9\*\(\)]"+short_forms
        match_content = re.search(search_string, expr)
        while match_content is not None:
            expr = expr[0:match_content.span()[0]+1]+" "+expr[match_content.span()[0]+1:]
            match_content = re.search(search_string, expr)
        # Remove space after prefix short forms if they are preceded by numbers, multiplication or space
        # Example: "100 m Pa" ---> "100 mPa"
        prefix_short_forms = "("+"|".join(prefix_short_forms)+")"
        search_string = r"[0-9\*\(\) ]"+prefix_short_forms+" "
        match_content = re.search(search_string, expr)
        while match_content is not None:
            expr = expr[0:match_content.span()[0]+1]+match_content.group()[0:-1]+expr[match_content.span()[1]:]
            match_content = re.search(search_string, expr)
        # Remove multiplication and space after prefix short forms if they are preceded by numbers, multiplication or space
        # Example:  "100 m* Pa" ---> "100 mPa"
        search_string = r"[0-9\*\(\) ]"+prefix_short_forms+"\* "
        match_content = re.search(search_string, expr)
        while match_content is not None:
            expr = expr[0:match_content.span()[0]+1]+match_content.group()[0:-2]+expr[match_content.span()[1]:]
            match_content = re.search(search_string, expr)
        # Replace multiplication followed by space before unit short forms with only spaces if they are preceded by numbers or space
        # Example:  "100* Pa" ---> "100 Pa"
        unit_short_forms = "("+"|".join(unit_short_forms)+")"
        search_string = r"[0-9\(\) ]\* "+unit_short_forms
        match_content = re.search(search_string, expr)
        while match_content is not None:
            expr = expr[0:match_content.span()[0]]+match_content.group().replace("*", " ")+expr[match_content.span()[1]:]
            match_content = re.search(search_string, expr)


    expr = preprocess_unicode(expr)
    success = True
    return success, expr, None


def feedback_string_generator(tags, graph, parameters_dict):
    strings = dict()
    for tag in tags:
        # feedback_string = graph.criteria[tag].feedback_string_generator(inputs)
        feedback_string = "PLACEHOLDER"
        if feedback_string is not None:
            strings.update({tag: feedback_string})
    return


def parsing_parameters_generator(params, unsplittable_symbols=tuple(), symbol_assumptions=tuple()):
    parsing_parameters = create_sympy_parsing_params(params)
    parsing_parameters.update({
        "strictness": params.get("strictness", "natural"),
        "rtol": float(params.get("rtol", 0)),
        "atol": float(params.get("atol", 0)),
    })
    return parsing_parameters


# CONSIDER: Move these to separate file so that they can be shared with
# the preview function implementation (or move preview implementation here)
default_parameters = deepcopy(symbolic_default_parameters)
default_parameters.update(
    {
        "physical_quantity": True,
        "strictness": "natural",
        "units_string": "SI common imperial",
    }
)


default_criteria = ["response matches answer"]


context = {
    "expression_preview": preview_function,
    "generate_criteria_parser": generate_criteria_parser,
    "expression_preprocess": expression_preprocess,
    "expression_parse": parse_quantity,
    "default_parameters": default_parameters,
    "default_criteria": default_criteria,
    "feedback_procedure_generator": feedback_procedure_generator,
    "feedback_string_generator": feedback_string_generator,
    "parsing_parameters_generator": parsing_parameters_generator,
}
