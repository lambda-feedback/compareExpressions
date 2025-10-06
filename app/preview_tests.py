import os
import pytest

from .utility.preview_utilities import Params
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
    from .tests.symbolic_preview_tests import TestPreviewFunction as TestSymbolicComparison

    # Import tests that makes sure that physical quantities are handled as expected
    from .tests.physical_quantity_preview_tests import TestPreviewFunction as TestQuantityComparison

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

    @pytest.mark.parametrize(
        "response, is_latex, response_latex, response_sympy",
        [
            ("plus_minus x", False, '\\left\\{- x,~x\\right\\}', "plus_minus x"),
            ("\\pm x", True, '\\pm x', '{-x, x}'),
            (r"\pm x^{2}+\mp y^{2}", True, "\pm x^{2}+\mp y^{2}", "{-x**2 + y**2, x**2 - y**2}"),
            ("plus_minus x**2 + minus_plus y**2", False, r"\left\{- x^{2} + y^{2},~x^{2} - y^{2}\right\}", "plus_minus x**2 + minus_plus y**2"),
            ("- minus_plus x^2 minus_plus y^2", False, r"\left\{- x^{2} + y^{2},~x^{2} - y^{2}\right\}", "- minus_plus x^2 minus_plus y^2"),
            ("- minus_plus x^2 - plus_minus y^2", False, r"\left\{- x^{2} - - y^{2},~x^{2} - y^{2}\right\}", "- minus_plus x^2 - plus_minus y^2"),
            ("pm x**2 + mp y**2", False, r"\left\{- x^{2} + y^{2},~x^{2} - y^{2}\right\}", "plus_minus x**2 + minus_plus y**2"),
            ("+- x**2 + -+ y**2", False, r"\left\{- x^{2} + y^{2},~x^{2} - y^{2}\right\}", "plus_minus x**2 + minus_plus y**2"),
        ]
    )
    def test_using_plus_minus_symbols(self, response, is_latex, response_latex, response_sympy):
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "is_latex": is_latex,
            "symbols": {
                "plus_minus": {
                    "latex": r"\(\pm\)",
                    "aliases": ["pm", "+-"],
                },
                "minus_plus": {
                    "latex": r"\(\mp\)",
                    "aliases": ["mp", "-+"],
                },
            },
        }
        params = Params(**params)
        result = preview_function(response, params)
        assert result["preview"]["latex"] == response_latex
        assert result["preview"]["sympy"] == response_sympy

    def test_lh_rh_response(self):
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "is_latex": False,
            "symbols": {
                "plus_minus": {
                    "latex": r"\(\pm\)",
                    "aliases": ["pm", "+-"],
                },
                "minus_plus": {
                    "latex": r"\(\mp\)",
                    "aliases": ["mp", "-+"],
                },
            },
        }
        params = Params(**params)
        result = preview_function("x + y = y + x", params)
        assert result["preview"]["latex"] == "x + y=x + y"
        assert result["preview"]["sympy"] == "x + y=y + x"

if __name__ == "__main__":
    pytest.main(['-xk not slow', "--tb=line", os.path.abspath(__file__)])
