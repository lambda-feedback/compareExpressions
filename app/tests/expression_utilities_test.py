import pytest
from sympy import Symbol, sqrt, sin as sympy_sin

from ..utility.expression_utilities import (
    compute_relative_tolerance_from_significant_decimals,
    convert_absolute_notation,
    convert_unicode_dashes,
    create_expression_set,
    extract_latex,
    find_matching_parenthesis,
    latex_symbols,
    preprocess_expression,
    protect_elementary_functions_substitutions,
    substitute,
    substitute_input_symbols,
    substitutions_sort_key,
    sympy_symbols,
    sympy_to_latex,
    transform_unicode_greek_symbols,
)


class TestConvertUnicodeDashes:

    @pytest.mark.parametrize(
        "expr, expected",
        [
            # No dashes at all
            ("x+y", []),
            # ASCII hyphen-minus is not a unicode dash — no substitution
            ("x-y", []),
            # Empty string
            ("", []),
            # HYPHEN (U+2010)
            ("x‐y", [("‐", "-")]),
            # NON-BREAKING HYPHEN (U+2011)
            ("x‑y", [("‑", "-")]),
            # FIGURE DASH (U+2012)
            ("x‒y", [("‒", "-")]),
            # EN DASH (U+2013)
            ("x–y", [("–", "-")]),
            # EM DASH (U+2014)
            ("x—y", [("—", "-")]),
            # MINUS SIGN (U+2212)
            ("x−y", [("−", "-")]),
            # SMALL HYPHEN-MINUS (U+FE63)
            ("x﹣y", [("﹣", "-")]),
            # FULLWIDTH HYPHEN-MINUS (U+FF0D)
            ("x－y", [("－", "-")]),
            # Multiple different unicode dashes in one expression
            ("x–y−z", [("–", "-"), ("−", "-")]),
            # Repeated occurrences of the same dash — still one substitution pair
            ("x−y−z", [("−", "-")]),
        ]
    )
    def test_convert_unicode_dashes(self, expr, expected):
        result = convert_unicode_dashes(expr)
        assert result == expected


class TestConvertAbsoluteNotation:

    @pytest.mark.parametrize(
        "expr, expected_expr, has_feedback",
        [
            # No pipes — unchanged
            ("x+y", "x+y", False),
            # Exactly two pipes — simple conversion
            ("|x|", "Abs(x)", False),
            ("|x+y|", "Abs(x+y)", False),
            # Two non-adjacent absolute values
            ("|x|+|y|", "Abs(x)+Abs(y)", False),
        ]
    )
    def test_convert_absolute_notation(self, expr, expected_expr, has_feedback):
        result_expr, feedback = convert_absolute_notation(expr, "response")
        assert result_expr == expected_expr
        assert (feedback is not None) == has_feedback

    def test_ambiguous_pipes_produce_feedback(self):
        # More than 2 pipes with ambiguous positions produces feedback
        expr, feedback = convert_absolute_notation("|x|y|z|", "response")
        assert feedback is not None
        assert feedback[0] == "ABSOLUTE_VALUE_NOTATION_AMBIGUITY"


class TestTransformUnicodeGreekSymbols:

    def test_no_greek_symbols_returns_empty(self):
        assert transform_unicode_greek_symbols("x + y") == []

    def test_named_greek_symbol_returns_self_substitution(self):
        result = transform_unicode_greek_symbols("alpha + 1")
        assert ("alpha", " alpha ") in result

    def test_unicode_greek_alias_maps_to_name(self):
        # α is an alias for "alpha"
        result = transform_unicode_greek_symbols("α")
        assert ("α", " alpha ") in result

    def test_multiple_greek_symbols(self):
        result = transform_unicode_greek_symbols("alpha + beta")
        assert ("alpha", " alpha ") in result
        assert ("beta", " beta ") in result

    def test_unicode_beta_alias(self):
        result = transform_unicode_greek_symbols("β")
        assert ("β", " beta ") in result


class TestProtectElementaryFunctionsSubstitutions:

    def test_no_functions_returns_empty(self):
        assert protect_elementary_functions_substitutions("x + y") == []

    def test_sin_generates_self_substitution(self):
        result = protect_elementary_functions_substitutions("sin(x)")
        assert ("sin", " sin ") in result

    def test_alias_maps_to_canonical_name(self):
        # arctan is an alias for atan
        result = protect_elementary_functions_substitutions("arctan(x)")
        assert ("arctan", " atan ") in result

    def test_multiple_functions(self):
        result = protect_elementary_functions_substitutions("sin(x) + cos(x)")
        assert ("sin", " sin ") in result
        assert ("cos", " cos ") in result


