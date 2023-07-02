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
    from .quantity_evaluation_tests import TestEvaluationFunction as TestQuantities


if __name__ == "__main__":
    pytest.main(['-xsk not slow', "--tb=line", os.path.abspath(__file__)])
