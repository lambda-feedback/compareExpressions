from copy import deepcopy

import pytest

from app.preview.physical_quantity import fix_exponents, preview_function
from app.tests.physical_quantity_test_cases import slr_natural_si_syntax_test_cases, slr_strict_si_syntax_test_cases


class TestPreviewFunction:
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

    @pytest.mark.parametrize(
        "response,value,unit,content,value_latex,unit_latex,criteria", slr_strict_si_syntax_test_cases
    )
    @pytest.mark.slow
    def test_strict_syntax_cases(self, response, value, unit, content, value_latex, unit_latex, criteria):
        params = {
            "strict_syntax": False,
            "physical_quantity": True,
            "units_string": "SI",
            "strictness": "strict",
            "elementary_functions": True,
        }
        result = preview_function(response, params)["preview"]
        latex = ""
        if value_latex is None and unit_latex is not None:
            latex = unit_latex
        elif value_latex is not None and unit_latex is None:
            latex = value_latex
        elif value_latex is not None and unit_latex is not None:
            latex = value_latex + "~" + unit_latex
        assert result["latex"] == latex

    @pytest.mark.parametrize(
        "response,value,unit,content,value_latex,unit_latex,criteria", slr_natural_si_syntax_test_cases
    )
    def test_natural_syntax_cases(self, response, value, unit, content, value_latex, unit_latex, criteria):
        params = {
            "strict_syntax": False,
            "physical_quantity": True,
            "units_string": "SI",
            "strictness": "natural",
            "elementary_functions": True,
        }
        result = preview_function(response, params)["preview"]
        latex = ""
        if value_latex is None and unit_latex is not None:
            latex = unit_latex
        elif value_latex is not None and unit_latex is None:
            latex = value_latex
        elif value_latex is not None and unit_latex is not None:
            latex = value_latex + "~" + unit_latex
        assert result["latex"] == latex

    @pytest.mark.parametrize(
        "response,preview_latex,preview_sympy",
        [
            ("sin(123)", r"\sin{\left(123 \right)}", "sin(123)"),
            ("sqrt(162)", r"\sqrt{162}", "sqrt(162)"),
        ],
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
        response = "162 \\mathrm{~N} / \\mathrm{m}^{2}"
        result = preview_function(response, params)["preview"]
        assert result["latex"] == r"162~\frac{\mathrm{newton}}{\mathrm{metre}^{2}}"
        assert result["sympy"] == "162 newton/metre**(2)"

    @pytest.mark.parametrize(
        "response, latex, sympy",
        [
            (r"\frac{F}{p \cdot \mu}", r"\frac{F}{\mu p}", "F/((mu*p))"),
            (r"F \cdot p", "F p", "F*p"),
            (r"\frac{10}{2} \mathrm{~kg}", r"\frac{10}{2}~\mathrm{kilogram}", "10/2 kilogram"),
        ],
    )
    def test_latex_physical_quantity_preview(self, response, latex, sympy):
        params = {
            "is_latex": True,
            "physical_quantity": True,
            "elementary_functions": True,
        }
        result = preview_function(response, params)["preview"]
        assert result["latex"] == latex
        assert result["sympy"] == sympy

    @pytest.mark.parametrize(
        ("latex", "expected"),
        [
            ("m^{-2}", "m**(-2)"),
            ("x^{23}", "x**(23)"),
            # With '**' the notation used to be skipped twice, eating the exponent's first character.
            ("m**{-2}", "m**(-2)"),
            ("x**{23}", "x**(23)"),
            ("x^2", "x**2"),
            # An unbraced exponent used to borrow the next brace anywhere in the string.
            ("x^2y^{3}", "x**2y**(3)"),
        ],
    )
    def test_fix_exponents(self, latex, expected):
        assert fix_exponents(latex) == expected

    def test_latex_preview_keeps_the_exponent_sign(self):
        preview = preview_function(r"162 \mathrm{~N} \mathrm{~m}**{-2}", {"is_latex": True})["preview"]
        assert preview["sympy"] == "162 newton metre**(-2)"

    def test_latex_preview_of_a_unit_alone(self):
        assert preview_function(r"\mathrm{kg}", {"is_latex": True})["preview"]["sympy"] == "kilogram"

    def test_preview_does_not_mutate_params(self):
        # Fixed while porting units to the typed expression_parsing API
        # (the LaTeX branch set params["is_latex"] = False on the caller's dict).
        params = {"is_latex": True, "symbols": {"F": {"latex": "F", "aliases": []}}}
        before = deepcopy(params)
        preview_function(r"3 \mathrm{kg}", params)
        assert params == before
