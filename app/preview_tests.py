import os
import pytest

from .preview_utilities import Params
from .preview import preview_function


class TestPreviewFunction():
    """
    TestCase Class used to test the algorithm.
    ---
    Tests are used here to check that the algorithm written
    is working as it should.

    It's best practise to write these tests first to get a
    kind of 'specification' for how your algorithm should
    work, and you should run these tests before committing
    your code to AWS.

    Read the docs on how to use unittest here:
    https://docs.python.org/3/library/unittest.html

    Use preview_function() to check your algorithm works
    as it should.
    """

    # Import tests that makes sure that mathematical expression comparison works as expected
    from .symbolic_comparison_preview_tests import TestPreviewFunction as TestSymbolicComparison

    # Import tests that makes sure that physical quantities are handled as expected
    from .quantity_comparison_preview_tests import TestPreviewFunction as TestQuantityComparison

    def test_empty_latex_expression(self):
        response = ""
        params = Params(is_latex=True)
        result = preview_function(response, params)
        assert "preview" in result.keys()

        preview = result["preview"]
        assert preview["latex"] == ""

    def test_empty_non_latex_expression(self):
        response = ""
        params = Params(is_latex=False)
        result = preview_function(response, params)
        assert "preview" in result.keys()

        preview = result["preview"]
        assert preview["sympy"] == ""

    def test_latex_and_sympy_are_returned(self):
        response = "x+1"
        params = Params(is_latex=True)
        result = preview_function(response, params)
        assert "preview" in result.keys()

        preview = result["preview"]
        assert "latex" in preview.keys()
        assert "sympy" in preview.keys()

        response = "x+1"
        params = Params(is_latex=False)
        result = preview_function(response, params)
        assert "preview" in result

        preview = result["preview"]
        assert "latex" in preview
        assert "sympy" in preview

    def test_natural_logarithm_notation(self):
        response = "ln(x)"
        params = Params(is_latex=False)
        result = preview_function(response, params)
        assert "preview" in result.keys()

        preview = result["preview"]
        assert preview["latex"] == r"\ln{\left(x \right)}"


if __name__ == "__main__":
    pytest.main(['-xk not slow', "--tb=line", os.path.abspath(__file__)])
