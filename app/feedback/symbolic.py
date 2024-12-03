# Format for feedback string entry: criteria["eval_tag"]("criteria_tag", inputs) = "formatted string" | None
criteria_equivalences = {
    **{
        eq: "response=answer" for eq in [
            "answer=response",
            "answer-response=0",
            "-answer+response=0",
            "answer/response=1",
            "response/answer-1=0"
        ]
    }
}
feedback_generators = dict()
feedback_generators["EQUIVALENCES"] = criteria_equivalences
feedback_generators["INTERNAL"] = lambda tag: lambda inputs: {
    "ABSOLUTE_VALUE_NOTATION_AMBIGUITY": f"Notation in {inputs.get('name','')} might be ambiguous, use `Abs(.)` instead of `|.|`",
    "NO_RESPONSE": "No response submitted.",
    "MULTIPLE_ANSWER_FAIL_ALL": "At least one answer or response was incorrect.",
    "MULTIPLE_ANSWER_FAIL_RESPONSE": "At least one response was incorrect.",
    "MULTIPLE_ANSWER_FAIL_ANSWER": "At least one answer is missing in the response.",
    "PARSE_ERROR": f"`{inputs.get('x','')}` could not be parsed as a valid mathematical expression. Ensure that correct codes for input symbols are used, correct notation is used, that the expression is unambiguous and that all parentheses are closed.",
    "NOTATION_WARNING_EXPONENT": "Note that `^` cannot be used to denote exponentiation, use `**` instead.",
    "NOTATION_WARNING_FACTORIAL": "Note that `!` cannot be used to denote factorial, use `factorial(...)` instead.",
    "EXPRESSION_NOT_EQUALITY": "The response was an expression but was expected to be an equality.",
    "EQUALITY_NOT_EXPRESSION": "The response was an equality but was expected to be an expression.",
    "EQUALITIES_EQUIVALENT": None,
    "EQUALITIES_NOT_EQUIVALENT": "The response is not the expected equality.",
    "WITHIN_TOLERANCE": None,  # "The difference between the response the answer is within specified error tolerance.",
    "NOT_NUMERICAL": None,  # "The expression cannot be evaluated numerically.",
}[tag]
feedback_generators["GENERIC"] = lambda tag: lambda inputs: {
    "TRUE": None,
    "FALSE": f"{inputs['criterion'].content_string()} is false.",
    "UNKNOWN": f"Cannot determine if {inputs['criterion'].content_string()} is true or false.",
}[tag]
feedback_generators["response=answer"] = lambda tag: lambda inputs: {
    "TRUE": None,  # "The response is equal to the expected answer.",
    "FALSE": None,  # "The response is not equal to the expected answer.",
    "UNKNOWN": None,  # "Cannot determine if answer is equal to response.",
}[tag]
feedback_generators["response=answer_where"] = lambda tag: lambda inputs: {
    "TRUE": None,  # "The response is equal to the expected value.",
    "FALSE": None,  # "The response is not equal to the expected value.",
}[tag]
feedback_generators["IDENTIFY_REASON"] = lambda tag: lambda inputs: {
    "UNKNOWN": None,
    "ONE_ADDITION_TO_SUBTRACTION": f"{inputs['criterion'].children[0].content_string()} if one addition is changed to a subtraction or vice versa.",
    "ONE_EXPONENT_FLIP": f"{inputs['criterion'].children[0].content_string()} is true if one exponent has its sign changed.",
    "ONE_SWAP_ADDITION_AND_MULTIPLICATION": f"{inputs['criterion'].children[0].content_string()} is true if one addition is replaced with a multiplication or vice versa.",
}[tag]
feedback_generators["GET_CANDIDATES"] = lambda tag: lambda inputs: None
feedback_generators["WRITTEN_AS"] = lambda tag: lambda inputs: {
    "NUMBER": None,
    "CARTESIAN": None,
    "EXPONENTIAL": None,
    "UNKNOWN": None,
}[tag]
feedback_generators["SYNTACTICAL_EQUIVALENCE"] = lambda tag: lambda inputs: {
    "TRUE": None,
    "FALSE": None,
    "UNKNOWN": None,
}[tag]
feedback_generators["SAME_SYMBOLS"] = lambda tag: lambda inputs: {
    "TRUE": None,
    "FALSE": "The response can be simplified further.",
}[tag]
feedback_generators["SAME_FORM"] = lambda tag: lambda inputs: {
    "CARTESIAN": "Response and answer are both written on Cartesian form.",  # None,
    "EXPONENTIAL": "Response and answer are both written on exponential form.",  # None,
    "UNKNOWN": "The response is not written on the expected form.",
}[tag]
