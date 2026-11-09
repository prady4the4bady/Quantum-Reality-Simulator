"""Unit tests for the classical heat diffusion interface, validation, and runtime."""

import math

import numpy as np
import pytest

from qrs.classical import (
    HeatDiffusionResult,
    HeatDiffusionUncertainty,
    propagate_uncertainty,
    simulate_heat_diffusion,
)
from qrs.runtime import ExperimentManifest, check_reproducibility, run_manifest
from qrs.runtime.manifest import HEAT_DIFFUSION


def _result(**overrides: object) -> HeatDiffusionResult:
    parameters: dict[str, object] = {
        "alpha": 1e-6,
        "length": 0.1,
        "t_end": 600.0,
        "num_points": 401,
        "num_output_points": 101,
    }
    parameters.update(overrides)
    return simulate_heat_diffusion(**parameters)  # type: ignore[arg-type]


def test_default_simulation_shape_and_metadata() -> None:
    result = _result()

    assert isinstance(result, HeatDiffusionResult)
    assert result.alpha == 1e-6
    assert result.length == 0.1
    assert result.t_end == 600.0
    assert result.num_points == 401
    assert result.num_output_points == 101
    assert result.dx == pytest.approx(0.1 / 400.0)
    assert result.first_mode_decay_rate == pytest.approx(1e-6 * (math.pi / 0.1) ** 2)
    assert result.method == "Radau"
    assert result.t.shape == (101,)
    assert result.t.dtype == np.float64
    for array in (result.u, result.analytic_u):
        assert array.shape == (101, 401)
        assert array.dtype == np.float64
    assert result.x.shape == (401,)
    assert result.x.dtype == np.float64


def test_time_grid_includes_requested_endpoints() -> None:
    result = _result(t_end=10.0, num_output_points=51)

    assert result.t[0] == 0.0
    assert result.t[-1] == 10.0
    assert np.all(np.diff(result.t) > 0.0)
    assert result.x[0] == 0.0
    assert result.x[-1] == 0.1


def test_boundaries_are_exactly_zero() -> None:
    result = _result()

    assert result.boundary_max == 0.0
    assert np.all(result.u[:, 0] == 0.0)
    assert np.all(result.u[:, -1] == 0.0)


def test_initial_profile_matches_at_t_zero() -> None:
    result = _result()

    x = result.x
    expected = np.sin(math.pi * x / 0.1) + 0.5 * np.sin(3.0 * math.pi * x / 0.1)
    np.testing.assert_allclose(result.u[0], expected, atol=1e-15)
    assert result.initial_profile_error < 1e-12


def test_solution_is_non_negative_and_finite() -> None:
    result = _result()

    assert result.min_u >= -1e-12
    assert np.all(np.isfinite(result.u))
    assert np.all(np.isfinite(result.analytic_u))


@pytest.mark.parametrize("alpha", [0.0, -1.0, math.nan, math.inf])
def test_invalid_alpha_is_rejected(alpha: float) -> None:
    with pytest.raises((TypeError, ValueError), match="alpha"):
        _result(alpha=alpha)


@pytest.mark.parametrize("length", [0.0, -0.1, math.nan, math.inf])
def test_invalid_length_is_rejected(length: float) -> None:
    with pytest.raises((TypeError, ValueError), match="length"):
        _result(length=length)


@pytest.mark.parametrize("t_end", [-1.0, math.nan, math.inf])
def test_invalid_t_end_is_rejected(t_end: float) -> None:
    with pytest.raises((TypeError, ValueError), match="t_end"):
        _result(t_end=t_end)


@pytest.mark.parametrize("num_points", [2, 1, 0, -5])
def test_num_points_below_three_is_rejected(num_points: int) -> None:
    with pytest.raises(ValueError, match="at least 3"):
        _result(num_points=num_points)


@pytest.mark.parametrize("num_points", [2.5, "10", True])
def test_non_integer_num_points_is_rejected(num_points: object) -> None:
    with pytest.raises(TypeError, match="num_points"):
        _result(num_points=num_points)


@pytest.mark.parametrize("num_output_points", [1, 0, -5])
def test_num_output_points_below_two_is_rejected(num_output_points: int) -> None:
    with pytest.raises(ValueError, match="at least 2"):
        _result(num_output_points=num_output_points)


@pytest.mark.parametrize("value", ["abc", None, True])
def test_wrong_scalar_types_are_rejected(value: object) -> None:
    with pytest.raises(TypeError, match="alpha"):
        _result(alpha=value)


@pytest.mark.parametrize("name", ["rtol", "atol"])
@pytest.mark.parametrize("value", [0.0, -1.0, math.nan])
def test_invalid_solver_tolerances_are_rejected(name: str, value: float) -> None:
    with pytest.raises((TypeError, ValueError), match=name):
        _result(**{name: value})


