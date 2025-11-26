import os
import pytest

from ..evaluation import evaluation_function
from ..preview import preview_function

def create_diagram_for_documentation(filename, result):
    for (index, graph) in enumerate(result["criteria_graphs_vis"].values()):
        with open(filename+"_"+str(index)+".md", "w") as f:
            #f.write(r'<!DOCTYPE html><html lang="en"><body><style>.mermaid {display: inline-flex;}</style>'+'\n')
            f.write("```mermaid\n")
            for g in result["criteria_graphs_vis"].values():
                print(g)
                #f.write('<pre class="mermaid">\n'+g+'\n</pre>\n')
                f.write(g+"\n")
            #f.write('<script type="module"> import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";</script></body></html>')
            f.write("```\n")

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
        "response, is_latex, response_latex",
        [
            (r"\pm x^{2}+\mp y^{2}", True, r"\left\{x^{2} - y^{2},~- x^{2} + y^{2}\right\}"),
            ("plus_minus x**2 + minus_plus y**2", False, r"\left\{x^{2} - y^{2},~- x^{2} + y^{2}\right\}"),
            ("- minus_plus x^2 minus_plus y^2", False, r"\left\{- x^{2} + y^{2},~x^{2} - y^{2}\right\}"),
            ("- minus_plus x^2 - plus_minus y^2", False, r"\left\{x^{2} - y^{2},~- x^{2} - - y^{2}\right\}"),
            ("pm x**2 + mp y**2", False, r"\left\{x^{2} - y^{2},~- x^{2} + y^{2}\right\}"),
            ("+- x**2 + -+ y**2",  False, r"\left\{x^{2} - y^{2},~- x^{2} + y^{2}\right\}"),
        ]
    )
    def test_using_plus_minus_symbols(self, response, is_latex, response_latex):
        answer = "plus_minus x**2 + minus_plus y**2"
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
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
        if is_latex is True:
            processed_response = preview_function(response, {**params, **{"is_latex": True}})["preview"]["sympy"]
            result = evaluation_function(processed_response, answer, params)
            assert result["is_correct"] is True
            params.update({"is_latex": True})
        # Checking latex output disabled as the function return a few different
        # variants of the latex in an unpredictable way
        # preview = preview_function(response, params)["preview"]
        # assert preview["latex"] == response_latex
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True

    @pytest.mark.parametrize(
        "response, response_latex",
        [
            ("x**2-5*y**2-7=0", r"x^{2} - 5 \cdot y^{2} - 7=0"),
            ("x^2 = 5y^2+7", r"x^{2}=5 \cdot y^{2} + 7"),
            ("2x^2 = 10y^2+14", r"2 \cdot x^{2}=10 \cdot y^{2} + 14"),
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
        assert result["is_correct"] is True

    @pytest.mark.parametrize(
        "response, answer, response_latex, value, strictness, units_string, tags",
        [
            ("2.00 kilometre/hour", "2.00 km/h", r"2.0~\frac{\mathrm{kilometre}}{\mathrm{hour}}", True, None, None, set(['response matches answer_TRUE', 'response matches answer_UNIT_COMPARISON_IDENTICAL'])),
            ("2.00", "2.00 km/h", r"2.0", False, None, None, set(["response matches answer_MISSING_UNIT"])),
            ("kilometre/hour", "2.00 km/h", r"\frac{\mathrm{kilometre}}{\mathrm{hour}}", False, None, None, set(["response matches answer_MISSING_VALUE"])),
            ("2 km/h", "2.00 km/h", r"2~\frac{\mathrm{kilometre}}{\mathrm{hour}}", True, None, None, set(['response matches answer_TRUE', 'response matches answer_UNIT_COMPARISON_IDENTICAL'])),
            ("2 km", "2.00 km/h", r"2~\mathrm{kilometre}", False, None, None, {'response matches answer_FALSE', 'response matches answer_DIMENSION_MATCH_FALSE'}),
            ("0.56 m/s", "2.00 km/h", r"0.56~\frac{\mathrm{metre}}{\mathrm{second}}", False, None, None, {'response matches answer_FALSE', 'response matches answer_DIMENSION_MATCH_TRUE'}),
            ("0.556 m/s", "2.00 km/h", r"0.556~\frac{\mathrm{metre}}{\mathrm{second}}", True, None, None, {'response matches answer_TRUE', 'response matches answer_UNIT_COMPARISON_SIMILAR'}),
            ("2000 meter/hour", "2.00 km/h", r"2000~\frac{\mathrm{metre}}{\mathrm{hour}}", True, None, None, {"response matches answer_TRUE", "response matches answer_UNIT_COMPARISON_PREFIX_IS_SMALL"}),
            ("0.002 megametre/hour", "2.00 km/h", r"0.002~\frac{\mathrm{megametre}}{\mathrm{hour}}", True, None, None, {"response matches answer_TRUE", "response matches answer_UNIT_COMPARISON_PREFIX_IS_LARGE"}),
            ("2 metre/millihour", "2.00 km/h", r"2~\frac{\mathrm{metre}}{\mathrm{millihour}}", True, None, None, {"response matches answer_TRUE", "response matches answer_UNIT_COMPARISON_SIMILAR"}),
            ("1.243 mile/hour", "2.00 km/h", r"1.243~\frac{\mathrm{mile}}{\mathrm{hour}}", True, None, None, {"response matches answer_TRUE", "response matches answer_UNIT_COMPARISON_SIMILAR"}),
            ("109.12 foot/minute", "2.00 km/h", r"109.12~\frac{\mathrm{foot}}{\mathrm{minute}}", True, None, None, {"response matches answer_TRUE", "response matches answer_UNIT_COMPARISON_SIMILAR"}),
            ("0.556 m/s", "0.556 metre/second", r"0.556~\frac{\mathrm{metre}}{\mathrm{second}}", True, "strict", "SI", {"response matches answer_TRUE", "response matches answer_UNIT_COMPARISON_IDENTICAL"}),
            ("5.56 dm/s", "0.556 metre/second", r"5.56~\frac{\mathrm{decimetre}}{\mathrm{second}}", True, "strict", "SI", {"response matches answer_TRUE", "response matches answer_UNIT_COMPARISON_SIMILAR"}),
            ("55.6 centimetre second^(-1)", "0.556 metre/second", r"55.6~\mathrm{centimetre}~\mathrm{second}^{(-1)}", True, "strict", "SI", {"response matches answer_TRUE", "response matches answer_UNIT_COMPARISON_SIMILAR"}),
            ("1.24 mile/hour", "1.24 mile/hour", r"1.24~\frac{\mathrm{mile}}{\mathrm{hour}}", True, "strict", "imperial common", {"response matches answer_TRUE", "response matches answer_UNIT_COMPARISON_IDENTICAL"}),
            ("2 km/h", "1.24 mile/hour", r"2~\frac{\mathrm{kilometre}}{\mathrm{hour}}", True, "strict", "imperial common", {"response matches answer_TRUE", "response matches answer_UNIT_COMPARISON_SIMILAR"}),  # Ideally False but works with base SI units
            ("109.12 foot/minute", "1.24 mile/hour", r"109.12~\frac{\mathrm{foot}}{\mathrm{minute}}", True, "strict", "imperial common", {"response matches answer_TRUE", "response matches answer_UNIT_COMPARISON_SIMILAR"}),
        ]
    )
    def test_checking_the_value_of_a_physical_quantity(self, response, answer, response_latex, value, strictness, units_string, tags):
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
        result = evaluation_function(response, answer, params, include_test_data=True)
        assert preview["latex"] == response_latex
        assert result["response_latex"] == response_latex
        assert tags == set(result["tags"])
        assert result["is_correct"] == value

    def test_checking_the_value_of_a_physical_quantity_and_create_diagram_for_docs(self):
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "physical_quantity": True,
        }
        response = "2.00 kilometre/hour"
        answer = "2.00 km/h"
        result = evaluation_function(response, answer, params, include_test_data=True)
        create_diagram_for_documentation("physical_quantity", result)
        assert result["is_correct"] == True

    @pytest.mark.parametrize(
        "res,ans,convention,value",
        [
            ("1/ab", "1/(ab)", "implicit_higher_precedence", True),
            ("1/ab", "1/a*b", "implicit_higher_precedence", False),
            ("1/ab", "(1/a)*b", "implicit_higher_precedence", False),
            ("1/ab", "1/(ab)", "equal_precedence", False),
            ("1/ab", "1/a*b", "equal_precedence", True),
            ("1/ab", "(1/a)*b", "equal_precedence", True),
        ]
    )
    def test_implicit_multiplication_convention(self, res, ans, convention, value):
        params = {"strict_syntax": False, "convention": convention}
        result = evaluation_function(res, ans, params)
        assert result["is_correct"] is value

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
            assert result["is_correct"] is True
        for response in atol_response_false:
            result = evaluation_function(response, answer, params)
            assert result["is_correct"] is False
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "rtol": 0.5,
        }
        for response in rtol_response_true:
            result = evaluation_function(response, answer, params)
            assert result["is_correct"] is True
        for response in rtol_response_false:
            result = evaluation_function(response, answer, params)
            assert result["is_correct"] is False

    @pytest.mark.parametrize(
        "response, answer, response_latex, criteria, value, feedback_tags, extra_params",
        [
            (
                "exp(lambda*x)/(1+exp(lambda*x))",
                "c*exp(lambda*x)/(1+c*exp(lambda*x))",
                r"\frac{e^{\lambda \cdot x}}{e^{\lambda \cdot x} + 1}",
                "diff(response,x)=lambda*response*(1-response)",
                True,
                [],
                {"symbols": {"lambda": {"latex": r"\(\lambda\)", "aliases": []}}}
            ),
            (
                "5*exp(lambda*x)/(1+5*exp(lambda*x))",
                "c*exp(lambda*x)/(1+c*exp(lambda*x))",
                r"\frac{5 \cdot e^{\lambda \cdot x}}{5 \cdot e^{\lambda \cdot x} + 1}",
                "diff(response,x)=lambda*response*(1-response)",
                True,
                [],
                {"symbols": {"lambda": {"latex": r"\(\lambda\)", "aliases": []}}}
            ),
            (
                "6*exp(lambda*x)/(1+7*exp(lambda*x))",
                "c*exp(lambda*x)/(1+c*exp(lambda*x))",
                r"\frac{6 \cdot e^{\lambda \cdot x}}{7 \cdot e^{\lambda \cdot x} + 1}",
                "diff(response,x)=lambda*response*(1-response)",
                False,
                [],
                {"symbols": {"lambda": {"latex": r"\(\lambda\)", "aliases": []}}}
            ),
            (
                "c*exp(lambda*x)/(1+c*exp(lambda*x))",
                "c*exp(lambda*x)/(1+c*exp(lambda*x))",
                r"\frac{c \cdot e^{\lambda \cdot x}}{c \cdot e^{\lambda \cdot x} + 1}",
                "diff(response,x)=lambda*response*(1-response)",
                True,
                [],
                {"symbols": {"lambda": {"latex": r"\(\lambda\)", "aliases": []}}}
            ),
            ("5x", "5x", r"5 \cdot x", "answer-response = 0, response/answer = 1", True, ["answer-response = 0_TRUE"], dict()),
            ("x", "5x", r"x", "answer-response = 0, response/answer = 1", False, ["answer-response = 0_FALSE"], dict()),
            ("2x", "x", r"2 \cdot x", "response=2*answer", True, ["response=2*answer_TRUE"], dict()),
            ("x", "x", "x", "response=2*answer", False, ["response=2*answer_FALSE"], dict()),
            ("-x", "x", "- x", "answer=-response", True, ["answer=-response_TRUE"], dict()),
            ("x", "x", "x", "response=-answer", False, ["response=-answer_FALSE"], dict()),
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

    @pytest.mark.parametrize("response", ["epsilon_r", "eps", "eps_r", "e_r"])
    def test_using_input_symbols_alternatives(self, response):
        answer = "epsilon_r"
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "symbols": {
                "epsilon_r": {
                    "latex": r"\(\epsilon_r\)",
                    "aliases": ["eps", "eps_r", "e_r"],
                },
            },
        }
        preview = preview_function(response, params)["preview"]
        result = evaluation_function(response, answer, params)
        assert preview["latex"] == r"\epsilon_r"
        assert result["is_correct"] is True

    @pytest.mark.parametrize(
        "response,value",
        [
            ("k*alpha*(d^2 T)/(dx^2) = k*(dT/dt) - alpha*q_dot", True),
            ("k*alpha*(d^2 T)/(dx^2) = k*(dT/dt) + alpha*q_dot", False),
            ("d^2T/dx^2 + q_dot/k = 1/alpha*(dT/dt)", True),
            ("d^2 T/dx^2 + q_dot/k = 1/alpha*(dT/dt)", True),
            ("(d^2 T)/(dx^2) + q_dot/k = 1/alpha*(dT/dt)", True),
            ("Derivative(T(x,t),x,x) + Derivative(q(x,t),t)/k = 1/alpha*Derivative(T(x,t),t)", True),
        ]
    )
    def test_MECH50001_2_24_a(self, response, value):
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "symbol_assumptions": "('alpha','constant') ('k','constant') ('T','function') ('q','function')",
            'symbols': {
                'alpha': {'aliases': [], 'latex': r'\alpha'},
                'Derivative(q(x,t),t)': {'aliases': ['q_{dot}', 'q_dot'], 'latex': r'\dot{q}'},
                'Derivative(T(x,t),t)': {'aliases': ['dT/dt'], 'latex': r'\frac{\mathrm{d}T}{\mathrm{d}t}'},
                'Derivative(T(x,t),x)': {'aliases': ['dT/dx'], 'latex': r'\frac{\mathrm{d}T}{\mathrm{d}x}'},
                'Derivative(T(x,t),x,x)': {'aliases': ['(d^2 T)/(dx^2)', 'd^2 T/dx^2', 'd^2T/dx^2'], 'latex': r'\frac{\mathrm{d}^2 T}{\mathrm{d}x^2}'},
            },
        }
        answer = "(d^2 T)/(dx^2) + q_dot/k = 1/alpha*(dT/dt)"
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is value

    def test_incorrect_response_with_custom_feedback(self):
        response = "x+1"
        answer = "x+2"
        response = evaluation_function(response, answer, {"feedback_for_incorrect_response": "Custom feedback"})
        assert response["is_correct"] is False
        assert response["feedback"] == "Custom feedback"

    @pytest.mark.parametrize(
        "response, answer, criteria, value, feedback_tags, additional_params",
        [
            (
                "2+2*I",
                "2+2*I",
                "answer=response",
                True,
                [
                    "answer_WRITTEN_AS_CARTESIAN",
                    "response written as answer_TRUE",
                    "answer=response_TRUE",
                    "answer=response_SAME_SYMBOLS_TRUE",
                ],
                {
                    "symbols": {"I": {"aliases": ["i", "j"], "latex": r"\(i\)"}},
                    "complexNumbers": True,
                }
            ),
            (
                "2+2I",
                "2+2*I",
                "answer=response",
                True,
                [
                    "answer_WRITTEN_AS_CARTESIAN",
                    "response written as answer_TRUE",
                    "answer=response_TRUE",
                    "answer=response_SAME_SYMBOLS_TRUE",
                ],
                {
                    "symbols": {"I": {"aliases": ["i", "j"], "latex": r"\(i\)"}},
                    "complexNumbers": True,
                }
            ),
            (
                "2.00+2.00*I",
                "2+2*I",
                "answer=response",
                True,
                [
                    "answer_WRITTEN_AS_CARTESIAN",
                    "response written as answer_TRUE",
                    "answer=response_TRUE",
                    "answer=response_SAME_SYMBOLS_TRUE",
                ],
                {
                    "symbols": {"I": {"aliases": ["i", "j"], "latex": r"\(i\)"}},
                    "complexNumbers": True,
                }
            ),
            (
                "2*I+2",
                "2+2*I",
                "answer=response",
                False,
                [
                    "answer_WRITTEN_AS_CARTESIAN",
                    "response written as answer_FALSE",
                    "answer=response_TRUE",
                    "answer=response_SAME_SYMBOLS_TRUE",
                ],
                {
                    "symbols": {"I": {"aliases": ["i", "j"], "latex": r"\(i\)"}},
                    "complexNumbers": True,
                }
            ),
            (
                "(x-5)^2-6",
                "(x-4)^2-5",
                "response written as answer",
                True,
                [
                    "answer_WRITTEN_AS_UNKNOWN",
                    "response written as answer_TRUE"
                ],
                {"detailed_feedback": True}
            ),
            (
                "(x-4)^2-5",
                "(x-4)^2-5",
                "answer=response",
                True,
                [
                    "answer=response_TRUE",
                    "answer=response_SAME_SYMBOLS_TRUE",
                    "answer_WRITTEN_AS_UNKNOWN",
                    "response written as answer_TRUE"
                ],
                {"detailed_feedback": True}
            ),
            (
                "(x-4)^2 - 5",
                "(x-4)^2-5",
                "answer=response",
                True,
                [
                    "answer=response_TRUE",
                    "answer=response_SAME_SYMBOLS_TRUE",
                    "answer_WRITTEN_AS_UNKNOWN",
                    "response written as answer_TRUE"
                ],
                {"detailed_feedback": True}
            ),
            (
                "x^2-8x+11",
                "(x-4)^2-5",
                "answer=response",
                False,
                [
                    "answer=response_TRUE",
                    "answer=response_SAME_SYMBOLS_TRUE",
                    "answer_WRITTEN_AS_UNKNOWN",
                    "response written as answer_FALSE"
                ],
                {"detailed_feedback": True}
            ),
            (
                "(x-3)^2-3",
                "(x-4)^2-5",
                "answer=response",
                False,
                [
                    "answer=response_FALSE",
                    "answer_WRITTEN_AS_UNKNOWN",
                    "response written as answer_TRUE"
                ],
                {"detailed_feedback": True}
            ),
            (
                "(x+4)^2-5",
                "(x+(-4))^2-5",
                "response written as answer",
                True,
                [
                    "answer_WRITTEN_AS_UNKNOWN",
                    "response written as answer_TRUE"
                ],
                {"detailed_feedback": True}
            ),
            (
                "(x-4)^2+5",
                "(x-4)^2+(-5)",
                "response written as answer",
                True,
                [
                    "answer_WRITTEN_AS_UNKNOWN",
                    "response written as answer_TRUE"
                ],
                {"detailed_feedback": True}
            ),
            (
                "(x+4)^2+5",
                "(x+(-4))^2+(-5)",
                "response written as answer",
                True,
                [
                    "answer_WRITTEN_AS_UNKNOWN",
                    "response written as answer_TRUE"
                ],
                {"detailed_feedback": True}
            ),
        ]
    )
    def test_syntactical_comparison(self, response, answer, criteria, value, feedback_tags, additional_params):
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "syntactical_comparison": True,
            "criteria": criteria,
        }
        params.update(additional_params)
        result = evaluation_function(response, answer, params, include_test_data=True)
        assert result["is_correct"] is value
        assert set(feedback_tags) == set(result["tags"])

    @pytest.mark.parametrize(
        "response, value, tags",
        [
            (
                "2a+2b+2c",
                True,
                [
                    "response proportional to answer_TRUE",
                ],
            ),
            (
                "a+2b+3c",
                False,
                [
                    "response proportional to answer_FALSE",
                ],
            ),
            (
                "pi*(a+b+c)",
                True,
                [
                    "response proportional to answer_TRUE",
                ],
            ),
            (
                "x*(a+b+c)",
                False,
                [
                    "response proportional to answer_FALSE",
                ],
            ),
        ]
    )
    def test_custom_comparison_with_criteria_proportional(self, response, value, tags):
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "criteria": "response proportional to answer",
        }
        answer = "a+b+c"
        result = evaluation_function(response, answer, params, include_test_data=True)
        assert result["is_correct"] is value
        assert set(tags) == set(result["tags"])

    @pytest.mark.parametrize(
        "response, value, tags",
        [
            (
                "2*x^2+0.5+0.25*sin(x)^2",
                False,
                [
                    "answer <= response_TRUE",
                    "2+answer > response_UNKNOWN",
                ]
            ),
        ]
    )
    def test_custom_comparison_with_criteria_order(self, response, value, tags):
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "criteria": "answer <= response, 2+answer > response",
            "symbol_assumptions": "('x', 'real')",
        }
        answer = "2*x^2"
        result = evaluation_function(response, answer, params, include_test_data=True)
        create_diagram_for_documentation("custom_comparison_with_criteria_order", result)
