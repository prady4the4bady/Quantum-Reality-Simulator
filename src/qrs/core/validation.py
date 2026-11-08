"""Strict validation of scalar physical inputs.

The helpers reject booleans explicitly because Python treats ``bool`` as an
``int`` subclass. Silently accepting ``True`` as a mass of ``1.0`` would make
invalid physical input look valid.
"""

from __future__ import annotations

import math
from numbers import Real


def require_finite_real(value: Real, name: str) -> float:
    """Return ``value`` as a finite ``float`` or raise a descriptive error.

    Parameters
    ----------
    value:
        Candidate scalar. Must be a real number and must not be a boolean.
    name:
        Human-readable parameter name used in error messages.

    Raises
    ------
    TypeError
        If ``value`` is not a real number or is a boolean.
    ValueError
        If ``value`` is NaN or infinite.
    """

    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number, got {type(value).__name__}")

    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite, got {result!r}")
    return result


def require_positive_finite(value: Real, name: str) -> float:
    """Return a finite, strictly positive ``float`` or raise an error."""

    result = require_finite_real(value, name)
    if result <= 0.0:
        raise ValueError(f"{name} must be greater than zero, got {result!r}")
    return result
