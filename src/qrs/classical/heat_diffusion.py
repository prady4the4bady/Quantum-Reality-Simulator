r"""One-dimensional heat equation with homogeneous Dirichlet boundaries.

Solves the parabolic problem

.. math::

    \frac{\partial u}{\partial t} = \alpha \frac{\partial^2 u}{\partial x^2},
    \qquad 0 < x < L, \quad t > 0,

with zero Dirichlet boundaries

.. math::

    u(0,t) = 0, \qquad u(L,t) = 0,

and initial profile

.. math::

    u(x,0) = \sin\!\left(\frac{\pi x}{L}\right)
           + 0.5\,\sin\!\left(\frac{3\pi x}{L}\right).

All quantities use SI units: diffusivity in metres squared per second (m²/s),
length in metres (m), position in metres (m), and time in seconds (s).

The spatial discretisation uses second-order central differences on a uniform
grid and the method of lines; time integration uses SciPy's ``solve_ivp`` with
the implicit Radau method and a constant sparse tridiagonal CSC Jacobian, which
is appropriate because the semi-discrete system is stiff for fine grids.

``num_points`` must be odd so that ``x = L/2`` lies exactly on a grid point.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Integral
from typing import Final

import numpy as np
from numpy.typing import NDArray
from scipy import sparse
from scipy.integrate import solve_ivp

from qrs.core.validation import require_finite_real, require_positive_finite

_SUPPORTED_METHODS = frozenset({"Radau"})

# Maximum allowed relative standard deviation for the uncertain diffusivity.
# Above ~0.15, a sampled alpha <= 0 becomes likely with 10000 samples, so the
# run raises at runtime.
HEAT_MAX_ALPHA_RELATIVE_STD: Final[float] = 0.15


@dataclass(frozen=True, slots=True)
class HeatDiffusionResult:
    """Numerical and analytical results for one heat-diffusion run.

    Arrays are indexed by the requested evaluation times. ``u`` is the
    numerical solution including the boundary columns, which are exactly zero.
    ``analytic_u`` is the exact Fourier sine-series solution sampled at the
    same times and positions.
    """

    alpha: float
    length: float
    t_end: float
    num_points: int
    num_output_points: int
    dx: float
    first_mode_decay_rate: float
    alpha_relative_std: float
    num_samples: int
    x: NDArray[np.float64]
    t: NDArray[np.float64]
    u: NDArray[np.float64]
    analytic_u: NDArray[np.float64]
    max_abs_error: float
    max_abs_error_t_end: float
    u_mid_t_end: float
    analytic_u_mid_t_end: float
    boundary_max: float
    initial_profile_error: float
    min_u: float
    max_u: float
    method: str


@dataclass(frozen=True, slots=True)
class HeatDiffusionUncertainty:
    """Monte Carlo uncertainty propagation results for heat diffusion.

    The diffusivity ``alpha`` is sampled from
    ``Normal(alpha0, (alpha0 * alpha_relative_std)^2)`` using
    ``numpy.random.default_rng(seed)``. Each sample is evaluated through the
    numerical solver using the identity that the PDE depends only on the
    product ``alpha * t``: a single dense-output integration at ``alpha0`` is
    interpolated at ``t_j = alpha_j * t_q / alpha0``.
    """

    alpha_relative_std: float
    num_samples: int
    seed: int
    mean: float
    std: float
    stderr: float
    interval_low: float
    interval_high: float


def _validate_num_points(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{name} must be an integer, got {type(value).__name__}")
    count = int(value)
    if count < 3:
        raise ValueError(f"{name} must be at least 3, got {count}")
    if count % 2 == 0:
        raise ValueError(f"{name} must be odd so that L/2 lies on a grid point, got {count}")
    return count


def _validate_num_output_points(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{name} must be an integer, got {type(value).__name__}")
    count = int(value)
    if count < 2:
        raise ValueError(f"{name} must be at least 2, got {count}")
    return count


def _validate_t_end(value: object, name: str) -> float:
    t_end = require_finite_real(value, name)
    if t_end < 0.0:
        raise ValueError(f"{name} must be non-negative, got {t_end!r}")
    return t_end


def _validate_alpha_relative_std(value: object, name: str) -> float:
    std = require_positive_finite(value, name)
    if std > HEAT_MAX_ALPHA_RELATIVE_STD:
        raise ValueError(
            f"{name} must be at most {HEAT_MAX_ALPHA_RELATIVE_STD} "
            f"(larger values make a non-positive sampled alpha likely), got {std!r}"
        )
    return std


def _validate_num_samples(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{name} must be an integer, got {type(value).__name__}")
    count = int(value)
    if count < 2:
        raise ValueError(f"{name} must be at least 2, got {count}")
    return count


def _analytic_solution(
    *,
    alpha: float,
    length: float,
    x: NDArray[np.float64],
    t: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Exact Fourier sine-series solution sampled on (t, x)."""

    lam = (math.pi / length) ** 2
    t_col = t[:, None]
    x_row = x[None, :]
    return np.exp(-alpha * lam * t_col) * np.sin(math.pi * x_row / length) + 0.5 * np.exp(
        -9.0 * alpha * lam * t_col
    ) * np.sin(3.0 * math.pi * x_row / length)


