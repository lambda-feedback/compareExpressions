import pytest
from ..evaluation import evaluation_function

class TestListOfSymbolicExpressions:
    def test_positive_and_negative(self):
        responses = ["F*s^2 + 8*F*s", "F*s^2 + 8*F*s", "-2019q*m","4pi*(a/b)"]#input by student
        answers   = ["F*s^2 + 8*F*s",  "F*s^2 + 8*F*s", "-2019q*m","4pi*(a/b)"]#compared to student input
        params    = {"strict_syntax": False, "elementary_functions": True}#simplify what student puts in, allow for sin cos et




        
        out = evaluation_function(responses, answers, params)
        assert out["is_correct"] == True