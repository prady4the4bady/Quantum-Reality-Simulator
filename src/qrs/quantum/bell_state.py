"""Bell-state preparation and verification on PennyLane's ``default.qubit``.

Conventions
-----------
* Logical wires are ``(0, 1)``.
* ``default.qubit`` uses big-endian computational-basis ordering: for wires
  ``(0, 1)`` the statevector is ordered ``|00>, |01>, |10>, |11>``. The
  bitstring for basis index ``i`` is ``format(i, "02b")``, where the first
  character corresponds to wire 0.
* The prepared state is the Bell state
  ``|Phi+> = (|00> + |11>) / sqrt(2)``, produced by a Hadamard on wire 0
  followed by a controlled-NOT with control 0 and target 1.
* Execution is analytic (statevector, no shots) and CPU-only. Results are
  produced by PennyLane device execution; probabilities are never hardcoded.

The CHSH value uses the convention

.. math::

    S = E(Z, B_0) + E(Z, B_1) + E(X, B_0) - E(X, B_1),

with :math:`B_0 = (Z + X)/\\sqrt{2}` and :math:`B_1 = (Z - X)/\\sqrt{2}` on
wire 1. For ``|Phi+>`` this equals :math:`2\\sqrt{2}`, violating the
classical bound of 2.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pennylane as qml
from numpy.typing import NDArray

_WIRES: tuple[int, int] = (0, 1)
_STATE_DIMENSION = 4
_NORMALIZATION_TOLERANCE = 1e-12


@dataclass(frozen=True, slots=True)
class BellStateResult:
    """Executed Bell-state results and independent verification metrics.

    Attributes
    ----------
    statevector:
        Complex statevector returned by the PennyLane device, ordered as
        ``|00>, |01>, |10>, |11>`` for wires ``(0, 1)``.
    probabilities:
        Computational-basis probabilities ``|amplitude|**2`` derived from
        ``statevector``. Index-aligned with ``bitstrings``.
    bitstrings:
        Basis labels in device order, where character ``k`` is wire ``k``.
    zz_correlation, xx_correlation, yy_correlation, zx_correlation,
    xz_correlation:
        Pauli correlation functions measured on the device.
    e_z_b0, e_z_b1, e_x_b0, e_x_b1:
        CHSH expectation values using the settings documented in the module
        docstring.
    chsh_value:
        :math:`S = E(Z, B_0) + E(Z, B_1) + E(X, B_0) - E(X, B_1)`.
    reduced_density_matrix:
        Single-qubit reduced density matrix of wire 0 returned by the device.
    purity:
        :math:`\\mathrm{Tr}(\\rho_0^2)`, equal to 0.5 for a maximally mixed
        one-qubit reduced state.
    reference_statevector:
        Independently constructed ``(1, 0, 0, 1)/sqrt(2)`` reference.
    fidelity:
        Pure-state fidelity :math:`|\\langle\\psi_{\\text{ref}}|\\psi\\rangle|^2`
        between the reference and the device state.
    wire_order:
        Logical wire order used for the statevector and bitstrings.
    """

    statevector: NDArray[np.complex128]
    probabilities: NDArray[np.float64]
    bitstrings: tuple[str, ...]
    zz_correlation: float
    xx_correlation: float
    yy_correlation: float
    zx_correlation: float
    xz_correlation: float
    e_z_b0: float
    e_z_b1: float
    e_x_b0: float
    e_x_b1: float
    chsh_value: float
    reduced_density_matrix: NDArray[np.complex128]
    purity: float
    reference_statevector: NDArray[np.complex128]
    fidelity: float
    wire_order: tuple[int, ...]


def _prepare_bell_state() -> None:
    """Apply the minimal circuit that prepares ``|Phi+>``."""

    qml.Hadamard(wires=0)
    qml.CNOT(wires=[0, 1])


def _validate_statevector(statevector: NDArray[np.complex128]) -> None:
    if statevector.shape != (_STATE_DIMENSION,):
        raise RuntimeError(
            f"Bell-state device returned shape {statevector.shape}; expected ({_STATE_DIMENSION},)"
        )
    if not np.all(np.isfinite(statevector)):
        raise RuntimeError("Bell-state device returned non-finite amplitudes")

    norm_squared = float(np.sum(np.abs(statevector) ** 2))
    if abs(norm_squared - 1.0) > _NORMALIZATION_TOLERANCE:
        raise RuntimeError(
            f"Bell-state device returned a non-normalized statevector "
            f"(norm squared {norm_squared!r})"
        )


def _reference_bell_state() -> NDArray[np.complex128]:
    """Construct ``(|00> + |11>) / sqrt(2)`` without using PennyLane."""

    amplitude = 1.0 / math.sqrt(2.0)
    reference = np.zeros(_STATE_DIMENSION, dtype=np.complex128)
    reference[0] = amplitude
    reference[3] = amplitude
    return reference


def simulate_bell_state() -> BellStateResult:
    """Prepare ``|Phi+>`` on ``default.qubit`` and measure its properties.

    The circuit is executed analytically on PennyLane's CPU statevector
    device. All reported quantities are derived from actual device results:
    the statevector, five Pauli correlation functions, the four CHSH terms,
    and the single-qubit reduced density matrix.

    Returns
    -------
    BellStateResult
        Device statevector, basis probabilities, correlation functions,
        CHSH value, reduced density matrix, purity, and fidelity against an
        independently constructed reference state.

    Raises
    ------
    RuntimeError
        If the device returns a malformed, non-finite, or non-normalized
        state, or a malformed reduced density matrix.
    """

    device = qml.device("default.qubit", wires=_WIRES)

    @qml.qnode(device, interface=None)
    def state_circuit() -> NDArray[np.complex128]:
        _prepare_bell_state()
        return qml.state()

    @qml.qnode(device, interface=None)
    def expectation_circuit(observable: qml.operation.Operator) -> float:
        _prepare_bell_state()
        return qml.expval(observable)

    @qml.qnode(device, interface=None)
    def reduced_state_circuit() -> NDArray[np.complex128]:
        _prepare_bell_state()
        return qml.density_matrix(wires=[0])

    statevector = np.asarray(state_circuit(), dtype=np.complex128)
    _validate_statevector(statevector)

    probabilities = np.abs(statevector) ** 2
    bitstrings = tuple(format(index, f"0{len(_WIRES)}b") for index in range(_STATE_DIMENSION))

    zz_correlation = float(expectation_circuit(qml.PauliZ(0) @ qml.PauliZ(1)))
    xx_correlation = float(expectation_circuit(qml.PauliX(0) @ qml.PauliX(1)))
    yy_correlation = float(expectation_circuit(qml.PauliY(0) @ qml.PauliY(1)))
    zx_correlation = float(expectation_circuit(qml.PauliZ(0) @ qml.PauliX(1)))
    xz_correlation = float(expectation_circuit(qml.PauliX(0) @ qml.PauliZ(1)))

    inverse_sqrt_two = 1.0 / math.sqrt(2.0)
    b0 = qml.Hamiltonian(
        [inverse_sqrt_two, inverse_sqrt_two],
        [qml.PauliZ(1), qml.PauliX(1)],
    )
    b1 = qml.Hamiltonian(
        [inverse_sqrt_two, -inverse_sqrt_two],
        [qml.PauliZ(1), qml.PauliX(1)],
    )

    e_z_b0 = float(expectation_circuit(qml.PauliZ(0) @ b0))
    e_z_b1 = float(expectation_circuit(qml.PauliZ(0) @ b1))
    e_x_b0 = float(expectation_circuit(qml.PauliX(0) @ b0))
    e_x_b1 = float(expectation_circuit(qml.PauliX(0) @ b1))
    chsh_value = e_z_b0 + e_z_b1 + e_x_b0 - e_x_b1

    reduced_density_matrix = np.asarray(reduced_state_circuit(), dtype=np.complex128)
    if reduced_density_matrix.shape != (2, 2):
        raise RuntimeError(
            f"reduced density matrix has shape {reduced_density_matrix.shape}; expected (2, 2)"
        )
    if not np.all(np.isfinite(reduced_density_matrix)):
        raise RuntimeError("reduced density matrix contains non-finite values")
    purity = float(np.real(np.trace(reduced_density_matrix @ reduced_density_matrix)))

    reference_statevector = _reference_bell_state()
    overlap = np.vdot(reference_statevector, statevector)
    fidelity = float(np.clip(abs(overlap) ** 2, 0.0, 1.0))

    return BellStateResult(
        statevector=statevector,
        probabilities=probabilities,
        bitstrings=bitstrings,
        zz_correlation=zz_correlation,
        xx_correlation=xx_correlation,
        yy_correlation=yy_correlation,
        zx_correlation=zx_correlation,
        xz_correlation=xz_correlation,
        e_z_b0=e_z_b0,
        e_z_b1=e_z_b1,
        e_x_b0=e_x_b0,
        e_x_b1=e_x_b1,
        chsh_value=chsh_value,
        reduced_density_matrix=reduced_density_matrix,
        purity=purity,
        reference_statevector=reference_statevector,
        fidelity=fidelity,
        wire_order=_WIRES,
    )
