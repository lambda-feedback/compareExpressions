import pytest
from ..utility.expression_utilities import parse_expression, create_sympy_parsing_params

class TestMultiCharacterTransformerIntegration:
    """
    Integration tests for Multi-Character Implicit Multiplication Transformer.
    Uses expression_utilities.py directly to parse expressions.
    """

    def assert_expression_equality(self, response, answer, symbols_dict, local_dict=None):
        """
        Helper to parse both response and answer with the same parameters
        and assert they result in equivalent SymPy expressions.
        """
        if local_dict is None:
            local_dict = {}

        # define parameters
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "symbols": symbols_dict,
            # Pass custom functions/assumptions if needed
            "symbol_assumptions": [] 
        }

        parsing_params = create_sympy_parsing_params(params)

        try:
            parsed_response = parse_expression(response, parsing_params)
            parsed_answer = parse_expression(answer, parsing_params)
        except Exception as e:
            pytest.fail(f"Parsing failed for input '{response}' or '{answer}': {str(e)}")

        assert parsed_response == parsed_answer, \
            f"\nInput:    {response}\nExpected: {parsed_answer}\nGot:      {parsed_response}"

    def test_multi_character_implicit_multi_variable(self):
        """Original test case with multi-character symbol"""
        symbols = {
            "a": {"aliases": ["a"]},
            "bc": {"aliases": ["bc"]},
            "d": {"aliases": ["d"]}
        }
        answer = "a/(bc*d)"
        
        # Case 1: Full explicit
        self.assert_expression_equality("a/(bc*d)", answer, symbols)
        
        # Case 2: Implicit with brackets
        self.assert_expression_equality("a/(bcd)", answer, symbols)
        
        # Case 3: Implicit no brackets
        # Note: This relies on the tokenizer/splitter handling 'bcd' correctly relative to the transformer
        self.assert_expression_equality("a/bcd", answer, symbols)

    def test_multiple_divisions_with_implicit(self):
        """Test multiple divisions in sequence"""
        symbols = {
            "a": {"aliases": ["a"]},
            "b": {"aliases": ["b"]},
            "c": {"aliases": ["c"]},
            "d": {"aliases": ["d"]},
            "e": {"aliases": ["e"]}
        }
        # a/bc/de should be (a/(b*c))/(d*e)
        answer = "a/(b*c)/(d*e)"
        response = "a/bc/de"
        self.assert_expression_equality(response, answer, symbols)

    def test_addition_with_division_and_implicit(self):
        """Test that addition doesn't interfere"""
        symbols = {
            "a": {"aliases": ["a"]},
            "b": {"aliases": ["b"]},
            "c": {"aliases": ["c"]},
            "d": {"aliases": ["d"]}
        }
        answer = "a/(b*c) + d"
        response = "a/bc + d"
        self.assert_expression_equality(response, answer, symbols)

    def test_multiplication_after_division(self):
        """Test explicit multiplication after division"""
        symbols = {
            "a": {"aliases": ["a"]},
            "b": {"aliases": ["b"]},
            "c": {"aliases": ["c"]},
            "d": {"aliases": ["d"]}
        }
        # a/bc*d should be (a/(b*c))*d
        answer = "(a/(b*c))*d"
        response = "a/bc*d"
        self.assert_expression_equality(response, answer, symbols)

    def test_power_with_implicit_multiplication(self):
        """Test power operator with implicit multiplication"""
        symbols = {
            "a": {"aliases": ["a"]},
            "b": {"aliases": ["b"]},
            "c": {"aliases": ["c"]},
        }
        # a/b^2c should be a/(b^2*c) since power binds tighter
        answer = "a/(b**2*c)"
        response = "a/b^2c"
        self.assert_expression_equality(response, answer, symbols)

    def test_longer_multi_character_symbols(self):
        """Test with longer multi-character symbols"""
        symbols = {
            "x": {"aliases": ["x"]},
            "abc": {"aliases": ["abc"]},
            "def": {"aliases": ["def"]},
        }
        answer = "x/(abc*def)"
        test_cases = [
            "x/(abc*def)",
            "x/(abcdef)",
            "x/abcdef",
        ]
        for response in test_cases:
            self.assert_expression_equality(response, answer, symbols)

    def test_overlapping_symbol_names(self):
        """Test when symbol names could overlap"""
        symbols = {
            "a": {"aliases": ["a"]},
            "ab": {"aliases": ["ab"]},
            "abc": {"aliases": ["abc"]},
            "c": {"aliases": ["c"]},
        }
        # abc should be recognized as single symbol
        answer = "a/(abc*c)"
        response = "a/abcc"
        self.assert_expression_equality(response, answer, symbols)

    def test_numbers_with_implicit_multiplication(self):
        """Test with numeric literals"""
        symbols = {
            "a": {"aliases": ["a"]},
            "b": {"aliases": ["b"]},
        }
        # a/2b should be a/(2*b)
        answer = "a/(2*b)"
        response = "a/2b"
        self.assert_expression_equality(response, answer, symbols)

    def test_number_variable_number(self):
        """Test number followed by variable followed by number"""
        symbols = {
            "x": {"aliases": ["x"]},
        }
        # 1/2x3 should be 1/(2*x*3)
        answer = "1/(2*x*3)"
        response = "1/2x3"
        self.assert_expression_equality(response, answer, symbols)

    def test_implicit_before_parentheses(self):
        """Test implicit multiplication before parentheses"""
        symbols = {
            "a": {"aliases": ["a"]},
            "b": {"aliases": ["b"]},
            "c": {"aliases": ["c"]},
            "d": {"aliases": ["d"]},
        }
        # a(bcd) should be a*(b*c*d)
        answer = "a*(b*c*d)"
        response = "a(bcd)"
        self.assert_expression_equality(response, answer, symbols)

    def test_implicit_before_parentheses_with_multichar(self):
        """Test implicit multiplication before parentheses with multi-char symbols"""
        symbols = {
            "a": {"aliases": ["a"]},
            "bc": {"aliases": ["bc"]},
            "d": {"aliases": ["d"]},
        }
        # a(bcd) should be a*(bc*d)
        answer = "a*(bc*d)"
        response = "a(bcd)"
        self.assert_expression_equality(response, answer, symbols)

    def test_division_then_implicit_then_parentheses(self):
        """Test a/b(cd)"""
        symbols = {
            "a": {"aliases": ["a"]},
            "b": {"aliases": ["b"]},
            "c": {"aliases": ["c"]},
            "d": {"aliases": ["d"]},
        }
        # a/b(cd) should be a/(b*(c*d))
        answer = "a/(b*(c*d))"
        response = "a/b(cd)"
        self.assert_expression_equality(response, answer, symbols)

    def test_complex_expression(self):
        """Test a complex expression"""
        symbols = {
            "a": {"aliases": ["a"]},
            "b": {"aliases": ["b"]},
            "c": {"aliases": ["c"]},
            "d": {"aliases": ["d"]},
            "e": {"aliases": ["e"]},
        }
        # a/bc + d/ef should be a/(b*c) + d/(e*f)
        answer = "a/(b*c) + d/(e*f)"
        response = "a/bc + d/ef"
        self.assert_expression_equality(response, answer, symbols)

    def test_three_way_implicit_multiplication(self):
        """Test three or more implicitly multiplied terms"""
        symbols = {
            "a": {"aliases": ["a"]},
            "b": {"aliases": ["b"]},
            "c": {"aliases": ["c"]},
            "d": {"aliases": ["d"]},
            "e": {"aliases": ["e"]},
        }
        # a/bcde should be a/(b*c*d*e)
        answer = "a/(b*c*d*e)"
        response = "a/bcde"
        self.assert_expression_equality(response, answer, symbols)

    def test_explicit_multiplication_should_not_be_grouped(self):
        """Test that explicit multiplication maintains standard precedence"""
        symbols = {
            "a": {"aliases": ["a"]},
            "b": {"aliases": ["b"]},
            "c": {"aliases": ["c"]},
        }
        # a/b*c should be (a/b)*c, not a/(b*c)
        answer = "(a/b)*c"
        response = "a/b*c"
        self.assert_expression_equality(response, answer, symbols)

    def test_mixed_implicit_and_explicit(self):
        """Test mixing implicit and explicit multiplication"""
        symbols = {
            "a": {"aliases": ["a"]},
            "b": {"aliases": ["b"]},
            "c": {"aliases": ["c"]},
            "d": {"aliases": ["d"]},
        }
        # a/bc*d should be (a/(b*c))*d
        answer = "(a/(b*c))*d"
        response = "a/bc*d"
        self.assert_expression_equality(response, answer, symbols)