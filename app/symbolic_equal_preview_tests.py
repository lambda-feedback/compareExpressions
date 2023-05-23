import unittest

from .symbolic_equal_preview import Params, extract_latex, preview_function
from .symbolic_equal import evaluation_function
from .symbolic_equal_tests import generate_input_variations #, elementary_function_test_cases

# REMARK: If a case is marked with an alternative output, this means that it is difficult in this case to prevent sympy from simplifying for that particular case
elementary_function_test_cases = [
    ("sin", "Bsin(pi)", "0", r"B \sin{\left(\pi \right)}"),
    ("sinc", "Bsinc(0)", "B", r"B 1"), # r"B \sinc{\left(0 \right)}"
    ("csc", "Bcsc(pi/2)", "B", r"B \csc{\left(\frac{\pi}{2} \right)}"),
    ("cos", "Bcos(pi/2)", "0", r"B \cos{\left(\frac{\pi}{2} \right)}"),
    ("sec", "Bsec(0)", "B", r"B \sec{\left(0 \right)}"),
    ("tan", "Btan(pi/4)", "B", r"B \tan{\left(\frac{\pi}{4} \right)}"),
    ("cot", "Bcot(pi/4)", "B", r"B \cot{\left(\frac{\pi}{4} \right)}"),
    ("asin", "Basin(1)", "B*pi/2", r"B \operatorname{asin}{\left(1 \right)}"),
    ("acsc", "Bacsc(1)", "B*pi/2", r"B \operatorname{acsc}{\left(1 \right)}"),
    ("acos", "Bacos(1)", "0", r"B \operatorname{acos}{\left(1 \right)}"),
    ("asec", "Basec(1)", "0", r"B \operatorname{asec}{\left(1 \right)}"),
    ("atan", "Batan(1)", "B*pi/4", r"B \operatorname{atan}{\left(1 \right)}"),
    ("acot", "Bacot(1)", "B*pi/4", r"B \operatorname{acot}{\left(1 \right)}"),
    ("atan2", "Batan2(1,1)","B*pi/4", r"\frac{\pi}{4} B"), # r"B \operatorname{atan2}{\left(1,1 \right)}"
    ("sinh", "Bsinh(x)+Bcosh(x)", "B*exp(x)", r"B \sinh{\left(x \right)} + B \cosh{\left(x \right)}"),
    ("cosh", "Bcosh(1)", "B*cosh(-1)", r"B \cosh{\left(1 \right)}"),
    ("tanh", "2Btanh(x)/(1+tanh(x)^2)", "B*tanh(2*x)", r"\frac{2 B \tanh{\left(x \right)}}{\tanh^{2}{\left(x \right)} + 1}"), # Ideally this case should print tanh(x)^2 instead of tanh^2(x)
    ("csch", "Bcsch(x)", "B/sinh(x)", r"B \operatorname{csch}{\left(x \right)}"),
    ("sech", "Bsech(x)", "B/cosh(x)", r"B \operatorname{sech}{\left(x \right)}"),
    ("asinh", "Basinh(sinh(1))", "B", r"B \operatorname{asinh}{\left(\sinh{\left(1 \right)} \right)}"),
    ("acosh", "Bacosh(cosh(1))", "B", r"B \operatorname{acosh}{\left(\cosh{\left(1 \right)} \right)}"),
    ("atanh", "Batanh(tanh(1))", "B", r"B \operatorname{atanh}{\left(\tanh{\left(1 \right)} \right)}"),
    ("asech", "Bsech(asech(1))", "B", r"B \operatorname{sech}{\left(\operatorname{asech}{\left(1 \right)} \right)}"),
    ("exp", "Bexp(x)exp(x)", "B*exp(2*x)", r"B e^{x} e^{x}"),
    ("exp2", "a+b*E^2", "a+b*exp(2)", r"a + b e^{2}"),
    ("exp3", "a+b*e^2", "a+b*exp(2)", r"a + b e^{2}"),
    ("log", "Bexp(log(10))", "10B", r"B e^{\log{\left(10 \right)}}"),
    ("sqrt", "Bsqrt(4)", "2B", r"\sqrt{4} B"),
    ("sign", "Bsign(1)", "B", r"B \operatorname{sign}{\left(1 \right)}"),
    ("abs", "BAbs(-2)", "2B", r"B \left|{-2}\right|"),
    ("Max", "BMax(0,1)", "B", r"B 1"), # r"B \max{\left(0,1 \right)}"
    ("Min", "BMin(1,2)", "B", "B 1"), # r"B \min{\left(1,2 \right)}"
    ("arg", "Barg(1)", "0", r"B \arg{\left(1 \right)}"),
    ("ceiling", "Bceiling(0.6)", "B", r"B 1"), # r"B \left\lceil 0.6 \right\rceil"),
    ("floor", "Bfloor(0.6)", "0", r"B 0"), # r"B \left\lfloor 0.6 \right\rfloor"),
    ("MECH50001_7.2", "fs/(1-Mcos(theta))", "fs/(1-M*cos(theta))", r"\frac{f s}{1 - M \cos{\left(\theta \right)}}"),
]


