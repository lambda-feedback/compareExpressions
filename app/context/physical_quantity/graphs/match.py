from lambdafeedback.criteria import CriteriaGraph
from lambdafeedback.expression_parsing import compute_relative_tolerance_from_significant_decimals

from ....feedback.physical_quantity import feedback_string_generators as physical_quantity_feedback_string_generators
from ...graph_helpers import attach_terminal_criterion, outcome_tag
from ..comparison import comparison_function, is_proportional, parse_criterion_sides

is_equal = comparison_function("=")


def _tolerances(parameters):
    """`(rtol, atol)`, with `rtol` taken from the significant figures of the answer if no tolerance is given."""
    rtol = parameters["parsing_parameters"]["rtol"]
    atol = parameters["parsing_parameters"]["atol"]
    if parameters.get('atol', 0) == 0 and parameters.get('rtol', 0) == 0:
        ans = parameters["reserved_expressions"]["answer"]["quantity"].value
        if ans is not None:
            rtol = compute_relative_tolerance_from_significant_decimals(ans.content_string())
    return rtol, atol


def _missing_or_unexpected(parameters, label, lhs_string, rhs_string):
    """Tag for a response missing a value or unit that the answer has (or vice versa), otherwise None."""
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
    return None


def _within_tolerance(parameters, lhs_string, rhs_string, rtol, atol):
    """Whether the standard values of the response and answer are within the numerical tolerances."""
    value_match = False
    # TODO: better analysis of where `answer` is found in the criteria so that
    #       numerical tolerances can be applied appropriately
    if rtol > 0 or atol > 0:
        if (lhs_string == 'answer' and rhs_string == 'response') or (lhs_string == 'response' and rhs_string == 'answer'):
            ans = parameters["reserved_expressions"]["answer"]["standard"]["value"].simplify()
            res = parameters["reserved_expressions"]["response"]["standard"]["value"].simplify()
        if (ans is not None and ans.is_constant()) and (res is not None and res.is_constant()):
            if rtol > 0 and (ans != 0):
                value_match = bool(abs(float((ans-res)/ans)) < rtol)
            elif atol > 0 or (ans == 0):
                answer_unit_factor = float(parameters["reserved_expressions"]["answer"]["quantity"].unit_factor)
                value_match = bool(abs(float(ans-res)) < atol*answer_unit_factor)
    return value_match


def _quantity_match(parameters, label, lhs, rhs, lhs_string, rhs_string, rtol, atol):
    reserved_expressions = parameters["reserved_expressions"].items()

    def quantity_match(_response):
        missing_or_unexpected = _missing_or_unexpected(parameters, label, lhs_string, rhs_string)
        if missing_or_unexpected is not None:
            return missing_or_unexpected

        substitutions = [(key, expr["standard"]["value"]) for (key, expr) in reserved_expressions]
        value_match = is_equal(lhs, rhs, substitutions)
        if value_match is False:
            value_match = _within_tolerance(parameters, lhs_string, rhs_string, rtol, atol)

        substitutions = [(key, expr["standard"]["unit"]) for (key, expr) in reserved_expressions]
        unit_match = is_equal(lhs, rhs, substitutions)

        return outcome_tag(label, value_match is True and unit_match is True, {"lhs": lhs_string, "rhs": rhs_string})
    return quantity_match


def _dimension_match(parameters, label, lhs, rhs, lhs_string, rhs_string):
    reserved_expressions = parameters["reserved_expressions"].items()

    def dimension_match(_response):
        substitutions = [(key, expr["dimension"]) for (key, expr) in reserved_expressions]
        dimension_match, _ = is_proportional(lhs, rhs, substitutions)
        return outcome_tag(label+"_DIMENSION_MATCH", dimension_match is True, {"lhs": lhs_string, "rhs": rhs_string})
    return dimension_match


def _unit_comparison(parameters, label, lhs, rhs):
    reserved_expressions = parameters["reserved_expressions"].items()

    def unit_comparison(_response):
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
    return unit_comparison


