class EvaluationResponse:
    def __init__(self):
        self.is_correct = False
        self.latex = None
        self._feedback = [] # A list that will hold all feedback items
        self._feedback_tags = {}  # A dictionary that holds a list with indices to all feedback items with the same tag
        self._criteria_graphs = {}
        self.latex = ""
        self.simplified = ""

    def get_feedback(self, tag):
        return self._feedback_tags.get(tag, None)

    def get_tags(self):
        return list(self._feedback_tags.keys())

    def add_feedback(self, feedback_item):
        if isinstance(feedback_item, tuple):
            self._feedback.append(feedback_item[1])
            if feedback_item[0] not in self._feedback_tags.keys():
                self._feedback_tags.update({feedback_item[0]: [len(self._feedback)-1]})
            else:
                self._feedback_tags[feedback_item[0]].append(len(self._feedback)-1)
        else:
            raise TypeError("Feedback must be on the form (tag, feedback).")
        self._feedback_tags

    def add_criteria_graph(self, name, graph):
        self._criteria_graphs.update({name: graph.json()})

    def _serialise_feedback(self) -> str:
        return "<br>".join(x[1] if (isinstance(x, tuple) and len(x[1].strip())) > 0 else x for x in self._feedback)

    def serialise(self, include_test_data=False) -> dict:
        out = dict(is_correct=self.is_correct, feedback=self._serialise_feedback())
        out.update(dict(tags=list(self._feedback_tags.keys())))
        if include_test_data is True:
            out.update(dict(criteria_graphs=self._criteria_graphs))
        if self.latex is not None:
            out.update(dict(response_latex=self.latex))
        if self.simplified is not None:
            out.update(dict(response_simplified=self.simplified))
        return out

    def __getitem__(self, key):
        return self.serialise(include_test_data=True)[key]
