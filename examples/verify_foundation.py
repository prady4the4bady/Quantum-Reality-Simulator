"""End-to-end smoke check of both phase-1 scientific prototypes.

Usage
-----
    .venv\\Scripts\\python.exe examples\\verify_foundation.py

This script complements the pytest suite. It runs both simulations with
public defaults, checks the headline scientific claims, and exits non-zero on
failure. It is intended as a quick manual verification, not as a substitute
for the tests.
"""

from __future__ import annotations

import math
import sys

from qrs.classical import simulate_harmonic_oscillator
from qrs.quantum import simulate_bell_state


def main() -> int:
    failures: list[str] = []

    classical = simulate_harmonic_oscillator(
        mass=1.0,
        stiffness=4.0,
        initial_displacement=1.0,
        initial_velocity=0.0,
        t_span=(0.0, 10.0),
    )
    if classical.max_abs_displacement_error > 1e-8:
        failures.append(
            "classical displacement error "
            f"{classical.max_abs_displacement_error:.3e} exceeds 1e-8 m"
        )
    if classical.max_relative_energy_drift > 1e-8:
        failures.append(
            f"classical energy drift {classical.max_relative_energy_drift:.3e} exceeds 1e-8"
        )

    bell = simulate_bell_state()
    if abs(float(bell.probabilities.sum()) - 1.0) > 1e-12:
        failures.append("Bell-state probabilities do not sum to 1")
    if abs(bell.fidelity - 1.0) > 1e-12:
        failures.append(f"Bell-state fidelity {bell.fidelity!r} is not 1")
    if abs(bell.chsh_value - 2.0 * math.sqrt(2.0)) > 1e-12:
        failures.append(f"CHSH value {bell.chsh_value!r} is not 2*sqrt(2)")
    if bell.chsh_value <= 2.0:
        failures.append("CHSH value does not violate the classical bound")

    print(f"classical max |x error| : {classical.max_abs_displacement_error:.3e} m")
    print(f"classical relative E    : {classical.max_relative_energy_drift:.3e}")
    print(f"Bell probabilities      : {bell.probabilities.tolist()}")
    print(f"Bell fidelity           : {bell.fidelity:.15f}")
    print(f"CHSH S                  : {bell.chsh_value:.15f}")

    if failures:
        print("\nFAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("\nAll phase-1 foundation checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