def _build_rhs_and_jacobian(alpha: float, dx: float, num_interior: int):
    """Build the right-hand side and constant sparse CSC Jacobian.

    The state vector holds the interior values ``u_1 .. u_{N-2}``; the
    boundaries ``u_0 = u_{N-1} = 0`` are enforced exactly.
    """

    coefficient = alpha / (dx * dx)

    def rhs(_time: float, state: NDArray[np.float64]) -> NDArray[np.float64]:
        out = np.empty_like(state)
        out[0] = coefficient * (-2.0 * state[0] + state[1])
        if num_interior > 2:
            out[1:-1] = coefficient * (state[:-2] - 2.0 * state[1:-1] + state[2:])
        out[-1] = coefficient * (state[-2] - 2.0 * state[-1])
        return out

    jac = sparse.diags(
        [coefficient, -2.0 * coefficient, coefficient],
        [-1, 0, 1],
        shape=(num_interior, num_interior),
        format="csc",
    )
    return rhs, jac


def _integrate(
    rhs,
    jac,
    initial_state: NDArray[np.float64],
    t_span: tuple[float, float],
    t_eval: NDArray[np.float64] | None,
    dense_output: bool,
    rtol: float,
    atol: float,
):
    solution = solve_ivp(
        rhs,
        t_span,
        initial_state,
        method="Radau",
        t_eval=t_eval,
        dense_output=dense_output,
        rtol=rtol,
        atol=atol,
        jac=jac,
    )
    if not solution.success:
        raise RuntimeError(f"heat diffusion integration failed: {solution.message}")
    return solution