def test_manifest_round_trip_preserves_fields() -> None:
    manifest = ExperimentManifest.create(model_name=HEAT_DIFFUSION, seed=42)
    data = manifest.to_dict()
    loaded = ExperimentManifest.from_dict(data)

    assert loaded.model_name == HEAT_DIFFUSION
    assert loaded.parameters == manifest.parameters
    assert loaded.solver_config == manifest.solver_config
    assert loaded.seed == manifest.seed
    assert loaded.experiment_id == manifest.experiment_id


def test_manifest_experiment_id_changes_with_content() -> None:
    base = ExperimentManifest.create(model_name=HEAT_DIFFUSION, seed=0)
    altered = ExperimentManifest.create(model_name=HEAT_DIFFUSION, seed=1)
    assert base.experiment_id != altered.experiment_id


def test_seed_determinism_reproduces_identical_summary() -> None:
    manifest_a = ExperimentManifest.create(model_name=HEAT_DIFFUSION, seed=0)
    manifest_b = ExperimentManifest.create(model_name=HEAT_DIFFUSION, seed=0)
    envelope_a = run_manifest(manifest_a)
    envelope_b = run_manifest(manifest_b)

    assert envelope_a.result_summary == envelope_b.result_summary
    assert envelope_a.validation_status == envelope_b.validation_status


def test_default_uq_values_regression_seed_0() -> None:
    """Regression check against previously reviewed output, not a scientific validation.

    The default heat-diffusion manifest with seed 0 must reproduce the
    previously recorded uq_mean and uq_std exactly.
    """
    manifest = ExperimentManifest.create(model_name=HEAT_DIFFUSION, seed=0)
    envelope = run_manifest(manifest)
    summary = envelope.result_summary

    assert summary["uq_mean"] == pytest.approx(0.550755250912931, abs=1e-9)
    assert summary["uq_std"] == pytest.approx(0.01569055194620832, abs=1e-9)


def test_reproducibility_re_runs_within_tolerance() -> None:
    manifest = ExperimentManifest.create(model_name=HEAT_DIFFUSION, seed=0)
    first, second = check_reproducibility(manifest, tolerance=1e-12)

    assert first.validation_status == "passed"
    assert second.validation_status == "passed"
    assert first.result_summary == second.result_summary


@pytest.mark.parametrize("num_points", [4, 6, 10, 100])
def test_even_num_points_is_rejected(num_points: int) -> None:
    """num_points must be odd so that L/2 lies exactly on a grid point."""
    with pytest.raises(ValueError, match="must be odd"):
        _result(num_points=num_points)


def test_t_end_zero_returns_initial_profile() -> None:
    """t_end=0 is handled explicitly: solution is the initial profile."""
    result = simulate_heat_diffusion(
        alpha=1e-6, length=0.1, t_end=0.0, num_points=401, num_output_points=2
    )

    assert result.t_end == 0.0
    assert result.t.shape == (2,)
    assert result.t[0] == 0.0
    assert result.t[-1] == 0.0
    assert result.u.shape == (2, 401)
    assert result.analytic_u.shape == (2, 401)
    assert result.max_abs_error == 0.0
    assert result.boundary_max == 0.0
    assert result.initial_profile_error == 0.0
    assert result.min_u >= -1e-12
    assert np.all(np.isfinite(result.u))


def test_run_manifest_t_end_zero() -> None:
    """t_end=0 through the runtime: u(L/2, 0) = 0.5 and all errors are zero."""
    manifest = ExperimentManifest.create(
        model_name=HEAT_DIFFUSION,
        parameters={"t_end": 0.0},
        solver_config={"rtol": 1e-10, "atol": 1e-12},
        seed=0,
    )
    envelope = run_manifest(manifest)

    assert envelope.validation_status == "passed", envelope.validation_details
    summary = envelope.result_summary
    assert summary["uq_std"] == 0.0
    assert summary["uq_mean"] == pytest.approx(0.5, abs=1e-12)
    assert summary["max_abs_error"] == 0.0


def test_result_summary_includes_uq_parameters() -> None:
    """result_summary records alpha_relative_std and num_samples."""
    envelope = run_manifest(
        ExperimentManifest.create(
            model_name=HEAT_DIFFUSION,
            parameters={
                "alpha": 1e-6,
                "length": 0.1,
                "t_end": 600.0,
                "num_points": 401,
                "num_output_points": 101,
                "alpha_relative_std": 0.05,
                "num_samples": 10000,
            },
            solver_config={"rtol": 1e-10, "atol": 1e-12},
            seed=0,
        )
    )

    summary = envelope.result_summary
    assert summary["alpha_relative_std"] == 0.05
    assert summary["num_samples"] == 10000
    assert "uq_mean" in summary
    assert "uq_std" in summary
    assert "uq_stderr" in summary
    assert "uq_interval_low" in summary
    assert "uq_interval_high" in summary


