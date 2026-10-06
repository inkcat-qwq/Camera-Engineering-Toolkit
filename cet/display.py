"""Pure display formatting. All input lengths are mm; calculations stay exact."""
import math
from .core import finite, integer


def _number(value, decimals):
    if value == 0:
        return "0" if decimals is None else f"{0:.{decimals}f}"
    # Keep very small nonzero results visible instead of rounding to zero.
    if decimals is not None and abs(value) < .5 * 10 ** (-decimals):
        return f"{value:.3g}"
    return f"{value:.{decimals}f}" if decimals is not None else f"{value:.4g}"


def length(mm, *, signed=False):
    value = float(mm)
    if math.isinf(value):
        return "∞" if value > 0 else "−∞"
    finite(mm, "Length")
    magnitude = abs(value)
    if magnitude >= 1000:
        scaled, unit = value / 1000, "m"
        decimals = max(0, 3 - int(math.floor(math.log10(abs(scaled))))) if magnitude < 1e7 else None
    else:
        scaled, unit = value, "mm"
        decimals = 3 if magnitude < 10 else 2 if magnitude < 100 else 1
        if 0 < magnitude < 1:
            decimals = min(9, max(3, 3 - int(math.floor(math.log10(magnitude)))))
    text = _number(scaled, decimals)
    return ("+" if signed and value > 0 else "") + text + " " + unit


def angle(degrees):
    value = finite(degrees, "Angle")
    return _number(value, 2 if abs(value) >= 1 else None) + "°"


def percentage(fraction, samples):
    p = finite(fraction, "Probability", nonnegative=True)
    if p > 1:
        raise ValueError("Probability must be between zero and one.")
    n = integer(samples, "Samples", 1, 2**53)
    # At most one decimal digit finer than the observed one-event resolution.
    decimals = min(6, max(1, int(math.ceil(math.log10(n / 100)))))
    return _number(100 * p, decimals) + "%"


def comparison_focals(text):
    """Bound work before splitting/parsing an untrusted comparison text field."""
    if len(text) > 1024 or text.count(",") >= 60:
        raise ValueError("Use at most 60 format / focal-length combinations.")
    values = [finite(float(v.strip()), "Focal length", positive=True) for v in text.split(",") if v.strip()]
    if not values:
        raise ValueError("Enter at least one focal length.")
    if any(v > 10000 for v in values):
        raise ValueError("Comparison focal lengths must not exceed 10,000 mm.")
    return values
