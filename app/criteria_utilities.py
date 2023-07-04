class CriterionCollection:

    def __init__(self):
        self.tags = set()
        self.checks = dict()
        self.results = dict()
        self.feedbacks = dict()
        return

    def add_criterion(self, tag, check, result, feedback):
        if tag in self.tags:
            raise Exception(
                "Criterion with tag: '"
                + str(tag)
                + "' already defined, use update_criterion to change criterion or choose a unique tag")
        else:
            self.tags.add(tag)
            self.checks.update({tag: check})
            self.results.update({tag: result})
            self.feedbacks.update({tag: feedback})
        return

    def update_criterion(self, tag, check, result, feedback):
        if tag not in self.tags:
            raise Exception("No criterion with tag: '"+str(tag)+"' defined.")
        else:
            self.checks.update({tag: check})
            self.results.update({tag: result})
            self.feedbacks.update({tag: feedback})
        return


# TODO: check if code above this comment is still used

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
