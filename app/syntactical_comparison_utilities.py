import re
import math
from .feedback.symbolic_comparison import feedback_generators as symbolic_feedback_generators
from .criteria_graph_utilities import CriteriaGraph

# Based on regular expressions from
# https://slavik.meltser.info/validate-number-with-regular-expression/
is_integer_regex = '(-?(0|[1-9]\d*)(e-?(0|[1-9]\d*))?)'
is_number_on_decimal_form_regex = '(-?(0|[1-9]\d*)?(\.\d+)?(?<=\d)(e-?(0|[1-9]\d*))?)'

is_number_regex = '((\(?'+is_number_on_decimal_form_regex+'+\)?)\/?\(?'+is_number_on_decimal_form_regex+'?\)?)'



def split_on_number(string):
    split_string = []
    number_indices = []
    i = 0
    while i < len(string):
        match = re.search(is_number_regex, string)
        if match is not None:
            start, end = match.span()
            if start > i:
                split_string.append(string[i:start])
            number_indices.append(len(split_string))
            split_string.append(match.group())
            i = end
        else:
            i = len(string)
    return split_string, number_indices

def extract_numbers(string):
    numbers = []
    i = 0
    while i < len(string):
        match = re.search(is_number_regex, string[i:])
        if match is not None:
            start, end = match.span()
            if start != end:
                numbers.append(match.group())
            if end > 0:
                i += end
            else:
                i += 1
        else:
            i = len(string)
    return numbers

def is_number_simplified(string):
    split_string = string.split('/')
    if len(split_string) == 1:
        return True
    elif len(split_string) == 2:
        numerator = split_string[0].strip()
        denominator = split_string[1].strip()
        if re.fullmatch(is_integer_regex, numerator) is None or re.fullmatch(is_integer_regex, denominator) is None:
            return False
        else:
            if math.gcd(int(numerator)) == 1:
                return True
            else:
                return False
    else:
        raise Exception("Case not handled yet")

def is_number(string):
    match_content = re.fullmatch(is_number_regex, string)
    return match_content is not None and len(match_content.group(0)) > 0

def numbers_in_string_are_simplified(string):
    string = "".join(string.split())
    numbers = extract_numbers(string)
    result = True
    for number in numbers:
        result = is_number_simplified(number) and result
    return result

def is_complex_number_on_cartesian_form(string):
    string = "".join(string.split())
    result = re.fullmatch(is_number_regex+"?(\+|-)?"+is_number_regex+"?\*?I?", string)
    result = result is not None and numbers_in_string_are_simplified(string)
    return result

def is_complex_number_on_exponential_form(string):
    string = "".join(string.split())
    result = re.fullmatch(is_number_regex+"?\*?(E\^|E\*\*|exp)\(?"+is_number_regex+"?\*?I\)?", string)
    return result is not None

def is_complex_number_on_polar_form(string):
    string = "".join(string.split())
    result = re.fullmatch(is_number_regex+"?\*?\(?(cos\("+is_number_regex+"\))(\+|-)I\*?sin\("+is_number_regex+"\)\)?", string)
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
    "POLAR": {
        "matcher": is_complex_number_on_polar_form,
        "summary": lambda criterion, parameters_dict: str(criterion.children[0].content_string())+" and "+str(criterion.children[1].content_string())+" are both complex numbers written on polar form",
        "details": lambda criterion, parameters_dict: str(criterion.children[0].content_string())+" and "+str(criterion.children[1].content_string())+" are both complex numbers written on polar form, i.e. $a (\cos(b) + i \sin(b))$.",
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
