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
    from .symbolic_comparison_evaluation_tests import TestEvaluationFunction as TestSymbolicComparison

    # Import tests that makes sure that physical quantities are handled as expected
    from .quantity_comparison_evaluation_tests import TestEvaluationFunction as TestQuantities

    # Import tests that corresponds to examples in documentation and examples module
    from .example_tests import TestEvaluationFunction as TestExamples

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

if __name__ == "__main__":
    pytest.main(['-k not slow', '--tb=line', '--durations=10', os.path.abspath(__file__)])
