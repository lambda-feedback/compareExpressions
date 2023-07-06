import os
import pytest

from .evaluation import evaluation_function
from .preview import preview_function

class TestEvaluationFunction():
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
        "assumptions,value",
        [
            (None, False),
            ("('a','positive') ('b','positive')", True),
        ]
    )
    def test_setting_input_symbols_to_be_assumed_positive_to_avoid_issues_with_fractional_powers(self, assumptions, value):
        response = "sqrt(a)/sqrt(b)"
        answer = "sqrt(a/b)"
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
        }
        if assumptions is not None:
            params.update({"symbol_assumptions": assumptions})
        preview = preview_function(response, params)["preview"]
        result = evaluation_function(response, answer, params)
        assert preview["latex"] == r"\frac{\sqrt{a}}{\sqrt{b}}"
        assert result["is_correct"] == value

    @pytest.mark.parametrize(
        "response, response_latex",
        [
            ("plus_minus x**2 + minus_plus y**2", r"\left\{x^{2} - y^{2},~- x^{2} + y^{2}\right\}"),
            ("- minus_plus x^2 minus_plus y^2", r"\left\{- x^{2} + y^{2},~x^{2} - y^{2}\right\}"),
            ("- minus_plus x^2 - plus_minus y^2", r"\left\{x^{2} - y^{2},~- x^{2} - - y^{2}\right\}"),
        ]
    )
    def test_using_plus_minus_symbols(self, response, response_latex):
        answer = "plus_minus x**2 + minus_plus y**2"
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
        }
        preview = preview_function(response, params)["preview"]
        result = evaluation_function(response, answer, params)
        # Checking latex output disabled as the function return a few different
        # variants of the latex in an unpredictable way
        # assert preview["latex"] == response_latex
        assert result["is_correct"] == True

    @pytest.mark.parametrize(
        "response, response_latex",
        [
            ("x**2-5*y**2-7=0", r"x^{2} - 5 \cdot y^{2} - 7 = 0"),
            ("x^2 = 5y^2+7", r"x^{2} = 5 \cdot y^{2} + 7"),
            ("2x^2 = 10y^2+14", r"2 \cdot x^{2} = 10 \cdot y^{2} + 14"),
        ]
    )
    def test_equalities_in_the_answer_and_response(self, response, response_latex):
        answer = "x**2-5*y**2-7=0"
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
        }
        preview = preview_function(response, params)["preview"]
        result = evaluation_function(response, answer, params)
        assert preview["latex"] == response_latex
        assert result["is_correct"] == True

    @pytest.mark.parametrize(
        "response, response_latex, value",
        [
            ("2.00 kilometre/hour", r"2.0~\frac{\mathrm{kilometre}}{\mathrm{hour}}", True),
            ("2 km/h", r"2~\frac{\mathrm{kilometre}}{\mathrm{hour}}", True),
            ("0.56 m/s", r"0.56~\frac{\mathrm{metre}}{\mathrm{second}}", False),
            ("0.556 m/s", r"0.556~\frac{\mathrm{metre}}{\mathrm{second}}", True),
            ("2000 meter/hour", r"2000~\frac{\mathrm{metre}}{\mathrm{hour}}", True),
            ("2 metre/millihour", r"2~\frac{\mathrm{metre}}{\mathrm{millihour}}", True),
            ("1.243 mile/hour", r"1.243~\frac{\mathrm{mile}}{\mathrm{hour}}", True),
            ("109.12 foot/minute", r"109.12~\frac{\mathrm{foot}}{\mathrm{minute}}", True),
        ]
    )
    def test_checking_the_value_of_an_expression_or_a_physical_quantity(self, response, response_latex, value):
        answer = "2.00 km/h"
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "physical_quantity": True,
        }
        preview = preview_function(response, params)["preview"]
        result = evaluation_function(response, answer, params)
        assert preview["latex"] == response_latex
        assert result["is_correct"] == value

if __name__ == "__main__":
    pytest.main(['-sk not slow', "--tb=line", os.path.abspath(__file__)])
