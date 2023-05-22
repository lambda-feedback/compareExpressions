import pytest
import os

from .symbolic_equal import evaluation_function
from .expression_utilities import elementary_functions_names, substitute
from .evaluation_response_utilities import EvaluationResponse
from .feedback.symbolic_comparison import internal as symbolic_comparison_internal_messages

def generate_input_variations(response, answer):
    input_variations = [(response, answer)]
    variation_definitions = [lambda x : x.replace('**','^'),
                             lambda x : x.replace('**','^').replace('*',' '),
                             lambda x : x.replace('**','^').replace('*','')]
    for variation in variation_definitions:
        response_variation = variation(response)
        answer_variation = variation(answer)
        if (response_variation != response):
            input_variations.append((response_variation, answer))
        if (answer_variation != answer):
            input_variations.append((response, answer_variation))
        if (response_variation != response) and (answer_variation != answer):
            input_variations.append((response_variation, answer_variation))
    return input_variations

def generate_input_variations_from_elementary_function_aliases(response, answer, params):
    input_variations = [(response, answer)]
    names = []
    alias_substitutions = []
    for (name,alias) in elementary_functions_names:
        if name in answer or name in response:
            names.append(name)
            alias_substitutions += [(name, x) for x in alias]
    alias_substitutions.sort(key=lambda x: -len(x[0]))
    for substitution in alias_substitutions:
        subs_answer = substitute(answer, alias_substitutions)
        subs_response = substitute(response, alias_substitutions)
        input_variations += [(subs_answer, subs_response)]
    return input_variations

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

    Use evaluation_function() to check your algorithm works
    as it should.
    """

    response = "3*x**2 + 3*x +  5"
    answer = "2+3+x+2*x + x*x*3"
    @pytest.mark.parametrize("response,answer", generate_input_variations(response, answer))
    def test_simple_polynomial_correct(self, response, answer):
        params = {"strict_syntax": False}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True

    response = "3*longName**2 + 3*longName + 5"
    answer = "2+3+longName+2*longName + 3*longName * longName"
    @pytest.mark.parametrize("response,answer", generate_input_variations(response, answer))
    def test_simple_polynomial_with_input_symbols_correct(self, response, answer):
        params = {"strict_syntax": False, "input_symbols": [["longName",[]]]}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True

    def test_simple_polynomial_with_input_symbols_implicit_correct(self):
        response = "abcxyz"
        answer = "abc*xyz"
        params = {"strict_syntax": False, "input_symbols": [["abc",[]],["xyz",[]]]}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True

    response = "3*x**2 + 3*x +  5"
    answer = "2+3+x+2*x + x*x*3 - x"
    @pytest.mark.parametrize("response,answer", generate_input_variations(response, answer))
    def test_simple_polynomial_incorrect(self, response, answer):
        params = {"strict_syntax": False}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is False

    response = "cos(x)**2 + sin(x)**2 + y"
    answer = "y + 1"
    @pytest.mark.parametrize("response,answer", generate_input_variations(response, answer))
    def test_simple_trig_correct(self, response, answer):
        params = {"strict_syntax": False}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True

    response = "1/( ((x+1)**2) * ( sqrt(1-(x/(x+1))**2) ) )"
    answer = "1/((x+1)*(sqrt(2x+1)))"
    input_variations = generate_input_variations(response, answer)
    response = "1/((x+1)*(sqrt(2x+1)))"
    answer = "1/( ((x+1)**2) * ( sqrt(1-(x/(x+1))**2) ) )"
    input_variations += generate_input_variations(response, answer)
    @pytest.mark.parametrize("response,answer", generate_input_variations(response, answer))
    def test_complicated_expression_correct(self, response, answer):
        params = {"strict_syntax": False, "symbol_assumptions": "('x','positive')"}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True

    input_variations = []
    fractional_powers_res = ["sqrt(v)/sqrt(g)","v**(1/2)/g**(1/2)","v**(0.5)/g**(0.5)"]
    fractional_powers_ans = ["sqrt(v/g)","(v/g)**(1/2)","(v/g)**(0.5)"]
    for response in fractional_powers_ans:
        for answer in fractional_powers_ans:
            input_variations += generate_input_variations(response, answer)
    fractional_powers_res = ["v**(1/5)/g**(1/5)","v**(0.2)/g**(0.2)"]
    fractional_powers_ans = ["(v/g)**(1/5)","(v/g)**(0.2)"]
    for response in fractional_powers_ans:
        for answer in fractional_powers_ans:
            input_variations += generate_input_variations(response, answer)
    response = "v**(1/n)/g**(1/n)"
    answer = "(v/g)**(1/n)"
    input_variations += generate_input_variations(response, answer)
    @pytest.mark.parametrize("response,answer", input_variations)
    def test_simple_fractional_powers_correct(self, response, answer):
        params = {"strict_syntax": False, "symbol_assumptions": "('g','positive') ('v','positive')"}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True

    def test_invalid_user_expression(self):
        response = "a*(b+c"
        answer = "a*(b+c)"
        result = evaluation_function(response,answer,{})
        assert "PARSE_ERROR" in result["tags"]

    def test_invalid_author_expression(self):
        response = "3*x"
        answer = "3x"
        e = None
        with pytest.raises(Exception) as e:
            evaluation_function(response, answer, {})
        assert e is not None

    response = "1+tan(x)**2 + y"
    answer = "sec(x)**2 + y"
    @pytest.mark.parametrize("response,answer", generate_input_variations(response, answer))
    def test_recp_trig_correct(self, response, answer):
        params = {"strict_syntax": False}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True

    response = "x/2"
    answer = "0.5*x"
    @pytest.mark.parametrize("response,answer", generate_input_variations(response, answer))
    def test_decimals_correct(self, response, answer):
        params = {"strict_syntax": False}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True

    response = "|x|+y"
    answer = "Abs(x)+y"
    @pytest.mark.parametrize("response,answer", generate_input_variations(response, answer))
    def test_absolute_correct(self, response, answer):
        params = {"strict_syntax": False}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True

    response = "a|x|+|y|"
    answer = "a*Abs(x)+Abs(y)"
    input_variations = generate_input_variations(response, answer)
    response = "|x|a+|y|"
    answer = "a*Abs(x)+Abs(y)"
    input_variations += generate_input_variations(response, answer)
    @pytest.mark.parametrize("response,answer", input_variations)
    def test_absolute_ambiguity(self, response, answer):
        params = {"strict_syntax": False, "elementary_functions": True}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True
        assert "ABSOLUTE_VALUE_NOTATION_AMBIGUITY" in result["tags"]

    response = "|x+|y||"
    answer = "Abs(x+Abs(y))"
    input_variations = generate_input_variations(response, answer)
    response = "a*|x+b*|y||"
    answer = "a*Abs(x+b*Abs(y))"
    input_variations += generate_input_variations(response, answer)
    @pytest.mark.parametrize("response,answer", input_variations)
    def test_nested_absolute_response(self, response, answer):
        params = {"strict_syntax": False, "elementary_functions": True}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True
        assert "ABSOLUTE_VALUE_NOTATION_AMBIGUITY" in result["tags"]

    @pytest.mark.parametrize(
        "response,answer",
        [
            ("|x|+|y|", "Abs(x)+Abs(y)"),
            ("|x|+|y|", "|x|+|y|"),
            ("|x+|y||", "|x+|y||"),
            ("a*|x+b*|y||", "a*|x+b*|y||"),
            
        ]
    )
    def test_many_absolute_response(self, response, answer):
        response = "|x|+|y|"
        answer = "Abs(x)+Abs(y)"
        result = evaluation_function(response, answer, {})
        assert result["is_correct"] is True

    def test_absolute_ambiguity_response(self):
        response = "|a+b|c+d|e+f|"
        answer = "|a+b|*c+d*|e+f|"
        result = evaluation_function(response, answer, {})
        assert "ABSOLUTE_VALUE_NOTATION_AMBIGUITY" in result["tags"]

    def test_absolute_ambiguity_answer(self):
        response = "|a+b|*c+d*|e+f|"
        answer = "|a+b|c+d|e+f|"

        e = None
        with pytest.raises(Exception) as e:
            evaluation_function(response, answer, {})
        assert e is not None
        assert e.value.args[1] == "ABSOLUTE_VALUE_NOTATION_AMBIGUITY"

    def test_clashing_symbols(self):
        params = {}
        response = "beta+gamma+zeta+I+N+O+Q+S+E"
        answer = "E+S+Q+O+N+I+zeta+gamma+beta"
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True

    response = "pi"
    answer = "2*asin(1)"
    @pytest.mark.parametrize("response,answer", generate_input_variations(response, answer))
    def test_special_constants(self, response, answer):
        response = "pi"
        answer = "2*asin(1)"
        params = {"strict_syntax": False, "elementary_functions": True}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True

    response = "I"
    answer = "(-1)**(1/2)"
    @pytest.mark.parametrize("response,answer", generate_input_variations(response, answer))
    def test_complex_numbers(self, response, answer):
        params = {"complexNumbers": True, "strict_syntax": False}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True

    response = "beta(1,x)"
    answer = "1/x"
    input_variations = generate_input_variations(response, answer)
    response = "gamma(5)"
    answer = "24"
    input_variations += generate_input_variations(response, answer)
    response = "zeta(2)"
    answer = "pi**2/6"
    input_variations += generate_input_variations(response, answer)
    @pytest.mark.parametrize("response,answer", generate_input_variations(response, answer))
    def test_special_functions(self, response, answer):
        params = {"specialFunctions": True, "strict_syntax": False}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True

    response = "-minus_plus x**2 - plus_minus y**2"
    answer = "plus_minus x**2 + minus_plus y**2"
    @pytest.mark.parametrize("response,answer", generate_input_variations(response, answer))
    def test_plus_minus_all_correct(self, response, answer):
        params = {"strict_syntax": False}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True

    response = "- -+ x**2 - +- y**2"
    answer = "+- x**2 + -+ y**2"
    @pytest.mark.parametrize("response,answer", generate_input_variations(response, answer))
    def test_plus_minus_replace_symbols_all_correct(self, response, answer):
        params = {"plus_minus": "+-", "minus_plus": "-+", "strict_syntax": False}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True

    response = "plus_minus x**2 - minus_plus y**2"
    answer = "plus_minus x**2 + minus_plus y**2"
    @pytest.mark.parametrize("response,answer", generate_input_variations(response, answer))
    def test_plus_minus_all_incorrect(self, response, answer):
        params = {"strict_syntax": False}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is False

    response = "-minus_plus x**2 - plus_minus y**2"
    answer = "plus_minus x**2 + minus_plus y**2"
    @pytest.mark.parametrize("response,answer", generate_input_variations(response, answer))
    def test_plus_minus_all_responses_correct(self, response, answer):
        params = {"multiple_answers_criteria": "all_responses", "strict_syntax": False}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True

    response = "-x**2 - y**2"
    answer = "plus_minus x**2 + minus_plus y**2"
    @pytest.mark.parametrize("response,answer", generate_input_variations(response, answer))
    def test_plus_minus_all_responses_incorrect(self, response, answer):
        params = {"multiple_answers_criteria": "all_responses", "strict_syntax": False}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is False

    response = "-x**2"
    answer = "plus_minus minus_plus x**2"
    @pytest.mark.parametrize("response,answer", generate_input_variations(response, answer))
    def test_plus_minus_all_answers_correct(self, response, answer):
        params = {"multiple_answers_criteria": "all_responses", "strict_syntax": False}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True

    response = "x**2"
    answer = "plus_minus minus_plus x**2"
    @pytest.mark.parametrize("response,answer", generate_input_variations(response, answer))
    def test_plus_minus_all_answers_incorrect(self, response, answer):
        params = {"multiple_answers_criteria": "all_responses", "strict_syntax": False}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is False

    def test_simplified_in_correct_response(self):
        response = "a*x + b"
        answer = "b + a*x"
        result = evaluation_function(response, answer, {})
        assert result["is_correct"] is True
        assert result["response_simplified"] == "a*x + b"

    def test_simplified_in_wrong_response(self):
        response = "a*x + b"
        answer = "b + a*x + 8"
        result = evaluation_function(response, answer, {})
        assert result["is_correct"] is False
        assert result["response_simplified"] == "a*x + b"

    response = "2*x**2 = 10*y**2+14"
    answer = "x**2-5*y**2-7=0"
    @pytest.mark.parametrize("response,answer", generate_input_variations(response, answer))
    def test_equality_sign_in_answer_and_response_correct(self, response, answer):
        params = {"strict_syntax": False}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True

    response = "2*x**2 = 10*y**2+20"
    answer = "x**2-5*y**2-7=0"
    @pytest.mark.parametrize("response,answer", generate_input_variations(response, answer))
    def test_equality_sign_in_answer_and_response_incorrect(self, response, answer):
        params = {"strict_syntax": False}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is False

    response = "2*x**2-10*y**2-14"
    answer = "x**2-5*y**2-7=0"
    @pytest.mark.parametrize("response,answer", generate_input_variations(response, answer))
    def test_equality_sign_in_answer_not_response(self, response, answer):
        params = {"strict_syntax": False}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is False
        assert "EXPRESSION_NOT_EQUALITY" in result["tags"]

    response = "2*x**2 = 10*y**2+14"
    answer = "x**2-5*y**2-7"
    @pytest.mark.parametrize("response,answer", generate_input_variations(response, answer))
    def test_equality_sign_in_response_not_answer(self, response, answer):
        params = {"strict_syntax": False}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is False
        assert "EQUALITY_NOT_EXPRESSION" in result["tags"]

    def test_empty_input_symbols_codes_and_alternatives(self):
        answer = '(1+(gamma-1)/2)((-1)/(gamma-1))'
        response = '(1+(gamma-1)/2)((-1)/(gamma-1))'
        params = {'strict_syntax': False,
                   'input_symbols': [['gamma', ['']], ['', ['A']], [' ', ['B']], ['C', ['  ']]]
                 }
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True

    @pytest.mark.parametrize(
        "description,response,answer,tolerance,outcome",
        [
            (
                "Correct response, tolerance specified with atol",
                "6.73",
                "sqrt(3)+5",
                {"atol": 0.005},
                True
            ),
            (
                "Incorrect response, tolerance specified with atol",
                "6.7",
                "sqrt(3)+5",
                {"atol": 0.005},
                False
            ),
            (
                "Correct response, tolerance specified with rtol",
                "6.73",
                "sqrt(3)+5",
                {"rtol": 0.0005},
                True
            ),
            (
                "Incorrect response, tolerance specified with rtol",
                "6.7",
                "sqrt(3)+5",
                {"rtol": 0.0005},
                False
            ),
            (
                "Response is not constant, tolerance specified with atol",
                "6.7+x",
                "sqrt(3)+5",
                {"atol": 0.005},
                False
            ),
            (
                "Answer is not constant, tolerance specified with atol",
                "6.73",
                "sqrt(3)+x",
                {"atol": 0.005},
                False
            ),
            (
                "Response is not constant, tolerance specified with rtol",
                "6.7+x",
                "sqrt(3)+5",
                {"rtol": 0.0005},
                False
            ),
            (
                "Answer is not constant, tolerance specified with rtol",
                "6.73",
                "sqrt(3)+x",
                {"rtol": 0.0005},
                False
            ),
        ]
    )
    def test_numerical_comparison(self, description, response, answer, tolerance, outcome):
        params = {"numerical": True}
        params.update(tolerance)
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is outcome

    def test_warning_inappropriate_symbol(self):
        answer = '2**4'
        response = '2^4'
        params = {'strict_syntax': True }
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is False
        assert "NOTATION_WARNING" in result["tags"]

    @pytest.mark.parametrize(
        "response,answer",
        [
            (
                '0,5',
                '0.5'
            ),
            (
                '(0,002*6800*v)/1,2',
                '(0,002*6800*v)/1.2'
            ),
            (
                '-∞',
                '-inf'
            ),
            (
                'x.y',
                'x*y'
            ),
        ]
    )
    def test_error_inappropriate_symbol(self, response, answer):
        params = {'strict_syntax': True }
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is False
        assert "PARSE_ERROR" in result["tags"]

    @pytest.mark.parametrize(
        "description,response",
        [
            (
                "Empty response",
                "",
            ),
            (
                "Whitespace response",
                "  \t\n",
            ),
        ]
    )
    def test_empty_response(self, description, response):
        answer = "5*x"
        result = evaluation_function(response, answer, {})
        assert "NO_RESPONSE" in result["tags"]

    @pytest.mark.parametrize(
        "description,answer",
        [
            (
                'Empty answer',
                ''
            ),
            (
                'Whitespace answer',
                '  \t\n'
            ),
        ]
    )
    def test_empty_answer(self, description, answer):
        response = "5*x"
        e = None
        with pytest.raises(Exception) as e:
            evaluation_function(response, answer, {})
        assert e is not None
        assert e.value.args[0] == "No answer was given."

    @pytest.mark.parametrize(
        "description,response,answer,outcome",
        [
            (
                "With `fx` in response",
                "-A*exp(x/b)*sin(y/b)+fx+C",
                "-A*exp(x/b)*sin(y/b)+fx+C",
                True
            ),
            (
                "Without `-` in response",
                "-A*exp(x/b)*sin(y/b)+fx+C",
                "A*exp(x/b)*sin(y/b)+fx+C",
                False
            ),
            (
                "With `f(x)` in response",
                "A*exp(x/b)*sin(y/b)+f(x)+C",
                "-A*exp(x/b)*sin(y/b)+f(x)+C",
                False
            ),
        ]
    )
    def test_slow_response(self, description, response, answer, outcome):
        params = {"strict_syntax": False,
                  "input_symbols": [["fx",["f","f_x","fofx"]],\
                                    ["C",["c","k","K"]],\
                                    ["A",["a"]],\
                                    ["B",["b"]],\
                                    ["x",["X"]],\
                                    ["y",["Y"]]]}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is outcome

    def test_pi_with_rtol(self):
        answer = "pi"
        response = "3.14"
        params = {"strict_syntax": False,
                  "rtol": 0.05,
                  "input_symbols": [["pi",["Pi","PI","π"]]]}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True

    @pytest.mark.parametrize(
        "response,outcome",
        [
            (
                res,
                False
            ) for res in [
                "-(sin(xy)y+(e^y))/(x(e^y+sin(xy)x))"
                "sin(xy)y",
                "sin(xy)x",
                "x(e^y+sin(xy)x)",
                "e^y+sin(xy)x"
            ]
        ]
    )
    def test_PHYS40002_2_2_b(self, response, outcome):
        params = {"strict_syntax": False}
        answer = "-(y*sin(x*y) + e^(y)) / (x*(e^(y) + sin(x*y)))"
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is outcome

    @pytest.mark.parametrize(
        "response,outcome",
        [
            (
                res,
                True
            ) for res in [
                "6*cos(5*x+1)-90*x*sin(5*x+1)-225*x**2*cos(5*x+1)+125*x**3*sin(5*x+1)",
                "6cos(5x+1)-90x*sin(5x+1)-225x^2cos(5x+1)+125x^3sin(5x+1)",
            ]
        ]+[
            (
                res,
                False
            ) for res in [
                "-90xsin(5x+1)",
                "6cos(5x+1)-90xsin(5x+1)-225x^2cos(5x+1)+125x^3sin(5x+1)",
                "(125x^3)*(cos(5x+1))-(225x^2)*(cos(5x+1))-(90x)*(sin(5x+1))+6cos(5x+1)",
            ]
        ]
    )
    def test_PHYS40002_2_6_a(self, response, outcome):
        params = {"strict_syntax": False}
        answer = "6*cos(5*x+1)-90*x*sin(5*x+1)-225*x**2*cos(5*x+1)+125*x**3*sin(5*x+1)"
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is outcome

    params = {"strict_syntax": False, "elementary_functions": True}
    @pytest.mark.parametrize(
        "description,response,answer",
        [("sin",)+var for var in generate_input_variations_from_elementary_function_aliases("Bsin(pi)", "0", params)]
        +[("sinc",)+var for var in generate_input_variations_from_elementary_function_aliases("Bsinc(0)", "B", params)]
        +[("csc",)+var for var in generate_input_variations_from_elementary_function_aliases("Bcsc(pi/2)", "B", params)]
        +[("cos",)+var for var in generate_input_variations_from_elementary_function_aliases("Bcos(pi/2)", "0", params)]
        +[("sec",)+var for var in generate_input_variations_from_elementary_function_aliases("Bsec(0)", "B", params)]
        +[("tan",)+var for var in generate_input_variations_from_elementary_function_aliases("Btan(pi/4)", "B", params)]
        +[("cot",)+var for var in generate_input_variations_from_elementary_function_aliases("Bcot(pi/4)", "B", params)]
        +[("asin",)+var for var in generate_input_variations_from_elementary_function_aliases("Basin(1)", "B*pi/2", params)]
        +[("acsc",)+var for var in generate_input_variations_from_elementary_function_aliases("Bacsc(1)", "B*pi/2", params)]
        +[("acos",)+var for var in generate_input_variations_from_elementary_function_aliases("Bacos(1)", "0", params)]
        +[("asec",)+var for var in generate_input_variations_from_elementary_function_aliases("Basec(1)", "0", params)]
        +[("atan",)+var for var in generate_input_variations_from_elementary_function_aliases("Batan(1)", "B*pi/4", params)]
        +[("acot",)+var for var in generate_input_variations_from_elementary_function_aliases("Bacot(1)", "B*pi/4", params)]
        +[("atan2",)+var for var in generate_input_variations_from_elementary_function_aliases("Batan2(1,1)","B*pi/4", params)]
        +[("sinh",)+var for var in generate_input_variations_from_elementary_function_aliases("Bsinh(x)+Bcosh(x)", "B*exp(x)", params)]
        +[("cosh",)+var for var in generate_input_variations_from_elementary_function_aliases("Bcosh(1)", "B*cosh(-1)", params)]
        +[("tanh",)+var for var in generate_input_variations_from_elementary_function_aliases("B*2*tanh(x)/(1+tanh(x)^2)", "B*tanh(2*x)", params)]
        +[("csch",)+var for var in generate_input_variations_from_elementary_function_aliases("Bcsch(x)", "B/sinh(x)", params)]
        +[("sech",)+var for var in generate_input_variations_from_elementary_function_aliases("Bsech(x)", "B/cosh(x)", params)]
        +[("asinh",)+var for var in generate_input_variations_from_elementary_function_aliases("Basinh(sinh(1))", "B", params)]
        +[("acosh",)+var for var in generate_input_variations_from_elementary_function_aliases("Bacosh(cosh(1))", "B", params)]
        +[("atanh",)+var for var in generate_input_variations_from_elementary_function_aliases("Batanh(tanh(1))", "B", params)]
        +[("asech",)+var for var in generate_input_variations_from_elementary_function_aliases("Bsech(asech(1))", "B", params)]
        +[("exp",)+var for var in generate_input_variations_from_elementary_function_aliases("Bexp(x)*exp(x)", "B*exp(2*x)", params)]
        +[("exp2",)+var for var in generate_input_variations_from_elementary_function_aliases("a+b*E^2", "a+b*exp(2)", params)]
        +[("log",)+var for var in generate_input_variations_from_elementary_function_aliases("Bexp(log(10))", "10B", params)]
        +[("sqrt",)+var for var in generate_input_variations_from_elementary_function_aliases("Bsqrt(4)", "2B", params)]
        +[("sign",)+var for var in generate_input_variations_from_elementary_function_aliases("Bsign(1)", "B", params)]
        +[("abs",)+var for var in generate_input_variations_from_elementary_function_aliases("BAbs(-2)", "2B", params)]
        +[("Max",)+var for var in generate_input_variations_from_elementary_function_aliases("BMax(0,1)", "B", params)]
        +[("Min",)+var for var in generate_input_variations_from_elementary_function_aliases("BMin(1,2)", "B", params)]
        +[("arg",)+var for var in generate_input_variations_from_elementary_function_aliases("Barg(1)", "0", params)]
        +[("ceiling",)+var for var in generate_input_variations_from_elementary_function_aliases("Bceiling(0.6)", "B", params)]
        +[("floor",)+var for var in generate_input_variations_from_elementary_function_aliases("Bfloor(0.6)", "0", params)]
        +[("MECH50001_7.2",)+var for var in generate_input_variations_from_elementary_function_aliases("fs/(1-Mcos(theta))", "fs/(1-M*cos(theta))", params)]
    )
    def test_elementary_functions(self, description, response, answer):
        params = {"strict_syntax": False, "elementary_functions": True}
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True


if __name__ == "__main__":
    pytest.main(['-xsk not slow', "--tb=line", os.path.abspath(__file__)])