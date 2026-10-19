import pytest
from sympy import Integer, Symbol

# Import necessary data and reference cases for tests
from app import evaluation
from app.context.physical_quantity.comparison import is_proportional
from app.evaluation import evaluation_function
from app.tests.physical_quantity_test_cases import slr_strict_si_syntax_test_cases, slr_natural_si_syntax_test_cases
from lambdafeedback.units import (
    COMMON_UNITS,
    IMPERIAL_UNITS,
    SI_BASE_UNITS,
    SI_DERIVED_UNITS,
    SI_PREFIXES,
    VERY_COMMON_UNITS,
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

    @pytest.mark.parametrize("string,value,unit,content,value_latex,unit_latex,criteria", slr_strict_si_syntax_test_cases)
    @pytest.mark.slow
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
    @pytest.mark.slow
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
        units = SI_BASE_UNITS + SI_DERIVED_UNITS + COMMON_UNITS + VERY_COMMON_UNITS + IMPERIAL_UNITS
        incorrect = []
        errors = []
        n = 0
        for prefix in SI_PREFIXES:
            for u1 in units:
                for u2 in units:
                    if u1 is not u2:
                        answer = prefix[0] + u1[0] + " " + u2[0]
                        for u1_alt in (u1[0],) + u1[3]:
                            for u2_alt in (u2[0],) + u2[3] + u2[4]:
                                n += 1
                                response = prefix[0] + u1_alt + u2_alt
                                try:
                                    result = evaluation_function(response, answer, params)
                                except Exception:
                                    errors.append((answer, response))
                                    continue
                                if result["is_correct"] is False:
                                    incorrect.append((answer, response, result["response_latex"]))
        m = len(errors) + len(incorrect)
        details = "Total: " + str(m) + "/" + str(n) + "\nIncorrect:\n" + "".join([str(x) + "\n" for x in incorrect]) + "\nErrors:\n" + "".join([str(x) + "\n" for x in errors])
        # Current number of collisions caused by concatenating two units, e.g. "barnewton" has "barn" as substring, "aremole" has "rem" as substring etc.
        assert m <= 144, details

    @pytest.mark.skip("Too resource intensive")
    def test_slow_quantity_short_forms_natural_syntax(self):
        params = {"strict_syntax": False, "physical_quantity": True, "units_string": "SI common imperial", "strictness": "natural"}
        units = SI_BASE_UNITS + SI_DERIVED_UNITS + COMMON_UNITS + VERY_COMMON_UNITS + IMPERIAL_UNITS
        incorrect = []
        errors = []
        n = 0
        for prefix in SI_PREFIXES:
            for u1 in units:
                for u2 in units:
                    if u1 is not u2 and (prefix[1] + u1[1] not in [u[1] for u in units]):
                        answer = prefix[0] + u1[0] + " " + u2[0]
                        response = prefix[1] + u1[1] + u2[1]
                        n += 1
                        try:
                            result = evaluation_function(response, answer, params)
                            assert result["is_correct"]
                        except Exception:
                            errors.append((answer, response, result["response_latex"]))
                            continue
                        if result["is_correct"] is False:
                            incorrect.append((answer, response, result["response_latex"]))
        m = len(errors) + len(incorrect)
        details = "Total: " + str(m) + "/" + str(n) + "\nIncorrect:\n" + "".join([str(x) + "\n" for x in incorrect]) + "\nErrors:\n" + "".join([str(x) + "\n" for x in errors])
        # Current number of collisions caused by concatenating short forms for units, e.g. 'femtometre inch' and 'femtominute' both have short form 'fmin'
        assert m <= 551, details

    @pytest.mark.parametrize(
        "value,unit,small_diff,large_diff",
        [
            ("10.5",       "kg m/s^2", 0.04,    0.06),
            ("10.55",      "kg m/s^2", 0.004,   0.006),
            ("0.105",      "kg m/s^2", 0.0004,  0.0006),
            ("0.0010",     "kg m/s^2", 0.00004, 0.00006),
            ("100",        "kg m/s^2", 0.4,     0.6),
            ("100*10**10", "kg m/s^2", 4 * 10**9, 6 * 10**9)
        ]
    )
    @pytest.mark.slow
    def test_compute_relative_tolerance_from_significant_digits(self, value, unit, small_diff, large_diff):
        ans = value + " " + unit
        res_correct_under = str(eval(value) - small_diff) + " " + unit
        res_correct_over = str(eval(value) + small_diff) + " " + unit
        res_incorrect_under = str(eval(value) - large_diff) + " " + unit
        res_incorrect_over = str(eval(value) + large_diff) + " " + unit
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

    @pytest.mark.parametrize(
        "response, answer, order_operator, value",
        [
            ("10 Hz", "5 Hz", ">", True),
            ("5 Hz", "10 Hz", ">", False),
            ("10 Hz", "10 Hz", ">", False),
            ("10 Hz", "5 Hz", "<", False),
            ("5 Hz", "10 Hz", "<", True),
            ("10 Hz", "10 Hz", "<", False),
            ("10 Hz", "5 Hz", ">=", True),
            ("5 Hz", "10 Hz", ">=", False),
            ("10 Hz", "10 Hz", ">=", True),
            ("10 Hz", "5 Hz", "<=", False),
            ("5 Hz", "10 Hz", "<=", True),
            ("10 Hz", "10 Hz", "<=", True),
        ]
    )
    def test_order_operators(self, response, answer, order_operator, value):
        params = {
            "strict_syntax": False,
            "physical_quantity": True,
            "elementary functions": True,
            "criteria": "response " + order_operator + " answer"
        }
        result = evaluation_function(response, answer, params, include_test_data=True)
        assert result["is_correct"] is value

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

    @pytest.mark.filterwarnings("ignore:legacy_preprocessing is deprecated:DeprecationWarning")
    def test_legacy_strictness(self):
        ans = "100*kilo*pascal*ohm"
        res = "100 kilopascal ohm"
        params = {
            'strict_syntax': False,
            'physical_quantity': True,
            'strictness': 'legacy',
        }
        with pytest.warns(DeprecationWarning, match="legacy_preprocessing is deprecated"):
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

    def test_physical_quantity_with_rel_tol(self):
        ans = "7500 m/s"
        res = "7504.1 m/s"
        params = {
            'relative_tolerance': 0.05,
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

    def test_physical_quantity_with_abs_tol(self):
        ans = "7500 m/s"
        res = "7504.1 m/s"
        params = {
            'absolute_tolerance': 5,
            'strict_syntax': False,
            'physical_quantity': True,
            'elementary_functions': True,
        }
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is True

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

    def test_physical_quantity_with_atol_and_kg_unit(self):
        ans = "20 kg"
        params = {
            'atol': 0.05,
            'strict_syntax': False,
            'physical_quantity': True,
            'elementary_functions': True,
        }
        res = "19.97 kg"
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is True
        res = "19.5 kg"
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is False

    def test_physical_quantity_with_atol_and_km_unit(self):
        ans = "5 km"
        params = {
            'atol': 0.05,
            'strict_syntax': False,
            'physical_quantity': True,
            'elementary_functions': True,
        }
        res = "5.03 km"
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is True
        res = "5.2 km"
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is False

    def test_physical_quantity_with_abs_tol_and_non_base_unit(self):
        ans = "20 kg"
        res = "19.97 kg"
        params = {
            'absolute_tolerance': 0.05,
            'strict_syntax': False,
            'physical_quantity': True,
            'elementary_functions': True,
        }
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is True

    def test_physical_quantity_with_atol_and_imperial_mass_unit(self):
        ans = "10 lb"
        params = {
            'atol': 0.05,
            'strict_syntax': False,
            'physical_quantity': True,
            'elementary_functions': True,
        }
        res = "10.03 lb"
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is True
        res = "10.2 lb"
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is False

    def test_physical_quantity_with_atol_and_imperial_length_unit(self):
        ans = "3 mile"
        params = {
            'atol': 0.05,
            'strict_syntax': False,
            'physical_quantity': True,
            'elementary_functions': True,
        }
        res = "3.02 mile"
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is True
        res = "3.1 mile"
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is False

    def test_physical_quantity_with_atol_and_compound_unit_force(self):
        ans = "10 kg m/s^2"
        params = {
            'atol': 0.02,
            'strict_syntax': False,
            'physical_quantity': True,
            'elementary_functions': True,
        }
        res = "10.01 kg m/s^2"
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is True
        res = "10.05 kg m/s^2"
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is False

    def test_physical_quantity_with_atol_and_compound_unit_density(self):
        ans = "2.5 kg/m^3"
        params = {
            'atol': 0.01,
            'strict_syntax': False,
            'physical_quantity': True,
            'elementary_functions': True,
        }
        res = "2.505 kg/m^3"
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is True
        res = "2.52 kg/m^3"
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is False

    def test_physical_quantity_with_atol_and_mixed_units_kg_g(self):
        ans = "1 kg"
        params = {
            'atol': 0.01,
            'strict_syntax': False,
            'physical_quantity': True,
            'elementary_functions': True,
        }
        res = "998 g"
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is True
        res = "950 g"
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is False

    def test_physical_quantity_with_rtol_and_kg_unit(self):
        ans = "20 kg"
        res = "21 kg"
        params = {
            'rtol': 0.1,
            'strict_syntax': False,
            'physical_quantity': True,
            'elementary_functions': True,
        }
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is True

    def test_physical_quantity_with_rtol_and_imperial_mass_unit(self):
        ans = "10 lb"
        res = "10.9 lb"
        params = {
            'rtol': 0.1,
            'strict_syntax': False,
            'physical_quantity': True,
            'elementary_functions': True,
        }
        result = evaluation_function(res, ans, params, include_test_data=True)
        assert result["is_correct"] is True

    @pytest.mark.parametrize(
        "criteria,is_correct",
        [
            ("response matches 2 m", False),
            ("response matches 2", False),
            ("2 m matches response", False),
            # Only checks that it no longer raises: the value match ignores `dimension(...)`
            ("dimension(response) matches dimension(answer)", None),
            ("answer matches answer", True),
        ]
    )
    def test_matches_criteria_other_than_response_and_answer_when_values_differ(self, criteria, is_correct):
        # Used to raise UnboundLocalError in the tolerance check (bug 1 in the bug report)
        params = {
            'strict_syntax': False,
            'physical_quantity': True,
            'elementary_functions': True,
            'criteria': criteria,
        }
        result = evaluation_function("2.1 m", "1.0 m", params)
        if is_correct is not None:
            assert result["is_correct"] is is_correct

    @pytest.mark.parametrize(
        "res,ans,criteria,is_correct",
        [
            # Used to raise TypeError: cannot determine truth value of Relational (bug 14 in the bug report)
            ("2.1 m", "1 m", "response > 1.5 m", True),
            ("2.1 m", "1 m", "response > 1.5 metre", True),
            ("2.1 m", "1 m", "response > 3 m", False),
            ("2.1 m", "1 m", "response > answer", True),
            # Used to raise TypeError when the quantities have no units
            ("2.1", "1", "response > answer", True),
            ("2.1", "1", "response < 2", False),
        ]
    )
    def test_order_criteria_against_written_out_quantity(self, res, ans, criteria, is_correct):
        params = {
            'strict_syntax': False,
            'physical_quantity': True,
            'elementary_functions': True,
            'criteria': criteria,
        }
        result = evaluation_function(res, ans, params)
        assert result["is_correct"] is is_correct

    @pytest.mark.parametrize(
        "res,criteria,is_correct",
        [
            # Used to be false for every response (bug 16 in the bug report)
            ("2 m", "response matches 2 m", True),
            ("2 m", "response matches 2 metre", True),
            ("2 m", "2 m matches response", True),
            ("2000 mm", "response matches 2 m", True),
            ("2.1 m", "response matches 2 m", False),
            ("2 s", "response matches 2 m", False),
        ]
    )
    def test_matches_criteria_against_written_out_quantity(self, res, criteria, is_correct):
        params = {
            'strict_syntax': False,
            'physical_quantity': True,
            'elementary_functions': True,
            'criteria': criteria,
        }
        result = evaluation_function(res, "1 m", params)
        assert result["is_correct"] is is_correct

    @pytest.mark.parametrize(
        "lhs_value,rhs_value,expected",
        [
            (Integer(2000), Integer(2), (True, 1000.0)),
            (Integer(2), Integer(2000), (True, 0.001)),
            # Used to divide by zero (bug 2 in the bug report)
            (Integer(2), Integer(0), (False, None)),
            (Integer(0), Integer(2), (False, None)),
            (Integer(0), Integer(0), (False, None)),
            (Symbol("z"), Integer(2), (False, None)),
        ]
    )
    def test_is_proportional(self, lhs_value, rhs_value, expected):
        # Units and dimensions are never zero, so `evaluation_function` cannot reach these cases
        x, y = Symbol("x"), Symbol("y")
        assert is_proportional(x, y, [("x", lhs_value), ("y", rhs_value)]) == expected

    @pytest.mark.parametrize("criteria", ["response matches answer", "response > answer"])
    def test_criteria_graph_identifier(self, criteria, monkeypatch):
        # The identifier is not in the serialised test data, so capture the graphs before feedback is generated
        criteria_graphs = {}
        generate_feedback = evaluation.generate_feedback

        def capture_graphs(graphs, evaluation_parameters):
            criteria_graphs.update(graphs)
            generate_feedback(graphs, evaluation_parameters)

        monkeypatch.setattr(evaluation, "generate_feedback", capture_graphs)
        evaluation_function("2.1 m", "1 m", {"physical_quantity": True, "criteria": criteria})
        # The matches graph used to have identifier None (bug 8 in the bug report)
        assert criteria_graphs[criteria].identifier == criteria

    @pytest.mark.parametrize(
        "ans,res",
        [
            ("10 ohm", "10 Ω"),
            ("10 microA", "10 μA"),
            ("10 microA", "10 μ A"),
            ("30 degree", "30 °"),
        ]
    )
    @pytest.mark.slow
    def test_greek_letter_units(self, ans, res):
        params = {
            'strict_syntax': False,
            'physical_quantity': True,
            'elementary_functions': True,
        }
        result = evaluation_function(res, ans, params)
        assert result["is_correct"] is True
