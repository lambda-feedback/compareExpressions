import os
import pytest

from .preview_utilities import Params, extract_latex
from .quantity_comparison_preview import preview_function
from .slr_quantity_tests import slr_strict_si_syntax_test_cases, slr_natural_si_syntax_test_cases


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

    @pytest.mark.parametrize("response,value,unit,content,value_latex,unit_latex,criteria", slr_strict_si_syntax_test_cases)
    def test_strict_syntax_cases(self, response, value, unit, content, value_latex, unit_latex, criteria):
        params = {"strict_syntax": False, "physical_quantity": True, "units_string": "SI", "strictness": "strict"}
        result = preview_function(response, params)["preview"]
        latex = ""
        if value_latex is None and unit_latex is not None:
            latex = unit_latex
        elif value_latex is not None and unit_latex is None:
            latex = value_latex
        elif value_latex is not None and unit_latex is not None:
            latex = value_latex+"~"+unit_latex
        assert result["latex"] == latex

    @pytest.mark.parametrize("response,value,unit,content,value_latex,unit_latex,criteria", slr_natural_si_syntax_test_cases)
    def test_natural_syntax_cases(self, response, value, unit, content, value_latex, unit_latex, criteria):
        params = {"strict_syntax": False, "physical_quantity": True, "units_string": "SI", "strictness": "natural"}
        result = preview_function(response, params)["preview"]
        latex = ""
        if value_latex is None and unit_latex is not None:
            latex = unit_latex
        elif value_latex is not None and unit_latex is None:
            latex = value_latex
        elif value_latex is not None and unit_latex is not None:
            latex = value_latex+"~"+unit_latex
        assert result["latex"] == latex

    @pytest.mark.parametrize("response,preview_latex,preview_sympy",
        [
            ("sin(123)", r"\sin{\left(123 \right)}", "sin(123)"),
            ("sqrt(162)", r"\sqrt{162}", "sqrt(162)"),
        ]
    )
    def test_issue_with_function_name_that_can_be_compound_unit(self, response, preview_latex, preview_sympy):
        params = {
            "physical_quantity": True,
            "elementary_functions": True,
        }
        result = preview_function(response, params)["preview"]
        assert result["latex"] == preview_latex
        assert result["sympy"] == preview_sympy

    def test_handwritten_input(self):
        params = {
            "is_latex": True,
            "physical_quantity": True,
            "elementary_functions": True,
        }
        response = "\\sqrt{162} \\mathrm{~N} / \\mathrm{m}^{2}"
        result = preview_function(response, params)["preview"]
        assert result["latex"] == r'\sqrt{162}~\frac{\mathrm{newton}}{\mathrm{metre}^{(2)}}' # TODO: Fix so that unnecessary parenthesis are simplified away
        assert result["sympy"] == "sqrt(162) newton / metre**(2)"

if __name__ == "__main__":
    pytest.main(['-sk not slow', "--tb=line", os.path.abspath(__file__)])
