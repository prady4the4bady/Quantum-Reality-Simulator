"""Unit tests for shared scalar validation helpers."""

import math

import numpy as np
import pytest

from qrs.core.validation import require_finite_real, require_positive_finite


@pytest.mark.parametrize("value", [0.0, 1, -3, np.float64(2.5), np.int64(7)])
def test_require_finite_real_accepts_real_numbers(value: object) -> None:
    assert require_finite_real(value, "x") == float(value)


@pytest.mark.parametrize("value", [True, False])
def test_require_finite_real_rejects_booleans(value: bool) -> None:
    with pytest.raises(TypeError, match="x must be a real number"):
        require_finite_real(value, "x")


@pytest.mark.parametrize("value", [1 + 2j, "1.0", None, [1.0], {}])
def test_require_finite_real_rejects_non_real_types(value: object) -> None:
    with pytest.raises(TypeError, match="x must be a real number"):
        require_finite_real(value, "x")


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_require_finite_real_rejects_non_finite_values(value: float) -> None:
    with pytest.raises(ValueError, match="x must be finite"):
        require_finite_real(value, "x")


@pytest.mark.parametrize("value", [1.0, 1, np.float64(3.5), np.int64(2)])
def test_require_positive_finite_accepts_positive_values(value: object) -> None:
    assert require_positive_finite(value, "k") == float(value)


@pytest.mark.parametrize("value", [0.0, -1.0, -1, math.nan, math.inf])
def test_require_positive_finite_rejects_invalid_values(value: float) -> None:
    with pytest.raises(ValueError):
        require_positive_finite(value, "k")
