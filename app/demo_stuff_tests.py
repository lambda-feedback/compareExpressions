import unittest, pytest, sys, os

try:
    from evaluation import evaluation_function
except ImportError:
    from .evaluation import evaluation_function

# If evaluation_tests is run with the command line argument 'skip_resource_intensive_tests'
# then tests marked with @unittest.skipIf(skip_resource_intensive_tests,message_on_skip)
# will be skipped. This can be used to avoid takes that take a long time when making several
# small changes with most tests running between each change
message_on_skip = "Test skipped to save on resources"
skip_resource_intensive_tests = False
if "skip_resource_intensive_tests" in sys.argv:
    skip_resource_intensive_tests = True
    sys.argv.remove("skip_resource_intensive_tests")

class TestClass():
    """
    TestCase Class used to test the algorithm.
    ---
    Tests are used here to check that the algorithm written
    is working as it should.

    These tests are organised in classes to ensure that the same
    calling conventions can be used for tests using unittest and
    tests using pytest.

    Read the docs on how to use unittest and pytest here:
    https://docs.python.org/3/library/unittest.html
    https://docs.pytest.org/en/7.2.x/

    Use evaluation_function() to call the evaluation function.
    """

    @pytest.mark.parametrize("res,ans,is_correct,tags,x_values",\
        [
            ("x+2",                  "x+2",        True, [],                                 ['0','1']),
            ("x+1",                  "x+2",        False,["WRONG_POLYNOMIAL"],               ['0','1']),
            ("x^3-x^2-x+1",          "x+2",        False,["WRONG_DEGREE"],                   ['0','1']),
            ("2-x",                  "2-x",        True, [],                                 ['0','1']),
            ("x-2",                  "x-2",        True, [],                                 ['0','1']),
            ("x^2+1",                "x^2+1",      True, [],                                 ['0','1','2']),
            ("x^2+1",                "x+1",        False,["WRONG_POLYNOMIAL","WRONG_DEGREE"],['0','1','2']),
            ("x^2+x+1",              "x^2+x+1",    True, [],                                 ['0','1','2']),
            ("x^3-3*x^2+1",          "x^3-3*x^2+1",True, [],                                 ['0','1','2','3']),
            ("x^4-5*x^3+8*x^2-6*x+1","x^3-3*x^2+1",False,["WRONG_DEGREE"],                   ['0','1','2','3']),
            ("x*(x-1)",              "x^2-x",     False,["PARSE_EXCEPTION"],                ['0','1','2']),
        ]
    )
    def test_demo_polynomial(self,res,ans,is_correct,tags,x_values):
        params = {"strict_syntax": False, "demo_stuff": "polynomial", "x_values": x_values}
        result = evaluation_function(res,ans,params)
        for tag in tags:
            assert tag in result["tags"].keys()
        assert result["is_correct"] == is_correct

if __name__ == "__main__":
    pytest.main(["-xs", "--tb=line",os.path.basename(__file__)])
