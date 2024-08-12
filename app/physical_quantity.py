# -------
# IMPORTS
# -------

from copy import deepcopy
from .physical_quantity_utilities import (
    PhysicalQuantity,
    QuantityTags,
    SLR_quantity_parser,
    SLR_quantity_parsing
)
from .quantity_comparison_preview import preview_function
from .feedback.quantity_comparison import feedback_string_generators as physical_quantity_feedback_string_generators
from .expression_utilities import (
    substitute_input_symbols,
    create_sympy_parsing_params,
    compute_relative_tolerance_from_significant_decimals,
    parse_expression
)
from .physical_quantity_utilities import (
    units_sets_dictionary,
    set_of_SI_prefixes,
    set_of_SI_base_unit_dimensions,
    conversion_to_base_si_units
)
from .slr_parsing_utilities import create_node, infix, operate, group, catch_undefined, SLR_Parser
from sympy import Symbol

from .criteria_graph_utilities import CriteriaGraph


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

    def matches(inputs):
        if isinstance(inputs[0], PhysicalQuantity) and isinstance(inputs[1], PhysicalQuantity):
            value0 = inputs[0].standard_value
            unit0 = inputs[0].standard_unit
            value1 = inputs[1].standard_value
            unit1 = inputs[1].standard_unit
            value_match = False
            unit_match = False
            if value0 is None and value1 is None:
                value_match = True
            elif value0 is not None and value1 is not None:
                value_match = symbolic_comparison(value0, value1, parameters)["is_correct"]
            if unit0 is None and unit0 is None:
                unit_match = True
            elif unit0 is not None and unit1 is not None:
                unit_match = bool((unit0 - unit1).simplify() == 0)
            return value_match and unit_match
        elif isinstance(inputs[0], Basic) and isinstance(inputs[1], Basic):
            if inputs[0] is not None and inputs[1] is not None:
                dimension_match = bool((inputs[0] - inputs[1]).cancel().simplify().simplify() == 0)  # TODO: Make separate function for checking equality of expressions that can be parsed
            else:
                dimension_match = False
            return dimension_match
        return False

    def compare(comparison):
        comparison_dict = {
            "=": lambda inputs: bool((inputs[0] - inputs[1]).cancel().simplify().simplify() == 0),
            "<=": lambda inputs: bool((inputs[0] - inputs[1]).cancel().simplify().simplify() <= 0),
            ">=": lambda inputs: bool((inputs[0] - inputs[1]).cancel().simplify().simplify() >= 0),
            "<": lambda inputs: bool((inputs[0] - inputs[1]).cancel().simplify().simplify() < 0),
            ">": lambda inputs: bool((inputs[0] - inputs[1]).cancel().simplify().simplify() > 0),
        }

        def wrap(inputs):
            if inputs[0] is not None and inputs[1] is not None:
                return comparison_dict[comparison](inputs)
            else:
                return False
        return wrap

    criteria_operations = {
        "and": lambda x: x[0] and x[1],
        "not": lambda x: not x[0],
        "has": lambda x: x[0] is not None,
        "unit": lambda quantity: quantity[0].unit,
        "expanded_unit": lambda quantity: quantity[0].expanded_unit,
        "base_unit": lambda quantity: quantity[0].standard_unit,
        "value": lambda quantity: quantity[0].value,
        "is_number": lambda value: value[0] is not None and value[0].tags == {QuantityTags.N},
        "is_expression": lambda value: value[0] is not None and QuantityTags.V in value[0].tags,
        "matches": matches,
        "dimension": lambda quantity: quantity[0].dimension,
        "=": compare("="),
        "<=": compare("<="),
        ">=": compare(">="),
        "<": compare("<"),
        ">": compare(">"),
    }

    token_list = [
        (start_symbol,   start_symbol),
        (end_symbol,     end_symbol),
        (null_symbol,    null_symbol),
        (" *BOOL *",     "BOOL"),
        (" *UNIT *",     "UNIT"),
        (" *VALUE *",    "VALUE"),
        (" *QUANTITY *", "QUANTITY"),
        (" *DIMENSION *", "DIMENSION"),
        ("\( *",         "START_DELIMITER"),
        (" *\)",         "END_DELIMITER"),
        ("response",     "QUANTITY"),
        ("answer",       "QUANTITY"),
        ("INPUT",        "INPUT", catch_undefined),
    ]
    token_list += [(" *"+x+" *", " "+x+" ") for x in criteria_operations.keys()]

    productions = [
        ("START",     "BOOL", create_node),
        ("BOOL",      "BOOL and BOOL", infix),
        ("BOOL",      "UNIT matches UNIT", infix),
        ("BOOL",      "VALUE matches VALUE", infix),
        ("BOOL",      "QUANTITY matches QUANTITY", infix),
        ("BOOL",      "DIMENSION matches DIMENSION", infix),
        ("BOOL",      "not(BOOL)", operate(1)),
        ("BOOL",      "has(UNIT)", operate(1)),
        ("BOOL",      "has(VALUE)", operate(1)),
        ("BOOL",      "is_number(VALUE)", operate(1)),
        ("BOOL",      "is_expression(VALUE)", operate(1)),
        ("BOOL",      "UNIT=UNIT", infix),
        ("BOOL",      "UNIT<=UNIT", infix),
        ("BOOL",      "UNIT>=UNIT", infix),
        ("BOOL",      "UNIT<UNIT", infix),
        ("BOOL",      "UNIT>UNIT", infix),
        ("UNIT",      "unit(QUANTITY)", operate(1)),
        ("UNIT",      "base_unit(QUANTITY)", operate(1)),
        ("UNIT",      "expanded_unit(QUANTITY)", operate(1)),
        ("UNIT",      "INPUT UNIT", group(2, empty=True)),
        ("UNIT",      "UNIT INPUT", group(2, empty=True)),
        ("VALUE",     "value(QUANTITY)", operate(1)),
        ("QUANTITY",  "INPUT", create_node),
        ("DIMENSION", "dimension(QUANTITY)", operate(1)),
    ]

    return SLR_Parser(token_list, productions, start_symbol, end_symbol, null_symbol)


