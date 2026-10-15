from sympy import Equality

from ....feedback.symbolic import feedback_generators as symbolic_feedback_string_generators
from ...graph_helpers import attach_terminal_criterion
from ..comparison import check_equality


def as_sets(response, answer):
    """
    Returns whether `response` and `answer` should be compared as sets, together with
    `response` and `answer` wrapped in a set if only the other one is a set.
    """
    if isinstance(response, set) and isinstance(answer, set):
        return True, response, answer
    elif isinstance(response, set):
        return True, response, set([answer])
    elif isinstance(answer, set):
        return True, set([response]), answer
    return False, response, answer


def add_set_equivalence_nodes(graph, END, criterion, parameters_dict, label, lhs, rhs, response_list, answer_list):
    """
    Adds the nodes that check if each element of `response_list` is equal to an element of
    `answer_list` (and vice versa, depending on `multiple_answers_criteria`) to `graph`.
    """
    def set_equivalence(unused_input):
        matches = {"responses": [False]*len(response_list), "answers": [False]*len(answer_list)}
        for i, response in enumerate(response_list):
            for j, answer in enumerate(answer_list):
                current_pair = [("response", response), ("answer", answer)]
                if isinstance(response, Equality) != isinstance(answer, Equality):
                    result = False
                else:
                    result = check_equality(criterion, parameters_dict, local_substitutions=current_pair)
                if result is True:
                    matches["responses"][i] = True
                    matches["answers"][j] = True
        if parameters_dict["multiple_answers_criteria"] == "all":
            is_correct = all(matches["responses"]) and all(matches["answers"])
            if is_correct is False:
                return {
                    label+"_MULTIPLE_ANSWER_FAIL_ALL": None
                }
        elif parameters_dict["multiple_answers_criteria"] == "all_responses":
            is_correct = all(matches["responses"])
            if is_correct is False:
                return {
                    label+"_MULTIPLE_ANSWER_FAIL_RESPONSE": None
                }
        elif parameters_dict["multiple_answers_criteria"] == "all_answers":
            is_correct = all(matches["answers"])
            if is_correct is False:
                return {
                    label+"_MULTIPLE_ANSWER_FAIL_ANSWER": None
                }
        else:
            raise SyntaxWarning(f"Unknown multiple_answers_criteria: {parameters_dict['multiple_answers_criteria']}")
        return {
            label+"_TRUE": None
        }

    graph.add_evaluation_node(
        label,
        summary=label,
        details="Checks if "+str(lhs)+"="+str(rhs)+".",
        evaluate=set_equivalence
    )
    graph.attach_new_criterion(
        label,
        label+"_TRUE",
        summary=str(lhs)+"="+str(rhs),
        details=str(lhs)+" is equal to "+str(rhs)+".",
        feedback_string_generator=symbolic_feedback_string_generators["response=answer"]("TRUE")
    )
    attach_terminal_criterion(
        graph,
        label,
        label+"_MULTIPLE_ANSWER_FAIL_ALL",
        END,
        summary=str(lhs)+" is not equal to "+str(rhs),
        details="At least one answer or response was incorrect.",
        feedback_string_generator=symbolic_feedback_string_generators["INTERNAL"]("MULTIPLE_ANSWER_FAIL_ALL")
    )
    attach_terminal_criterion(
        graph,
        label,
        label+"_MULTIPLE_ANSWER_FAIL_RESPONSE",
        END,
        summary="Unexpected element in response.",
        details="At least one response was incorrect.",
        feedback_string_generator=symbolic_feedback_string_generators["INTERNAL"]("MULTIPLE_ANSWER_FAIL_RESPONSE")
    )
    attach_terminal_criterion(
        graph,
        label,
        label+"_MULTIPLE_ANSWER_FAIL_ANSWER",
        END,
        summary="Missing element in response",
        details="At least one answer is missing in the response.",
        feedback_string_generator=symbolic_feedback_string_generators["INTERNAL"]("MULTIPLE_ANSWER_FAIL_ANSWER")
    )