def _add_match_nodes(graph, END, label, inputs, quantity_match, dimension_match, unit_comparison):
    graph.add_evaluation_node(
        label,
        summary=f"Do the quantities {inputs[0]} and {inputs[1]} match?",
        details=f"Converts {inputs[0]} and {inputs[1]} match to a common set of base units and compares their values.",
        evaluate=quantity_match
    )
    graph.attach_new_criterion(
        label,
        label+"_TRUE",
        summary=f"The quantities {inputs[0]} and {inputs[1]} match.",
        details=f"The quantities {inputs[0]} and {inputs[1]} match.",
        feedback_string_generator=physical_quantity_feedback_string_generators["MATCHES"]("QUANTITY_MATCH")
    )
    graph.attach_new_criterion(
        label,
        label+"_FALSE",
        summary=f"The quantities {inputs[0]} and {inputs[1]} does not match.",
        details=f"The quantities {inputs[0]} and {inputs[1]} does not match.",
        feedback_string_generator=physical_quantity_feedback_string_generators["MATCHES"]("QUANTITY_MISMATCH")
    )
    attach_terminal_criterion(
        graph,
        label,
        label+"_MISSING_VALUE",
        END,
        summary="The response is missing a value.",
        details="The response is missing a value.",
        feedback_string_generator=physical_quantity_feedback_string_generators["MATCHES"]("MISSING_VALUE")
    )
    attach_terminal_criterion(
        graph,
        label,
        label+"_UNEXPECTED_VALUE",
        END,
        summary="The response is expected only have unit(s), no value.",
        details="The response is expected only have unit(s), no value.",
        feedback_string_generator=physical_quantity_feedback_string_generators["MATCHES"]("UNEXPECTED_VALUE")
    )
    attach_terminal_criterion(
        graph,
        label,
        label+"_MISSING_UNIT",
        END,
        summary="The response is missing unit(s).",
        details="The response is missing unit(s).",
        feedback_string_generator=physical_quantity_feedback_string_generators["MATCHES"]("MISSING_UNIT")
    )
    attach_terminal_criterion(
        graph,
        label,
        label+"_UNEXPECTED_UNIT",
        END,
        summary="The response is expected to be a value without unit(s).",
        details="The response is expected to be a value without unit(s).",
        feedback_string_generator=physical_quantity_feedback_string_generators["MATCHES"]("UNEXPECTED_UNIT")
    )
    graph.attach_new_evaluation(
        label+"_FALSE",
        label+"_DIMENSION_MATCH",
        summary=f"Do the dimensions of {inputs[0]} and {inputs[1]} match?",
        details=f"Do the dimensions of {inputs[0]} and {inputs[1]} match?",
        evaluate=dimension_match
    )
    attach_terminal_criterion(
        graph,
        label+"_DIMENSION_MATCH",
        label+"_DIMENSION_MATCH"+"_TRUE",
        END,
        summary=f"The quantities {inputs[0]} and {inputs[1]} have the same dimensions.",
        details=f"The quantities {inputs[0]} and {inputs[1]} have the same dimensions.",
        feedback_string_generator=physical_quantity_feedback_string_generators["MATCHES"]("DIMENSION_MATCH")
    )
    attach_terminal_criterion(
        graph,
        label+"_DIMENSION_MATCH",
        label+"_DIMENSION_MATCH"+"_FALSE",
        END,
        summary=f"The quantities {inputs[0]} and {inputs[1]} have different dimensions.",
        details=f"The quantities {inputs[0]} and {inputs[1]} have different dimensions.",
        feedback_string_generator=physical_quantity_feedback_string_generators["MATCHES"]("DIMENSION_MISMATCH")
    )
    graph.attach_new_evaluation(
        label+"_TRUE",
        label+"_UNIT_COMPARISON",
        summary=f"Compares how similar the units of {inputs[0]} and {inputs[1]} are.",
        details=f"Compares how similar the units of {inputs[0]} and {inputs[1]} are.",
        evaluate=unit_comparison
    )
    graph.attach_new_criterion(
        label+"_UNIT_COMPARISON",
        label+"_UNIT_COMPARISON"+"_IDENTICAL",
        summary=f"The units of quantities {inputs[0]} and {inputs[1]} are identical.",
        details=f"The units of quantities {inputs[0]} and {inputs[1]} are identical.",
        feedback_string_generator=physical_quantity_feedback_string_generators["MATCHES"]("UNIT_COMPARISON_IDENTICAL")
    )
    graph.attach_new_criterion(
        label+"_UNIT_COMPARISON",
        label+"_UNIT_COMPARISON"+"_SIMILAR",
        summary=f"The units of quantities {inputs[0]} and {inputs[1]} are similar.",
        details=f"The units of quantities {inputs[0]} and {inputs[1]} are similar.",
        feedback_string_generator=physical_quantity_feedback_string_generators["MATCHES"]("UNIT_COMPARISON_SIMILAR")
    )
    attach_terminal_criterion(
        graph,
        label+"_UNIT_COMPARISON",
        label+"_UNIT_COMPARISON"+"_PREFIX_IS_LARGE",
        END,
        summary=f"The units of {inputs[0]} are much greater than the units of {inputs[1]}.",
        details=f"The units of {inputs[0]} are at least 1000 times greater than the units of {inputs[1]}.",
        feedback_string_generator=physical_quantity_feedback_string_generators["MATCHES"]("PREFIX_IS_LARGE")
    )
    attach_terminal_criterion(
        graph,
        label+"_UNIT_COMPARISON",
        label+"_UNIT_COMPARISON"+"_PREFIX_IS_SMALL",
        END,
        summary=f"The units of {inputs[0]} are much smaller than the units of {inputs[1]}.",
        details=f"The units of {inputs[0]} are at least 1000 times smaller than the units of {inputs[1]}.",
        feedback_string_generator=physical_quantity_feedback_string_generators["MATCHES"]("PREFIX_IS_SMALL")
    )


def criterion_match_node(criterion, parameters, label=None):
    graph = CriteriaGraph(label)
    END = graph.add_end_node()
    rtol, atol = _tolerances(parameters)

    if label is None:
        label = criterion.content_string()

    inputs = criterion.children
    lhs_string, rhs_string, lhs, rhs = parse_criterion_sides(criterion, parameters)

    _add_match_nodes(
        graph,
        END,
        label,
        inputs,
        quantity_match=_quantity_match(parameters, label, lhs, rhs, lhs_string, rhs_string, rtol, atol),
        dimension_match=_dimension_match(parameters, label, lhs, rhs, lhs_string, rhs_string),
        unit_comparison=_unit_comparison(parameters, label, lhs, rhs),
    )
    return graph
