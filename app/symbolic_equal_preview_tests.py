import unittest

try:
    from .preview import Params, extract_latex, preview_function
except ImportError:
    from preview import Params, extract_latex, preview_function


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
        params = Params(is_latex=False)
        result = preview_function(response, params)
        self.assertNotIn("error", result)

        preview = result["preview"]

        self.assertEqual(
            preview.get("latex"),
            "- 3 x^{2} + \\sin{\\left(x \\right)} "
            "+ \\cos{\\left(2 x \\right)}",
        )

    def test_latex_with_equality_symbol(self):
        response = "\\frac{x + x^2 + x}{x} = y"

        params = Params(is_latex=True, simplify=False)
        result = preview_function(response, params)
        self.assertNotIn("error", result)

        preview = result["preview"]

        self.assertEqual(preview.get("sympy"), "Eq((x**2 + x + x)/x, y)")

    def test_sympy_with_equality_symbol(self):
        response = "Eq((x + x**2 + x)/x, 1)"
        params = Params(is_latex=False, simplify=False)
        result = preview_function(response, params)
        self.assertNotIn("error", result)

        preview = result["preview"]

        self.assertEqual(preview.get("latex"), "\\frac{x^{2} + x + x}{x} = 1")

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

    def test_latex_conversion_preserves_optional_symbols(self):
        response = "m_{ \\text{table} } + \\text{hello}_\\text{world} - x + 1"
        params = Params(
            is_latex=True,
            simplify=False,
            symbols={
                "m_table": {
                    "latex": r"hello \( m_{\text{table}} \) world",
                    "aliases": [],
                },
                "test": {
                    "latex": r"hello $ \text{hello}_\text{world} $ world.",
                    "aliases": [],
                },
            },
        )
        result = preview_function(response, params)
        self.assertNotIn("error", result)

        preview = result["preview"]

        self.assertEqual(preview.get("sympy"), "m_table + test - x + 1")

    def test_sympy_conversion_preserves_optional_symbols(self):
        response = "m_table + test + x + 1"
        params = Params(
            is_latex=False,
            simplify=False,
            symbols={
                "m_table": {"latex": "m_{\\text{table}}", "aliases": []},
                "test": {
                    "latex": "\\text{hello}_\\text{world}",
                    "aliases": [],
                },
            },
        )
        result = preview_function(response, params)
        self.assertNotIn("error", result)

        preview = result["preview"]

        self.assertEqual(
            preview.get("latex"),
            "m_{\\text{table}} + \\text{hello}_\\text{world} + x + 1",
        )

    def test_invalid_latex_returns_error(self):
        response = "\frac{ m_{ \\text{table} } + x + 1 }{x"
        params = Params(
            is_latex=True,
            simplify=False,
            symbols={"m_table": {"latex": "m_{\\text{table}}", "aliases": []}},
        )

        with self.assertRaises(ValueError):
            preview_function(response, params)

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


if __name__ == "__main__":
    unittest.main()
