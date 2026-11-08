"""Scientific validation of the classical harmonic oscillator."""

import math

import numpy as np
import pytest

from qrs.classical import simulate_harmonic_oscillator

pytestmark = pytest.mark.scientific


def test_trajectory_matches_analytic_solution() -> None:
    result = simulate_harmonic_oscillator(
        mass=2.0,
        stiffness=8.0,
        initial_displacement=0.3,
        initial_velocity=-0.4,
        t_span=(0.0, 5.0),
        num_points=501,
    )

    assert result.max_abs_displacement_error < 1e-8
    assert result.max_relative_displacement_error < 1e-8
    np.testing.assert_allclose(
        result.displacement,
        result.analytic_displacement,
        rtol=0.0,
        atol=1e-8,
    )


def test_energy_is_conserved_within_solver_tolerance() -> None:
    result = simulate_harmonic_oscillator(
        mass=0.5,
        stiffness=2.0,
        initial_displacement=1.0,
        initial_velocity=0.5,
        t_span=(0.0, 20.0),
        num_points=2001,
        rtol=1e-10,
        atol=1e-12,
    )

    assert result.initial_energy > 0.0
    assert result.max_relative_energy_drift < 1e-8
    np.testing.assert_allclose(result.energy, result.initial_energy, rtol=1e-8, atol=0.0)


def test_tighter_tolerances_reduce_discretization_error() -> None:
    common = {
        "mass": 2.0,
        "stiffness": 8.0,
        "initial_displacement": 0.3,
        "initial_velocity": -0.4,
        "t_span": (0.0, 5.0),
        "num_points": 501,
    }
    coarse = simulate_harmonic_oscillator(**common, rtol=1e-6, atol=1e-9)
    fine = simulate_harmonic_oscillator(**common, rtol=1e-10, atol=1e-12)

    assert coarse.max_abs_displacement_error < 1e-5
    assert fine.max_abs_displacement_error < 1e-8
    assert fine.max_abs_displacement_error < coarse.max_abs_displacement_error / 10.0
    assert fine.max_relative_energy_drift < coarse.max_relative_energy_drift


def test_oscillation_period_matches_two_pi_over_omega() -> None:
    mass = 1.0
    stiffness = 9.0
    omega = math.sqrt(stiffness / mass)
    period = 2.0 * math.pi / omega

    result = simulate_harmonic_oscillator(
        mass=mass,
        stiffness=stiffness,
        initial_displacement=1.0,
        initial_velocity=0.0,
        t_span=(0.0, period),
        num_points=2,
        rtol=1e-12,
        atol=1e-14,
    )

    assert result.displacement[0] == pytest.approx(1.0, abs=1e-14)
    assert result.displacement[-1] == pytest.approx(1.0, abs=1e-10)
    assert result.velocity[-1] == pytest.approx(0.0, abs=1e-10)


def test_independent_methods_agree_with_analytic_reference() -> None:
    common = {
        "mass": 2.0,
        "stiffness": 8.0,
        "initial_displacement": 0.3,
        "initial_velocity": -0.4,
        "t_span": (0.0, 5.0),
        "num_points": 501,
    }
    results = {
        method: simulate_harmonic_oscillator(**common, method=method)
        for method in ("RK45", "DOP853", "Radau")
    }

    for method, result in results.items():
        assert result.max_abs_displacement_error < 1e-8, method

    np.testing.assert_allclose(
        results["RK45"].displacement,
        results["DOP853"].displacement,
        rtol=0.0,
        atol=1e-8,
    )
    np.testing.assert_allclose(
        results["Radau"].displacement,
        results["DOP853"].displacement,
        rtol=0.0,
        atol=1e-8,
    )


def test_phase_space_orbit_keeps_energy_invariant() -> None:
    result = simulate_harmonic_oscillator(
        mass=1.0,
        stiffness=4.0,
        initial_displacement=0.5,
        initial_velocity=1.0,
        t_span=(0.0, 6.0),
        num_points=601,
    )

    phase_space_radius = result.displacement**2 + (result.velocity / result.angular_frequency) ** 2
    np.testing.assert_allclose(
        phase_space_radius,
        phase_space_radius[0],
        rtol=0.0,
        atol=1e-8,
    )
