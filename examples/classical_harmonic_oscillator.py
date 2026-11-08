"""Run the phase-1 classical harmonic oscillator and print validation metrics.

Usage
-----
    .venv\\Scripts\\python.exe examples\\classical_harmonic_oscillator.py

The script integrates ``m*x'' + k*x = 0`` for a 1 kg mass on a 4 N/m spring,
starting from a 1 m displacement at rest, and compares the numerical
trajectory with the exact analytical solution.
"""

from __future__ import annotations

from qrs.classical import simulate_harmonic_oscillator


def main() -> None:
    result = simulate_harmonic_oscillator(
        mass=1.0,
        stiffness=4.0,
        initial_displacement=1.0,
        initial_velocity=0.0,
        t_span=(0.0, 10.0),
        num_points=1001,
    )

    print("Classical harmonic oscillator")
    print(f"  mass                   : {result.mass:.6g} kg")
    print(f"  stiffness              : {result.stiffness:.6g} N/m")
    print(f"  angular frequency      : {result.angular_frequency:.6f} rad/s")
    print(f"  integration method     : {result.method}")
    print(f"  samples                : {result.time.size}")
    print(f"  initial energy         : {result.initial_energy:.6f} J")
    print(f"  max |x_num - x_exact|  : {result.max_abs_displacement_error:.3e} m")
    print(f"  max relative x error   : {result.max_relative_displacement_error:.3e}")
    print(f"  max absolute E drift   : {result.max_abs_energy_drift:.3e} J")
    print(f"  max relative E drift   : {result.max_relative_energy_drift:.3e}")

    midpoint = result.time.size // 2
    print()
    print("  t (s)      x (m)        v (m/s)      E (J)")
    for index in (0, midpoint, result.time.size - 1):
        print(
            f"  {result.time[index]:8.4f}  "
            f"{result.displacement[index]:10.6f}  "
            f"{result.velocity[index]:10.6f}  "
            f"{result.energy[index]:9.6f}"
        )


if __name__ == "__main__":
    main()
