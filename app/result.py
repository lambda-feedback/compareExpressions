from compareexpressions.criteria import CriteriaGraph


class EvaluationResult:
    """
        Collects the outcome of an evaluation and serialises it into the
        response returned by `evaluation_function`.

        Satisfies `compareexpressions.criteria.ResultLike`, so
        `CriteriaGraph.export_feedback` can add to it.
    """
    def __init__(self):
        self.is_correct = False
        self.latex = ""
        self.simplified = ""
        self.criteria_graphs = {}  # name -> CriteriaGraph, included in test data
        self._feedback = []  # (tag, text) pairs in the order they were added

    @property
    def tags(self):
        return list(dict.fromkeys(tag for (tag, _) in self._feedback))

    def get_feedback(self, tag):
        return [text for (t, text) in self._feedback if t == tag]

    def add_feedback(self, tag, feedback):
        """Record `feedback` under `tag`. Blank feedback records the tag without adding any text."""
        self._feedback.append((tag, feedback or ""))

    def _serialise_feedback(self):
        return "<br>".join(text.strip() for (_, text) in self._feedback if len(text.strip()) > 0)

    def serialise(self, include_test_data=False) -> dict:
        out = dict(is_correct=self.is_correct, feedback=self._serialise_feedback(), tags=self.tags)
        if include_test_data is True:
            out.update(CriteriaGraph.test_data(self.criteria_graphs))
        if self.latex is not None:
            out.update(dict(response_latex=self.latex))
        if self.simplified is not None:
            simplified = self.simplified
            if isinstance(simplified, list):
                simplified = ", ".join(simplified)
            out.update(dict(response_simplified=simplified))
        return out
