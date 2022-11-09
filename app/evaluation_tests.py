import unittest, sys

try:
    from .evaluation import evaluation_function
except ImportError:
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

    Use evaluation_function() to check your algorithm works
    as it should.
    """

    def test_AAA(self):
        exprs = ["-10.5 (kg m)^3/s^2",\
                 "10 kilogram*metre*second**(-2)",\
                 "10 kilogram*metre/second**2",\
                 "(5.27*pi/sqrt(11) + 5*7)^(2+2.3) (kilogram megametre^2)/(fs^4 daA)",\
                 "(5.27*pi/sqrt(11) + 5*7)^(4.3) (kilogram megametre^2)/(fs^4 daA)",\
                 "(5*27/11 + 5*7)^(2*3) (kilogram megametre^2)/(fs^4 daA)",\
                 "(pi+10) kg*m/s^2",\
                 "10*pi kilogram*metre/second^2",\
                 "10 kilogram/(metre second^2)",\
                 "10 kilogram*metre/second^2",\
                 "10 kilogram metre/second^2",\
                 "10 kg*m/s^2",\
                 " 10 kg m/s^2 ",\
                 "10 1/s^2",\
                 "q",\
                 "10",\
                 "1/s^2",\
                ]
        params = {"strict_syntax": False, "strict_SI_syntax": True}
        for expr in exprs:
            with self.subTest(expr=expr):
                answer = expr
                response = expr
                result = evaluation_function(response, answer, params)
                print("-------------------------")
                print(result["feedback"])
                print(result["response_latex"])
                self.assertEqual(result["is_correct"],True)

        exprs = ["10 gram/metresecond",\
                 "10 second/gram + 5 gram*second + 7 ms + 5 gram/second",\
                 "10 second/gram * 7 ms * 5 gram/second",\
                ]

if __name__ == "__main__":
    unittest.main()
