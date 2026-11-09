"""Classical numerical simulation modules."""

from qrs.classical.harmonic_oscillator import (
    HarmonicOscillatorResult,
    simulate_harmonic_oscillator,
)
from qrs.classical.heat_diffusion import (
    HeatDiffusionResult,
    HeatDiffusionUncertainty,
    heat_diffusion_dense_solution,
    propagate_uncertainty,
    simulate_heat_diffusion,
)

__all__ = [
    "HarmonicOscillatorResult",
    "HeatDiffusionResult",
    "HeatDiffusionUncertainty",
    "heat_diffusion_dense_solution",
    "propagate_uncertainty",
    "simulate_harmonic_oscillator",
    "simulate_heat_diffusion",
]
