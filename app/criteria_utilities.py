def undefined_key(key):
    raise KeyError("No feedback defined for key: "+str(key))


def no_feedback(inputs):
    return ""


class Criterion:

    def __init__(self, check, feedback_for_undefined_key=undefined_key):
        self.check = check
        self.feedback = dict()
        self.feedback_for_undefined_key = feedback_for_undefined_key
        return

    def __getitem__(self, key):
        if key in self.feedback.keys():
            return self.feedback[key]
        return self.feedback_for_undefined_key

    def __setitem__(self, key, value):
        self.feedback.update({key: value})
        return

class CriterionNode:

    def __init__(self, definition, output, actions):
        self.definition = definition
        self.result = None
        self.output = output,
        self.actions = actions

    def check(self, inputs):
        if self.result is None:
            self.result = self._check_criteria(definition, inputs)
            