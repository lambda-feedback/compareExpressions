import re

is_nonnegative_number_regex = '((0|[1-9]\d*)?(\.\d+)?(?<=\d)(e-?(0|[1-9]\d*))?)'


is_number_regex = '(-?(0|[1-9]\d*)?(\.\d+)?(?<=\d)( *(e|E|\*10^|\*10\*\*)-?(0|[1-9]\d*))?)'


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
    string = string.replace('\\', '\\\\')
    for s in list:
        string = string.replace(s, '\\'+s)
    return string


def generate_arbitrary_number_pattern_matcher(string):
    non_numbers = []
    number_pattern = '(\\('+is_number_regex+'\\))'
    nonneg_number_pattern = is_nonnegative_number_regex
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
    "NUMBER": {
        "matcher": is_number,
        "name": "simplified number",
        "summary": lambda criterion, parameters_dict: str(criterion.children[0].content_string())+" and "+str(criterion.children[1].content_string())+" are both numbers written in simplified form.",
        "details": lambda criterion, parameters_dict: str(criterion.children[0].content_string())+" and "+str(criterion.children[1].content_string())+" are both numbers written in simplified form.",
    },
    "CARTESIAN": {
        "matcher": is_complex_number_on_cartesian_form,
        "name": "cartesian",
        "summary": lambda criterion, parameters_dict: str(criterion.children[0].content_string())+" and "+str(criterion.children[1].content_string())+" are both complex numbers written in cartesian form",
        "details": lambda criterion, parameters_dict: str(criterion.children[0].content_string())+" and "+str(criterion.children[1].content_string())+" are both complex numbers written in cartesian form, i.e. $a+bi$.",
    },
    "EXPONENTIAL": {
        "matcher": is_complex_number_on_exponential_form,
        "name": "exponential",
        "summary": lambda criterion, parameters_dict: str(criterion.children[0].content_string())+" and "+str(criterion.children[1].content_string())+" are both complex numbers written in exponential form",
        "details": lambda criterion, parameters_dict: str(criterion.children[0].content_string())+" and "+str(criterion.children[1].content_string())+" are both complex numbers written in exponential form, i.e. $a exp(bi)$.",
    },
}
