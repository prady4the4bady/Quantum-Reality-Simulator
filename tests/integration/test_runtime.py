"""Integration tests for manifest execution and reproducibility checks.

These tests exercise the runtime against the real Phase 1 physics functions;
no physics code is mocked. The single summary-comparison test replaces the
runner entry point to force a disagreement that deterministic physics cannot
produce on demand.
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Mapping
from typing import Any

import pytest

import qrs.runtime.runner as runner_module
from qrs.classical import simulate_harmonic_oscillator
from qrs.quantum import simulate_bell_state
from qrs.runtime import (
    ExperimentManifest,
    ResultEnvelope,
    capture_environment,
    check_reproducibility,
    run_manifest,
)
from qrs.runtime.manifest import BELL_STATE, HARMONIC_OSCILLATOR

pytestmark = pytest.mark.integration

OSCILLATOR_PARAMETERS: Mapping[str, float] = {
    "mass": 1.0,
    "stiffness": 4.0,
    "initial_displacement": 1.0,
    "initial_velocity": 0.5,
    "t_start": 0.0,
    "t_end": 5.0,
}


def create_oscillator_manifest(**overrides: Any) -> ExperimentManifest:
    options: dict[str, Any] = {
        "model_name": HARMONIC_OSCILLATOR,
        "parameters": OSCILLATOR_PARAMETERS,
        "environment": capture_environment(),
    }
    options.update(overrides)
    return ExperimentManifest.create(**options)


def create_bell_manifest(**overrides: Any) -> ExperimentManifest:
    options: dict[str, Any] = {
        "model_name": BELL_STATE,
        "environment": capture_environment(),
    }
    options.update(overrides)
    return ExperimentManifest.create(**options)


def test_run_manifest_harmonic_records_real_metrics() -> None:
    manifest = create_oscillator_manifest()
    expected = simulate_harmonic_oscillator(
        mass=1.0,
        stiffness=4.0,
        initial_displacement=1.0,
        initial_velocity=0.5,
        t_span=(0.0, 5.0),
        num_points=1001,
        method="DOP853",
        rtol=1e-10,
        atol=1e-12,
    )

    envelope = run_manifest(manifest)
    summary = envelope.result_summary

    assert envelope.schema_version == 1
    assert envelope.validation_status == "passed"
    assert envelope.artefacts == ()
    assert envelope.experiment_id == manifest.experiment_id
    assert summary["mass"] == expected.mass
    assert summary["stiffness"] == expected.stiffness
    assert summary["angular_frequency"] == expected.angular_frequency
    assert summary["initial_displacement"] == expected.initial_displacement
    assert summary["initial_velocity"] == expected.initial_velocity
    assert summary["initial_energy"] == expected.initial_energy
    assert summary["t_start"] == 0.0
    assert summary["t_end"] == 5.0
    assert summary["num_points"] == 1001
    assert summary["max_abs_displacement_error"] == expected.max_abs_displacement_error
    assert summary["max_relative_displacement_error"] == expected.max_relative_displacement_error
    assert summary["max_abs_energy_drift"] == expected.max_abs_energy_drift
    assert summary["max_relative_energy_drift"] == expected.max_relative_energy_drift
    assert summary["method"] == "DOP853"
    assert envelope.validation_details["checks_passed"] == 2
    assert envelope.validation_details["checks_failed"] == 0
    assert envelope.validation_details["failed_checks"] == ""


def test_run_manifest_bell_records_real_metrics() -> None:
    manifest = create_bell_manifest()
    expected = simulate_bell_state()

    envelope = run_manifest(manifest)
    summary = envelope.result_summary

    assert envelope.validation_status == "passed"
    assert envelope.artefacts == ()
    assert summary["fidelity"] == expected.fidelity
    assert summary["purity"] == expected.purity
    assert summary["chsh_value"] == expected.chsh_value
    assert summary["chsh_value"] == pytest.approx(2.0 * math.sqrt(2.0), abs=1e-12)
    assert summary["zz_correlation"] == expected.zz_correlation
    assert summary["xx_correlation"] == expected.xx_correlation
    assert summary["yy_correlation"] == expected.yy_correlation
    assert summary["zx_correlation"] == expected.zx_correlation
    assert summary["xz_correlation"] == expected.xz_correlation
    assert summary["e_z_b0"] == expected.e_z_b0
    assert summary["e_z_b1"] == expected.e_z_b1
    assert summary["e_x_b0"] == expected.e_x_b0
    assert summary["e_x_b1"] == expected.e_x_b1
    assert summary["probability_sum"] == pytest.approx(1.0, abs=1e-12)
    assert envelope.validation_details["checks_passed"] == 9
    assert envelope.validation_details["checks_failed"] == 0


def test_run_manifest_rejects_non_manifest() -> None:
    with pytest.raises(TypeError, match="manifest must be an ExperimentManifest"):
        run_manifest({})  # type: ignore[arg-type]


def test_run_manifest_rejects_stale_identifier() -> None:
    manifest = create_oscillator_manifest()
    tampered = dataclasses.replace(manifest, seed=1)

    with pytest.raises(ValueError, match="experiment_id does not match"):
        run_manifest(tampered)


def test_run_manifest_reports_validation_failure() -> None:
    manifest = create_oscillator_manifest(
        parameters={"initial_displacement": 1.0},
        solver_config={"num_points": 2, "rtol": 1e-2, "atol": 1e-2},
    )

    envelope = run_manifest(manifest)

    assert envelope.validation_status == "failed"
    assert envelope.validation_details["checks_passed"] == 0
    assert envelope.validation_details["checks_failed"] == 2
    assert envelope.validation_details["failed_checks"] == (
        "displacement_error,relative_energy_drift"
    )
    assert envelope.result_summary["max_abs_displacement_error"] > 1e-8


def test_check_reproducibility_harmonic_succeeds() -> None:
    manifest = create_oscillator_manifest()

    first, second = check_reproducibility(manifest)

    assert first.experiment_id == manifest.experiment_id
    assert second.experiment_id == manifest.experiment_id
    assert first.validation_status == "passed"
    assert second.validation_status == "passed"
    assert dict(first.result_summary) == dict(second.result_summary)
    assert dict(first.validation_details) == dict(second.validation_details)


def test_check_reproducibility_bell_succeeds() -> None:
    manifest = create_bell_manifest()

    first, second = check_reproducibility(manifest)

    assert first.experiment_id == manifest.experiment_id
    assert dict(first.result_summary) == dict(second.result_summary)
    assert first.result_summary["chsh_value"] == second.result_summary["chsh_value"]


def test_check_reproducibility_rejects_stale_identifier() -> None:
    manifest = create_oscillator_manifest()
    tampered = dataclasses.replace(manifest, seed=1)

    with pytest.raises(ValueError, match="experiment_id does not match"):
        check_reproducibility(tampered)


def test_check_reproducibility_rejects_tampered_environment() -> None:
    manifest = create_oscillator_manifest()
    tampered = dataclasses.replace(
        manifest,
        environment={**manifest.environment, "numpy": "0.0.0"},
    )

    with pytest.raises(ValueError, match="experiment_id does not match"):
        check_reproducibility(tampered)


def test_check_reproducibility_detects_environment_drift() -> None:
    environment = dict(capture_environment())
    environment["python"] = "0.0.0"
    manifest = create_oscillator_manifest(environment=environment)

    with pytest.raises(RuntimeError, match="environment drift detected") as excinfo:
        check_reproducibility(manifest)

    message = str(excinfo.value)
    assert "python: manifest='0.0.0'" in message
    assert f"current={capture_environment()['python']!r}" in message


def test_check_reproducibility_allows_environment_drift() -> None:
    environment = dict(capture_environment())
    environment["python"] = "0.0.0"
    manifest = create_oscillator_manifest(environment=environment)

    first, second = check_reproducibility(manifest, allow_environment_drift=True)

    assert first.validation_status == "passed"
    assert dict(first.result_summary) == dict(second.result_summary)


def test_check_reproducibility_rejects_failed_validation() -> None:
    manifest = create_oscillator_manifest(
        parameters={"initial_displacement": 1.0},
        solver_config={"num_points": 2, "rtol": 1e-2, "atol": 1e-2},
    )

    with pytest.raises(RuntimeError, match="validation did not pass"):
        check_reproducibility(manifest)


def test_check_reproducibility_rejects_summary_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = create_oscillator_manifest()
    summary = {"mass": 1.0, "method": "DOP853"}
    details = {"failed_checks": ""}
    first = ResultEnvelope(
        schema_version=1,
        manifest=manifest,
        result_summary=summary,
        validation_status="passed",
        validation_details=details,
        artefacts=(),
    )
    second = ResultEnvelope(
        schema_version=1,
        manifest=manifest,
        result_summary={**summary, "mass": 2.0},
        validation_status="passed",
        validation_details=details,
        artefacts=(),
    )
    envelopes = iter((first, second))

    def fake_run_manifest(_: ExperimentManifest) -> ResultEnvelope:
        return next(envelopes)

    monkeypatch.setattr(runner_module, "run_manifest", fake_run_manifest)

    with pytest.raises(RuntimeError, match="reproducibility comparison failed for 'mass'"):
        check_reproducibility(manifest)


def test_check_reproducibility_accepts_matching_custom_tolerance() -> None:
    manifest = create_bell_manifest()

    first, second = check_reproducibility(manifest, tolerance=1e-9)

    assert dict(first.result_summary) == dict(second.result_summary)


@pytest.mark.parametrize("tolerance", [0.0, -1.0, math.nan, math.inf, -math.inf])
def test_check_reproducibility_rejects_invalid_tolerance(tolerance: float) -> None:
    manifest = create_bell_manifest()

    with pytest.raises(ValueError):
        check_reproducibility(manifest, tolerance=tolerance)


@pytest.mark.parametrize("tolerance", ["1e-12", None, True])
def test_check_reproducibility_rejects_non_numeric_tolerance(tolerance: object) -> None:
    manifest = create_bell_manifest()

    with pytest.raises((TypeError, ValueError)):
        check_reproducibility(manifest, tolerance=tolerance)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["yes", 1, None])
def test_check_reproducibility_rejects_non_boolean_drift_flag(value: object) -> None:
    manifest = create_bell_manifest()

    with pytest.raises(TypeError, match="allow_environment_drift must be a boolean"):
        check_reproducibility(manifest, allow_environment_drift=value)  # type: ignore[arg-type]


def test_check_reproducibility_rejects_non_manifest() -> None:
    with pytest.raises(TypeError, match="manifest must be an ExperimentManifest"):
        check_reproducibility({})  # type: ignore[arg-type]
