from lambdafeedback.criteria import CriteriaGraph
from lambdafeedback.expression_parsing import generate_arbitrary_number_pattern_matcher

from ....feedback.symbolic import feedback_generators as symbolic_feedback_string_generators
from ....feedback.syntactical_forms import PATTERNS as syntactical_forms


def written_as_known_form(string, name):
    def find_form(unused_input):
        forms = set()
        for form_label in syntactical_forms.keys():
            if syntactical_forms[form_label].matcher(string) is True:
                forms.add(form_label)
        if len(forms) > 0:
            return {name+"_WRITTEN_AS_"+form_label: None for form_label in forms}
        else:
            return {name+"_WRITTEN_AS_UNKNOWN": None}
    return find_form


def compare_to_form(string, form_label, label):
    def inner(unused_input):
        result = dict()
        if syntactical_forms[form_label].matcher(string) is True:
            result.update({label+"_TRUE": None})
        else:
            result.update({label+"_FALSE": None})
        return result
    return inner


def response_written_as_answer(response, answer, label):
    def inner(unused_input):
        matcher = generate_arbitrary_number_pattern_matcher(answer)
        if matcher(response):
            return {label+"_TRUE": None}
        else:
            return {label+"_FALSE": None}
    return inner


def _add_known_form_nodes(graph, label, lhs, rhs, response):
    """For each known form, adds nodes that check if `lhs` is written in that form when `rhs` is."""
    for form_label in syntactical_forms.keys():
        graph.attach_new_criterion(
            str(rhs)+"_WRITTEN_AS_KNOWN_FORM",
            str(rhs)+"_WRITTEN_AS_"+form_label,
            summary=str(rhs)+" in written in "+syntactical_forms[form_label].name+" form.",
            details=str(rhs)+" in written in "+syntactical_forms[form_label].name+" form.",
            feedback_string_generator=symbolic_feedback_string_generators["WRITTEN_AS"](form_label),
        )
        graph.attach_new_evaluation(
            str(rhs)+"_WRITTEN_AS_"+form_label,
            str(lhs)+"_COMPARE_FORM_TO_"+form_label,
            summary="Is "+str(lhs)+" written in "+syntactical_forms[form_label].name+" form.",
            details="Checks if "+str(lhs)+" is written in "+syntactical_forms[form_label].name+" form.",
            evaluate=compare_to_form(response, form_label, label),
            sufficiencies={str(rhs)+"_WRITTEN_AS_"+form_label}
        )
        graph.attach(str(lhs)+"_COMPARE_FORM_TO_"+form_label, label+"_TRUE")
        graph.attach(str(lhs)+"_COMPARE_FORM_TO_"+form_label, label+"_FALSE")


def criterion_written_as_node(criterion, parameters_dict, label=None):
    if label is None:
        label = criterion.content_string()

    graph = CriteriaGraph(label)
    graph.add_end_node()

    lhs = criterion.children[0].content_string()
    rhs = criterion.children[1].content_string()

    if set([lhs, rhs]) != set(["response", "answer"]):
        return graph

    # TODO: Make a version that can compare the forms of any two reserved expressions
    answer = parameters_dict["reserved_expressions_strings"]["task"]["answer"]
    response = parameters_dict["reserved_expressions_strings"]["learner"]["response"]

    graph.add_evaluation_node(
        str(rhs)+"_WRITTEN_AS_KNOWN_FORM",
        summary=label,
        details=f"Checks if {rhs} is written in a known form.",
        evaluate=written_as_known_form(answer, rhs)
    )
    graph.attach_new_criterion(
        str(rhs)+"_WRITTEN_AS_KNOWN_FORM",
        str(rhs)+"_WRITTEN_AS_UNKNOWN",
        summary=str(rhs)+" is not written in a known form.",
        details=str(rhs)+" is not written in a known form.",
        feedback_string_generator=symbolic_feedback_string_generators["WRITTEN_AS"]("UNKNOWN")
    )
    graph.attach_new_evaluation(
        str(rhs)+"_WRITTEN_AS_UNKNOWN",
        label,
        summary="Is "+str(lhs)+" written in the same form as "+str(rhs)+".",
        details="Checks if "+str(lhs)+" is written in the same form as "+str(rhs)+".",
        evaluate=response_written_as_answer(response, answer, label),
        sufficiencies={str(rhs)+"_WRITTEN_AS_UNKNOWN"}
    )
    graph.attach_new_criterion(
        label,
        label+"_TRUE",
        summary=str(rhs)+" written in the same form as "+str(rhs)+".",
        details=str(rhs)+" written in the same form as "+str(rhs)+".",
        feedback_string_generator=symbolic_feedback_string_generators["SYNTACTICAL_EQUIVALENCE"]("TRUE")
    )
    graph.attach_new_criterion(
        label,
        label+"_FALSE",
        summary=str(rhs)+" written in the same form as "+str(rhs)+".",
        details=str(rhs)+" written in the same form as "+str(rhs)+".",
        feedback_string_generator=symbolic_feedback_string_generators["SYNTACTICAL_EQUIVALENCE"]("FALSE")
    )
    _add_known_form_nodes(graph, label, lhs, rhs, response)
    return graph
