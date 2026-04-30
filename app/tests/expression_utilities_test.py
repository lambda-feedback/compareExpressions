import pytest
from ..utility.expression_utilities import convert_unicode_dashes


class TestConvertUnicodeDashes:

    @pytest.mark.parametrize(
        "expr, expected",
        [
            # No dashes at all
            ("x+y", []),
            # ASCII hyphen-minus is not a unicode dash — no substitution
            ("x-y", []),
            # Empty string
            ("", []),
            # HYPHEN (U+2010)
            ("x‐y", [("‐", "-")]),
            # NON-BREAKING HYPHEN (U+2011)
            ("x‑y", [("‑", "-")]),
            # FIGURE DASH (U+2012)
            ("x‒y", [("‒", "-")]),
            # EN DASH (U+2013)
            ("x–y", [("–", "-")]),
            # EM DASH (U+2014)
            ("x—y", [("—", "-")]),
            # MINUS SIGN (U+2212)
            ("x−y", [("−", "-")]),
            # SMALL HYPHEN-MINUS (U+FE63)
            ("x﹣y", [("﹣", "-")]),
            # FULLWIDTH HYPHEN-MINUS (U+FF0D)
            ("x－y", [("－", "-")]),
            # Multiple different unicode dashes in one expression
            ("x–y−z", [("–", "-"), ("−", "-")]),
            # Repeated occurrences of the same dash — still one substitution pair
            ("x−y−z", [("−", "-")]),
        ]
    )
    def test_convert_unicode_dashes(self, expr, expected):
        result = convert_unicode_dashes(expr)
        assert result == expected