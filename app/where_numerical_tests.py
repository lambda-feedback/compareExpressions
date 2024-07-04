import pytest
import os

from .evaluation import evaluation_function

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

    @pytest.mark.parametrize(
        "response, answer, criteria, value, feedback_tags, additional_params",
        [
            ("14", "a+b*c", "response=answer where a=2; b=3; c=4", True, [],
                {
                    'symbols': {
                        'a': {'aliases': [], 'latex': r'\(a\)'},
                        'b': {'aliases': [''], 'latex': r'\(b)'},
                        'c': {'aliases': [], 'latex': r'\(c)'},
                    },
                    'atol': 1,
                    'rtol':0,
                }),
            
            ("2/3", "a/b", "response=answer where a=2; b=3", True, [],
                {
                    'symbols': {
                        'a': {'aliases': [], 'latex': r'\(a)'},
                        'b': {'aliases': [], 'latex': r'\(b)'},
                    },
                    'rtol': 0.1,
                    'atol':0.1,
                }),


            ("0.6667", "a/b", "response=answer where a=2; b=3", True, [],
                {
                    'symbols': {
                        'a': {'aliases': [], 'latex': r'\(a)'},
                        'b': {'aliases': [], 'latex': r'\(b)'},
                    },
                    'rtol': 0.1,
                    'atol':0,
                }),
                
            ("0.1667", "a/b", "response=answer where a=1; b=6", True, [],
                {
                    'symbols': {
                        'a': {'aliases': [], 'latex': r'\(a)'},
                        'b': {'aliases': [], 'latex': r'\(b)'},
                    },
                    'rtol': 0,
                    'atol':0.1,
                }), 
                
            ("1.41", "sqrt(a)", "response=answer where a=2", True, [],
                {
                    'symbols': {
                        'a': {'aliases': [], 'latex': r'\(a)'},
                    },
                    'rtol': 0,
                    'atol':0.1,
                }),

            ("2", "(a/b)^c", "response=answer where a=7; b=5; c=1.4", False, [],
                {
                    'symbols': {
                        'a': {'aliases': [], 'latex': r'\(a)'},
                        'b': {'aliases': [], 'latex': r'\(b)'},
                        'c': {'aliases': [], 'latex': r'\(c)'},                        
                    },
                    'rtol': 0.01,
                    'atol':0,
                }),   
                
            ("1.6017", "(a/b)^c", "response=answer where a=7; b=5; c=1.4", True, [],
                {
                    'symbols': {
                        'a': {'aliases': [], 'latex': r'\(a)'},
                        'b': {'aliases': [], 'latex': r'\(b)'},
                        'c': {'aliases': [], 'latex': r'\(c)'},                        
                    },
                    'rtol': 0.01,
                    'atol':0,
                }),                  
                
        ]
    )
    def test_criteria_where_numerical_comparison(self, response, answer, criteria, value, feedback_tags, additional_params):
        params = {
            "strict_syntax": False,
            "elementary_functions": True,
            "criteria": criteria,
        }
        params.update(additional_params)
        result = evaluation_function(response, answer, params, include_test_data=True)
        assert result["is_correct"] is value
        for feedback_tag in feedback_tags:
            assert feedback_tag in result["tags"]


if __name__ == "__main__":
    pytest.main(['-xsk not slow', "--tb=line", '--durations=10', os.path.abspath(__file__)])