class TestPreviewFunction(unittest.TestCase):
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

    def test_empty_latex_expression(self):
        response = ""
        params = Params(is_latex=True)
        result = preview_function(response, params)
        self.assertIn("preview", result)

        preview = result["preview"]
        self.assertEqual(preview["latex"], "")

    def test_empty_sympy_expression(self):
        response = ""
        params = Params(is_latex=False)
        result = preview_function(response, params)
        self.assertIn("preview", result)
        self.assertNotIn("error", result)

        preview = result["preview"]
        self.assertEqual(preview["sympy"], "")

    def test_latex_and_sympy_are_returned(self):
        response = "x+1"
        params = Params(is_latex=True)
        result = preview_function(response, params)
        self.assertIn("preview", result)
        self.assertNotIn("error", result)

        preview = result["preview"]

        self.assertIn("latex", preview)
        self.assertIn("sympy", preview)

        response = "x+1"
        params = Params(is_latex=False)
        result = preview_function(response, params)
        self.assertIn("preview", result)
        self.assertNotIn("error", result)

        preview = result["preview"]

        self.assertIn("latex", preview)
        self.assertIn("sympy", preview)

    def test_doesnt_simplify_latex_by_default(self):
        response = "\\frac{x + x^2 + x}{x}"
        params = Params(is_latex=True)
        result = preview_function(response, params)
        preview = result["preview"]

        self.assertEqual(preview.get("sympy"), "(x**2 + x + x)/x")

    def test_doesnt_simplify_sympy_by_default(self):
        response = "(x + x**2 + x)/x"
        params = Params(is_latex=False)
        result = preview_function(response, params)
        self.assertNotIn("error", result)
        preview = result["preview"]

        self.assertEqual(preview.get("latex"), "\\frac{x^{2} + x + x}{x}")

    def test_simplifies_latex_on_param(self):
        response = "\\frac{x + x^2 + x}{x}"
        params = Params(is_latex=True, simplify=True)
        result = preview_function(response, params)
        self.assertNotIn("error", result)
        preview = result["preview"]

        self.assertEqual(preview.get("sympy"), "x + 2")

    def test_simplifies_sympy_on_param(self):
        response = "(x + x**2 + x)/x"
        params = Params(is_latex=False, simplify=True)
        result = preview_function(response, params)
        self.assertNotIn("error", result)
        preview = result["preview"]

        self.assertEqual(preview.get("latex"), "x + 2")

    def test_sympy_handles_implicit_multiplication(self):
        response = "sin(x) + cos(2x) - 3x**2"
        params = Params(is_latex=False, strict_syntax=False)
        result = preview_function(response, params)
        self.assertNotIn("error", result)

        preview = result["preview"]

        self.assertEqual(
            preview.get("latex"),
            "- 3 x^{2} + \\sin{\\left(x \\right)} "
            "+ \\cos{\\left(2 x \\right)}",
        )

#    def test_latex_with_equality_symbol(self):
#        response = "\\frac{x + x^2 + x}{x} = y"
#
#        params = Params(is_latex=True, simplify=False)
#        result = preview_function(response, params)
#        self.assertNotIn("error", result)
#
#        preview = result["preview"]
#
#        self.assertEqual(preview.get("sympy"), "Eq((x**2 + x + x)/x, y)")

