import pytest

from app.context.symbolic.numerical import decimal_places_match, sig_figs_match
from app.context.tolerance import absolute_tolerance_from_decimal_places, relative_tolerance_from_sig_figs


class TestRelativeToleranceFromSigFigs:

    @pytest.mark.parametrize(
        "sig_figs, expected",
        [
            (1, 0.5),
            (2, 5e-2),
            (3, 5e-3),
            (6, 5e-6),
        ]
    )
    def test_relative_tolerance_from_sig_figs(self, sig_figs, expected):
        assert relative_tolerance_from_sig_figs(sig_figs) == pytest.approx(expected)

    def test_no_lower_floor(self):
        # Unlike compute_relative_tolerance_from_significant_decimals there is no
        # DEFAULT_SIGNIFICANT_FIGURES floor
        assert relative_tolerance_from_sig_figs(1) == pytest.approx(0.5)


class TestSigFigsMatch:

    @pytest.mark.parametrize(
        "response_string, response_value, answer_value, sig_figs, expected",
        [
            # Correct value and precision
            ("3.14", 3.14, 3.14159, 3, True),
            # Numerically wrong
            ("3.15", 3.15, 3.14159, 3, False),
            # Numerically correct but too many digits written
            ("3.14159", 3.14159, 3.14159, 3, False),
            # Numerically correct but too few digits written
            ("3.1", 3.1, 3.10, 3, False),
            # Negative numbers
            ("-3.14", -3.14, -3.14159, 3, True),
            # Zero answer: precision check is bypassed
            ("0", 0.0, 0.0, 3, True),
            # Trailing decimal zeros are significant
            ("92.00", 92.00, 92, 4, True),
            # Leading zeros are not significant
            ("0.0032", 0.0032, 0.0032, 2, True),
            # Whole number trailing zeros are not significant
            ("540", 540, 540, 2, True),
            ("540", 540, 540, 3, False),
            # Explicit trailing decimal point makes trailing zeros significant
            ("540.", 540, 540, 3, True),
            # Scientific notation
            ("5.02e4", 50200, 50200, 3, True),
            # Non-numeric response
            ("two", 0, 3.14159, 3, False),
            ("3.14e", 3.14, 3.14159, 3, False),
        ]
    )
    def test_sig_figs_match(self, response_string, response_value, answer_value, sig_figs, expected):
        assert sig_figs_match(response_string, response_value, answer_value, sig_figs) is expected


class TestAbsoluteToleranceFromDecimalPlaces:

    @pytest.mark.parametrize(
        "decimal_places, expected",
        [
            (0, 0.5),
            (1, 5e-2),
            (2, 5e-3),
            (3, 5e-4),
        ]
    )
    def test_absolute_tolerance_from_decimal_places(self, decimal_places, expected):
        assert absolute_tolerance_from_decimal_places(decimal_places) == pytest.approx(expected)


class TestDecimalPlacesMatch:

    @pytest.mark.parametrize(
        "response_string, response_value, answer_value, decimal_places, expected",
        [
            # Correct value and precision
            ("3.14", 3.14, 3.14159, 2, True),
            # Numerically wrong
            ("3.15", 3.15, 3.14159, 2, False),
            # Numerically correct but too many decimal places written
            ("3.142", 3.142, 3.14159, 2, False),
            # Numerically correct but too few decimal places written
            ("3.1", 3.1, 3.1, 2, False),
            ("3.10", 3.1, 3.1, 2, True),
            # Negative numbers
            ("-3.14", -3.14, -3.14159, 2, True),
            # Zero value: precision is still checked, unlike sig_figs_match
            ("0", 0.0, 0.0, 2, False),
            ("0.00", 0.0, 0.0, 2, True),
            # Trailing decimal zeros count
            ("92.00", 92.00, 92, 2, True),
            ("92.0", 92.0, 92, 2, False),
            # decimal_places = 0 requires a whole-number response
            ("3", 3.0, 3.14159, 0, True),
            ("3.0", 3.0, 3.14159, 0, False),
            # Scientific notation
            ("5e-3", 0.005, 0.005, 3, True),
            ("5.0e-3", 0.005, 0.005, 3, False),
            ("5.02e4", 50200, 50200, 0, True),
            # Non-numeric response
            ("two", 0, 3.14159, 2, False),
            ("3.14e", 3.14, 3.14159, 2, False),
        ]
    )
    def test_decimal_places_match(self, response_string, response_value, answer_value, decimal_places, expected):
        assert decimal_places_match(response_string, response_value, answer_value, decimal_places) is expected
