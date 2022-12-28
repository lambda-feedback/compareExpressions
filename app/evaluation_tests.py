import unittest, pytest, sys, os
sys.path.append(".")

from slr_strict_si_syntax_tests import TestClass as TestStrictSLRSyntax
from slr_strict_si_syntax_tests import slr_strict_si_syntax_test_cases

from evaluation import evaluation_function

# If evaluation_tests is run with the command line argument 'skip_resource_intensive_tests'
# then tests marked with @unittest.skipIf(skip_resource_intensive_tests,message_on_skip)
# will be skipped. This can be used to avoid takes that take a long time when making several
# small changes with most tests running between each change
message_on_skip = "Test skipped to save on resources"
skip_resource_intensive_tests = False
if "skip_resource_intensive_tests" in sys.argv:
    skip_resource_intensive_tests = True
    sys.argv.remove("skip_resource_intensive_tests")

class TestEvaluationFunction():
    """
    TestCase Class used to test the algorithm.
    ---
    Tests are used here to check that the algorithm written
    is working as it should.

    These tests are organised in classes to enusre that the same
    calling conventions can be used for tests using unittest and
    tests using pytest.

    Read the docs on how to use unittest and pytest here:
    https://docs.python.org/3/library/unittest.html
    https://docs.pytest.org/en/7.2.x/

    Use evaluation_function() to check your algorithm works
    as it should.
    """

    @pytest.mark.parametrize("string,value,unit,content,unit_latex,criteria",slr_strict_si_syntax_test_cases)
    def test_strict_syntax_cases(self,string,value,unit,content,unit_latex,criteria):
        params = {"strict_syntax": False, "strict_SI_syntax": True}
        answer = string
        response = string
        result = evaluation_function(answer,response,params)

if __name__ == "__main__":
    pytest.main(["-x", "--tb=line",os.path.basename(__file__)])
