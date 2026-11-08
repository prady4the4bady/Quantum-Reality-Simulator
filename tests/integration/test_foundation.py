"""Integration test exercising the whole phase-1 scientific foundation."""

from __future__ import annotations

import numpy as np
import pytest

import qrs
from qrs.classical import simulate_harmonic_oscillator
from qrs.quantum import simulate_bell_state

pytestmark = pytest.mark.integration


def test_both_prototypes_run_deterministically_end_to_end() -> None:
    classical = simulate_harmonic_oscillator(
        mass=1.0,
        stiffness=4.0,
        initial_displacement=1.0,
        initial_velocity=0.0,
        t_span=(0.0, 10.0),
        num_points=1001,
    )
    bell = simulate_bell_state()
    repeated_bell = simulate_bell_state()

    assert qrs.__version__ == "0.1.0"

    assert classical.max_abs_displacement_error < 1e-8
    assert classical.max_relative_energy_drift < 1e-8
    assert classical.energy.shape == (1001,)

    assert bell.fidelity > 1.0 - 1e-12
    assert bell.chsh_value > 2.0
    assert abs(float(np.sum(bell.probabilities)) - 1.0) < 1e-12

    np.testing.assert_array_equal(bell.statevector, repeated_bell.statevector)
    assert bell.chsh_value == repeated_bell.chsh_value
