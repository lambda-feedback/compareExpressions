import pytest

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

    The symbolic preview itself is tested in the lambdafeedback-expression-parsing
    package. The physical quantity preview is tested in physical_quantity_preview_test.py.
    """

    def test_empty_latex_expression(self):
        response = ""
        params = dict(is_latex=True)
        result = preview_function(response, params)
        assert "preview" in result.keys()

        preview = result["preview"]
        assert preview["latex"] == ""

    def test_empty_non_latex_expression(self):
        response = ""
        params = dict(is_latex=False)
        result = preview_function(response, params)
        assert "preview" in result.keys()

        preview = result["preview"]
        assert preview["sympy"] == ""

    def test_latex_and_sympy_are_returned(self):
        response = "x+1"
        params = dict(is_latex=True)
        result = preview_function(response, params)
        assert "preview" in result.keys()

        preview = result["preview"]
        assert "latex" in preview.keys()
        assert "sympy" in preview.keys()

        response = "x+1"
        params = dict(is_latex=False)
        result = preview_function(response, params)
        assert "preview" in result

        preview = result["preview"]
        assert "latex" in preview
        assert "sympy" in preview

    def test_natural_logarithm_notation(self):
        response = "ln(x)"
        params = dict(is_latex=False)
        result = preview_function(response, params)
        assert "preview" in result.keys()

        preview = result["preview"]
        assert preview["latex"] == r"\ln{\left(x \right)}"

    @pytest.mark.parametrize(
        "response, is_latex, elementary_functions,  response_latex, response_sympy", [
            ("e", False, True, "e", "E",),
            ("oo", False, True, "\\infty", "oo"),
            ("ex", False, True, "e \\cdot x", "Ex"),
            ("e * x", False, True,  "e \\cdot x", "E * x"),
            ("E", False, True, "e", "E", ),
            ("e", False, False, "e", "e",),
            ("ex", False, False, "e \\cdot x", "ex"),
            ("e * x", False, False, "e \\cdot x", "e * x"),
            ("E", False, False, "E", "E",),
            ("E", True, True, "E", "E",),
            ("e", True, False, "e", "e",),
            ("ex", True, False, "ex", "e*x"),
            ("e * x", True, False, "e * x", "e*x"),
            ("E", True, False, "E", "E",),
            ("ER_2", True, False, "ER_2", "E*R_2",),
            ("exp(1)", False, True, "e^{1}", "exp(1)"),
            ("e**1", False, True, "e^{1}", "E**1"),
            ("e^{1}", True, True, "e^{1}", "e"),
            ("exp(0)", False, True, "e^{0}", "exp(0)"),
            ("e**0", False, True, "e^{0}", "E**0"),
            ("e^{0}", True, True, "e^{0}", "1"),
            ("exp(2)", False, True, "e^{2}", "exp(2)"),
            ("e**2", False, True, "e^{2}", "E**2"),
            ("e^{2}", True, True, "e^{2}", "e**2"),
            ("exp(x)", False, True, "e^{x}", "exp(x)"),
            ("e**x", False, True, "e^{x}", "E**x"),
            ("e^{x}", True, True, "e^{x}", "e**x")
        ]
    )
    def test_eulers_number_notation(self, response, is_latex, elementary_functions, response_latex, response_sympy):
        params = dict(is_latex=is_latex, elementary_functions=elementary_functions, strict_syntax=False)
        result = preview_function(response, params)
        assert "preview" in result.keys()

        preview = result["preview"]
        assert preview["latex"] == response_latex
        assert preview["sympy"] == response_sympy

    @pytest.mark.parametrize(
        "response, is_latex, response_latex, response_sympy, symbols", [
            ("e**ea", False, "e^{ea}", "E**ea", {"ea": {"aliases": ["ea", "Ea"], "latex": "ea"}}),
            ("e**Ea", False, "e^{ea}", "E**ea", {"ea": {"aliases": ["ea", "Ea"], "latex": "ea"}}),
            ("e^{ea}", True, "e^{ea}", "e**ea", {"ea": {"aliases": ["ea", "Ea"], "latex": "ea"}}),
            ("e^{Ea}", True, "e^{Ea}", "e**ea", {"ea": {"aliases": ["ea", "Ea"], "latex": "ea"}}),
            ("e**aea", False, "e^{aea}", "E**aea", {"aea": {"aliases": ["aea", "aEa"], "latex": "aea"}}),
            ("e**aEa", False, "e^{aea}", "E**aea", {"aea": {"aliases": ["aea", "aEa"], "latex": "aea"}}),
            ("e^{aea}", True, "e^{aea}", "e**aea", {"aea": {"aliases": ["aea", "aEa"], "latex": "aea"}}),
            ("e^{aEa}", True, "e^{aEa}", "e**aea", {"aea": {"aliases": ["aea", "aEa"], "latex": "aea"}}),
        ]
    )
    def test_e_latex(self, response, is_latex, response_latex, response_sympy, symbols):
        params = {
            "is_latex": is_latex,
            "strict_syntax": False,
            "elementary_functions": True,
            "symbols": symbols,
        }

        result = preview_function(response, params)
        assert "preview" in result.keys()
        preview = result["preview"]

        assert preview["latex"] == response_latex, "latex_error"
        assert preview["sympy"] == response_sympy, "sympy_error"

    @pytest.mark.parametrize(
        "response, is_latex, response_latex, response_sympy, symbols", [
            ("ab", False, "ab", "ab", {"ab": {"aliases": ["Ab", "AB", "aB"], "latex": "ab"}}),
            ("Ab", False, "ab", "ab", {"ab": {"aliases": ["Ab", "AB", "aB"], "latex": "ab"}}),
            ("aB", False, "ab", "ab", {"ab": {"aliases": ["Ab", "AB", "aB"], "latex": "ab"}}),
            ("AB", False, "ab", "ab", {"ab": {"aliases": ["Ab", "AB", "aB"], "latex": "ab"}}),
            ("ab", True, "ab", "ab", {"ab": {"aliases": ["Ab", "AB", "aB"], "latex": "ab"}}),
            ("Ab", True, "Ab", "ab", {"ab": {"aliases": ["Ab", "AB", "aB"], "latex": "ab"}}),
            ("aB", True, "aB", "ab", {"ab": {"aliases": ["Ab", "AB", "aB"], "latex": "ab"}}),
            ("AB", True, "AB", "ab", {"ab": {"aliases": ["Ab", "AB", "aB"], "latex": "ab"}}),
        ]
    )
    def test_alias(self, response, is_latex, response_latex, response_sympy, symbols):
        params = {
            "is_latex": is_latex,
            "strict_syntax": False,
            "elementary_functions": True,
            "symbols": symbols,
        }

        result = preview_function(response, params)
        assert "preview" in result.keys()
        preview = result["preview"]

        assert preview["latex"] == response_latex, "latex error"
        assert preview["sympy"] == response_sympy, "sympy error"

    @pytest.mark.parametrize(
        "response, is_latex, response_latex, response_sympy",
        [
            ("plus_minus x", False, '\\left\\{- x,~x\\right\\}', "plus_minus x"),
            ("\\pm x", True, '\\pm x', '{-x, x}'),
            (r"\pm x^{2}+\mp y^{2}", True, r"\pm x^{2}+\mp y^{2}", "{-x**2 + y**2, x**2 - y**2}"),
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
        params = dict(**params)
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
        params = dict(**params)
        result = preview_function("x + y = y + x", params)
        assert result["preview"]["latex"] == "x + y=x + y"
        assert result["preview"]["sympy"] == "x + y=y + x"

    def test_multi_character_implicit_multi_variable(self):
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "symbols": {
                "a": {"aliases": ["a"], "latex": "a"},
                "bc": {"aliases": ["bc"], "latex": "bc"},
                "d": {"aliases": ["d"], "latex": "d"}
            },
        }

        response_full = "a/(bc*d)"
        response_implicit_bracket = "a/(bcd)"
        response_implicit_no_bracket = "a/bcd"

        result = preview_function(response_full, params)
        assert result["preview"]["latex"] == '\\frac{a}{bc \\cdot d}'
        assert result["preview"]["sympy"] == "a/(bc*d)"

        result = preview_function(response_implicit_bracket, params)
        assert result["preview"]["latex"] == '\\frac{a}{bc \\cdot d}'
        assert result["preview"]["sympy"] == "a/(bcd)"

        result = preview_function(response_implicit_no_bracket, params)
        assert result["preview"]["latex"] =='\\frac{a}{bc \\cdot d}'
        assert result["preview"]["sympy"] == "a/bcd"

    @pytest.mark.parametrize(
        "response, is_latex, latex, sympy", [
            ("A/s(e**(-a*s)-e**(-b*s))", False, r"\frac{A \cdot \left(e^{- a \cdot s} - e^{- b \cdot s}\right)}{s}", "A/s( E**(-a*s)- E**(-b*s))"),
            ("A/s(e**(-as)-e**(-bs))", False, r"\frac{A \cdot \left(e^{- a \cdot s} - e^{- b \cdot s}\right)}{s}", "A/s( E**(-as)- E**(-bs))"),
            ("(A/s)( e^{-a*s}-e^{-b*s})", True, r"(A/s)( e^{-a*s}-e^{-b*s})", "A*(-1/e**(b*s) + e**(-a*s))/s"),
            ("(A/s)( e^{-as}-e^{-bs})", True, r"(A/s)( e^{-as}-e^{-bs})", "A*(-1/e**(b*s) + e**(-a*s))/s"),
        ]
    )
    def test_laplace_transforms(self, response, is_latex, latex, sympy):
        params = {
            "is_latex": is_latex,
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
        }

        result = preview_function(response, params)
        assert result["preview"]["latex"] == latex
        assert result["preview"]["sympy"] == sympy

    @pytest.mark.parametrize(
        "response, is_latex, latex, sympy", [
            ("(x+y)*(x+z)", False, "\\left(x + y\\right) \\cdot \\left(x + z\\right)","(x+y)*(x+z)"),
            ("(x+y)*x+z", False, "x \\cdot \\left(x + y\\right) + z", "(x+y)*x+z"),
            ("x+y*(x+z)", False, "x + y \\cdot \\left(x + z\\right)", "x+y*(x+z)"),
            ("[x+y]*[x+z]", False, "\\left(x + y\\right) \\cdot \\left(x + z\\right)", "(x+y)*(x+z)"),
            ("[x+y]*x+z", False, "x \\cdot \\left(x + y\\right) + z", "(x+y)*x+z"),
            ("x+y*[x+z]", False, "x + y \\cdot \\left(x + z\\right)", "x+y*(x+z)"),
            ("{x+y}*{x+z}", False, "\\left(x + y\\right) \\cdot \\left(x + z\\right)", "(x+y)*(x+z)"),
            ("{x+y}*x+z", False, "x \\cdot \\left(x + y\\right) + z", "(x+y)*x+z"),
            ("x+y*{x+z}", False, "x + y \\cdot \\left(x + z\\right)", "x+y*(x+z)"),
        ]
    )
    def test_brackets(self, response, is_latex, latex, sympy):
        params = {
            "is_latex": is_latex,
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
        }

        result = preview_function(response, params)
        assert result["preview"]["latex"] == latex
        assert result["preview"]["sympy"] == sympy

    @pytest.mark.parametrize(
        "response, latex, sympy", [
            ("(x+y)*(x+z)", "\\left(x + y\\right) \\cdot \\left(x + z\\right)", "(x+y)*(x+z)"),
            ("(x+y)*x+z", "x \\cdot \\left(x + y\\right) + z", "(x+y)*x+z"),
            ("x+y*(x+z)", "x + y \\cdot \\left(x + z\\right)", "x+y*(x+z)"),
        ]
    )
    def test_brackets_strict_syntax_parentheses_still_work(self, response, latex, sympy):
        params = {
            "is_latex": False,
            "strict_syntax": True,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
        }

        result = preview_function(response, params)
        assert result["preview"]["latex"] == latex
        assert result["preview"]["sympy"] == sympy

    @pytest.mark.parametrize(
        "response", [
            "[x+y]*[x+z]",
            "[x+y]*x+z",
            "x+y*[x+z]",
        ]
    )
    def test_brackets_rejected_with_strict_syntax(self, response):
        params = {
            "is_latex": False,
            "strict_syntax": True,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
        }

        with pytest.raises(ValueError):
            preview_function(response, params)

    @pytest.mark.parametrize(
        "response", [
            "{x+y}*{x+z}",
            "{x+y}*x+z",
            "x+y*{x+z}",
        ]
    )
    def test_curly_braces_not_converted_with_strict_syntax(self, response):
        # With strict syntax `{}` is a set literal, not a bracket, and arithmetic on
        # sets is rejected (SymPy deprecates it, and evaluating it used to crash).
        params = {
            "is_latex": False,
            "strict_syntax": True,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
        }

        with pytest.raises(ValueError):
            preview_function(response, params)

    @pytest.mark.parametrize("strict_syntax", [False, True])
    def test_curly_brace_multiple_answers_still_works(self, strict_syntax):
        params = {
            "is_latex": False,
            "strict_syntax": strict_syntax,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
        }

        result = preview_function("{1, 2}", params)
        assert result["preview"]["latex"] == "\\left\\{1,~2\\right\\}"
        assert result["preview"]["sympy"] == "{1, 2}"
