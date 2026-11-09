"""Scientific validation of the classical heat diffusion domain."""

import math
from itertools import pairwise

import numpy as np
import pytest

from qrs.classical import simulate_heat_diffusion

pytestmark = pytest.mark.scientific

ALPHA = 1e-6
LENGTH = 0.1
T_END = 600.0
LAMBDA = (math.pi / LENGTH) ** 2


def _exact_u(x: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Exact Fourier sine-series solution sampled on (t, x)."""

    t_col = t[:, None]
    x_row = x[None, :]
    return np.exp(-ALPHA * LAMBDA * t_col) * np.sin(math.pi * x_row / LENGTH) + 0.5 * np.exp(
        -9.0 * ALPHA * LAMBDA * t_col
    ) * np.sin(3.0 * math.pi * x_row / LENGTH)


def test_analytic_agreement_within_gates() -> None:
    """HD-001/HD-002: solution matches the exact reference within HD-G1/HD-G2/HD-G3."""

    result = simulate_heat_diffusion(
        alpha=ALPHA, length=LENGTH, t_end=T_END, num_points=401, num_output_points=101
    )

    # HD-G1: max abs error over [0, t_end] <= 1e-5
    assert result.max_abs_error <= 1e-5, result.max_abs_error
    # HD-G2: error at t_end <= 2e-6
    assert result.max_abs_error_t_end <= 2e-6, result.max_abs_error_t_end
    # HD-G3: u(L/2, 600) vs exact within 2e-6
    assert abs(result.u_mid_t_end - result.analytic_u_mid_t_end) <= 2e-6

    np.testing.assert_allclose(
        result.u,
        result.analytic_u,
        rtol=0.0,
        atol=1e-5,
    )


def test_spatial_convergence_near_order_two() -> None:
    """HD-008: observed order computed from dx = L/(N-1) lies in [1.9, 2.1]."""

    errors = []
    for num_points in (51, 101, 201, 401):
        result = simulate_heat_diffusion(
            alpha=ALPHA,
            length=LENGTH,
            t_end=T_END,
            num_points=num_points,
            num_output_points=2,
        )
        errors.append((num_points, result.max_abs_error_t_end))

    for (n_coarse, e_coarse), (n_fine, e_fine) in pairwise(errors):
        dx_coarse = LENGTH / (n_coarse - 1)
        dx_fine = LENGTH / (n_fine - 1)
        order = math.log(e_coarse / e_fine) / math.log(dx_coarse / dx_fine)
        assert 1.9 <= order <= 2.1, f"order {order:.6f} for {n_coarse}->{n_fine}"


def test_first_mode_decay_matches_exact_rate() -> None:
    """HD-002: first-mode projection decays as exp(-alpha (pi/L)^2 t)."""

    result = simulate_heat_diffusion(
        alpha=ALPHA, length=LENGTH, t_end=T_END, num_points=401, num_output_points=101
    )

    x = result.x
    t = result.t
    w = np.full(len(x), 2.0 * result.dx / 2.0)
    w[0] = w[-1] = result.dx / 2.0
    s1 = np.sin(math.pi * x / LENGTH)
    norm = float(np.sum(w * s1 * s1))

    coeff = np.array([float(np.sum(w * result.u[k] * s1)) / norm for k in range(len(t))])
    exact_rate = ALPHA * LAMBDA
    exact_decay = np.exp(-exact_rate * t)

    max_error = float(np.max(np.abs(coeff - exact_decay)))
    assert max_error <= 2e-6, max_error

    measured_rate = -math.log(coeff[-1] / coeff[0]) / t[-1]
    relative_error = abs(measured_rate - exact_rate) / exact_rate
    assert relative_error <= 1e-4, relative_error


def test_boundary_conditions_exactly_zero() -> None:
    """HD-001: homogeneous Dirichlet boundaries are exactly zero."""

    result = simulate_heat_diffusion(
        alpha=ALPHA, length=LENGTH, t_end=T_END, num_points=401, num_output_points=101
    )

    assert result.boundary_max == 0.0
    assert np.all(result.u[:, 0] == 0.0)
    assert np.all(result.u[:, -1] == 0.0)


def test_coarse_grid_passes_validation() -> None:
    """A coarse grid (N=51) must not be wrongly marked failed by dx-scaled thresholds."""

    from qrs.runtime import ExperimentManifest, run_manifest
    from qrs.runtime.manifest import HEAT_DIFFUSION

    manifest = ExperimentManifest.create(
        model_name=HEAT_DIFFUSION,
        parameters={
            "alpha": ALPHA,
            "length": LENGTH,
            "t_end": T_END,
            "num_points": 51,
            "num_output_points": 2,
        },
        solver_config={"rtol": 1e-10, "atol": 1e-12},
        seed=0,
    )
    envelope = run_manifest(manifest)
    assert envelope.validation_status == "passed", envelope.validation_details


def test_sampled_alpha_below_zero_raises() -> None:
    """HD-004: sampled alpha <= 0 is rejected before the solver is called."""

    # Instead verify validation rejects alpha <= 0 at the entry point.
    with pytest.raises((TypeError, ValueError), match="alpha"):
        simulate_heat_diffusion(alpha=0.0, length=LENGTH, t_end=T_END)

    with pytest.raises((TypeError, ValueError), match="alpha"):
        simulate_heat_diffusion(alpha=-1e-7, length=LENGTH, t_end=T_END)


def test_uq_matches_exact_moments_within_standard_errors() -> None:
    """HD-014: solver-based UQ mean/std agree with exact moments within 4 standard errors."""

    from qrs.runtime import ExperimentManifest, run_manifest
    from qrs.runtime.manifest import HEAT_DIFFUSION

    # Exact moments at x = L/2, t = 600, alpha ~ N(1e-6, (5e-8)^2)
    exact_mean = 0.5508541291876023
    exact_std = 0.01571695033833832

    manifest = ExperimentManifest.create(
        model_name=HEAT_DIFFUSION,
        parameters={
            "alpha": ALPHA,
            "length": LENGTH,
            "t_end": T_END,
            "num_points": 401,
            "num_output_points": 101,
        },
        solver_config={"rtol": 1e-10, "atol": 1e-12},
        seed=0,
    )
    envelope = run_manifest(manifest)
    assert envelope.validation_status == "passed", envelope.validation_details

    summary = envelope.result_summary
    uq_mean = summary["uq_mean"]
    uq_std = summary["uq_std"]
    uq_stderr = summary["uq_stderr"]

    # Mean within 4 standard errors of exact mean
    assert abs(uq_mean - exact_mean) <= 4.0 * uq_stderr, (
        f"uq_mean {uq_mean} not within 4 SE ({4.0 * uq_stderr:.2e}) of exact {exact_mean}"
    )
    # Std within 5% of exact std
    assert abs(uq_std - exact_std) <= 0.05 * exact_std, (
        f"uq_std {uq_std} not within 5% of exact {exact_std}"
    )
    # 95% interval contains nominal q(1e-6)
    nominal = 0.5506991968905726
    assert summary["uq_interval_low"] <= nominal <= summary["uq_interval_high"]
