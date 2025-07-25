import pytest
import os

# Import necessary data and reference cases for tests
from .slr_quantity_tests import slr_strict_si_syntax_test_cases, slr_natural_si_syntax_test_cases
from ..evaluation import evaluation_function
from ..utility.unit_system_conversions import (
    set_of_SI_prefixes,
    set_of_SI_base_unit_dimensions,
    set_of_derived_SI_units_in_SI_base_units,
    set_of_common_units_in_SI, set_of_very_common_units_in_SI,
    set_of_imperial_units
)


class TestEvaluationFunction():
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

    # Import tests that makes sure that physical quantity parsing works as expected
    from .slr_quantity_tests import TestEvaluationFunction as TestStrictSLRSyntax

    log_details = True

    def log_details_to_file(self, details, filename):
        if self.log_details:
            f = open(filename, "w")
            f.write(details)
            f.close()
        return

    @pytest.mark.parametrize("string,value,unit,content,value_latex,unit_latex,criteria", slr_strict_si_syntax_test_cases)
    def test_strict_syntax_cases(self, string, value, unit, content, value_latex, unit_latex, criteria):
        params = {
            "strict_syntax": False,
            "physical_quantity": True,
            "units_string": "SI",
            "strictness": "strict",
            "elementary_functions": True
        }
        answer = string
        response = string
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True
        assert result["response_latex"] == "~".join([latex for latex in [value_latex, unit_latex] if latex is not None])

    @pytest.mark.parametrize("string,value,unit,content,value_latex,unit_latex,criteria", slr_natural_si_syntax_test_cases)
    def test_natural_syntax_cases(self, string, value, unit, content, value_latex, unit_latex, criteria):
        params = {
            "strict_syntax": False,
            "physical_quantity": True,
            "units_string": "SI",
            "strictness": "natural",
            "elementary_functions": True
        }
        answer = string
        response = string
        result = evaluation_function(response, answer, params)
        assert result["is_correct"] is True
        assert result["response_latex"] == "~".join([latex for latex in [value_latex, unit_latex] if latex is not None])

    @pytest.mark.skip("Too resource intensive")
    def test_slow_quantity_alternative_names_natural_syntax(self):
        params = {"strict_syntax": False, "physical_quantity": True, "units_string": "SI common imperial", "strictness": "natural"}
        units = set_of_SI_base_unit_dimensions | set_of_derived_SI_units_in_SI_base_units | set_of_common_units_in_SI | set_of_very_common_units_in_SI | set_of_imperial_units
        incorrect = []
        errors = []
        n = 0
        k = 0
        for prefix in set_of_SI_prefixes:
            for u1 in units:
                for u2 in units:
                    if u1 is not u2:
                        answer = prefix[0]+u1[0]+" "+u2[0]
                        for u1_alt in (u1[0],)+u1[3]:
                            for u2_alt in (u2[0],)+u2[3]+u2[4]:
                                n += 1
                                response = prefix[0]+u1_alt+u2_alt
                                try:
                                    result = evaluation_function(response, answer, params)
                                except Exception:
                                    errors.append((answer, response))
                                    continue
                                if result["is_correct"] is False:
                                    incorrect.append((answer, response, result["response_latex"]))
                                    print("Incorrect: "+str((answer, response, result["response_latex"])))
                                if n-k > 0:
                                    print(k)
                                    k += 1000
        m = len(errors)+len(incorrect)
        details = "Total: "+str(m)+"/"+str(n)+"\nIncorrect:\n"+"".join([str(x)+"\n" for x in incorrect])+"\nErrors:\n"+"".join([str(x)+"\n" for x in errors])
        self.log_details_to_file(details, "test_quantity_alternative_names_natural_syntax_log.txt")
        # Current number of collisions caused by concatenating two units, e.g. "barnewton" has "barn" as substring, "aremole" has "rem" as substring etc.
        assert len(errors)+len(incorrect) <= 144

    @pytest.mark.skip("Too resource intensive")
    def test_slow_quantity_short_forms_natural_syntax(self):
        params = {"strict_syntax": False, "physical_quantity": True, "units_string": "SI common imperial", "strictness": "natural"}
        units = set_of_SI_base_unit_dimensions | set_of_derived_SI_units_in_SI_base_units | set_of_common_units_in_SI | set_of_very_common_units_in_SI | set_of_imperial_units
        incorrect = []
        errors = []
        n = 0
        k = 0
        for prefix in set_of_SI_prefixes:
            for u1 in units:
                for u2 in units:
                    if u1 is not u2 and (prefix[1]+u1[1] not in [u[1] for u in units]):
                        answer = prefix[0]+u1[0]+" "+u2[0]
                        response = prefix[1]+u1[1]+u2[1]
                        n += 1
                        try:
                            result = evaluation_function(response, answer, params)
                            assert result["is_correct"]
                        except Exception:
                            errors.append((answer, response, result["response_latex"]))
                            continue
                        if result["is_correct"] is False:
                            incorrect.append((answer, response, result["response_latex"]))
                        if n-k > 0:
                            print(k)
                            k += 1000
        m = len(errors)+len(incorrect)
        details = "Total: "+str(m)+"/"+str(n)+"\nIncorrect:\n"+"".join([str(x)+"\n" for x in incorrect])+"\nErrors:\n"+"".join([str(x)+"\n" for x in errors])
        self.log_details_to_file(details, "test_quantity_short_forms_natural_syntax_units_log.txt")
        # Current number of collisions caused by concatenating short forms for units, e.g. 'femtometre inch' and 'femtominute' both have short form 'fmin'
        assert len(errors)+len(incorrect) <= 551

    @pytest.mark.parametrize(
        "value,unit,small_diff,large_diff",
        [
            ("10.5",       "kg m/s^2", 0.04,    0.06),
            ("10.55",      "kg m/s^2", 0.004,   0.006),
            ("0.105",      "kg m/s^2", 0.0004,  0.0006),
            ("0.0010",     "kg m/s^2", 0.00004, 0.00006),
            ("100",        "kg m/s^2", 0.4,     0.6),
            ("100*10**10", "kg m/s^2", 4*10**9, 6*10**9)
        ]
    )
    def test_compute_relative_tolerance_from_significant_digits(self, value, unit, small_diff, large_diff):
        ans = value+" "+unit
        res_correct_under = str(eval(value)-small_diff)+" "+unit
        res_correct_over = str(eval(value)+small_diff)+" "+unit
        res_incorrect_under = str(eval(value)-large_diff)+" "+unit
        res_incorrect_over = str(eval(value)+large_diff)+" "+unit
        params = {"strict_syntax": False, "physical_quantity": True, "units_string": "SI", "strictness": "strict"}
        assert evaluation_function(res_correct_under, ans, params)["is_correct"] is True
        assert evaluation_function(res_correct_over, ans, params)["is_correct"] is True
        assert evaluation_function(res_incorrect_under, ans, params)["is_correct"] is False
        assert evaluation_function(res_incorrect_over, ans, params)["is_correct"] is False

    @pytest.mark.parametrize(
        "ans,res",
        [
            ("-10500 g m/s^2", "-10.5 kg m/s^2"),
            ("-10.5 mm^2", "-0.0000105 m^2"),
            ("5 GN", "5000000000 metre kilogram second^(-2)"),
            ("10 pint", "5682.6 centimetre^3"),
            ("1 kg", "2.204 lb")
        ]
    )
    def test_convert_units(self, ans, res):
        params = {"strict_syntax": False, "physical_quantity": True, "units_string": "SI common imperial", "strictness": "strict"}
        result = evaluation_function(res, ans, params)
        assert result["is_correct"]

    @pytest.mark.parametrize(
        "ans,res,tag",
        [
            ("-10.5 kg m/s^2", "kg m/s^2",       "response matches answer_MISSING_VALUE"),
            ("-10.5 kg m/s^2", "-10.5",          "response matches answer_MISSING_UNIT"),
            ("kg m/s^2",       "-10.5 kg m/s^2", "response matches answer_UNEXPECTED_VALUE"),
            ("-10.5",          "-10.5 kg m/s^2", "response matches answer_UNEXPECTED_UNIT")
        ]
    )
    def test_si_units_check_tag(self, ans, res, tag):
        params = {"strict_syntax": False, "physical_quantity": True, "units_string": "SI", "strictness": "strict"}
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert tag in result["tags"]
        assert result["is_correct"] is False

    def test_si_units_parse_error(self):
        ans = "-10.5 kg m/s^2"
        res = "-10.5 kg m/s^"
        params = {"strict_syntax": False, "physical_quantity": True, "units_string": "SI", "strictness": "strict"}
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert "PARSE_ERROR_response" in result["tags"]
        assert result["is_correct"] is False

    @pytest.mark.parametrize(
        "res,is_correct,tag",
        [
            ("-10.5 kilogram metre/second^2",           True,  "response matches answer_TRUE"),
            ("-10.5 kilogram m/s^2",                    True,  "response matches answer_TRUE"),
            ("-10.5 kg m/s^2",                          True,  "response matches answer_TRUE"),
            ("-0.5 kg m/s^2+10 kg m/s^2",               False, "response_REVERTED_UNIT_3"),
            ("-10500 g m/s^2",                          True,  "response matches answer_UNIT_COMPARISON_PREFIX_IS_SMALL"),
            ("-10.46 kg m/s^2",                         True,  "response matches answer_TRUE"),
            ("-10.54 kg m/s^2",                         True,  "response matches answer_TRUE"),
            ("-10.44 kg m/s^2",                         False, "response matches answer_FALSE"),
            ("-10.56 kg m/s^2",                         False, "response matches answer_FALSE"),
            ("-10.5",                                   False, "response matches answer_MISSING_UNIT"),
            ("kg m/s^2",                                False, "response matches answer_MISSING_VALUE"),
            ("-sin(pi/2)*sqrt(441)^(0.77233) kg m/s^2", True,  "response matches answer_TRUE"),
        ]
    )
    def test_demo_si_units_demo_a(self, res, is_correct, tag):
        ans = "-10.5 kilogram metre/second^2"
        params = {
            "strict_syntax": False,
            "physical_quantity": True,
            "units_string": "SI",
            "strictness": "strict",
            "elementary_functions": True,
        }
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert tag in result["tags"]
        assert result["is_correct"] is is_correct

    @pytest.mark.parametrize(
        "res,ans,is_correct,tag,latex",
        [
            ("-10.5",          "-10.5",    True,  "response matches answer_TRUE", r"-10.5"),
            ("-10.5 kg m/s^2", "-10.5",    False, "response matches answer_UNEXPECTED_UNIT",         r"-10.5~\mathrm{kilogram}~\frac{\mathrm{metre}}{\mathrm{second}^{2}}"),
            ("kg m/s^2",       "kg m/s^2", True,  "response matches answer_TRUE", r"\mathrm{kilogram}~\frac{\mathrm{metre}}{\mathrm{second}^{2}}"),
            ("-10.5 kg m/s^2", "kg m/s^2", False, "response matches answer_UNEXPECTED_VALUE",        r"-10.5~\mathrm{kilogram}~\frac{\mathrm{metre}}{\mathrm{second}^{2}}"),
        ]
    )
    def test_demo_si_units_demo_b(self, res, ans, is_correct, tag, latex):
        params = {"strict_syntax": False, "physical_quantity": True, "units_string": "SI", "strictness": "strict"}
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["response_latex"] == latex
        assert tag in result["tags"]
        assert result["is_correct"] == is_correct

    def test_MECH60001_dynamic_signals_error_with_dB(self):
        ans = "48 dB"
        res = "48 dB"
        params = {
            "strict_syntax": False,
            "physical_quantity": True,
            "elementary functions": True
        }
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is True

    def test_quantity_with_multiple_of_positive_value(self):
        ans = "5 Hz"
        res = "10 Hz"
        params = {
            "strict_syntax": False,
            "physical_quantity": True,
            "elementary functions": True,
            "criteria": "response > answer"
        }
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is True

    def test_radians_to_frequency(self):
        ans = "2*pi*f radian/second"
        res = "f Hz"
        params = {
            "strict_syntax": False,
            "physical_quantity": True,
            "elementary functions": True
        }
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is True

    def test_print_floating_point_approximation_of_very_large_numbers(self):
        ans = "2.47*10^4 kg/s"
        res = "2.47**10^4 kg/s"  # This number is large enough than attempting to turn it into a string will cause an error
        params = {
            'rtol': 0.005,
            'comparison': 'expression',
            'strict_syntax': False,
            'physical_quantity': True,
        }
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is False

    def test_legacy_strictness(self):
        ans = "100*kilo*pascal*ohm"
        res = "100 kilopascal ohm"
        params = {
            'strict_syntax': False,
            'physical_quantity': True,
            'strictness': 'legacy',
        }
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is True
        ans = "8650*watt"
        res = "8.65kW"
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is True
        res = "8650W"
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is True
        res = "8650*W"
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is True
        res = "8.65 k   W"
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is True
        res = "8.65 k*W"
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is True
        res = "(8.65)kW"
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is True
        res = "(8650)W"
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is True

    def test_physical_quantity_with_rtol(self):
        ans = "7500 m/s"
        res = "7504.1 m/s"
        params = {
            'rtol': 0.05,
            'strict_syntax': False,
            'physical_quantity': True,
            'elementary_functions': True,
        }
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is True

    def test_physical_quantity_with_atol(self):
        ans = "7500 m/s"
        res = "7504.1 m/s"
        params = {
            'atol': 5,
            'strict_syntax': False,
            'physical_quantity': True,
            'elementary_functions': True,
        }
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is True

#    def test_rad_vs_Hz(self):
#        ans = "28.53 rad/s"
#        res = "4.5405 H"
#        params = {
#            'rtol': 0.03,
#            'strict_syntax': False,
#            'physical_quantity': True,
#            'elementary_functions': True,
#        }
#        result = evaluation_function(res, ans, params, include_test_data=True)
#        assert result["is_correct"] is True

    def test_tolerance_given_as_string(self):
        ans = "4.52 kg"
        res = "13.74 kg"
        params = {
            'rtol': '0.015',
            'strict_syntax': False,
            'physical_quantity': True,
            'elementary_functions': True,
        }
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is False

    def test_answer_zero_value(self):
        ans = "0 m"
        res = "1 m"
        params = {
            'rtol': 0,
            'atol': 0,
            'strict_syntax': False,
            'physical_quantity': True,
            'elementary_functions': True,
        }
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is False

if __name__ == "__main__":
    pytest.main(['-xk not slow', "--no-header", os.path.abspath(__file__)])
