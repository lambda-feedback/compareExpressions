from ..criteria_utilities import Criterion, no_feedback

# TODO: Find better way of identifying reference criteria
# equivalences dictionary should contain a list of variations that are likely to be produced by the following procedure:
# - rewrite critera as expr=0,
# - parse left hand side of rewritten critera as a sympy expression
# - turn sympy expression into a string and remove all whitespace
equivalences = dict()  
criteria = dict()

criteria["RESPONSE_EQUAL_ANSWER"] = Criterion("response=answer")
equivalences.update({"RESPONSE_EQUAL_ANSWER": ["answer-response","-answer+response","answer/response-1","response/answer-1"]})
criteria["RESPONSE_EQUAL_ANSWER"][True] = lambda inputs: "The response matches the expected answer."
criteria["RESPONSE_EQUAL_ANSWER"][False] = lambda inputs: "The response does not match the expected answer."

criteria["RESPONSE_DOUBLE_ANSWER"] = Criterion("response=2*answer")
equivalences.update({"RESPONSE_DOUBLE_ANSWER": ["answer-response/2","-answer+response/2","-2*answer-response","2*answer-response","-2+answer/response","-2+response/answer"]})
criteria["RESPONSE_DOUBLE_ANSWER"][True] = lambda inputs: "The response is the expected answer multiplied by 2."
criteria["RESPONSE_DOUBLE_ANSWER"][False] = lambda inputs: "The response is not the expected answer multiplied by 2."

criteria["RESPONSE_NEGATIVE_ANSWER"] = Criterion("response=-answer")
equivalences.update({"RESPONSE_NEGATIVE_ANSWER": ["answer+response","answer+response","answer/response+1","response/answer+1"]})
criteria["RESPONSE_NEGATIVE_ANSWER"][True] = lambda inputs: "The response is the expected answer multiplied by -1."
criteria["RESPONSE_NEGATIVE_ANSWER"][False] = lambda inputs: "The response is not the expected answer multiplied by -1."

# TODO: Handle multiple answer feedback properly
internal = {
    "ABSOLUTE_VALUE_NOTATION_AMBIGUITY": lambda name: f"Notation in {name} might be ambiguous, use `Abs(.)` instead of `|.|`",
    "NO_RESPONSE": "No response submitted.",
    "MULTIPLE_ANSWER_FAIL_ALL": "At least one answer or response was incorrect.",
    "MULTIPLE_ANSWER_FAIL_RESPONSE": "At least one response was incorrect.",
    "MULTIPLE_ANSWER_FAIL_ANSWERS": "At least one answer is missing in the response.",
    "PARSE_ERROR": lambda x: f"`{x}` could not be parsed as a valid mathematical expression. Ensure that correct codes for input symbols are used, correct notation is used, that the expression is unambiguous and that all parentheses are closed.",
    "NOTATION_WARNING": "Note that `^` cannot be used to denote exponentiation, use `**` instead.",
    "EXPRESSION_NOT_EQUALITY": "The response was an expression but was expected to be an equality.",
    "EQUALITY_NOT_EXPRESSION": "The response was an equality but was expected to be an expression.",
    "WITHIN_TOLERANCE": "The difference between the response the answer is within specified error tolerance.",
    "SYMBOLICALLY_EQUAL": "The difference response and answer are symbolically equal.",
}