def criterion_match_node(criterion, parameters, label=None):
    graph = CriteriaGraph(label)
    END = CriteriaGraph.END
    graph.add_node(END)
    reserved_expressions = parameters["reserved_expressions"].items()
    parsing_params = deepcopy(parameters["parsing_parameters"])
    if parameters.get('atol',0) == 0 and parameters.get('rtol',0) == 0:
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

    def is_equal(lhs, rhs, substitutions, rtol=0, atol=0):
        none_placeholder = Symbol('NONE_PLACEHOLDER')
        local_substitutions = [(key, none_placeholder) if expr is None else (key, expr) for (key, expr) in substitutions]
        expr0 = lhs.subs(local_substitutions)
        expr1 = rhs.subs(local_substitutions)
        return bool((expr0-expr1).cancel().simplify().simplify() == 0)

    def is_greater_than(lhs, rhs, substitutions):
        none_placeholder = Symbol('NONE_PLACEHOLDER')
        local_substitutions = [(key, none_placeholder) if expr is None else (key, expr) for (key, expr) in substitutions]
        expr0 = lhs.subs(local_substitutions)
        expr1 = rhs.subs(local_substitutions)
        return bool((expr0-expr1).cancel().simplify().simplify() > 0)

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
                    ans = parameters["reserved_expressions"]["answer"]["standard"]["value"]
                    res = parameters["reserved_expressions"]["response"]["standard"]["value"]
                if (ans is not None and ans.is_constant()) and (res is not None and res.is_constant()):
                    if parsing_params.get('rtol', 0) > 0:
                        value_match = bool(abs(float((ans-res)/ans)) < parsing_params['rtol'])
                    elif parsing_params.get('atol', 0) > 0:
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
        }
        graph_template = graph_templates.get(criterion.label.strip(), criterion_match_node)
        graph = graph_template(criterion, parameters_dict)
        for evaluation in graph.evaluations.values():
            if evaluation.label in parameters_dict.get("disabled_evaluation_nodes", set()):
                evaluation.replacement = CriteriaGraph.END
        graphs.update({label: graph})
    return graphs


def expression_preprocess(expr, name, parameters):
    prefixes = set(x[0] for x in set_of_SI_prefixes)
    fundamental_units = set(x[0] for x in set_of_SI_base_unit_dimensions)
    units_string = parameters.get("units_string", "SI common imperial")
    valid_units = set()
    for key in units_sets_dictionary.keys():
        if key in units_string:
            for unit in units_sets_dictionary[key]:
                valid_units = valid_units.union(set((unit[0], unit[1])+unit[3]+unit[4]))
    dimensions = set(x[2] for x in set_of_SI_base_unit_dimensions)
    unsplittable_symbols = list(prefixes|fundamental_units|valid_units|dimensions)
    preprocess_parameters = deepcopy(parameters)
    # TODO: find better way to add reserved keywords for physical quantity criteria added to prevent preprocessing to mangle them
    preprocess_parameters.update({"reserved_keywords": preprocess_parameters.get("reserved_keywords",[])+unsplittable_symbols+['matches']})
    expr = substitute_input_symbols(expr.strip(), preprocess_parameters)[0]
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


context = {
    "expression_preview": preview_function,
    "generate_criteria_parser": generate_criteria_parser,
    "expression_preprocess": expression_preprocess,
    "expression_parse": parse_quantity,
    "default_criteria": {"response matches answer"},
    "feedback_procedure_generator": feedback_procedure_generator,
    "feedback_string_generator": feedback_string_generator,
    "parsing_parameters_generator": create_sympy_parsing_params,
}