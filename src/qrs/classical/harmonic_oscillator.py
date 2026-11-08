"""Classical one-dimensional harmonic oscillator.

The implemented model is the undamped, unforced oscillator

.. math::

    m \\ddot{x}(t) + k x(t) = 0,

with constant mass :math:`m > 0` and spring stiffness :math:`k > 0`. The
equation is integrated as the first-order system

.. math::

    \\dot{x} = v, \\qquad \\dot{v} = -\\frac{k}{m} x.

All quantities use SI units: mass in kilograms (kg), stiffness in newtons per
metre (N/m), displacement in metres (m), velocity in metres per second (m/s),
time in seconds (s), and energy in joules (J).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from numbers import Integral

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import solve_ivp

from qrs.core.validation import require_finite_real, require_positive_finite

_SUPPORTED_METHODS = frozenset({"RK45", "RK23", "DOP853", "Radau", "BDF", "LSODA"})


@dataclass(frozen=True, slots=True)
class HarmonicOscillatorResult:
    """Numerical and analytical results for one oscillator trajectory.

    Arrays are indexed by the requested evaluation times. ``energy`` is the
    total mechanical energy :math:`E = \\tfrac{1}{2} m v^2 + \\tfrac{1}{2} k x^2`.
    Error fields compare the numerical trajectory with the exact analytical
    solution for the same initial conditions.
    """

    mass: float
    stiffness: float
    angular_frequency: float
    initial_displacement: float
    initial_velocity: float
    initial_energy: float
    time: NDArray[np.float64]
    displacement: NDArray[np.float64]
    velocity: NDArray[np.float64]
    energy: NDArray[np.float64]
    analytic_displacement: NDArray[np.float64]
    analytic_velocity: NDArray[np.float64]
    max_abs_displacement_error: float
    max_relative_displacement_error: float
    max_abs_energy_drift: float
    max_relative_energy_drift: float
    method: str


def _validate_time_span(t_span: Sequence[float]) -> tuple[float, float]:
    if isinstance(t_span, (str, bytes)):
        raise TypeError("t_span must be a sequence of two real numbers")

    try:
        values = tuple(t_span)
    except TypeError as exc:
        raise TypeError("t_span must be a sequence of two real numbers") from exc

    if len(values) != 2:
        raise ValueError(f"t_span must contain exactly two values, got {len(values)}")

    start = require_finite_real(values[0], "t_span[0]")
    end = require_finite_real(values[1], "t_span[1]")
    if end <= start:
        raise ValueError(f"t_span end must be greater than start, got ({start}, {end})")
    return start, end


def _validate_num_points(num_points: int) -> int:
    if isinstance(num_points, bool) or not isinstance(num_points, Integral):
        raise TypeError(f"num_points must be an integer, got {type(num_points).__name__}")
    count = int(num_points)
    if count < 2:
        raise ValueError(f"num_points must be at least 2, got {count}")
    return count


def _validate_tolerance(value: float, name: str) -> float:
    tolerance = require_positive_finite(value, name)
    return tolerance


def _analytic_solution(
    *,
    mass: float,
    stiffness: float,
    initial_displacement: float,
    initial_velocity: float,
    t_span: tuple[float, float],
    time: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    omega = math.sqrt(stiffness / mass)
    elapsed = time - t_span[0]
    cosine = np.cos(omega * elapsed)
    sine = np.sin(omega * elapsed)

    displacement = initial_displacement * cosine + (initial_velocity / omega) * sine
    velocity = -initial_displacement * omega * sine + initial_velocity * cosine
    return displacement, velocity


def simulate_harmonic_oscillator(
    *,
    mass: float,
    stiffness: float,
    initial_displacement: float = 0.0,
    initial_velocity: float = 0.0,
    t_span: Sequence[float] = (0.0, 10.0),
    num_points: int = 1001,
    method: str = "DOP853",
    rtol: float = 1e-10,
    atol: float = 1e-12,
) -> HarmonicOscillatorResult:
    """Integrate the undamped harmonic oscillator and compare with theory.

    Parameters
    ----------
    mass:
        Mass :math:`m` in kg. Must be finite and strictly positive.
    stiffness:
        Spring stiffness :math:`k` in N/m. Must be finite and strictly positive.
    initial_displacement:
        Displacement :math:`x(t_0)` in m.
    initial_velocity:
        Velocity :math:`\\dot{x}(t_0)` in m/s.
    t_span:
        ``(t_start, t_end)`` in s, with ``t_end > t_start``.
    num_points:
        Number of uniformly spaced evaluation times. Must be at least 2.
    method:
        SciPy ``solve_ivp`` method. Non-stiff methods are appropriate here.
    rtol, atol:
        Relative and absolute solver tolerances. Both must be positive.

    Returns
    -------
    HarmonicOscillatorResult
        Numerical trajectory, analytical reference, energy history and error
        metrics.

    Raises
    ------
    TypeError
        If an input has the wrong type.
    ValueError
        If a physical parameter or time interval is invalid.
    RuntimeError
        If SciPy fails to integrate the equation or returns non-finite data.
    """

    validated_mass = require_positive_finite(mass, "mass")
    validated_stiffness = require_positive_finite(stiffness, "stiffness")
    validated_displacement = require_finite_real(initial_displacement, "initial_displacement")
    validated_velocity = require_finite_real(initial_velocity, "initial_velocity")
    start, end = _validate_time_span(t_span)
    count = _validate_num_points(num_points)
    validated_rtol = _validate_tolerance(rtol, "rtol")
    validated_atol = _validate_tolerance(atol, "atol")

    if not isinstance(method, str) or not method:
        raise TypeError("method must be a non-empty string")
    if method not in _SUPPORTED_METHODS:
        supported = ", ".join(sorted(_SUPPORTED_METHODS))
        raise ValueError(f"unsupported integration method {method!r}; choose from {supported}")

    omega_squared = validated_stiffness / validated_mass

    def rhs(_time: float, state: NDArray[np.float64]) -> tuple[float, float]:
        displacement, velocity = state
        return velocity, -omega_squared * displacement

    initial_state = np.array(
        [validated_displacement, validated_velocity],
        dtype=np.float64,
    )
    time = np.linspace(start, end, count, dtype=np.float64)

    solution = solve_ivp(
        rhs,
        (start, end),
        initial_state,
        method=method,
        t_eval=time,
        rtol=validated_rtol,
        atol=validated_atol,
    )

    if not solution.success:
        raise RuntimeError(f"harmonic oscillator integration failed: {solution.message}")

    numerical_state = np.asarray(solution.y, dtype=np.float64)
    if numerical_state.shape != (2, count):
        raise RuntimeError(
            "harmonic oscillator integration returned an unexpected state shape "
            f"{numerical_state.shape}; expected (2, {count})"
        )
    if not np.all(np.isfinite(numerical_state)):
        raise RuntimeError("harmonic oscillator integration returned non-finite values")

    displacement = numerical_state[0]
    velocity = numerical_state[1]
    energy = 0.5 * validated_mass * velocity**2 + 0.5 * validated_stiffness * displacement**2

    analytic_displacement, analytic_velocity = _analytic_solution(
        mass=validated_mass,
        stiffness=validated_stiffness,
        initial_displacement=validated_displacement,
        initial_velocity=validated_velocity,
        t_span=(start, end),
        time=time,
    )

    absolute_error = np.abs(displacement - analytic_displacement)
    max_abs_error = float(np.max(absolute_error))
    analytic_scale = float(np.max(np.abs(analytic_displacement)))
    if analytic_scale == 0.0:
        max_relative_error = 0.0 if max_abs_error == 0.0 else math.inf
    else:
        max_relative_error = max_abs_error / analytic_scale

    initial_energy = 0.5 * validated_stiffness * validated_displacement**2 + (
        0.5 * validated_mass * validated_velocity**2
    )
    energy_drift = np.abs(energy - initial_energy)
    max_abs_energy_drift = float(np.max(energy_drift))
    if initial_energy == 0.0:
        max_relative_energy_drift = 0.0
    else:
        max_relative_energy_drift = max_abs_energy_drift / initial_energy

    return HarmonicOscillatorResult(
        mass=validated_mass,
        stiffness=validated_stiffness,
        angular_frequency=math.sqrt(omega_squared),
        initial_displacement=validated_displacement,
        initial_velocity=validated_velocity,
        initial_energy=initial_energy,
        time=time,
        displacement=displacement,
        velocity=velocity,
        energy=energy,
        analytic_displacement=analytic_displacement,
        analytic_velocity=analytic_velocity,
        max_abs_displacement_error=max_abs_error,
        max_relative_displacement_error=max_relative_error,
        max_abs_energy_drift=max_abs_energy_drift,
        max_relative_energy_drift=max_relative_energy_drift,
        method=method,
    )
