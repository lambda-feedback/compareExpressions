class EvaluationResponse:
    def __init__(self):
        self.is_correct = False
        self.latex = None
        self._feedback = []
        self._feedback_tags = {}

    def get_feedback(self, tag):
        return self._feedback_tags.get(tag,None)

    def add_feedback(self, feedback_item: tuple[str, str] | str):
        if isinstance(feedback_item,tuple):
            self._feedback.append(feedback_item[1])
            self._feedback_tags.update({feedback_item[0]: len(self._feedback)-1})
        self._feedback_tags

    def _serialise_feedback(self) -> str:
        return "\n".join(x[1] if isinstance(x,tuple) else x for x in self._feedback)

    def serialise(self) -> dict:
        out = dict(is_correct=self.is_correct, feedback=self._serialise_feedback(), tags=self._feedback_tags)
        if self.latex:
            out.update(dict(response_latex=self.latex))
        return out