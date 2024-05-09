is_number_regex = '(-?(0|[1-9]\d*)?(\.\d+)?(?<=\d)(e-?(0|[1-9]\d*))?)'

def is_complex_number_on_cartesian_form(string):
    string = "".join(string.split())
    result = re.fullmatch(is_number_regex+"?\+?"+is_number_regex+"?\*?I?", string)
    return result

def is_complex_number_on_exponential_form(string):
    string = "".join(string.split())
    result = re.fullmatch(is_number_regex+"?\*?(E\^|E\*\*|exp)\(?"+is_number_regex+"*\*?I\)?", string)
    return result is not None

def response_and_answer_on_same_form(label, parameters_dict):
    answer = parameters_dict["original_input"]["answer"]
    response = parameters_dict["original_input"]["response"]
    for (pattern_label, pattern_function) in patterns.items():
        if pattern_function(answer) and pattern(response):
            return {label+"_SAME_FORM_"+pattern_label}

def attach_pattern_criteria_graph(graph, attachment_node, criterion, parameters_dict, pattern_label):
    lhs = criterion.children[0].content_string()
    rhs = criterion.children[1].content_string()
    graph.attach(
        label+"_SAME_FORM",
        label+"_SAME_FORM_"+pattern_label,
        summary=str(lhs)+" and "+str(rhs)+" are both complex numbers written on cartesian form",
        details=str(lhs)+" and "+str(rhs)+" are both complex numbers written on cartesian form."
        #feedback_string_generator=symbolic_feedback_generators["SAME_SYMBOLS"]("TRUE")
    )
    graph.attach(label+"_SAME_FORM"+"_CARTESIAN", END.label)


patterns = {
    "CARTESIAN": is_complex_number_on_cartesian_form,
    "EXPONENTIAL": is_complex_number_on_exponential_form,
}
