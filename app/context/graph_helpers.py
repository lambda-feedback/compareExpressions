"""Helpers for building the `CriteriaGraph`s shared by the symbolic and physical quantity contexts."""


def outcome_tag(label, result, inputs=None):
    """`{label+"_TRUE": inputs}` if `result` is True, `label+"_FALSE"` if it is False, otherwise `label+"_UNKNOWN"`."""
    if result is True:
        return {label+"_TRUE": inputs}
    elif result is False:
        return {label+"_FALSE": inputs}
    else:
        return {label+"_UNKNOWN": inputs}


def attach_terminal_criterion(graph, evaluation_label, label, end, summary, details, feedback_string_generator=None):
    """Attaches a new criterion `label` to `evaluation_label` and connects it to the `end` node."""
    graph.attach_new_criterion(
        evaluation_label,
        label,
        summary=summary,
        details=details,
        feedback_string_generator=feedback_string_generator
    )
    graph.attach(label, end.label)