#        with open("diagrams.html", "w") as f:
#            f.write(r'<!DOCTYPE html><html lang="en"><body><style>.mermaid {display: inline-flex;}</style>'+'\n')
#            for g in result["criteria_graphs_vis"].values():
#                print(g)
#                f.write('<pre class="mermaid">\n'+g+'\n</pre>\n')
#            f.write('<script type="module"> import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";</script></body></html>')
        assert result["is_correct"] is value
        assert set(tags) == set(result["tags"])

    @pytest.mark.parametrize(
        "response, value, tags",
        [
            (
                "pi*n",
                True,
                [
                    "sin(response)=0_TRUE",
                    "sin(response)=0_SAME_SYMBOLS_TRUE",
                    "response contains n_TRUE",
                ],
            ),
        ]
    )
    def test_custom_comparison_with_criteria_contains(self, response, value, tags):
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "criteria": "sin(response)=0, response contains n",
            "symbols": {
                "n": {
                    "latex": r"\(n\)",
                    "aliases": ["i", "k", "N", "I", "K"],
                },
            },
            "symbol_assumptions": "('n', 'integer')"
        }
        answer = "0"
        result = evaluation_function(response, answer, params, include_test_data=True)
        assert result["is_correct"] is value
        assert set(tags) == set(result["tags"])

    @pytest.mark.parametrize(
        "response, answer, criteria, value, feedback_tags, custom_feedback, additional_params",
        [
            (
                "2*x^2+0.5+0.25*sin(x)^2",
                "2x^2",
                "answer <= response, 2+answer > response",
                False,
                [
                    "answer <= response_TRUE",
                    "2+answer > response_UNKNOWN",
                ],
                {
                    "answer <= response_TRUE": "Custom response true",
                    "2+answer > response_UNKNOWN": "μ Custom response unknown",
                },
                {
                    "symbol_assumptions": "('x', 'real')",
                }
            ),
        ]
    )
    def test_criteria_custom_feedback(self, response, answer, criteria, value, feedback_tags, custom_feedback, additional_params):
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "criteria": criteria,
            "custom_feedback": custom_feedback,
        }
        params.update(additional_params)
        result = evaluation_function(response, answer, params, include_test_data=True)
        assert result["is_correct"] is value
        assert set(feedback_tags) == set(result["tags"])
        for string in custom_feedback.values():
            assert string in result["feedback"]

if __name__ == "__main__":
    pytest.main(['-sk not slow', "--tb=line", os.path.abspath(__file__)])
