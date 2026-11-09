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

from qrs.classical import simulate_harmonic_oscillator
from qrs.core.validation import require_positive_finite
from qrs.quantum import simulate_bell_state
from qrs.runtime.envelope import SCHEMA_VERSION as ENVELOPE_SCHEMA_VERSION
from qrs.runtime.envelope import ResultEnvelope
from qrs.runtime.manifest import (
    BELL_STATE,
    ENVIRONMENT_KEYS,
    HARMONIC_OSCILLATOR,
    ExperimentManifest,
    capture_environment,
)
from qrs.runtime.serialization import Scalar

OSCILLATOR_ERROR_TOLERANCE: Final[float] = 1e-8
"""Maximum accepted oscillator error metrics, matching Phase 1 validation."""

QUANTUM_REFERENCE_TOLERANCE: Final[float] = 1e-12
"""Absolute tolerance for the independent Bell-state reference, from Phase 1."""

_CHSH_REFERENCE: Final[float] = 2.0 * math.sqrt(2.0)


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
