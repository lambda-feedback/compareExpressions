def undefined_key(key):
    raise KeyError("No feedback defined for key: "+str(key))


def no_feedback(inputs):
    return ""


class Criterion:

    def __init__(self, check, feedback_for_undefined_key=undefined_key, doc_string=None):
        self.check = check
        self.feedback = dict()
        self.feedback_for_undefined_key = feedback_for_undefined_key
        self.doc_string = doc_string
        return

    def __getitem__(self, key):
        if key in self.feedback.keys():
            return self.feedback[key]
        else:
            return self.feedback_for_undefined_key

    def __setitem__(self, key, value):
        self.feedback.update({key: value})
        return

undefined_optional_parameter = object()

class CriteriaGraphNode:

    def __init__(self, label, criterion=None, children=undefined_optional_parameter):
        self.label = label
        self.criterion = criterion
        if children is undefined_optional_parameter:
            self.children = dict()
        else:
            self.children = children
        return

    def __getitem__(self, key):
        if key in self.children.keys():
            return self.children[key]
        else:
            return None

    def __setitem__(self, key, value):
        self.children.update({key: value})
        return

    def traverse(self, context, record=True):
        check = context["check_function"]
        inputs = context["inputs"]
        outputs = context["eval_response"]
        if record is True:
            if self.criterion is None:
                result = None
            else:
                result = check(self.label, self.criterion, inputs, outputs)
            if self.children is not None:
                try:
                    if self.children[result] is not None:
                        self.children[result].traverse(context, record)
                except KeyError as exc:
                    raise Exception(f"Unexpected result ({str(result)}) in criteria {self.label}.") from exc
        return result
