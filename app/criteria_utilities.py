class CriterionCollection:

    def __init__(self):
        self.tags = set()
        self.checks = dict()
        self.results = dict()
        self.feedbacks = dict()
        return

    def add_criterion(self,tag,check,result,feedback):
        if tag in self.tags:
            raise Exception("Criterion with tag: '"+str(tag)+"' already defined, use update_criterion to change criterion or choose a unique tag")
        else:
            self.tags.add(tag)
            self.checks.update({tag:check})
            self.results.update({tag:result})
            self.feedbacks.update({tag:feedback})
        return

    def update_criterion(self,tag,check,result,feedback):
        if tag not in self.tags:
            raise Exception("No criterion with tag: '"+str(tag)+"' defined.")
        else:
            self.checks.update({tag:check})
            self.results.update({tag:result})
            self.feedbacks.update({tag:feedback})
        return