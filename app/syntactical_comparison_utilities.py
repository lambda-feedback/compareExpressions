import re
from .feedback.symbolic_comparison import feedback_generators as symbolic_feedback_generators
from .criteria_graph_utilities import CriteriaGraph

is_nonnegative_number_regex = '((0|[1-9]\d*)?(\.\d+)?(?<=\d)(e-?(0|[1-9]\d*))?)'
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

def escape_regex_reserved_characters(string):
    list = '+*?^$.[]{}()|/'
    string = string.replace('\\','\\\\')
    for s in list:
        string = string.replace(s,'\\'+s)
    return string

#def generate_arbitrary_number_pattern_matcher(string):
#    non_numbers = []
#    number = re.search(is_number_regex, string)
#    start = 0
#    end = 0
#    offset = 0
#    while number is not None:
#        start, end = number.span()
#        start += offset
#        end += offset
#        non_number = escape_regex_reserved_characters(string[offset:start])
#        non_number = ''.join(non_number.split())
#        non_numbers.append(non_number)
#        offset = end
#        number = re.search(is_number_regex, string[offset:])
#    non_numbers.append(string[offset:])
#    pattern = is_number_regex.join(non_numbers)
#    def matcher(comp_string):
#        comp_string = ''.join(comp_string.split())
#        result = re.fullmatch(pattern, comp_string)
#        return result is not None
#    return matcher

def generate_arbitrary_number_pattern_matcher(string):
    non_numbers = []
    number_pattern = '(\\('+is_number_regex+'\\))'
    nonneg_number_pattern = is_nonnegative_number_regex
    #number_pattern = '('+'(\\\\('+is_number_regex+'\\\\))'+'|'+is_nonnegative_number_regex+')'
    full_pattern = '('+number_pattern+'|'+nonneg_number_pattern+')'
    number = re.search(number_pattern, string)
    nonneg_number = re.search(nonneg_number_pattern, string)
    start = 0
    end = 0
    offset = 0
    while (number is not None) or (nonneg_number is not None):
        start_number = len(string)
        end_number = len(string)
        start_nonneg_number = len(string)
        end_nonneg_number = len(string)
        if number is not None:
            start_number, end_number = number.span()
        if nonneg_number is not None:
            start_nonneg_number, end_nonneg_number = nonneg_number.span()
        if start_number < start_nonneg_number:
            start, end = number.span()
        else:
            start, end = nonneg_number.span()
        start += offset
        end += offset
        non_number = escape_regex_reserved_characters(string[offset:start])
        if len(non_number) > 0:
            non_number = '('+non_number+')'
        non_number = ''.join(non_number.split())
        non_numbers.append(non_number)
        offset = end
        number = re.search(number_pattern, string[offset:])
        nonneg_number = re.search(nonneg_number_pattern, string[offset:])
    non_numbers.append(string[offset:])
    pattern = full_pattern.join(non_numbers)
    def matcher(comp_string):
        comp_string = ''.join(comp_string.split())
        result = re.fullmatch(pattern, comp_string)
        return result is not None
    return matcher

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
    local_answer = parameters_dict["original_input"]["answer"]
    local_response = parameters_dict["original_input"]["response"]
    matches_found = set()

    def inner(unused_input):
        for form_label in patterns.keys():
            if patterns[form_label]["matcher"](local_answer) and patterns[form_label]["matcher"](local_response):
                matches_found.add(label+"_"+form_label)
        if len(matches_found) == 0:
            matches_found.add(label+"_UNKNOWN")
        return matches_found
    return inner


def written_as_answer(label, parameters_dict):
    local_answer = parameters_dict["original_input"]["answer"]
    local_response = parameters_dict["original_input"]["response"]
    matches_found = set()

    def inner(unused_input):
        matcher = generate_arbitrary_number_pattern_matcher(local_answer)
        if matcher(local_response):
            matches_found.add(label+"_TRUE")
        else:
            matches_found.add(label+"_FALSE")
        return matches_found
    return inner

def written_as(comp, ref, parameters_dict):
    if ref == "answer":
        ref = parameters_dict["original_input"]["answer"]
    elif ref == "response":
        ref = parameters_dict["original_input"]["response"]
    if comp == "answer":
        comp = parameters_dict["original_input"]["answer"]
    elif comp == "response":
        comp = parameters_dict["original_input"]["response"]
    matcher = generate_arbitrary_number_pattern_matcher(ref)
    return matcher(comp)