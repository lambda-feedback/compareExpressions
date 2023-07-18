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
        "response, answer, response_latex, value, strictness, units_string",
        [
            ("2.00 kilometre/hour", "2.00 km/h", r"2.0~\frac{\mathrm{kilometre}}{\mathrm{hour}}", True, None, None),
            ("2 km/h", "2.00 km/h", r"2~\frac{\mathrm{kilometre}}{\mathrm{hour}}", True, None, None),
            ("0.56 m/s", "2.00 km/h", r"0.56~\frac{\mathrm{metre}}{\mathrm{second}}", False, None, None),
            ("0.556 m/s", "2.00 km/h", r"0.556~\frac{\mathrm{metre}}{\mathrm{second}}", True, None, None),
            ("2000 meter/hour", "2.00 km/h", r"2000~\frac{\mathrm{metre}}{\mathrm{hour}}", True, None, None),
            ("2 metre/millihour", "2.00 km/h", r"2~\frac{\mathrm{metre}}{\mathrm{millihour}}", True, None, None),
            ("1.243 mile/hour", "2.00 km/h", r"1.243~\frac{\mathrm{mile}}{\mathrm{hour}}", True, None, None),
            ("109.12 foot/minute", "2.00 km/h", r"109.12~\frac{\mathrm{foot}}{\mathrm{minute}}", True, None, None),
            ("0.556 m/s", "0.556 metre/second", r"0.556~\frac{\mathrm{metre}}{\mathrm{second}}", True, "strict", "SI"),
            ("5.56 dm/s", "0.556 metre/second", r"5.56~\frac{\mathrm{decimetre}}{\mathrm{second}}", True, "strict", "SI"),
            ("55.6 centimetre second^(-1)", "0.556 metre/second", r"55.6~\mathrm{centimetre}~\mathrm{second}^{(-1)}", True, "strict", "SI"),
            ("1.24 mile/hour", "1.24 mile/hour", r"1.24~\frac{\mathrm{mile}}{\mathrm{hour}}", True, "strict", "imperial common"),
            ("2 km/h", "1.24 mile/hour", r"2~\frac{\mathrm{kilometre}}{\mathrm{hour}}", True, "strict", "imperial common"),  # This should be False, but due to SI units being used as base it still works in this case...
            ("109.12 foot/minute", "1.24 mile/hour", r"109.12~\frac{\mathrm{foot}}{\mathrm{minute}}", True, "strict", "imperial common"),
        ]
    )
    def test_checking_the_value_of_an_expression_or_a_physical_quantity(self, response, answer, response_latex, value, strictness, units_string):
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "physical_quantity": True,
        }
        if strictness is not None:
            params.update({"strictness": strictness})
        if units_string is not None:
            params.update({"units_string": units_string})
        preview = preview_function(response, params)["preview"]
        result = evaluation_function(response, answer, params)
        assert preview["latex"] == response_latex
        assert result["response_latex"] == response_latex
        assert result["is_correct"] == value

    @pytest.mark.parametrize(
        "answer, atol_response_true, atol_response_false, rtol_response_true, rtol_response_false",
        [
            (
                "sqrt(47)+pi",
                ["10", "5.1", "14.9"],
                ["4.9", "15.1"],
                ["10", "5.1", "14.9"],
                ["4.9", "15.1"]
            ),
            (
                "(13/3)^pi",
                ["100", "96", "104"], 
                ["94", "106"],
                ["100", "51", "149"], 
                ["49", "151"],
            ),
            (
                "9^(e+ln(1.5305))",
                ["1000", "996", "1004"], 
                ["994", "1006"],
                ["1000", "501", "1499"], 
                ["499", "1501"],
            )
        ]
    )
    def test_setting_absolute_or_relative_tolerances_for_numerical_comparison(self, answer, atol_response_true, atol_response_false, rtol_response_true, rtol_response_false):
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "atol": 5,
        }
        for response in atol_response_true:
            result = evaluation_function(response, answer, params)
            assert result["is_correct"] == True
        for response in atol_response_false:
            result = evaluation_function(response, answer, params)
            assert result["is_correct"] == False
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "rtol": 0.5,
        }
        for response in rtol_response_true:
            result = evaluation_function(response, answer, params)
            assert result["is_correct"] == True
        for response in rtol_response_false:
            result = evaluation_function(response, answer, params)
            assert result["is_correct"] == False

    @pytest.mark.parametrize(
        "response, answer, response_latex, criteria, value, feedback_tags, extra_params",
        [
            ("exp(lambda*x)/(1+exp(lambda*x))", "c*exp(lambda*x)/(1+c*exp(lambda*x))", r"\frac{e^{\lambda \cdot x}}{e^{\lambda \cdot x} + 1}", "diff(response,x)=lambda*response*(1-response)", True, [], {"symbols": {"lambda": {"latex": r"\(\lambda\)", "aliases": []}}}),
            ("5*exp(lambda*x)/(1+5*exp(lambda*x))", "c*exp(lambda*x)/(1+c*exp(lambda*x))", r"\frac{5 \cdot e^{\lambda \cdot x}}{5 \cdot e^{\lambda \cdot x} + 1}", "diff(response,x)=lambda*response*(1-response)", True, [], {"symbols": {"lambda": {"latex": r"\(\lambda\)", "aliases": []}}}),
            ("6*exp(lambda*x)/(1+7*exp(lambda*x))", "c*exp(lambda*x)/(1+c*exp(lambda*x))", r"\frac{6 \cdot e^{\lambda \cdot x}}{7 \cdot e^{\lambda \cdot x} + 1}", "diff(response,x)=lambda*response*(1-response)", False, [], {"symbols": {"lambda": {"latex": r"\(\lambda\)", "aliases": []}}}),
            ("c*exp(lambda*x)/(1+c*exp(lambda*x))", "c*exp(lambda*x)/(1+c*exp(lambda*x))", r"\frac{c \cdot e^{\lambda \cdot x}}{c \cdot e^{\lambda \cdot x} + 1}", "diff(response,x)=lambda*response*(1-response)", True, [], {"symbols": {"lambda": {"latex": r"\(\lambda\)", "aliases": []}}}),
            ("5x", "5x", r"5 \cdot x", "answer-response = 0, response/answer = 1", True, ["RESPONSE_EQUAL_ANSWER"], dict()),
            ("x", "5x", r"x", "answer-response = 0, response/answer = 1", False, ["RESPONSE_EQUAL_ANSWER"], dict()),
            ("2x", "x", r"2 \cdot x", "response=2*answer", True, ["RESPONSE_DOUBLE_ANSWER"], dict()),
            ("x", "x", "x", "response=2*answer", False, ["RESPONSE_DOUBLE_ANSWER"], dict()),
            ("-x", "x", "- x", "answer=-response", True, ["RESPONSE_NEGATIVE_ANSWER"], dict()),
            ("x", "x", "x", "response=-answer", False, ["RESPONSE_NEGATIVE_ANSWER"], dict()),
            ("1", "1", "1", "response^3-6*response^2+11*response-6=0", True, [], dict()),
            ("2", "1", "2", "response^3-6*response^2+11*response-6=0", True, [], dict()),
            ("3", "1", "3", "response^3-6*response^2+11*response-6=0", True, [], dict()),
            ("4", "1", "4", "response^3-6*response^2+11*response-6=0", False, [], dict()),
            ("sin(x)+2", "sin(x)", r"\sin{\left(x \right)} + 2", "Derivative(response,x)=cos(x)", True, [], dict()),
            ("sin(x)+2", "sin(x)", r"\sin{\left(x \right)} + 2", "diff(response,x)=cos(x)", True, [], dict()),
            ("cos(x)+2", "sin(x)", r"\cos{\left(x \right)} + 2", "diff(response,x)=cos(x)", False, [], dict()),
        ]
    )
    def test_customizing_comparison(self, response, answer, response_latex, criteria, value, feedback_tags, extra_params):
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "criteria": criteria,
        }
        params.update(extra_params)
        preview = preview_function(response, params)["preview"]
        result = evaluation_function(response, answer, params, include_test_data=True)
        assert preview["latex"] == response_latex
        assert result["response_latex"] == response_latex
        assert result["is_correct"] == value
        for feedback_tag in feedback_tags:
            assert feedback_tag in result["tags"]

if __name__ == "__main__":
    pytest.main(['-sk not slow', "--tb=line", os.path.abspath(__file__)])
