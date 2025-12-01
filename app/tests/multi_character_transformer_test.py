"""
Comprehensive test suite for implicit multiplication with higher precedence
when multi-character symbols are involved.

The key principle: When convention="implicit_higher_precedence", implicit 
multiplication should bind tighter than explicit division.

Example: a/bcd should parse as a/(b*c*d) not (a/b)*c*d
"""
from app.evaluation import evaluation_function

class TestMultiCharacterTransformer:

    def test_multi_character_implicit_multi_variable(self):
        """Original test case with multi-character symbol"""
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "symbols": {
                "a": {"aliases": ["a"]},
                "bc": {"aliases": ["bc"]},
                "d": {"aliases": ["d"]}
            },
        }
        answer = "a/(bc*d)"
        response_full = "a/(bc*d)"
        response_implicit_bracket = "a/(bcd)"
        response_implicit_no_bracket = "a/bcd"
    
        result = evaluation_function(response_full, answer, params)
        assert result["is_correct"] is True, "Response: a/(bc*d)"
    
        result = evaluation_function(response_implicit_bracket, answer, params)
        assert result["is_correct"] is True, "Response: a/(bcd)"
    
        result = evaluation_function(response_implicit_no_bracket, answer, params)
        assert result["is_correct"] is True, "Response: a/bcd"
    
    
    def test_multiple_divisions_with_implicit(self):
        """Test multiple divisions in sequence"""
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "symbols": {
                "a": {"aliases": ["a"]},
                "b": {"aliases": ["b"]},
                "c": {"aliases": ["c"]},
                "d": {"aliases": ["d"]},
                "e": {"aliases": ["e"]}
            },
        }
    
        # a/bc/de should be (a/(b*c))/(d*e)
        answer = "a/(b*c)/(d*e)"
        response = "a/bc/de"
    
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True, f"Failed for: {response}"
    
    
    def test_addition_with_division_and_implicit(self):
        """Test that addition doesn't interfere"""
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "symbols": {
                "a": {"aliases": ["a"]},
                "b": {"aliases": ["b"]},
                "c": {"aliases": ["c"]},
                "d": {"aliases": ["d"]}
            },
        }
    
        # a/bc + d should be a/(b*c) + d
        answer = "a/(b*c) + d"
        response = "a/bc + d"
    
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True, f"Failed for: {response}"
    
    
    def test_subtraction_with_division_and_implicit(self):
        """Test that subtraction doesn't interfere"""
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "symbols": {
                "a": {"aliases": ["a"]},
                "b": {"aliases": ["b"]},
                "c": {"aliases": ["c"]},
                "d": {"aliases": ["d"]}
            },
        }
    
        # a/bc - d should be a/(b*c) - d
        answer = "a/(b*c) - d"
        response = "a/bc - d"
    
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True, f"Failed for: {response}"
    
    
    def test_multiplication_after_division(self):
        """Test explicit multiplication after division"""
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "symbols": {
                "a": {"aliases": ["a"]},
                "b": {"aliases": ["b"]},
                "c": {"aliases": ["c"]},
                "d": {"aliases": ["d"]}
            },
        }
    
        # a/bc*d should be (a/(b*c))*d
        answer = "(a/(b*c))*d"
        response = "a/bc*d"
    
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True, f"Failed for: {response}"
    
    
    def test_power_with_implicit_multiplication(self):
        """Test power operator with implicit multiplication"""
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "symbols": {
                "a": {"aliases": ["a"]},
                "b": {"aliases": ["b"]},
                "c": {"aliases": ["c"]},
            },
        }
    
        # a/b^2c should be a/(b^2*c) since power binds tighter
        answer = "a/(b**2*c)"
        response = "a/b^2c"
    
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True, f"Failed for: {response}"
    
    
    def test_longer_multi_character_symbols(self):
        """Test with longer multi-character symbols"""
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "symbols": {
                "x": {"aliases": ["x"]},
                "abc": {"aliases": ["abc"]},
                "def": {"aliases": ["def"]},
            },
        }
    
        answer = "x/(abc*def)"
        test_cases = [
            "x/(abc*def)",
            "x/(abcdef)",
            "x/abcdef",
        ]
    
        for response in test_cases:
            result = evaluation_function(response, answer, params)
            assert result["is_correct"] is True, f"Failed for: {response}"
    
    
    def test_overlapping_symbol_names(self):
        """Test when symbol names could overlap"""
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "symbols": {
                "a": {"aliases": ["a"]},
                "ab": {"aliases": ["ab"]},
                "abc": {"aliases": ["abc"]},
                "c": {"aliases": ["c"]},
            },
        }
    
        # abc should be recognized as single symbol
        answer = "a/(abc*c)"
        response = "a/abcc"
    
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True, f"Failed for: {response}"
    
    
    def test_numbers_with_implicit_multiplication(self):
        """Test with numeric literals"""
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "symbols": {
                "a": {"aliases": ["a"]},
                "b": {"aliases": ["b"]},
            },
        }
    
        # a/2b should be a/(2*b)
        answer = "a/(2*b)"
        response = "a/2b"
    
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True, f"Failed for: {response}"
    
    
    def test_number_variable_number(self):
        """Test number followed by variable followed by number"""
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "symbols": {
                "x": {"aliases": ["x"]},
            },
        }
    
        # 1/2x3 should be 1/(2*x*3)
        answer = "1/(2*x*3)"
        response = "1/2x3"
    
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True, f"Failed for: {response}"
    
    
    def test_parenthesized_expression_after_division(self):
        """Test division followed by parenthesized expression"""
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "symbols": {
                "a": {"aliases": ["a"]},
                "b": {"aliases": ["b"]},
                "c": {"aliases": ["c"]},
            },
        }
    
        # a/(b+c) should remain a/(b+c)
        answer = "a/(b+c)"
        response = "a/(b+c)"
    
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True, f"Failed for: {response}"
    
    
    def test_implicit_before_parentheses(self):
        """Test implicit multiplication before parentheses"""
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "symbols": {
                "a": {"aliases": ["a"]},
                "b": {"aliases": ["b"]},
                "c": {"aliases": ["c"]},
                "d": {"aliases": ["d"]},
            },
        }
    
        # a(bcd) should be a*(b*c*d)
        answer = "a*(b*c*d)"
        response = "a(bcd)"
    
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True, f"Failed for: {response}"
    
    
    def test_implicit_before_parentheses_with_multichar(self):
        """Test implicit multiplication before parentheses with multi-char symbols"""
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "symbols": {
                "a": {"aliases": ["a"]},
                "bc": {"aliases": ["bc"]},
                "d": {"aliases": ["d"]},
            },
        }
    
        # a(bcd) should be a*(bc*d)
        answer = "a*(bc*d)"
        response = "a(bcd)"
    
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True, f"Failed for: {response}"
    
    
    def test_division_then_implicit_then_parentheses(self):
        """Test a/b(cd)"""
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "symbols": {
                "a": {"aliases": ["a"]},
                "b": {"aliases": ["b"]},
                "c": {"aliases": ["c"]},
                "d": {"aliases": ["d"]},
            },
        }
    
        # a/b(cd) should be a/(b*(c*d))
        answer = "a/(b*(c*d))"
        response = "a/b(cd)"
    
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True, f"Failed for: {response}"
    
    
    def test_nested_parentheses_after_division(self):
        """Test nested parentheses"""
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "symbols": {
                "a": {"aliases": ["a"]},
                "b": {"aliases": ["b"]},
                "c": {"aliases": ["c"]},
            },
        }
    
        # a/b(c) should be a/(b*c)
        answer = "a/(b*c)"
        response = "a/b(c)"
    
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True, f"Failed for: {response}"
    
    
    def test_function_call_should_not_be_affected(self):
        """Test that actual function calls are not affected"""
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "symbols": {
                "x": {"aliases": ["x"]},
            },
        }
    
        # sin(x) should remain sin(x), not sin*x
        answer = "sin(x)"
        response = "sin(x)"
    
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True, f"Failed for: {response}"
    
    
    def test_complex_expression(self):
        """Test a complex expression"""
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "symbols": {
                "a": {"aliases": ["a"]},
                "b": {"aliases": ["b"]},
                "c": {"aliases": ["c"]},
                "d": {"aliases": ["d"]},
                "e": {"aliases": ["e"]},
            },
        }
    
        # a/bc + d/ef should be a/(b*c) + d/(e*f)
        answer = "a/(b*c) + d/(e*f)"
        response = "a/bc + d/ef"
    
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True, f"Failed for: {response}"
    
    
    def test_three_way_implicit_multiplication(self):
        """Test three or more implicitly multiplied terms"""
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "symbols": {
                "a": {"aliases": ["a"]},
                "b": {"aliases": ["b"]},
                "c": {"aliases": ["c"]},
                "d": {"aliases": ["d"]},
                "e": {"aliases": ["e"]},
            },
        }
    
        # a/bcde should be a/(b*c*d*e)
        answer = "a/(b*c*d*e)"
        response = "a/bcde"
    
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True, f"Failed for: {response}"
    
    
    def test_all_multi_character_symbols(self):
        """Test when all symbols are multi-character"""
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "symbols": {
                "ab": {"aliases": ["ab"]},
                "cd": {"aliases": ["cd"]},
                "ef": {"aliases": ["ef"]},
            },
        }
    
        # ab/cdef should be ab/(cd*ef)
        answer = "ab/(cd*ef)"
        response = "ab/cdef"
    
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True, f"Failed for: {response}"
    
    
    def test_explicit_multiplication_should_not_be_grouped(self):
        """Test that explicit multiplication maintains standard precedence"""
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "symbols": {
                "a": {"aliases": ["a"]},
                "b": {"aliases": ["b"]},
                "c": {"aliases": ["c"]},
            },
        }
    
        # a/b*c should be (a/b)*c, not a/(b*c)
        answer = "(a/b)*c"
        response = "a/b*c"
    
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True, f"Failed for: {response}"
    
    
    def test_mixed_implicit_and_explicit(self):
        """Test mixing implicit and explicit multiplication"""
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "symbols": {
                "a": {"aliases": ["a"]},
                "b": {"aliases": ["b"]},
                "c": {"aliases": ["c"]},
                "d": {"aliases": ["d"]},
            },
        }
    
        # a/bc*d should be (a/(b*c))*d
        # Implicit bc groups, then explicit *d applies
        answer = "(a/(b*c))*d"
        response = "a/bc*d"
    
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True, f"Failed for: {response}"
    
    
    def test_no_implicit_mult_after_explicit_mult(self):
        """Test that explicit multiplication breaks implicit grouping"""
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "symbols": {
                "a": {"aliases": ["a"]},
                "b": {"aliases": ["b"]},
                "c": {"aliases": ["c"]},
                "d": {"aliases": ["d"]},
            },
        }
    
        # a/b*cd should be (a/b)*(c*d)
        answer = "(a/b)*(c*d)"
        response = "a/b*cd"
    
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True, f"Failed for: {response}"
    
    
    def test_single_character_after_division(self):
        """Test single character after division (no grouping needed)"""
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "symbols": {
                "a": {"aliases": ["a"]},
                "b": {"aliases": ["b"]},
            },
        }
    
        # a/b should remain a/b
        answer = "a/b"
        response = "a/b"
    
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True, f"Failed for: {response}"
    
    
    def test_power_in_implicit_sequence(self):
        """Test power within implicit multiplication sequence"""
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "convention": "implicit_higher_precedence",
            "symbols": {
                "a": {"aliases": ["a"]},
                "b": {"aliases": ["b"]},
                "c": {"aliases": ["c"]},
            },
        }
    
        # a/bc^2 should be a/(b*c^2) since power binds tighter than implicit mult
        answer = "a/(b*c**2)"
        response = "a/bc^2"
    
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True, f"Failed for: {response}"
    
    
        def test_basic_division_with_implicit_multiplication(self):
            """Test basic case: division followed by implicitly multiplied terms"""
            params = {
                "strict_syntax": False,
                "elementary_functions": True,
                "convention": "implicit_higher_precedence",
                "symbols": {
                    "a": {"aliases": ["a"]},
                    "b": {"aliases": ["b"]},
                    "c": {"aliases": ["c"]},
                    "d": {"aliases": ["d"]}
                },
            }
            answer = "a/(b*c*d)"
        
            # All these should be equivalent
            test_cases = [
                "a/(b*c*d)",  # Explicit
                "a/(bcd)",  # Implicit with parens
                "a/bcd",  # Pure implicit - key test case
            ]
        
            for response in test_cases:
                result = evaluation_function(response, answer, params)
                assert result["is_correct"] is True, f"Failed for: {response}"