"""Run the phase-1 PennyLane Bell-state experiment and print its results.

Usage
-----
    .venv\\Scripts\\python.exe examples\\bell_state.py

The circuit prepares ``|Phi+> = (|00> + |11>) / sqrt(2)`` with a Hadamard on
wire 0 and a controlled-NOT from wire 0 to wire 1 on PennyLane's analytic
``default.qubit`` device.
"""

from __future__ import annotations

from qrs.quantum import simulate_bell_state


def main() -> None:
    result = simulate_bell_state()

    print("Bell state |Phi+> on PennyLane default.qubit")
    print(f"  wire order             : {result.wire_order}")
    print()
    print("  basis    probability      amplitude")
    for bitstring, probability, amplitude in zip(
        result.bitstrings,
        result.probabilities,
        result.statevector,
        strict=True,
    ):
        amplitude_text = f"{amplitude.real:+.6f}{amplitude.imag:+.6f}j"
        print(f"  |{bitstring}>    {probability:10.6f}      {amplitude_text}")

    print()
    print("  Pauli correlations")
    print(f"    <ZZ>                 : {result.zz_correlation:+.6f}")
    print(f"    <XX>                 : {result.xx_correlation:+.6f}")
    print(f"    <YY>                 : {result.yy_correlation:+.6f}")
    print(f"    <ZX>                 : {result.zx_correlation:+.6f}")
    print(f"    <XZ>                 : {result.xz_correlation:+.6f}")

    print()
    print("  CHSH terms")
    print(f"    E(Z, B0)             : {result.e_z_b0:+.6f}")
    print(f"    E(Z, B1)             : {result.e_z_b1:+.6f}")
    print(f"    E(X, B0)             : {result.e_x_b0:+.6f}")
    print(f"    E(X, B1)             : {result.e_x_b1:+.6f}")
    print(f"    S                    : {result.chsh_value:+.6f}")

    print()
    print("  Entanglement and reference checks")
    print(f"    reduced rho (wire 0) : {result.reduced_density_matrix.tolist()}")
    print(f"    purity Tr(rho^2)     : {result.purity:.6f}")
    print(f"    fidelity to |Phi+>   : {result.fidelity:.15f}")


if __name__ == "__main__":
    main()