def simulate_heat_diffusion(
    *,
    alpha: float,
    length: float,
    t_end: float,
    num_points: int = 401,
    num_output_points: int = 101,
    alpha_relative_std: float = 0.05,
    num_samples: int = 10000,
    rtol: float = 1e-10,
    atol: float = 1e-12,
) -> HeatDiffusionResult:
    r"""Integrate the heat equation and compare with the exact solution.

    Parameters
    ----------
    alpha:
        Diffusivity in m²/s. Must be finite and strictly positive.
    length:
        Domain length ``L`` in m. Must be finite and strictly positive.
    t_end:
        Final time in s. Must be finite and non-negative. When ``t_end = 0``
        the solution is the initial profile at time zero.
    num_points:
        Number of uniformly spaced grid points. Must be an odd integer at least
        3 so that ``L/2`` lies exactly on a grid point.
    num_output_points:
        Number of uniformly spaced output times in ``[0, t_end]``. Must be an
        integer at least 2.
    alpha_relative_std:
        Relative standard deviation of the uncertain diffusivity. Must be
        positive, finite, and less than 1.
    num_samples:
        Number of Monte Carlo samples for uncertainty propagation. Must be an
        integer at least 2.
    rtol, atol:
        Relative and absolute solver tolerances. Both must be positive.

    Returns
    -------
    HeatDiffusionResult
        Numerical solution, analytical reference, and error metrics.

    Raises
    ------
    TypeError
        If an input has the wrong type.
    ValueError
        If a physical parameter or discretisation setting is invalid.
    RuntimeError
        If SciPy fails to integrate or returns non-finite / badly shaped data.
    """

    validated_alpha = require_positive_finite(alpha, "alpha")
    validated_length = require_positive_finite(length, "length")
    validated_t_end = _validate_t_end(t_end, "t_end")
    count = _validate_num_points(num_points, "num_points")
    output_count = _validate_num_output_points(num_output_points, "num_output_points")
    validated_alpha_relative_std = _validate_alpha_relative_std(
        alpha_relative_std, "alpha_relative_std"
    )
    validated_num_samples = _validate_num_samples(num_samples, "num_samples")
    validated_rtol = require_positive_finite(rtol, "rtol")
    validated_atol = require_positive_finite(atol, "atol")

    dx = validated_length / (count - 1)
    x = np.linspace(0.0, validated_length, count, dtype=np.float64)

    if validated_t_end == 0.0:
        # No time evolution: solution is the initial profile at t = 0.
        t = np.linspace(0.0, validated_t_end, output_count, dtype=np.float64)
        u0 = np.sin(math.pi * x / validated_length) + 0.5 * np.sin(
            3.0 * math.pi * x / validated_length
        )
        u = np.tile(u0, (output_count, 1))
        analytic_u = u.copy()
        max_abs_error = 0.0
        max_abs_error_t_end = 0.0
        mid_index = (count - 1) // 2
        u_mid_t_end = float(u[-1, mid_index])
        analytic_u_mid_t_end = float(analytic_u[-1, mid_index])
        boundary_max = 0.0
        initial_profile_error = 0.0
        min_u = float(np.min(u))
        max_u = float(np.max(u))
        return HeatDiffusionResult(
            alpha=validated_alpha,
            length=validated_length,
            t_end=validated_t_end,
            num_points=count,
            num_output_points=output_count,
            dx=dx,
            first_mode_decay_rate=validated_alpha * (math.pi / validated_length) ** 2,
            alpha_relative_std=validated_alpha_relative_std,
            num_samples=validated_num_samples,
            x=x,
            t=t,
            u=u,
            analytic_u=analytic_u,
            max_abs_error=max_abs_error,
            max_abs_error_t_end=max_abs_error_t_end,
            u_mid_t_end=u_mid_t_end,
            analytic_u_mid_t_end=analytic_u_mid_t_end,
            boundary_max=boundary_max,
            initial_profile_error=initial_profile_error,
            min_u=min_u,
            max_u=max_u,
            method="Radau",
        )

    t = np.linspace(0.0, validated_t_end, output_count, dtype=np.float64)

    u0 = np.sin(math.pi * x / validated_length) + 0.5 * np.sin(3.0 * math.pi * x / validated_length)
    initial_state = u0[1:-1].copy()
    num_interior = count - 2

    rhs, jac = _build_rhs_and_jacobian(validated_alpha, dx, num_interior)

    solution = _integrate(
        rhs,
        jac,
        initial_state,
        (0.0, validated_t_end),
        t,
        dense_output=False,
        rtol=validated_rtol,
        atol=validated_atol,
    )

    numerical = np.asarray(solution.y, dtype=np.float64)
    if numerical.shape != (num_interior, output_count):
        raise RuntimeError(
            "heat diffusion integration returned an unexpected state shape "
            f"{numerical.shape}; expected ({num_interior}, {output_count})"
        )
    if not np.all(np.isfinite(numerical)):
        raise RuntimeError("heat diffusion integration returned non-finite values")

    u = np.zeros((output_count, count), dtype=np.float64)
    u[:, 1:-1] = numerical.T

    analytic_u = _analytic_solution(
        alpha=validated_alpha,
        length=validated_length,
        x=x,
        t=t,
    )

    absolute_error = np.abs(u - analytic_u)
    max_abs_error = float(np.max(absolute_error))
    max_abs_error_t_end = float(np.max(absolute_error[-1]))

    mid_index = (count - 1) // 2  # exact because num_points is odd
    u_mid_t_end = float(u[-1, mid_index])
    analytic_u_mid_t_end = float(analytic_u[-1, mid_index])

    boundary_max = float(np.max(np.abs(u[:, [0, -1]])))
    initial_profile_error = float(np.max(absolute_error[0]))
    min_u = float(np.min(u))
    max_u = float(np.max(u))

    return HeatDiffusionResult(
        alpha=validated_alpha,
        length=validated_length,
        t_end=validated_t_end,
        num_points=count,
        num_output_points=output_count,
        dx=dx,
        first_mode_decay_rate=validated_alpha * (math.pi / validated_length) ** 2,
        alpha_relative_std=validated_alpha_relative_std,
        num_samples=validated_num_samples,
        x=x,
        t=t,
        u=u,
        analytic_u=analytic_u,
        max_abs_error=max_abs_error,
        max_abs_error_t_end=max_abs_error_t_end,
        u_mid_t_end=u_mid_t_end,
        analytic_u_mid_t_end=analytic_u_mid_t_end,
        boundary_max=boundary_max,
        initial_profile_error=initial_profile_error,
        min_u=min_u,
        max_u=max_u,
        method="Radau",
    )