class TestSubstituteInputSymbols:

    def test_plain_expression_unchanged(self):
        result = substitute_input_symbols("x+y", {})
        assert result == ["x+y"]

    def test_lambda_replaced_with_lamda(self):
        result = substitute_input_symbols("lambda", {})
        assert result == ["lamda"]

    def test_alias_replaced_with_symbol_code(self):
        params = {"symbols": {"x": {"latex": r"\(x\)", "aliases": ["x_var"]}}}
        result = substitute_input_symbols(["x_var"], params)
        assert result == ["x"]

    def test_symbol_code_preserved(self):
        params = {"symbols": {"x": {"latex": r"\(x\)", "aliases": ["x_var"]}}}
        result = substitute_input_symbols(["x"], params)
        assert result == ["x"]

    def test_list_input_accepted(self):
        result = substitute_input_symbols(["x", "y"], {})
        assert result == ["x", "y"]


class TestFindMatchingParenthesis:

    @pytest.mark.parametrize(
        "string, index, delimiters, expected",
        [
            # Simple pair
            ("(x)", 0, None, 2),
            # Longer content
            ("(x+y)", 0, None, 4),
            # Nested — outer pair
            ("((x+y))", 0, None, 6),
            # Nested — inner pair
            ("((x+y))", 1, None, 5),
            # No closing delimiter
            ("(x", 0, None, -1),
            # Custom square-bracket delimiters
            ("[x+y]", 0, ("[", "]"), 4),
            # Starts mid-string
            ("a(b+c)d", 1, None, 5),
        ]
    )
    def test_find_matching_parenthesis(self, string, index, delimiters, expected):
        if delimiters is None:
            result = find_matching_parenthesis(string, index)
        else:
            result = find_matching_parenthesis(string, index, delimiters)
        assert result == expected


class TestSubstitute:

    @pytest.mark.parametrize(
        "string, substitutions, expected",
        [
            # Empty substitutions — unchanged
            ("hello", [], "hello"),
            # Single substitution
            ("hello world", [("world", "earth")], "hello earth"),
            # Whole string replaced
            ("abc", [("abc", "xyz")], "xyz"),
            # No match — unchanged
            ("hello", [("world", "earth")], "hello"),
            # Earlier substitution in list wins at the same position
            ("abc", [("a", "p"), ("ab", "q")], "pbc"),
            # Longer substitution listed first wins
            ("abc", [("ab", "q"), ("a", "p")], "qc"),
            # Multiple non-overlapping substitutions
            ("a b c", [("a", "x"), ("b", "y"), ("c", "z")], "x y z"),
            # List input is joined into a single result
            (["hello", " ", "world"], [("world", "earth")], "hello earth"),
        ]
    )
    def test_substitute(self, string, substitutions, expected):
        assert substitute(string, substitutions) == expected

    def test_lookahead_tuple_matches_with_following_context(self):
        # (("sin", ["("]), " sin ") matches "sin(" but not "sin " or "sinx"
        subs = [(("sin", ["("]), " sin ")]
        assert substitute("sin(x)", subs) == " sin (x)"

    def test_lookahead_tuple_does_not_match_without_context(self):
        subs = [(("sin", ["("]), " sin ")]
        assert substitute("sinx", subs) == "sinx"


class TestComputeRelativeTolerance:

    @pytest.mark.parametrize(
        "string, expected",
        [
            # Non-numeric → 0
            ("not_a_number", 0),
            # 1 sig char, below DEFAULT_SIGNIFICANT_FIGURES=2 floor → 5e-2
            ("1", 5e-2),
            # "0.5" → chars "05" → lstrip "5" → len 1 → floor applies → 5e-2
            ("0.5", 5e-2),
            # "1.5" → chars "15" → len 2 → max(2,2)=2 → 5e-2
            ("1.5", 5e-2),
            # "100" → chars "100" (lstrip removes nothing, '1' stops it) → len 3 → 5e-3
            ("100", 5e-3),
            # "1.23" → chars "123" (decimal removed) → len 3 → 5e-3
            ("1.23", 5e-3),
            # Scientific notation: mantissa "1.23" → len 3 → 5e-3
            ("1.23e5", 5e-3),
            # Negative: "-1.23" → lstrip removes "-" → "123" → len 3 → 5e-3
            ("-1.23", 5e-3),
        ]
    )
    def test_relative_tolerance(self, string, expected):
        result = compute_relative_tolerance_from_significant_decimals(string)
        assert result == pytest.approx(expected)


