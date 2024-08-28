import re
from ..feedback.symbolic import feedback_generators as symbolic_feedback_generators
from .criteria_graph_utilities import CriteriaGraph

is_number_regex = '(-?(0|[1-9]\d*)?(\.\d+)?(?<=\d)(e-?(0|[1-9]\d*))?)'


def is_number(string):
    match_content = re.fullmatch(is_number_regex, string)
    return match_content is not None and len(match_content.group(0)) > 0


def is_complex_number_on_cartesian_form(string):
    string = "".join(string.split())
    result = re.fullmatch(is_number_regex+"?\+?"+is_number_regex+"?\*?I?", string)
    return result is not None


def is_complex_number_on_exponential_form(string):
    string = "".join(string.split())
    result = re.fullmatch(is_number_regex+"?\*?(E\^|E\*\*|exp)\(?"+is_number_regex+"*\*?I\)?", string)
    return result is not None


patterns = {
    "CARTESIAN": {
        "matcher": is_complex_number_on_cartesian_form,
        "summary": lambda criterion, parameters_dict: str(criterion.children[0].content_string())+" and "+str(criterion.children[1].content_string())+" are both complex numbers written on cartesian form",
        "details": lambda criterion, parameters_dict: str(criterion.children[0].content_string())+" and "+str(criterion.children[1].content_string())+" are both complex numbers written on cartesian form, i.e. $a+bi$.",
    },
    "EXPONENTIAL": {
        "matcher": is_complex_number_on_exponential_form,
        "summary": lambda criterion, parameters_dict: str(criterion.children[0].content_string())+" and "+str(criterion.children[1].content_string())+" are both complex numbers written on exponential form",
        "details": lambda criterion, parameters_dict: str(criterion.children[0].content_string())+" and "+str(criterion.children[1].content_string())+" are both complex numbers written on exponential form, i.e. $a exp(bi)$.",
    },
}


def attach_form_criteria(graph, attachment_node, criterion, parameters_dict, form_label):
    graph.attach(
        attachment_node,
        attachment_node+"_"+form_label,
        summary=patterns[form_label]["summary"](criterion, parameters_dict),
        details=patterns[form_label]["details"](criterion, parameters_dict),
        feedback_string_generator=symbolic_feedback_generators["SAME_FORM"](form_label),
    )
    graph.attach(attachment_node+"_"+form_label, CriteriaGraph.END.label)


def response_and_answer_on_same_form(label, parameters_dict):
    local_answer = parameters_dict["reserved_expressions_strings"]["task"]["answer"]
    local_response = parameters_dict["reserved_expressions_strings"]["learner"]["response"]
    matches_found = dict()

    def inner(unused_input):
        for form_label in patterns.keys():
            if patterns[form_label]["matcher"](local_answer) and patterns[form_label]["matcher"](local_response):
                matches_found.update({label+"_"+form_label: None})
        if len(matches_found) == 0:
            matches_found.update({label+"_UNKNOWN": None})
        return matches_found
    return inner
