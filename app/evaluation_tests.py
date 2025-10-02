import pytest
import os

from .evaluation import evaluation_function


class TestEvaluationFunction():
    """
    TestCase Class used to test the algorithm.
    ---
    Tests are used here to check that the algorithm written
    is working as it should.

    These tests are organised in classes to ensure that the same
    calling conventions can be used for tests using unittest and
    tests using pytest.

    Read the docs on how to use unittest and pytest here:
    https://docs.python.org/3/library/unittest.html
    https://docs.pytest.org/en/7.2.x/

    Use evaluation_function() to call the evaluation function.
    """

    # Import tests that makes sure that mathematical expression comparison works as expected
    from .tests.symbolic_evaluation_tests import TestEvaluationFunction as TestSymbolicComparison

    # Import tests that makes sure that physical quantities are handled as expected
    from .tests.physical_quantity_evaluation_tests import TestEvaluationFunction as TestQuantities

    # Import tests that corresponds to examples in documentation and examples module
    from .tests.example_tests import TestEvaluationFunction as TestExamples

    def test_eval_function_can_handle_latex_input(self):
        response = r"\sin x + x^{7}"
        answer = "sin(x)+x**7"
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "is_latex": True
        }
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True

    def test_eval_function_preserves_order_in_latex_input(self):
        response = r"c + a + b"
        answer = "c + a + b"
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "is_latex": True
        }
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True

    def test_AERO40007_1_6_instance_2024_25(self):
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "rtol": 0.01,
        }
        response = "231*16.4/1000*14=4"
        answer = "53"
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is False
        assert "response = answer_EQUALITY_NOT_EXPRESSION" in result["tags"]

    def test_CHEM40002_1_5_instance_2024_25(self):
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "complexNumbers": True,
            "symbols": {
                "I": {"aliases": ["i"], "latex": r"I"},
            },
        }
        response = "6 exp(5pi/6*I)"
        answer = "6(cos(5pi/6)+isin(5pi/6))"
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True


    def test_theata_character_implict_multi_variable(self):
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "normalise": True,
            "symbols": {
                "a": {"aliases": ["a"]},
                "bc": {"aliases": ["bc"]},
                "d": {"aliases": ["d"]}
            },
        }
        answer = "a/(theta*d)"
        response_full = "a/(theta*d)"
        response_implicit_bracket = "a/(thetad)"
        response_implicit_no_bracket = "a/thetad"

        result = evaluation_function(response_full, answer, params)
        assert result["is_correct"] is True, "Response: a/(theta*d)"

        result = evaluation_function(response_implicit_bracket, answer, params)
        assert result["is_correct"] is True, "Response: a/(thetad)"

        result = evaluation_function(response_implicit_no_bracket, answer, params)
        assert result["is_correct"] is True, "Response: a/thetad"

    def test_multi_character_implicit_multi_variable(self):
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "normalise": True,
            "symbols": {
                "a": {"aliases": ["a"]},
                "bc": {"aliases": ["bc"]},
                "d": {"aliases": ["d"]}
            },
        }
        answer = "a/(bc*d)"
        response_full = "a/(bc*d)"
        response_implicit_bracket = "a/(bcd)"
        response_implicit_no_bracket = "a/bcd"

        result = evaluation_function(response_full, answer, params)
        assert result["is_correct"] is True, "Response: a/(bc*d)"

        result = evaluation_function(response_implicit_bracket, answer, params)
        assert result["is_correct"] is True, "Response: a/(bcd)"

        result = evaluation_function(response_implicit_no_bracket, answer, params)
        assert result["is_correct"] is True, "Response: a/bcd"


if __name__ == "__main__":
    pytest.main(['-xk not slow', '--tb=short', '--durations=10', os.path.abspath(__file__)])
