"""Unit tests for the PennyLane Bell-state implementation."""

from __future__ import annotations

import dataclasses

import numpy as np
import pennylane as qml
import pytest

from qrs.quantum.bell_state import (
    BellStateResult,
    _prepare_bell_state,
    simulate_bell_state,
)


@pytest.fixture(scope="module")
def result() -> BellStateResult:
    return simulate_bell_state()


def test_result_metadata_shapes_and_dtypes(result: BellStateResult) -> None:
    assert isinstance(result, BellStateResult)
    assert result.wire_order == (0, 1)
    assert result.bitstrings == ("00", "01", "10", "11")
    assert result.statevector.shape == (4,)
    assert result.statevector.dtype == np.complex128
    assert result.probabilities.shape == (4,)
    assert result.probabilities.dtype == np.float64
    assert result.reference_statevector.shape == (4,)
    assert result.reduced_density_matrix.shape == (2, 2)


def test_statevector_is_normalized(result: BellStateResult) -> None:
    np.testing.assert_allclose(
        np.sum(np.abs(result.statevector) ** 2),
        1.0,
        rtol=0.0,
        atol=1e-12,
    )


def test_probabilities_are_derived_from_the_device_state(result: BellStateResult) -> None:
    np.testing.assert_array_equal(result.probabilities, np.abs(result.statevector) ** 2)
    np.testing.assert_allclose(np.sum(result.probabilities), 1.0, rtol=0.0, atol=1e-12)


def test_reduced_density_matrix_is_physical(result: BellStateResult) -> None:
    density_matrix = result.reduced_density_matrix

    np.testing.assert_allclose(density_matrix, density_matrix.conj().T, rtol=0.0, atol=1e-12)
    assert np.trace(density_matrix).real == pytest.approx(1.0, abs=1e-12)
    eigenvalues = np.linalg.eigvalsh(density_matrix)
    assert np.all(eigenvalues >= -1e-12)


def test_fidelity_matches_the_reported_reference_state(result: BellStateResult) -> None:
    overlap = np.vdot(result.reference_statevector, result.statevector)
    np.testing.assert_allclose(result.fidelity, abs(overlap) ** 2, rtol=0.0, atol=1e-12)


def test_chsh_value_is_the_configured_linear_combination(result: BellStateResult) -> None:
    expected = result.e_z_b0 + result.e_z_b1 + result.e_x_b0 - result.e_x_b1
    assert result.chsh_value == pytest.approx(expected, abs=0.0)


def test_result_is_immutable(result: BellStateResult) -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.chsh_value = 0.0  # type: ignore[misc]


def test_prepare_bell_state_uses_big_endian_basis_order() -> None:
    """Wire 0 must be the most significant bit of the statevector index.

    Applying ``X`` to wire 0 followed by ``Z`` to wire 1 maps ``|Phi+>`` to
    ``(|10> - |01>) / sqrt(2)``. If the device were little-endian, the
    amplitudes would appear at swapped indices with opposite signs.
    """

    device = qml.device("default.qubit", wires=(0, 1))

    @qml.qnode(device, interface=None)
    def wire_zero_operation() -> np.ndarray:
        _prepare_bell_state()
        qml.PauliX(wires=0)
        qml.PauliZ(wires=1)
        return qml.state()

    @qml.qnode(device, interface=None)
    def wire_one_operation() -> np.ndarray:
        _prepare_bell_state()
        qml.PauliX(wires=1)
        qml.PauliZ(wires=0)
        return qml.state()

    inverse_sqrt_two = 1.0 / np.sqrt(2.0)
    expected = np.array([0.0, -inverse_sqrt_two, inverse_sqrt_two, 0.0], dtype=np.complex128)

    np.testing.assert_allclose(wire_zero_operation(), expected, rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(wire_one_operation(), -expected, rtol=0.0, atol=1e-12)


def test_default_qubit_places_local_operation_on_the_requested_wire() -> None:
    device = qml.device("default.qubit", wires=2)

    @qml.qnode(device, interface=None)
    def flip_wire_zero() -> np.ndarray:
        qml.PauliX(wires=0)
        return qml.state()

    @qml.qnode(device, interface=None)
    def flip_wire_one() -> np.ndarray:
        qml.PauliX(wires=1)
        return qml.state()

    state_zero = np.asarray(flip_wire_zero())
    state_one = np.asarray(flip_wire_one())

    assert state_zero[2] == pytest.approx(1.0, abs=1e-12)
    assert state_one[1] == pytest.approx(1.0, abs=1e-12)