class TestSympySymbols:

    def test_returns_symbol_objects(self):
        result = sympy_symbols({"x": {}, "y": {}})
        assert result == {"x": Symbol("x"), "y": Symbol("y")}

    def test_empty_dict(self):
        assert sympy_symbols({}) == {}

    def test_symbol_names_preserved(self):
        result = sympy_symbols({"alpha": {}})
        assert result["alpha"] == Symbol("alpha")


class TestExtractLatex:

    @pytest.mark.parametrize(
        "symbol, expected",
        [
            # LaTeX delimiters removed
            (r"\(x^2\)", "x^2"),
            ("$x^2$", "x^2"),
            ("$$x^2$$", "x^2"),
            (r"\(\alpha\)", r"\alpha"),
            # No delimiters — returned as-is
            ("x^2", "x^2"),
            ("plain", "plain"),
        ]
    )
    def test_extract_latex(self, symbol, expected):
        assert extract_latex(symbol) == expected


class TestLatexSymbols:

    def test_maps_symbol_to_latex_string(self):
        syms = {"x": {"latex": r"\(x\)", "aliases": []}}
        result = latex_symbols(syms)
        assert result == {Symbol("x"): "x"}

    def test_greek_latex_preserved(self):
        syms = {"alpha": {"latex": r"\(\alpha\)", "aliases": []}}
        result = latex_symbols(syms)
        assert result == {Symbol("alpha"): r"\alpha"}

    def test_empty_dict(self):
        assert latex_symbols({}) == {}


class TestSympyToLatex:

    def test_simple_power(self):
        expr = Symbol("x") ** 2
        syms = {"x": {"latex": r"\(x\)", "aliases": []}}
        result = sympy_to_latex(expr, syms)
        assert result == "x^{2}"

    def test_custom_latex_name_used(self):
        expr = Symbol("alpha")
        syms = {"alpha": {"latex": r"\(\alpha\)", "aliases": []}}
        result = sympy_to_latex(expr, syms)
        assert result == r"\alpha"

    def test_sqrt(self):
        expr = sqrt(Symbol("x"))
        syms = {"x": {"latex": r"\(x\)", "aliases": []}}
        result = sympy_to_latex(expr, syms)
        assert result == r"\sqrt{x}"


class TestSubstitutionsSortKey:

    def test_longer_left_element_sorts_first(self):
        long_sub = ("abc", "p")
        short_sub = ("ab", "p")
        assert substitutions_sort_key(long_sub) < substitutions_sort_key(short_sub)

    def test_equal_left_length_longer_right_sorts_first(self):
        long_right = ("ab", "pqr")
        short_right = ("ab", "p")
        assert substitutions_sort_key(long_right) < substitutions_sort_key(short_right)

    def test_sort_orders_longer_substitutions_first(self):
        subs = [("a", "x"), ("abc", "y"), ("ab", "z")]
        subs.sort(key=substitutions_sort_key)
        assert subs[0][0] == "abc"
        assert subs[1][0] == "ab"
        assert subs[2][0] == "a"


class TestCreateExpressionSet:

    def test_plain_string_wrapped_in_list(self):
        result = create_expression_set("x+y", {})
        assert result == ["x+y"]

    def test_set_notation_split_into_list(self):
        result = create_expression_set("{x, y}", {})
        assert sorted(result) == ["x", "y"]

    def test_list_input_accepted(self):
        result = create_expression_set(["x", "y"], {})
        assert sorted(result) == ["x", "y"]

    def test_plus_minus_expands_to_two_expressions(self):
        params = {"plus_minus": "±"}
        result = create_expression_set("±x", params)
        assert sorted(result) == sorted(["+x", "-x"]) or sorted(result) == sorted(["x", "-x"])
        assert len(result) == 2


class TestPreprocessExpression:

    def test_plain_expression_succeeds(self):
        success, expr, feedback = preprocess_expression("response", "x+y", {})
        assert success is True
        assert expr == "x+y"
        assert feedback is None

    def test_absolute_value_notation_converted(self):
        success, expr, feedback = preprocess_expression("response", "|x|", {})
        assert success is True
        assert expr == "Abs(x)"
        assert feedback is None

    def test_ambiguous_pipes_returns_failure(self):
        success, expr, feedback = preprocess_expression("response", "|x|y|z|", {})
        assert success is False
        assert feedback is not None
        assert feedback[0] == "ABSOLUTE_VALUE_NOTATION_AMBIGUITY"