def propagate_uncertainty(
    *,
    alpha: float,
    length: float,
    t_end: float,
    num_points: int,
    alpha_relative_std: float,
    num_samples: int,
    seed: int,
    rtol: float = 1e-10,
    atol: float = 1e-12,
) -> HeatDiffusionUncertainty:
    r"""Propagate diffusivity uncertainty through the numerical solver.

    Samples ``alpha_j ~ Normal(alpha, (alpha * alpha_relative_std)^2)`` using
    ``numpy.random.default_rng(seed)``. Since the PDE depends only on the
    product ``alpha * t``, a single dense-output integration at ``alpha`` over
    ``[0, t_end * 1.25]`` is interpolated at ``t_j = alpha_j * t_end / alpha``
    for each sample, giving the quantity of interest at ``x = L/2`` and
    ``t = t_end``.

    Raises
    ------
    ValueError
        If any sampled diffusivity is non-positive, or if the interpolated
        times exceed the integration window.
    """

    validated_alpha = require_positive_finite(alpha, "alpha")
    validated_length = require_positive_finite(length, "length")
    validated_t_end = _validate_t_end(t_end, "t_end")
    count = _validate_num_points(num_points, "num_points")
    validated_alpha_relative_std = _validate_alpha_relative_std(
        alpha_relative_std, "alpha_relative_std"
    )
    validated_num_samples = _validate_num_samples(num_samples, "num_samples")
    validated_rtol = require_positive_finite(rtol, "rtol")
    validated_atol = require_positive_finite(atol, "atol")

    sigma = validated_alpha * validated_alpha_relative_std
    rng = np.random.default_rng(seed)
    alpha_samples = validated_alpha + sigma * rng.standard_normal(validated_num_samples)
    if np.any(alpha_samples <= 0.0):
        count_bad = int(np.sum(alpha_samples <= 0.0))
        raise ValueError(
            f"{count_bad} sampled diffusivity(ies) were non-positive; "
            "alpha must be strictly positive"
        )

    x_q = validated_length / 2.0
    t_q = validated_t_end

    # Compute t_j immediately after the alpha > 0 check. The integration
    # window must cover every t_j, so grow it if needed.
    t_j = alpha_samples * t_q / validated_alpha
    t_max = max(validated_t_end * 1.25, float(np.max(t_j)))

    mid_index = (count - 1) // 2  # exact because num_points is odd
    interior_index = mid_index - 1  # dense output excludes boundary columns

    if validated_t_end == 0.0:
        # No time evolution: u(x, 0) is deterministic given alpha0.
        u0 = np.sin(math.pi * x_q / validated_length) + 0.5 * np.sin(
            3.0 * math.pi * x_q / validated_length
        )
        values = np.full(validated_num_samples, u0, dtype=np.float64)
    else:
        sol = heat_diffusion_dense_solution(
            alpha=validated_alpha,
            length=validated_length,
            t_max=t_max,
            num_points=count,
            rtol=validated_rtol,
            atol=validated_atol,
        )

        if np.max(t_j) > t_max:
            raise ValueError(
                f"max(t_j) = {np.max(t_j):.6e} exceeds t_max = {t_max:.6e}; "
                "integration window too small"
            )

        interior_all = sol.sol(t_j)  # shape (num_interior, num_samples)
        values = interior_all[interior_index, :]

    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1))
    stderr = std / math.sqrt(values.size)
    low, high = np.percentile(values, [2.5, 97.5])
    return HeatDiffusionUncertainty(
        alpha_relative_std=validated_alpha_relative_std,
        num_samples=int(values.size),
        seed=seed,
        mean=mean,
        std=std,
        stderr=stderr,
        interval_low=float(low),
        interval_high=float(high),
    )


