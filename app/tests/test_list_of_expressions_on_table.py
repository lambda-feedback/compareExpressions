import pytest
from ..evaluation import evaluation_function

class TestEvaluationFunction():

    def test_positive_and_negative(self):
        responses = ["F*s^2 + 8*F*s", "F*s^2 + 8*F*s", "-2019q*m","4pi*(a/b)"]#input by student
        answers   = ["F*s^2 + 8*F*s",  "F*s^2 + 8*F*s", "-2019q*m","4pi*(a/b)"]#compared to student input
        params    = {"strict_syntax": False, "elementary_functions": True}#simplify what student puts in, allow for sin cos et
        out = evaluation_function(responses, answers, params)
        assert out["is_correct"] == True

    # This is a series of tests that check if we can set up a criteria that the sum of all responses
    # is equal to the sum of all answers
    @pytest.mark.parametrize(
        "responses, value",
        [
            (["1", "1-x", "1+x"], True),
            (["1+x", "1-x", "1"], True),
            (["1+x", "-1-x", "1"], False),
            (["1+x", "1-x", "x"], False),
        ]
    )
    def test_sum_of_response_elements(self, responses, value):
        answers = ["1", "1-x", "1+x"] # reference answer
        params  = {
            "strict_syntax": False,
            "elementary_functions": True,
            "": "response[0]+response[1]+response[2] = answer[0]+answer[1]+answer[2]"
        }
        out = evaluation_function(responses, answers, params)
        assert out["is_correct"] == value

    # This is a series of tests that check if we can set up a criteria that the sum of all responses
    # is equal to the sum of all answers, but the response and answers lists are formatted as they
    # would be if we used a table with one column in the web client
    @pytest.mark.parametrize(
        "responses, value",
        [
            ([["1"], ["1-x"], ["1+x"]], True),
            ([["1+x"], ["1-x"], ["1"]], True),
            ([["1+x"], ["-1-x"], ["1"]], False),
            ([["1+x"], ["1-x"], ["x"]], False),
        ]
    )
    def test_list_of_list_of_responses_column(self, responses, value):
        answers = [[["1"], ["1-x"], ["1+x"]]] # reference answer
        params  = {
            "strict_syntax": False,
            "elementary_functions": True,
            "": "response[0]+response[1]+response[2] = answer[0]+answer[1]+answer[2]"
        }
        out = evaluation_function(responses, answers, params)
        assert out["is_correct"] == value

    # This is a series of tests that check if we can set up a criteria that the sum of all responses
    # is equal to the sum of all answers, but the response and answers lists are formatted as they
    # would be if we used a table with one row in the web client
    @pytest.mark.parametrize(
        "responses, value",
        [
            ([["1", "1-x", "1+x"]], True),
            ([["1+x", "1-x", "1"]], True),
            ([["1+x", "-1-x", "1"]], False),
            ([["1+x", "1-x", "x"]], False),
        ]
    )
    def test_list_of_list_of_responses_row(self, responses, value):
        answers = [["1", "1+x", "1-x"]] # reference answer
        params  = {
            "strict_syntax": False,
            "elementary_functions": True,
            "": "response[0]+response[1]+response[2] = answer[0]+answer[1]+answer[2]"
        }
        out = evaluation_function(responses, answers, params)
        assert out["is_correct"] == value