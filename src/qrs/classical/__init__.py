"""Classical numerical simulation modules."""

from qrs.classical.harmonic_oscillator import (
    HarmonicOscillatorResult,
    simulate_harmonic_oscillator,
)
from qrs.classical.heat_diffusion import (
    HeatDiffusionResult,
    heat_diffusion_dense_solution,
    simulate_heat_diffusion,
)

__all__ = [
    "HarmonicOscillatorResult",
    "HeatDiffusionResult",
    "heat_diffusion_dense_solution",
    "simulate_harmonic_oscillator",
    "simulate_heat_diffusion",
]