def heat_diffusion_dense_solution(
    *,
    alpha: float,
    length: float,
    t_max: float,
    num_points: int,
    rtol: float = 1e-10,
    atol: float = 1e-12,
):
    r"""Return a ``solve_ivp`` solution with dense output over ``[0, t_max]``.

    This is used by the runtime for Monte Carlo uncertainty propagation: the
    PDE depends only on the product ``alpha * t``, so a single dense-output
    integration at ``alpha0`` can be interpolated at time
    ``t_j = alpha_j * t_q / alpha0`` for each sampled ``alpha_j``.

    Parameters
    ----------
    alpha:
        Diffusivity in m²/s. Must be finite and strictly positive.
    length:
        Domain length ``L`` in m. Must be finite and strictly positive.
    t_max:
        Final time in s for the dense-output integration. Must be finite and
        positive.
    num_points:
        Number of uniformly spaced grid points. Must be an odd integer at least
        3.
    rtol, atol:
        Relative and absolute solver tolerances. Both must be positive.

    Returns
    -------
    scipy.integrate.OdeSolution
        Dense-output solution whose ``sol(t)`` returns the interior state
        ``u_1 .. u_{N-2}`` at time ``t``.

    Raises
    ------
    TypeError, ValueError
        For invalid inputs (see ``simulate_heat_diffusion``).
    RuntimeError
        If the integration fails.
    """

    validated_alpha = require_positive_finite(alpha, "alpha")
    validated_length = require_positive_finite(length, "length")
    validated_t_max = require_finite_real(t_max, "t_max")
    if validated_t_max <= 0.0:
        raise ValueError(f"t_max must be positive, got {validated_t_max!r}")
    count = _validate_num_points(num_points, "num_points")
    validated_rtol = require_positive_finite(rtol, "rtol")
    validated_atol = require_positive_finite(atol, "atol")

    dx = validated_length / (count - 1)
    x = np.linspace(0.0, validated_length, count, dtype=np.float64)

    u0 = np.sin(math.pi * x / validated_length) + 0.5 * np.sin(3.0 * math.pi * x / validated_length)
    initial_state = u0[1:-1].copy()
    num_interior = count - 2

    rhs, jac = _build_rhs_and_jacobian(validated_alpha, dx, num_interior)

    return _integrate(
        rhs,
        jac,
        initial_state,
        (0.0, validated_t_max),
        None,
        dense_output=True,
        rtol=validated_rtol,
        atol=validated_atol,
    )
