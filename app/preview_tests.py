import unittest

try:
    from .preview import Params, preview_function
except ImportError:
    from preview import Params, preview_function


class TestEvaluationFunction(unittest.TestCase):
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

    def test_returns_is_correct_true(self):
        response, params = "x", Params(is_latex=True)
        result = preview_function(response, params)

        self.assertTrue(result["is_correct"])

    def test_empty_latex_expression(self):
        response, params = "", Params(is_latex=True)
        result = preview_function(response, params)

        self.assertTrue(result["is_correct"])

    def test_empty_sympy_expression(self):
        response, params = "", Params(is_latex=False)
        result = preview_function(response, params)

        self.assertIn("latex", result)
        self.assertIn("sympy", result)
        self.assertNotIn("error", result)

    def test_latex_and_sympy_are_returned(self):
        response, params = "x+1", Params(is_latex=True)
        result = preview_function(response, params)

        self.assertIn("latex", result)
        self.assertIn("sympy", result)
        self.assertNotIn("error", result)

        response, params = "x+1", Params(is_latex=False)
        result = preview_function(response, params)

        self.assertIn("latex", result)
        self.assertIn("sympy", result)
        self.assertNotIn("error", result)

    def test_doesnt_simplify_latex_by_default(self):
        response, params = (
            "\\frac{x + x^2 + x}{x}",
            Params(is_latex=True),
        )
        result = preview_function(response, params)

        self.assertEqual(result.get("sympy"), "(x**2 + x + x)/x")

    def test_doesnt_simplify_sympy_by_default(self):
        response, params = (
            "(x + x**2 + x)/x",
            Params(is_latex=False),
        )
        result = preview_function(response, params)

        self.assertNotIn("error", result)
        self.assertEqual(result.get("latex"), "\\frac{x^{2} + x + x}{x}")

    def test_simplifies_latex_on_param(self):
        response, params = (
            "\\frac{x + x^2 + x}{x}",
            Params(is_latex=True, simplify=True),
        )
        result = preview_function(response, params)

        self.assertNotIn("error", result)
        self.assertEqual(result.get("sympy"), "x + 2")

    def test_simplifies_sympy_on_param(self):
        response, params = (
            "(x + x**2 + x)/x",
            Params(is_latex=False, simplify=True),
        )
        result = preview_function(response, params)

        self.assertNotIn("error", result)
        self.assertEqual(result.get("latex"), "x + 2")

    def test_sympy_handles_implicit_multiplication(self):
        response, params = (
            "sin(x) + cos(2x) - 3x**2",
            Params(is_latex=False),
        )
        result = preview_function(response, params)

        self.assertNotIn("error", result)
        self.assertEqual(
            result.get("latex"),
            "- 3 x^{2} + \\sin{\\left(x \\right)} "
            "+ \\cos{\\left(2 x \\right)}",
        )

    def test_latex_with_equality_symbol(self):
        response, params = (
            "\\frac{x + x^2 + x}{x} = y",
            Params(is_latex=True, simplify=False),
        )
        result = preview_function(response, params)

        self.assertNotIn("error", result)
        self.assertEqual(result.get("sympy"), "Eq((x**2 + x + x)/x, y)")

    def test_sympy_with_equality_symbol(self):
        response, params = (
            "Eq((x + x**2 + x)/x, 1)",
            Params(is_latex=False, simplify=False),
        )
        result = preview_function(response, params)

        self.assertNotIn("error", result)
        self.assertEqual(result.get("latex"), "\\frac{x^{2} + x + x}{x} = 1")

    def test_latex_conversion_preserves_default_symbols(self):
        response, params = (
            "\\mu + x + 1",
            Params(is_latex=True),
        )
        result = preview_function(response, params)

        self.assertNotIn("error", result)
        self.assertEqual(result.get("sympy"), "mu + x + 1")

    def test_sympy_conversion_preserves_default_symbols(self):
        response, params = (
            "mu + x + 1",
            Params(is_latex=False),
        )
        result = preview_function(response, params)

        self.assertNotIn("error", result)
        self.assertEqual(result.get("latex"), "\\mu + x + 1")

    def test_latex_conversion_preserves_optional_symbols(self):
        response, params = (
            "m_{ \\text{table} } + \\text{hello}_\\text{world} - x + 1",
            Params(
                is_latex=True,
                symbols={
                    "m_table": "m_{\\text{table}}",
                    "test": "\\text{hello}_\\text{world}",
                },
            ),
        )
        result = preview_function(response, params)

        self.assertNotIn("error", result)
        self.assertEqual(result.get("sympy"), "m_table + test - x + 1")

    def test_sympy_conversion_preserves_optional_symbols(self):
        response, params = (
            "m_table + test + x + 1",
            Params(
                is_latex=False,
                symbols={
                    "m_table": "m_{\\text{table}}",
                    "test": "\\text{hello}_\\text{world}",
                },
            ),
        )
        result = preview_function(response, params)

        self.assertNotIn("error", result)
        self.assertEqual(
            result.get("latex"),
            "m_{\\text{table}} + \\text{hello}_\\text{world} + x + 1",
        )

    def test_invalid_latex_returns_error(self):
        response, params = (
            "\frac{ m_{ \\text{table} } + x + 1 }{x",
            Params(
                is_latex=True,
                symbols={"m_table": "m_{\\text{table}}"},
            ),
        )
        result = preview_function(response, params)

        self.assertIn("error", result)

    def test_invalid_sympy_returns_error(self):
        response, params = (
            "x + x***2 - 3 / x 4",
            Params(is_latex=False),
        )
        result = preview_function(response, params)

        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
