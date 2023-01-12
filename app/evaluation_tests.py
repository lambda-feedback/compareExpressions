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

    Use evaluation_function() to call the evaluation function.
    """

    @pytest.mark.parametrize("string,value,unit,content,unit_latex,criteria",slr_strict_si_syntax_test_cases)
    def test_strict_syntax_cases(self,string,value,unit,content,unit_latex,criteria):
        params = {"strict_syntax": False, "strict_SI_syntax": True}
        answer = string
        response = string
        result = evaluation_function(answer,response,params)
        assert result["is_correct"]

    @pytest.mark.parametrize("value,unit,small_diff,large_diff",\
        [
            ("10.5","kg m/s^2",0.04,0.06),\
            ("10.55","kg m/s^2",0.004,0.006),\
            ("0.105","kg m/s^2",0.0004,0.0006),\
            ("0.0010","kg m/s^2",0.00004,0.00006),\
            ("100","kg m/s^2",0.4,0.6),\
            ("100e10","kg m/s^2",4e9,6e9)
        ]
    )
    def test_compute_relative_tolerance_from_significant_decimals(self,value,unit,small_diff,large_diff):
        ans = value
        res_correct_under   = str(float(value)-small_diff)
        res_correct_over    = str(float(value)+small_diff)
        res_incorrect_under = str(float(value)-large_diff)
        res_incorrect_over  = str(float(value)+large_diff)
        params = {"strict_syntax": False, "strict_SI_syntax": True}
        assert evaluation_function(res_correct_under,ans,params)["is_correct"]   == True
        assert evaluation_function(res_correct_over,ans,params)["is_correct"]    == True
        assert evaluation_function(res_incorrect_under,ans,params)["is_correct"] == False
        assert evaluation_function(res_incorrect_over,ans,params)["is_correct"]  == False

    def test_convert_units(self):
        ans = "-10500 g m/s^2"
        res = "-10.5 kg m/s^2"
        params = {"strict_syntax": False, "strict_SI_syntax": True}
        result = evaluation_function(res,ans,params)
        assert result["is_correct"]

    @pytest.mark.parametrize("ans,res,tag",\
        [
            ("-10.5 kg m/s^2","kg m/s^2",      "MISSING_VALUE"),\
            ("-10.5 kg m/s^2","-10.5",         "MISSING_UNIT"),\
            ("kg m/s^2",      "-10.5 kg m/s^2","UNEXPECTED_VALUE"),\
            ("-10.5",         "-10.5 kg m/s^2","UNEXPECTED_UNIT")
        ]
    )
    def test_check_tag(self,ans,res,tag):
        params = {"strict_syntax": False, "strict_SI_syntax": True}
        result = evaluation_function(res,ans,params)
        assert tag in result["tags"].keys()
        assert result["is_correct"] == False

if __name__ == "__main__":
    pytest.main(["-x", "--tb=auto",os.path.basename(__file__)])
