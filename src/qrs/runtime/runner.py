"""Manifest execution and reproducibility checks for the QRS runtime.

The runner is intentionally thin: it validates manifest identity, maps the
manifest's flat scalar parameters onto the existing Phase 1 physics functions,
and records the returned metrics in a result envelope. It does not modify or
reimplement any physics.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Final

import numpy as np

from qrs.classical import (
    heat_diffusion_dense_solution,
    simulate_harmonic_oscillator,
    simulate_heat_diffusion,
)
from qrs.core.validation import require_positive_finite
from qrs.quantum import simulate_bell_state
from qrs.runtime.envelope import SCHEMA_VERSION as ENVELOPE_SCHEMA_VERSION
from qrs.runtime.envelope import ResultEnvelope
from qrs.runtime.manifest import (
    BELL_STATE,
    ENVIRONMENT_KEYS,
    HARMONIC_OSCILLATOR,
    HEAT_DIFFUSION,
    ExperimentManifest,
    capture_environment,
)
from qrs.runtime.serialization import Scalar

OSCILLATOR_ERROR_TOLERANCE: Final[float] = 1e-8
"""Maximum accepted oscillator error metrics, matching Phase 1 validation."""

QUANTUM_REFERENCE_TOLERANCE: Final[float] = 1e-12
"""Absolute tolerance for the independent Bell-state reference, from Phase 1."""

_CHSH_REFERENCE: Final[float] = 2.0 * math.sqrt(2.0)

# Heat diffusion validation thresholds scale with dx^2 (safety factor 3) using
# the error bound from docs/domains/HEAT_DIFFUSION_SPEC.md Section 4. The
# constants are the measured error at N=401 (dx=2.5e-4) divided by dx^2, so
# the threshold at N=401 equals 3 * measured_error and relaxes quadratically
# for coarser grids.
HEAT_ERROR_SAFETY_FACTOR: Final[float] = 3.0
_HEAT_DX_401: Final[float] = 0.1 / 400.0
_HEAT_C_BOUND: Final[float] = (
    8.768433026773437e-06 / _HEAT_DX_401**2
)  # max_abs_error / dx^2 at N=401
_HEAT_C_BOUND_T_END: Final[float] = (
    1.613655514765e-06 / _HEAT_DX_401**2
)  # max_abs_error_t_end / dx^2 at N=401

# Fixed Monte Carlo sample count for heat-diffusion uncertainty propagation.
HEAT_NUM_SAMPLES: Final[int] = 10000
HEAT_RELATIVE_STD: Final[float] = 0.05


def _oscillator_summary(result: object, manifest: ExperimentManifest) -> dict[str, Scalar]:
    parameters = manifest.parameters
    solver = manifest.solver_config
    return {
        "mass": result.mass,  # type: ignore[attr-defined]
        "stiffness": result.stiffness,  # type: ignore[attr-defined]
        "angular_frequency": result.angular_frequency,  # type: ignore[attr-defined]
        "initial_displacement": result.initial_displacement,  # type: ignore[attr-defined]
        "initial_velocity": result.initial_velocity,  # type: ignore[attr-defined]
        "initial_energy": result.initial_energy,  # type: ignore[attr-defined]
        "t_start": float(parameters["t_start"]),
        "t_end": float(parameters["t_end"]),
        "num_points": int(solver["num_points"]),
        "max_abs_displacement_error": result.max_abs_displacement_error,  # type: ignore[attr-defined]
        "max_relative_displacement_error": result.max_relative_displacement_error,  # type: ignore[attr-defined]
        "max_abs_energy_drift": result.max_abs_energy_drift,  # type: ignore[attr-defined]
        "max_relative_energy_drift": result.max_relative_energy_drift,  # type: ignore[attr-defined]
        "method": result.method,  # type: ignore[attr-defined]
    }


def _oscillator_checks(result: object) -> dict[str, bool]:
    return {
        "displacement_error": (
            result.max_abs_displacement_error  # type: ignore[attr-defined]
            < OSCILLATOR_ERROR_TOLERANCE
        ),
        "relative_energy_drift": (
            result.max_relative_energy_drift  # type: ignore[attr-defined]
            < OSCILLATOR_ERROR_TOLERANCE
        ),
    }


def _bell_summary(result: object) -> dict[str, Scalar]:
    return {
        "fidelity": result.fidelity,  # type: ignore[attr-defined]
        "purity": result.purity,  # type: ignore[attr-defined]
        "chsh_value": result.chsh_value,  # type: ignore[attr-defined]
        "zz_correlation": result.zz_correlation,  # type: ignore[attr-defined]
        "xx_correlation": result.xx_correlation,  # type: ignore[attr-defined]
        "yy_correlation": result.yy_correlation,  # type: ignore[attr-defined]
        "zx_correlation": result.zx_correlation,  # type: ignore[attr-defined]
        "xz_correlation": result.xz_correlation,  # type: ignore[attr-defined]
        "e_z_b0": result.e_z_b0,  # type: ignore[attr-defined]
        "e_z_b1": result.e_z_b1,  # type: ignore[attr-defined]
        "e_x_b0": result.e_x_b0,  # type: ignore[attr-defined]
        "e_x_b1": result.e_x_b1,  # type: ignore[attr-defined]
        "probability_sum": float(result.probabilities.sum()),  # type: ignore[attr-defined]
    }


def _bell_checks(result: object) -> dict[str, bool]:
    tolerance = QUANTUM_REFERENCE_TOLERANCE
    return {
        "fidelity": abs(result.fidelity - 1.0) <= tolerance,  # type: ignore[attr-defined]
        "purity": abs(result.purity - 0.5) <= tolerance,  # type: ignore[attr-defined]
        "normalization": (
            abs(float(result.probabilities.sum()) - 1.0) <= tolerance  # type: ignore[attr-defined]
        ),
        "chsh_value": abs(result.chsh_value - _CHSH_REFERENCE) <= tolerance,  # type: ignore[attr-defined]
        "zz_correlation": abs(result.zz_correlation - 1.0) <= tolerance,  # type: ignore[attr-defined]
        "xx_correlation": abs(result.xx_correlation - 1.0) <= tolerance,  # type: ignore[attr-defined]
        "yy_correlation": abs(result.yy_correlation + 1.0) <= tolerance,  # type: ignore[attr-defined]
        "zx_correlation": abs(result.zx_correlation) <= tolerance,  # type: ignore[attr-defined]
        "xz_correlation": abs(result.xz_correlation) <= tolerance,  # type: ignore[attr-defined]
    }


def _heat_summary(result: object, manifest: ExperimentManifest) -> dict[str, Scalar]:
    parameters = manifest.parameters
    uq = _heat_uncertainty(manifest, result)
    return {
        "alpha": float(parameters["alpha"]),  # type: ignore[index]
        "length": float(parameters["length"]),  # type: ignore[index]
        "t_end": float(parameters["t_end"]),  # type: ignore[index]
        "num_points": int(parameters["num_points"]),  # type: ignore[index]
        "num_output_points": int(parameters["num_output_points"]),  # type: ignore[index]
        "first_mode_decay_rate": result.first_mode_decay_rate,  # type: ignore[attr-defined]
        "max_abs_error": result.max_abs_error,  # type: ignore[attr-defined]
        "max_abs_error_t_end": result.max_abs_error_t_end,  # type: ignore[attr-defined]
        "u_mid_t_end": result.u_mid_t_end,  # type: ignore[attr-defined]
        "analytic_u_mid_t_end": result.analytic_u_mid_t_end,  # type: ignore[attr-defined]
        "boundary_max": result.boundary_max,  # type: ignore[attr-defined]
        "initial_profile_error": result.initial_profile_error,  # type: ignore[attr-defined]
        "min_u": result.min_u,  # type: ignore[attr-defined]
        "max_u": result.max_u,  # type: ignore[attr-defined]
        "method": result.method,  # type: ignore[attr-defined]
        "uq_mean": uq["mean"],
        "uq_std": uq["std"],
        "uq_stderr": uq["stderr"],
        "uq_interval_low": uq["interval_low"],
        "uq_interval_high": uq["interval_high"],
        "num_samples": uq["num_samples"],
        "seed": int(manifest.seed),
    }


def _heat_uncertainty(manifest: ExperimentManifest, result: object) -> dict[str, Scalar]:
    """Propagate diffusivity uncertainty through the numerical solver.

    Runs a single dense-output integration at ``alpha0`` over
    ``[0, t_end * 1.25]`` and interpolates at ``t_j = alpha_j * t_end / alpha0``
    for each sampled ``alpha_j``, exploiting that the PDE depends only on the
    product ``alpha * t``. Sampled ``alpha <= 0`` is rejected.
    """

    alpha0 = float(manifest.parameters["alpha"])  # type: ignore[index]
    length = float(manifest.parameters["length"])  # type: ignore[index]
    t_end = float(manifest.parameters["t_end"])  # type: ignore[index]
    num_points = int(manifest.parameters["num_points"])  # type: ignore[index]
    seed = int(manifest.seed)

    sigma = alpha0 * HEAT_RELATIVE_STD
    rng = np.random.default_rng(seed)
    alpha_samples = alpha0 + sigma * rng.standard_normal(HEAT_NUM_SAMPLES)
    alpha_samples = alpha_samples[alpha_samples > 0.0]
    if alpha_samples.size == 0:
        raise ValueError("all sampled diffusivities were non-positive")

    x_q = length / 2.0
    t_q = t_end
    t_max = t_end * 1.25

    dx = length / (num_points - 1)
    mid_index = round(x_q / dx)
    interior_index = mid_index - 1  # dense output excludes boundary columns

    sol = heat_diffusion_dense_solution(
        alpha=alpha0,
        length=length,
        t_max=t_max,
        num_points=num_points,
    )

    t_j = alpha_samples * t_q / alpha0
    interior_all = sol.sol(t_j)  # shape (num_interior, num_samples)
    interp_vals = interior_all[interior_index, :]

    mean = float(np.mean(interp_vals))
    std = float(np.std(interp_vals, ddof=1))
    stderr = std / math.sqrt(interp_vals.size)
    low, high = np.percentile(interp_vals, [2.5, 97.5])
    return {
        "mean": mean,
        "std": std,
        "stderr": stderr,
        "interval_low": float(low),
        "interval_high": float(high),
        "num_samples": int(interp_vals.size),
    }


def _heat_checks(result: object, manifest: ExperimentManifest) -> dict[str, bool]:
    parameters = manifest.parameters
    num_points = int(parameters["num_points"])  # type: ignore[index]
    length = float(parameters["length"])  # type: ignore[index]
    dx = length / (num_points - 1)
    scale = dx * dx

    max_abs_error_tolerance = HEAT_ERROR_SAFETY_FACTOR * scale * _HEAT_C_BOUND
    max_abs_error_t_end_tolerance = HEAT_ERROR_SAFETY_FACTOR * scale * _HEAT_C_BOUND_T_END

    return {
        "max_abs_error": (
            result.max_abs_error  # type: ignore[attr-defined]
            < max_abs_error_tolerance
        ),
        "max_abs_error_t_end": (
            result.max_abs_error_t_end  # type: ignore[attr-defined]
            < max_abs_error_t_end_tolerance
        ),
        "boundary_max": (
            result.boundary_max  # type: ignore[attr-defined]
            == 0.0
        ),
    }


def _envelope(
    manifest: ExperimentManifest,
    summary: Mapping[str, Scalar],
    checks: Mapping[str, bool],
    tolerance: float,
) -> ResultEnvelope:
    passed = tuple(name for name, ok in checks.items() if ok)
    failed = tuple(name for name, ok in checks.items() if not ok)
    details: dict[str, Scalar] = {
        "model_name": manifest.model_name,
        "tolerance": tolerance,
        "checks": ",".join(checks),
        "checks_passed": len(passed),
        "checks_failed": len(failed),
        "failed_checks": ",".join(failed),
    }
    return ResultEnvelope(
        schema_version=ENVELOPE_SCHEMA_VERSION,
        manifest=manifest,
        result_summary=summary,
        validation_status="passed" if not failed else "failed",
        validation_details=details,
        artefacts=(),
    )


def run_manifest(manifest: ExperimentManifest) -> ResultEnvelope:
    """Execute one manifest and return its result envelope.

    Parameters
    ----------
    manifest:
        Manifest to execute. Its ``experiment_id`` is verified before any
        physics runs.

    Returns
    -------
    ResultEnvelope
        Scalar summary, validation status, and check details. Artefacts are
        empty because Phase 2 writes no files.

    Raises
    ------
    TypeError
        If ``manifest`` is not an ``ExperimentManifest``.
    ValueError
        If the manifest identifier does not match its content.

    Notes
    -----
    Exceptions raised by the underlying physics functions propagate unchanged;
    the runtime does not wrap, retry, or suppress them.
    """

    if not isinstance(manifest, ExperimentManifest):
        raise TypeError(f"manifest must be an ExperimentManifest, got {type(manifest).__name__}")
    manifest.verify_experiment_id()

    parameters = manifest.parameters
    solver = manifest.solver_config

    if manifest.model_name == HARMONIC_OSCILLATOR:
        result = simulate_harmonic_oscillator(
            mass=float(parameters["mass"]),
            stiffness=float(parameters["stiffness"]),
            initial_displacement=float(parameters["initial_displacement"]),
            initial_velocity=float(parameters["initial_velocity"]),
            t_span=(float(parameters["t_start"]), float(parameters["t_end"])),
            num_points=int(solver["num_points"]),
            method=str(solver["method"]),
            rtol=float(solver["rtol"]),
            atol=float(solver["atol"]),
        )
        summary = _oscillator_summary(result, manifest)
        checks = _oscillator_checks(result)
        tolerance = OSCILLATOR_ERROR_TOLERANCE
    elif manifest.model_name == BELL_STATE:
        result = simulate_bell_state()
        summary = _bell_summary(result)
        checks = _bell_checks(result)
        tolerance = QUANTUM_REFERENCE_TOLERANCE
    elif manifest.model_name == HEAT_DIFFUSION:
        parameters = manifest.parameters
        solver = manifest.solver_config
        result = simulate_heat_diffusion(
            alpha=float(parameters["alpha"]),  # type: ignore[index]
            length=float(parameters["length"]),  # type: ignore[index]
            t_end=float(parameters["t_end"]),  # type: ignore[index]
            num_points=int(parameters["num_points"]),  # type: ignore[index]
            num_output_points=int(parameters["num_output_points"]),  # type: ignore[index]
            rtol=float(solver["rtol"]),  # type: ignore[index]
            atol=float(solver["atol"]),  # type: ignore[index]
        )
        summary = _heat_summary(result, manifest)
        checks = _heat_checks(result, manifest)
        tolerance = None  # heat diffusion uses dx-scaled per-check thresholds
    else:  # pragma: no cover - manifest validation rejects unknown model names
        raise ValueError(f"unsupported model_name {manifest.model_name!r}")

    return _envelope(manifest, summary, checks, tolerance)


def _compare_summaries(
    first: Mapping[str, Scalar],
    second: Mapping[str, Scalar],
    tolerance: float,
) -> None:
    if set(first) != set(second):
        missing = sorted(set(first) - set(second))
        extra = sorted(set(second) - set(first))
        raise RuntimeError(
            "reproducibility comparison failed: result summary keys differ "
            f"(missing: {missing}, extra: {extra})"
        )

    for key in sorted(first):
        left = first[key]
        right = second[key]
        if isinstance(left, bool) or isinstance(right, bool):
            if left != right:
                raise RuntimeError(
                    f"reproducibility comparison failed for {key!r}: {left!r} != {right!r}"
                )
            continue
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            left_number = float(left)
            right_number = float(right)
            if not (math.isfinite(left_number) and math.isfinite(right_number)):
                raise RuntimeError(
                    f"reproducibility comparison failed for {key!r}: "
                    f"non-finite value ({left!r}, {right!r})"
                )
            difference = abs(left_number - right_number)
            if difference > tolerance:
                raise RuntimeError(
                    f"reproducibility comparison failed for {key!r}: "
                    f"absolute difference {difference!r} exceeds tolerance {tolerance!r}"
                )
            continue
        if left != right:
            raise RuntimeError(
                f"reproducibility comparison failed for {key!r}: {left!r} != {right!r}"
            )


def check_reproducibility(
    manifest: ExperimentManifest,
    tolerance: float = QUANTUM_REFERENCE_TOLERANCE,
    *,
    allow_environment_drift: bool = False,
) -> tuple[ResultEnvelope, ResultEnvelope]:
    """Re-run a manifest twice and verify deterministic reproduction.

    The manifest identifier is verified first, which detects seed or content
    tampering. Unless ``allow_environment_drift`` is true, the manifest's
    recorded environment must match the current environment exactly. Result
    summaries are then compared key by key: numeric values must agree within
    an absolute ``tolerance`` and non-numeric values must match exactly.

    Parameters
    ----------
    manifest:
        Manifest to execute twice.
    tolerance:
        Positive absolute tolerance for numeric summary comparison.
    allow_environment_drift:
        Skip the recorded-versus-current environment comparison. Identifier
        integrity and summary comparison still apply.

    Returns
    -------
    tuple[ResultEnvelope, ResultEnvelope]
        The two envelopes produced from the same manifest.

    Raises
    ------
    TypeError
        If an argument has the wrong type.
    ValueError
        If ``tolerance`` is not positive and finite, or the manifest
        identifier does not match its content.
    RuntimeError
        If the environment differs and drift is not allowed, either run fails
        validation, or the summaries differ beyond tolerance.
    """

    if not isinstance(manifest, ExperimentManifest):
        raise TypeError(f"manifest must be an ExperimentManifest, got {type(manifest).__name__}")
    validated_tolerance = require_positive_finite(tolerance, "tolerance")
    if not isinstance(allow_environment_drift, bool):
        raise TypeError(
            "allow_environment_drift must be a boolean, "
            f"got {type(allow_environment_drift).__name__}"
        )

    manifest.verify_experiment_id()

    if not allow_environment_drift:
        current = capture_environment()
        differences = [key for key in ENVIRONMENT_KEYS if manifest.environment[key] != current[key]]
        if differences:
            details = "; ".join(
                f"{key}: manifest={manifest.environment[key]!r} current={current[key]!r}"
                for key in differences
            )
            raise RuntimeError(
                f"environment drift detected for {manifest.experiment_id}: {details}"
            )

    first = run_manifest(manifest)
    second = run_manifest(manifest)

    if first.manifest.seed != manifest.seed or second.manifest.seed != manifest.seed:
        raise RuntimeError("reproducibility check failed: seed changed between runs")
    if first.manifest.environment != manifest.environment:
        raise RuntimeError("reproducibility check failed: environment changed between runs")
    if first.manifest.environment != second.manifest.environment:
        raise RuntimeError("reproducibility check failed: environment changed between runs")

    if first.validation_status != "passed" or second.validation_status != "passed":
        failed = sorted(
            {
                str(first.validation_details.get("failed_checks", "")),
                str(second.validation_details.get("failed_checks", "")),
            }
        )
        raise RuntimeError(
            f"reproducibility check failed: validation did not pass ({'; '.join(failed)})"
        )

    _compare_summaries(first.result_summary, second.result_summary, validated_tolerance)
    return first, second
