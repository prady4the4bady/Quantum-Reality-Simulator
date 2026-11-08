"""Scientific validation of the PennyLane Bell-state implementation.

The reference observables in this module are built independently from
PennyLane using explicit Pauli matrices and Kronecker products. For a
big-endian two-qubit statevector the operator on wire 0 multiplies the left
factor: ``P_0 = kron(P, I)`` and ``P_1 = kron(I, P)``.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from qrs.quantum import simulate_bell_state

pytestmark = pytest.mark.scientific

_I = np.eye(2, dtype=np.complex128)
_X = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.complex128)
_Y = np.array([[0.0, -1.0j], [1.0j, 0.0]], dtype=np.complex128)
_Z = np.array([[1.0, 0.0], [0.0, -1.0]], dtype=np.complex128)


def _reference_state() -> np.ndarray:
    amplitude = 1.0 / math.sqrt(2.0)
    return np.array([amplitude, 0.0, 0.0, amplitude], dtype=np.complex128)


def _local_operator(wire: int, matrix: np.ndarray) -> np.ndarray:
    if wire == 0:
        return np.kron(matrix, _I)
    if wire == 1:
        return np.kron(_I, matrix)
    raise ValueError(f"unexpected wire {wire}")


def _expectation(state: np.ndarray, operator: np.ndarray) -> float:
    return float(np.real(np.vdot(state, operator @ state)))


def _reference_chsh_terms() -> tuple[float, float, float, float]:
    state = _reference_state()
    inverse_sqrt_two = 1.0 / math.sqrt(2.0)
    b0 = inverse_sqrt_two * (_local_operator(1, _Z) + _local_operator(1, _X))
    b1 = inverse_sqrt_two * (_local_operator(1, _Z) - _local_operator(1, _X))
    z0 = _local_operator(0, _Z)
    x0 = _local_operator(0, _X)
    return (
        _expectation(state, z0 @ b0),
        _expectation(state, z0 @ b1),
        _expectation(state, x0 @ b0),
        _expectation(state, x0 @ b1),
    )


def test_device_state_equals_the_phi_plus_reference() -> None:
    result = simulate_bell_state()

    np.testing.assert_allclose(result.statevector, _reference_state(), rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(result.probabilities, [0.5, 0.0, 0.0, 0.5], rtol=0.0, atol=1e-12)
    assert result.fidelity == pytest.approx(1.0, abs=1e-12)


def test_pauli_correlations_match_independent_matrix_reference() -> None:
    result = simulate_bell_state()
    state = _reference_state()

    zz = _expectation(state, _local_operator(0, _Z) @ _local_operator(1, _Z))
    xx = _expectation(state, _local_operator(0, _X) @ _local_operator(1, _X))
    yy = _expectation(
        state,
        _local_operator(0, _Y) @ _local_operator(1, _Y),
    )
    zx = _expectation(state, _local_operator(0, _Z) @ _local_operator(1, _X))
    xz = _expectation(state, _local_operator(0, _X) @ _local_operator(1, _Z))

    assert result.zz_correlation == pytest.approx(zz, abs=1e-12)
    assert result.xx_correlation == pytest.approx(xx, abs=1e-12)
    assert result.yy_correlation == pytest.approx(yy, abs=1e-12)
    assert result.zx_correlation == pytest.approx(zx, abs=1e-12)
    assert result.xz_correlation == pytest.approx(xz, abs=1e-12)

    assert result.zz_correlation == pytest.approx(1.0, abs=1e-12)
    assert result.xx_correlation == pytest.approx(1.0, abs=1e-12)
    assert result.yy_correlation == pytest.approx(-1.0, abs=1e-12)
    assert result.zx_correlation == pytest.approx(0.0, abs=1e-12)
    assert result.xz_correlation == pytest.approx(0.0, abs=1e-12)


def test_chsh_terms_match_independent_reference() -> None:
    result = simulate_bell_state()
    e_z_b0, e_z_b1, e_x_b0, e_x_b1 = _reference_chsh_terms()

    assert result.e_z_b0 == pytest.approx(e_z_b0, abs=1e-12)
    assert result.e_z_b1 == pytest.approx(e_z_b1, abs=1e-12)
    assert result.e_x_b0 == pytest.approx(e_x_b0, abs=1e-12)
    assert result.e_x_b1 == pytest.approx(e_x_b1, abs=1e-12)


def test_chsh_value_reaches_tsirelson_bound_and_violates_classical_limit() -> None:
    result = simulate_bell_state()

    assert result.chsh_value == pytest.approx(2.0 * math.sqrt(2.0), abs=1e-12)
    assert result.chsh_value > 2.0


def test_reduced_state_is_maximally_mixed_and_entangled() -> None:
    result = simulate_bell_state()
    expected_density_matrix = np.diag([0.5, 0.5]).astype(np.complex128)

    np.testing.assert_allclose(
        result.reduced_density_matrix,
        expected_density_matrix,
        rtol=0.0,
        atol=1e-12,
    )
    assert result.purity == pytest.approx(0.5, abs=1e-12)

    # For a pure two-qubit state the concurrence is
    # sqrt(2 * (1 - Tr(rho_A^2))); a value of 1 signals maximal entanglement.
    concurrence = math.sqrt(2.0 * (1.0 - result.purity))
    assert concurrence == pytest.approx(1.0, abs=1e-12)


def test_bell_simulation_is_deterministic() -> None:
    first = simulate_bell_state()
    second = simulate_bell_state()

    np.testing.assert_array_equal(first.statevector, second.statevector)
    np.testing.assert_array_equal(first.probabilities, second.probabilities)
    assert first.chsh_value == second.chsh_value
