"""The numerical tolerance check shared by the symbolic and physical quantity contexts."""

from __future__ import annotations

from sympy import Basic


def values_within_tolerance(res: Basic, ans: Basic, rtol: float, atol: float) -> bool:
    """
    Whether `res` is within the tolerances of `ans`, using the same rule as numpy.isclose:
    |ans - res| <= atol + rtol*|ans|.

    If `ans` and `res` still contain symbols that cancel in (ans - res)/ans (e.g. both are multiples of rho*L**3),
    only the relative tolerance is checked, since atol needs a numerical value of `ans`.
    Returns False when the values cannot be compared numerically.
    """
    try:
        return bool(abs(float(ans - res)) <= atol + rtol * abs(float(ans)))
    except TypeError:
        pass
    try:
        return bool(abs(float((ans - res) / ans)) <= rtol)
    except (TypeError, ZeroDivisionError):
        return False


def relative_tolerance_from_sig_figs(sig_figs: int) -> float:
    """The relative tolerance for agreement to `sig_figs` significant figures, 5*10**(-sig_figs)."""
    return 5 * 10 ** (-sig_figs)


def absolute_tolerance_from_decimal_places(decimal_places: int) -> float:
    """The absolute tolerance for agreement to `decimal_places` decimal places, 0.5*10**(-decimal_places)."""
    return 0.5 * 10 ** (-decimal_places)