@pytest.mark.parametrize("length", [0.01, 1.0])
def test_different_lengths_pass_validation(length: float) -> None:
    """Correct runs pass validation for L=0.01 and L=1.0."""
    envelope = run_manifest(
        ExperimentManifest.create(
            model_name=HEAT_DIFFUSION,
            parameters={
                "alpha": 1e-6,
                "length": length,
                "t_end": 600.0,
                "num_points": 401,
                "num_output_points": 101,
            },
            solver_config={"rtol": 1e-10, "atol": 1e-12},
            seed=0,
        )
    )

    assert envelope.validation_status == "passed", envelope.validation_details


def test_seed_changes_uncertainty_summary() -> None:
    envelope_seed_0 = run_manifest(ExperimentManifest.create(model_name=HEAT_DIFFUSION, seed=0))
    envelope_seed_1 = run_manifest(ExperimentManifest.create(model_name=HEAT_DIFFUSION, seed=1))

    s0 = envelope_seed_0.result_summary
    s1 = envelope_seed_1.result_summary
    assert s0["uq_mean"] != s1["uq_mean"]
    assert s0["uq_std"] != s1["uq_std"]


def test_manifest_rejects_even_num_points() -> None:
    """STEP 1: ExperimentManifest.create with num_points=400 raises ValueError."""
    with pytest.raises(ValueError, match="must be odd so that L/2 lies"):
        ExperimentManifest.create(
            model_name=HEAT_DIFFUSION,
            parameters={
                "alpha": 1e-6,
                "length": 0.1,
                "t_end": 600.0,
                "num_points": 400,
                "num_output_points": 101,
            },
            solver_config={"rtol": 1e-10, "atol": 1e-12},
            seed=0,
        )

    # num_points=401 still works
    manifest = ExperimentManifest.create(
        model_name=HEAT_DIFFUSION,
        parameters={
            "alpha": 1e-6,
            "length": 0.1,
            "t_end": 600.0,
            "num_points": 401,
            "num_output_points": 101,
        },
        solver_config={"rtol": 1e-10, "atol": 1e-12},
        seed=0,
    )
    assert manifest.model_name == HEAT_DIFFUSION


def test_dense_output_window_grows_with_samples() -> None:
    """STEP 2: alpha_relative_std=0.12, 10000 samples, seed 0 runs without error."""
    uq = propagate_uncertainty(
        alpha=1e-6,
        length=0.1,
        t_end=600.0,
        num_points=401,
        alpha_relative_std=0.12,
        num_samples=10000,
        seed=0,
    )
    assert isinstance(uq, HeatDiffusionUncertainty)
    assert uq.mean > 0.0
    assert uq.std > 0.0
    assert uq.stderr > 0.0
    assert uq.interval_low < uq.interval_high


def test_alpha_relative_std_0_15_accepted() -> None:
    """STEP 3: alpha_relative_std=0.15 is accepted by manifest and solver."""
    manifest = ExperimentManifest.create(
        model_name=HEAT_DIFFUSION,
        parameters={
            "alpha": 1e-6,
            "length": 0.1,
            "t_end": 600.0,
            "num_points": 401,
            "num_output_points": 101,
            "alpha_relative_std": 0.15,
            "num_samples": 1000,
        },
        solver_config={"rtol": 1e-10, "atol": 1e-12},
        seed=0,
    )
    assert manifest.parameters["alpha_relative_std"] == 0.15

    result = simulate_heat_diffusion(
        alpha=1e-6,
        length=0.1,
        t_end=600.0,
        num_points=401,
        num_output_points=101,
        alpha_relative_std=0.15,
        num_samples=1000,
    )
    assert result.alpha_relative_std == 0.15

    uq = propagate_uncertainty(
        alpha=1e-6,
        length=0.1,
        t_end=600.0,
        num_points=401,
        alpha_relative_std=0.15,
        num_samples=1000,
        seed=0,
    )
    assert isinstance(uq, HeatDiffusionUncertainty)
    assert uq.alpha_relative_std == 0.15


@pytest.mark.parametrize("value", [0.16, 0.2, 0.5])
def test_alpha_relative_std_above_0_15_rejected(value: float) -> None:
    """STEP 3: alpha_relative_std > 0.15 rejected by manifest, solver, and UQ."""
    with pytest.raises(ValueError, match=r"at most 0\.15"):
        ExperimentManifest.create(
            model_name=HEAT_DIFFUSION,
            parameters={
                "alpha": 1e-6,
                "length": 0.1,
                "t_end": 600.0,
                "num_points": 401,
                "num_output_points": 101,
                "alpha_relative_std": value,
                "num_samples": 1000,
            },
            solver_config={"rtol": 1e-10, "atol": 1e-12},
            seed=0,
        )

    with pytest.raises(ValueError, match=r"at most 0\.15"):
        simulate_heat_diffusion(
            alpha=1e-6,
            length=0.1,
            t_end=600.0,
            num_points=401,
            num_output_points=101,
            alpha_relative_std=value,
            num_samples=1000,
        )

    with pytest.raises(ValueError, match=r"at most 0\.15"):
        propagate_uncertainty(
            alpha=1e-6,
            length=0.1,
            t_end=600.0,
            num_points=401,
            alpha_relative_std=value,
            num_samples=1000,
            seed=0,
        )