#    def test_sympy_with_equality_symbol(self):
#        response = "Eq((x + x**2 + x)/x, 1)"
#        params = Params(is_latex=False, simplify=False)
#        result = preview_function(response, params)
#        self.assertNotIn("error", result)
#
#        preview = result["preview"]
#
#        self.assertEqual(preview.get("latex"), "\\frac{x^{2} + x + x}{x} = 1")

    def test_latex_conversion_preserves_default_symbols(self):
        response = "\\mu + x + 1"
        params = Params(is_latex=True, simplify=False)
        result = preview_function(response, params)
        self.assertNotIn("error", result)

        preview = result["preview"]

        self.assertEqual(preview.get("sympy"), "mu + x + 1")

    def test_sympy_conversion_preserves_default_symbols(self):
        response = "mu + x + 1"
        params = Params(is_latex=False, simplify=False)
        result = preview_function(response, params)
        self.assertNotIn("error", result)

        preview = result["preview"]

        self.assertEqual(preview.get("latex"), "\\mu + x + 1")

#    def test_latex_conversion_preserves_optional_symbols(self):
#        response = "m_{ \\text{table} } + \\text{hello}_\\text{world} - x + 1"
#        params = Params(
#            is_latex=True,
#            simplify=False,
#            symbols={
#                "m_table": {
#                    "latex": r"hello \( m_{\text{table}} \) world",
#                    "aliases": [],
#                },
#                "test": {
#                    "latex": r"hello $ \text{hello}_\text{world} $ world.",
#                    "aliases": [],
#                },
#            },
#        )
#        result = preview_function(response, params)
#        self.assertNotIn("error", result)
#
#        preview = result["preview"]
#
#        self.assertEqual(preview.get("sympy"), "m_table + test - x + 1")
#
#    def test_sympy_conversion_preserves_optional_symbols(self):
#        response = "m_table + test + x + 1"
#        params = Params(
#            is_latex=False,
#            simplify=False,
#            symbols={
#                "m_table": {"latex": "m_{\\text{table}}", "aliases": []},
#                "test": {
#                    "latex": "\\text{hello}_\\text{world}",
#                    "aliases": [],
#                },
#            },
#        )
#        result = preview_function(response, params)
#        self.assertNotIn("error", result)
#
#        preview = result["preview"]
#
#        self.assertEqual(
#            preview.get("latex"),
#            "m_{\\text{table}} + \\text{hello}_\\text{world} + x + 1",
#        )
#
#    def test_invalid_latex_returns_error(self):
#        response = "\frac{ m_{ \\text{table} } + x + 1 }{x"
#        params = Params(
#            is_latex=True,
#            simplify=False,
#            symbols={"m_table": {"latex": "m_{\\text{table}}", "aliases": []}},
#        )
#
#        with self.assertRaises(ValueError):
#            preview_function(response, params)

    def test_invalid_sympy_returns_error(self):
        response = "x + x***2 - 3 / x 4"
        params = Params(simplify=False, is_latex=False)

        with self.assertRaises(ValueError):
            preview_function(response, params)

    def test_extract_latex_in_delimiters(self):
        parentheses = r"\( x + 1 \)"
        dollars = r"$ x ** 2 + 1 $"
        double_dollars = r"$$ \sin x + \tan x $$"

        self.assertEqual(extract_latex(parentheses), " x + 1 ")
        self.assertEqual(extract_latex(dollars), " x ** 2 + 1 ")
        self.assertEqual(extract_latex(double_dollars), r" \sin x + \tan x ")

    def test_extract_latex_in_delimiters_and_text(self):
        parentheses = r"hello \( x + 1 \) world."
        dollars = r"hello $ x ** 2 + 1 $ world."

        self.assertEqual(extract_latex(parentheses), " x + 1 ")
        self.assertEqual(extract_latex(dollars), " x ** 2 + 1 ")

    def test_extract_latex_no_delimiters(self):
        test = r"'\sin x + \left ( \text{hello world} \right ) + \cos x"
        self.assertEqual(extract_latex(test), test)

    def test_extract_latex_multiple_expressions(self):
        parentheses = r"hello \( x + 1 \) world. \( \sin x + \cos x \) yes."
        dollars = r"hello $ x ** 2 + 1 $ world. \( \sigma \times \alpha \) no."
        mixture = r"hello $ x ** 2 - 1 $ world. $ \sigma \times \alpha $ !."

        self.assertEqual(extract_latex(parentheses), " x + 1 ")
        self.assertEqual(extract_latex(dollars), " x ** 2 + 1 ")
        self.assertEqual(extract_latex(mixture), " x ** 2 - 1 ")

    def test_elementary_functions_preview(self):
        params = {"strict_syntax": False, "elementary_functions": True}
        for case in elementary_function_test_cases:
            print(case[0])
            response = case[1]
            result = preview_function(response, params)
            self.assertEqual(result["preview"]["latex"], case[3])

if __name__ == "__main__":
    unittest.main()
