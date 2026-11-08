"""Unit tests for the classical harmonic oscillator interface and validation."""

import math

import numpy as np
import pytest

from qrs.classical import HarmonicOscillatorResult, simulate_harmonic_oscillator


def _result(**overrides: object) -> HarmonicOscillatorResult:
    parameters: dict[str, object] = {
        "mass": 1.0,
        "stiffness": 4.0,
        "initial_displacement": 1.0,
        "initial_velocity": 0.0,
        "t_span": (0.0, 2.0),
        "num_points": 5,
    }
    parameters.update(overrides)
    return simulate_harmonic_oscillator(**parameters)  # type: ignore[arg-type]


def test_default_simulation_shape_and_metadata() -> None:
    result = _result()

    assert isinstance(result, HarmonicOscillatorResult)
    assert result.mass == 1.0
    assert result.stiffness == 4.0
    assert result.angular_frequency == pytest.approx(2.0)
    assert result.initial_energy == pytest.approx(0.5 * 4.0, rel=0.0, abs=0.0)
    assert result.method == "DOP853"
    for array in (
        result.time,
        result.displacement,
        result.velocity,
        result.energy,
        result.analytic_displacement,
        result.analytic_velocity,
    ):
        assert array.shape == (5,)
        assert array.dtype == np.float64


def test_time_grid_includes_requested_endpoints() -> None:
    result = _result(t_span=(1.0, 3.0), num_points=101)

    assert result.time[0] == 1.0
    assert result.time[-1] == 3.0
    assert np.all(np.diff(result.time) > 0.0)


def test_energy_matches_mechanical_energy_definition() -> None:
    result = _result(initial_displacement=0.3, initial_velocity=-0.2)

    expected = 0.5 * result.mass * result.velocity**2 + (
        0.5 * result.stiffness * result.displacement**2
    )
    np.testing.assert_allclose(result.energy, expected, rtol=0.0, atol=0.0)


def test_analytic_solution_uses_elapsed_time_not_absolute_time() -> None:
    mass = 0.5
    stiffness = 2.0
    displacement = 0.2
    velocity = 0.1
    t_start = 2.5
    t_end = 7.5

    result = _result(
        mass=mass,
        stiffness=stiffness,
        initial_displacement=displacement,
        initial_velocity=velocity,
        t_span=(t_start, t_end),
        num_points=101,
    )

    omega = math.sqrt(stiffness / mass)
    elapsed = result.time - t_start
    expected_displacement = displacement * np.cos(omega * elapsed) + (velocity / omega) * np.sin(
        omega * elapsed
    )
    expected_velocity = -displacement * omega * np.sin(omega * elapsed) + (
        velocity * np.cos(omega * elapsed)
    )

    np.testing.assert_allclose(result.analytic_displacement, expected_displacement, atol=1e-15)
    np.testing.assert_allclose(result.analytic_velocity, expected_velocity, atol=1e-15)
    assert result.analytic_displacement[0] == pytest.approx(displacement, abs=1e-15)


def test_zero_initial_conditions_produce_zero_motion_and_energy() -> None:
    result = _result(initial_displacement=0.0, initial_velocity=0.0)

    assert result.initial_energy == 0.0
    np.testing.assert_allclose(result.displacement, 0.0, atol=1e-15)
    np.testing.assert_allclose(result.velocity, 0.0, atol=1e-15)
    np.testing.assert_allclose(result.energy, 0.0, atol=1e-15)
    assert result.max_relative_energy_drift == 0.0


@pytest.mark.parametrize("mass", [0.0, -1.0, math.nan, math.inf])
def test_invalid_mass_is_rejected(mass: float) -> None:
    with pytest.raises(ValueError, match="mass"):
        _result(mass=mass)


@pytest.mark.parametrize("stiffness", [0.0, -2.0, math.nan, math.inf])
def test_invalid_stiffness_is_rejected(stiffness: float) -> None:
    with pytest.raises(ValueError, match="stiffness"):
        _result(stiffness=stiffness)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_initial_conditions_are_rejected(value: float) -> None:
    with pytest.raises(ValueError, match="initial_displacement"):
        _result(initial_displacement=value)
    with pytest.raises(ValueError, match="initial_velocity"):
        _result(initial_velocity=value)


@pytest.mark.parametrize("value", ["abc", None, True])
def test_wrong_scalar_types_are_rejected(value: object) -> None:
    with pytest.raises(TypeError, match="mass"):
        _result(mass=value)


@pytest.mark.parametrize(
    ("t_span", "message"),
    [
        ((1.0,), "exactly two"),
        ((1.0, 2.0, 3.0), "exactly two"),
        ((2.0, 2.0), "greater than start"),
        ((3.0, 2.0), "greater than start"),
        ("01", "sequence"),
        (5.0, "sequence"),
    ],
)
def test_invalid_time_spans_are_rejected(t_span: object, message: str) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        _result(t_span=t_span)


@pytest.mark.parametrize("num_points", [1, 0, -5])
def test_num_points_below_two_is_rejected(num_points: int) -> None:
    with pytest.raises(ValueError, match="at least 2"):
        _result(num_points=num_points)


@pytest.mark.parametrize("num_points", [2.5, "10", True])
def test_non_integer_num_points_is_rejected(num_points: object) -> None:
    with pytest.raises(TypeError, match="num_points"):
        _result(num_points=num_points)


def test_unsupported_method_is_rejected_with_choices() -> None:
    with pytest.raises(ValueError, match="unsupported integration method"):
        _result(method="Euler")


@pytest.mark.parametrize("name", ["method", "rtol", "atol"])
@pytest.mark.parametrize("value", ["", None, 0.0, -1.0, math.nan])
def test_invalid_solver_options_are_rejected(name: str, value: object) -> None:
    with pytest.raises((TypeError, ValueError), match=name):
        _result(**{name: value})
