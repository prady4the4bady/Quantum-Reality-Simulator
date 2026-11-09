# Heat Diffusion Domain Specification — QRS Phase 3

| Field | Value |
| --- | --- |
| Status | **Proposed — pending explicit approval. Not implemented.** |
| Scope | Specification only; no solver code, no tests, no runtime changes |
| Related | [System architecture](../architecture/SYSTEM_ARCHITECTURE.md), [Numerical methods](../scientific-methods/NUMERICAL_METHODS.md), [Scientific validation](../validation/SCIENTIFIC_VALIDATION.md), [Implementation roadmap](../roadmap/IMPLEMENTATION_ROADMAP.md), [Experiment runtime](../runtime/MANIFEST_SPEC.md) |

> This document is a **candidate specification**. It describes what the Phase 3
> heat-diffusion domain should compute once approved and implemented. It does
> not describe existing code. No implementation exists under
> `src/qrs/classical/heat_diffusion.py`, no tests exist, and no runtime
> registration exists yet. Nothing in this document may be treated as
> implemented behaviour until this spec is approved and the corresponding code,
> tests, and runtime integration are committed and validated.

## 1. Purpose

Phase 3 adds a second classical domain to demonstrate that the QRS foundation
generalises beyond the harmonic oscillator, using an independently derived
analytical reference and explicitly propagated parameter uncertainty.

The domain is the one-dimensional heat equation with homogeneous Dirichlet
boundaries. All validation is against the exact Fourier sine-series solution,
and uncertainty is propagated by Monte Carlo sampling of the diffusivity.

## 2. Equation, units, and domain of validity

### 2.1 Governing equation

The model solves

.. math::

    \frac{\partial u}{\partial t} = \alpha \frac{\partial^2 u}{\partial x^2},
    \qquad 0 < x < L, \quad t > 0,

with homogeneous Dirichlet boundary conditions

.. math::

    u(0,t) = 0, \qquad u(L,t) = 0,

and initial profile

.. math::

    u(x,0) = \sin\!\left(\frac{\pi x}{L}\right)
           + 0.5\,\sin\!\left(\frac{3\pi x}{L}\right).

### 2.2 Units

All quantities use SI units consistently.

| Quantity | Symbol | Unit |
| --- | --- | --- |
| Diffusivity | `\alpha` | metre squared per second (m²/s) |
| Length | `L` | metre (m) |
| Position | `x` | metre (m) |
| Time | `t` | second (s) |
| Temperature field | `u` | dimensionless (model normalised) |

### 2.3 Assumptions and validity

- `\alpha > 0` (positive, finite diffusivity).
- `L > 0` (positive, finite domain length).
- `t >= 0` (non-negative, finite simulation time).
- The initial profile satisfies the boundary conditions exactly
  (`u(0,0) = u(L,0) = 0`).
- Grid points `num_points >= 3` (at least one interior point).
- The problem is linear, parabolic, and stiff for fine grids; the proposed
  solver is an implicit method suitable for stiff systems.
- No heat sources, no time-varying diffusivity, no radiation or convection.

The domain of validity is `alpha > 0`, `L > 0`, `t >= 0`, `num_points >= 3`.
Inputs outside this range are rejected with a descriptive error (see
requirements HD-004–HD-007).

## 3. Exact reference solution

Separation of variables gives the exact Fourier sine-series solution

.. math::

    u(x,t) =
    e^{-\alpha (\pi/L)^2 t} \sin\!\left(\frac{\pi x}{L}\right)
    + 0.5\,e^{-9\alpha (\pi/L)^2 t} \sin\!\left(\frac{3\pi x}{L}\right).

Only the first two sine modes are present because the initial condition
contains only `n = 1` and `n = 3`. The first-mode decay rate is
`\alpha (\pi/L)^2` and the third-mode decay rate is `9\alpha (\pi/L)^2`.

This is an independently constructed analytical reference; the numerical
solver must reproduce it within the documented tolerances.

## 4. Requirement identifiers

| ID | Requirement |
| --- | --- |
| HD-001 | Solve `u_t = alpha * u_xx` on `0 < x < L` with zero Dirichlet boundaries. |
| HD-002 | Initial profile `sin(pi x/L) + 0.5*sin(3*pi x/L)`. |
| HD-003 | All quantities in SI units; diffusivity in m²/s, length in m, time in s. |
| HD-004 | Reject `alpha <= 0` or non-finite `alpha`. |
| HD-005 | Reject `L <= 0` or non-finite `L`. |
| HD-006 | Reject `t_end < 0` or non-finite `t_end`; require `t_end >= t_start` (with `t_start = 0`). |
| HD-007 | Require `num_points >= 3` (integer, booleans rejected). |
| HD-008 | Method of lines with second-order central differences in space. |
| HD-009 | Time integration with `solve_ivp` Radau, `rtol=1e-10`, `atol=1e-12`. |
| HD-010 | Constant sparse tridiagonal CSC Jacobian supplied to Radau. |
| HD-011 | Frozen slotted result dataclass; fail loudly (raise) on bad shape or non-finite output. |
| HD-012 | Strict validation via `qrs.core.validation` (`require_finite_real`, `require_positive_finite`). |
| HD-013 | Additive runtime registration of `heat_diffusion` in the manifest; `seed` made operational for Monte Carlo. |
| HD-014 | Uncertainty contract: `alpha ~ Normal`, relative standard deviation, `N` Monte Carlo samples from `numpy.random.default_rng(seed)`, report mean, standard deviation, and 95% interval at a chosen point and time. |
| HD-015 | Determinism: identical manifest and seed reproduce identical summaries. |

## 5. Proposed numerical method

- Spatial discretisation: second-order central differences on a uniform grid
  `x_i = i*dx`, `dx = L / (num_points - 1)`, `i = 0 .. num_points-1`.
- Interior unknowns: `u_1 .. u_{num_points-2}`; boundaries `u_0 = u_{num_points-1} = 0`
  enforced exactly at all times.
- Semi-discrete system: `du/dt = A*u` where `A = (alpha/dx²) * tridiag(1, -2, 1)`.
- Time integration: `scipy.integrate.solve_ivp(..., method="Radau", rtol=1e-10, atol=1e-12)`.
- Jacobian: constant sparse tridiagonal CSC matrix `(alpha/dx²) * tridiag(1, -2, 1)`
  of size `(num_points-2) x (num_points-2)`, supplied to `solve_ivp` via `jac`.
- Output: solution evaluated at `num_output_points` uniformly spaced times in
  `[0, t_end]`, including the boundaries as exact zero columns.
- Result: frozen slotted dataclass mirroring `HarmonicOscillatorResult`, with
  arrays `x`, `t`, `u` (shape `(num_output_points, num_points)`), exact-solution
  arrays, max error metrics, and solver metadata.

## 6. Default case and measured acceptance gates

The candidate default case (unapproved, unwritten) is:

| Parameter | Value |
| --- | --- |
| `alpha` | `1e-6` m²/s |
| `L` | `0.1` m |
| `t_end` | `600` s |
| `num_points` | `401` |
| `num_output_points` | `101` |
| `alpha_relative_std` | `0.05` |
| `seed` | `0` |
| `num_samples` | `10000` |

Derived: `dx = 2.5e-4` m, `lambda = (pi/L)^2 = 986.9604401089356 m^-2`,
first-mode decay rate `9.869604401089355e-4 s^-1`, discrete eigenvalue max
`64 s^-1`, stiffness ratio `64845.56`. Radau is required because the problem is
stiff.

### 6.1 Deterministic acceptance gates (measured scratch values)

These gates are based on measured scratch runs, not guesses. They are
candidates pending approval and implementation.

| Gate | Condition | Measured reference |
| --- | --- | --- |
| HD-G1 | Max abs error vs exact over `[0, t_end]` | `<= 1e-5` (measured `8.768433e-06` at `t = 114.0`) |
| HD-G2 | Error at `t_end` | `<= 2e-6` (measured `1.613656e-06`) |
| HD-G3 | `u(L/2, 600)` vs exact | diff `<= 2e-6` (measured `1.086219e-06`) |
| HD-G4 | Boundary max abs value | `== 0.0` (measured `0.0`) |
| HD-G5 | Initial profile max abs error | `<= 1e-12` (measured `3.062e-16`) |
| HD-G6 | Solution range | `min >= 0.0` and `max` finite (measured `min = 0.0`, `max = 1.075812584993856`) |

### 6.2 Spatial convergence (measured)

Second-order convergence in space, measured max error over time at
`num_output_points = 101`:

| N | Max abs error | Observed order |
| --- | --- | --- |
| 51 | `5.596093e-04` | — |
| 101 | `1.402979e-04` | `2.024706` |
| 201 | `3.507249e-05` | `2.014505` |
| 401 | `8.768433e-06` | `2.007161` |

Convergence at `t_end`:

| N | Max abs error at `t_end` | Observed order |
| --- | --- | --- |
| 51 | `1.034228e-04` | — |
| 101 | `2.581960e-05` | `2.030883` |
| 201 | `6.455170e-06` | `2.014362` |
| 401 | `1.613656e-06` | `2.007335` |

Acceptance: measured order in `[1.9, 2.1]` (near order 2).

### 6.3 First-mode decay (measured)

Projection onto the first sine mode at `N = 401`:
- max `|projection - exp(-alpha (pi/L)^2 t)|` = `1.683722e-06` at `t = 600`.
- `projection(600) = 0.5531239176363335` vs exact `0.5531222339142945`.
- measured rate `9.869553667292098e-4 s^-1` vs exact `9.869604401089355e-4 s^-1`
  (relative `-5.140408e-06`).
- discrete first-mode norm `0.1` (matches analytical normalisation).

Acceptance: relative rate error `<= 1e-4` (measured `5.140408e-06`).

### 6.4 Performance (informational, not a gate)

Sparse Jacobian timings at `N = 51/101/201/401`:
`0.309 / 0.354 / 0.344 / 0.429` s. Dense Jacobian at `N = 401`: `20.147` s,
max solution difference `4.55e-15`, identical `nfev = 2157`. The sparse Jacobian
is required for the default case to be viable in tests.

## 7. Uncertainty contract

### 7.1 Model

Diffusivity is uncertain:

.. math::

    \alpha \sim \mathrm{Normal}(\alpha_0,\;(\alpha_0 \cdot \alpha\_relative\_std)^2).

Candidate default: `\alpha_0 = 1e-6`, `\alpha_relative_std = 0.05`, so
`\sigma_\alpha = 5e-8`.

### 7.2 Monte Carlo procedure

- Draw `num_samples` samples `\alpha_j \sim \mathrm{Normal}(\alpha_0, \sigma_\alpha)`
  using `numpy.random.default_rng(seed)`.
- For each sample, evaluate the quantity of interest at the chosen point and
  time: `x_q = L/2 = 0.05 m`, `t_q = 600 s`.
- Quantity of interest (exact solution at `x_q`, since `sin(3*pi*x_q/L) =
  sin(3*pi/2) = -1`):

.. math::

    q(\alpha) = e^{-\alpha (\pi/L)^2 t_q} - 0.5\,e^{-9\alpha (\pi/L)^2 t_q}.

- Report the sample mean, sample standard deviation (`ddof=1`), and the
  central 95% interval (2.5th and 97.5th percentiles).

### 7.3 Exact reference moments (for gate setting)

At `x_q = L/2`, `t_q = 600`, `\alpha ~ N(1e-6, (5e-8)^2)`:

| Moment | Value |
| --- | --- |
| Exact mean | `0.5508541291876023` |
| Exact standard deviation | `0.01571695033833832` |
| Exact variance | `2.470225279377931e-04` |
| Cov(`E1`, `E3`) | `2.201001713660186e-05` |
| Nominal `q(1e-6)` | `0.5506991968905726` |

### 7.4 Measured Monte Carlo statistics (seed 0, 10000 samples)

| Statistic | Value |
| --- | --- |
| Sample mean | `0.5507541787161618` |
| Sample std (`ddof=1`) | `0.01569071843905818` |
| 95% interval | `[0.5205521758896328, 0.5820815851322452]` |
| Standard error of mean | `1.569072e-04` |
| Mean error vs exact | `-9.995e-05` |
| Min sampled `\alpha` | `8.050289134972830e-07` |

Cross-checked seeds 1 and 2 (10000 samples each) give means `0.551025...` and
`0.550653...`, standard deviations `0.015698...` and `0.015803...`, intervals
`[0.520922..., 0.581895...]` and `[0.520097..., 0.582128...]` — consistent
with sampling variation.

Acceptance: sample mean within `3` standard errors of exact mean; sample
std within `5%` of exact std; interval contains the nominal value
`q(1e-6) = 0.5506991968905726`.

## 8. Manifest and runner integration (additive)

Integration is strictly additive; no existing model is modified.

- Register `HEAT_DIFFUSION = "heat_diffusion"` in `SUPPORTED_MODEL_NAMES`.
- `ExperimentManifest.create` merges heat-diffusion defaults over the model's
  parameters and solver config (analogous to harmonic oscillator), so
  serialised manifests are self-contained:

  | Parameters | Default |
  | --- | --- |
  | `alpha` | `1e-6` |
  | `length` | `0.1` |
  | `t_end` | `600.0` |
  | `num_points` | `401` |
  | `num_output_points` | `101` |

  | Solver configuration | Default |
  | --- | --- |
  | `rtol` | `1e-10` |
  | `atol` | `1e-12` |

- Model-specific validation (`HD-004`–`HD-007`): `alpha` and `length`
  positive finite; `t_end` finite and `>= 0`; `num_points` integer `>= 3`;
  `num_output_points` integer `>= 2`; `rtol`/`atol` positive finite; unknown or
  missing keys rejected.
- `seed` becomes operational for heat diffusion: it seeds
  `numpy.random.default_rng(seed)` for the Monte Carlo uncertainty
  propagation. For existing models `seed` remains metadata only.
- `run_manifest` dispatches `heat_diffusion` to
  `simulate_heat_diffusion(...)` and returns a `ResultEnvelope`. Exceptions
  propagate unchanged; the runtime does not wrap, retry, or suppress them.
- `result_summary` records: `alpha`, `length`, `t_end`, `num_points`,
  `num_output_points`, `first_mode_decay_rate`, `max_abs_error`, `max_abs_error_t_end`,
  `u_mid_t_end`, `boundary_max`, `initial_profile_error`, `min_u`, `max_u`,
  `method`, plus uncertainty fields `uq_mean`, `uq_std`, `uq_interval_low`,
  `uq_interval_high`, `num_samples`, `seed`.
- Validation checks (analogous to section 6 of MANIFEST_SPEC):
  - `max_abs_error < 1e-5`;
  - `max_abs_error_t_end < 2e-6`;
  - boundary check passes.
- `check_reproducibility` compares summaries key by key under a documented
  tolerance; changing `seed` changes the Monte Carlo summary and therefore the
  reproducibility comparison (unlike existing models where `seed` is metadata).

## 9. Proposed tests

Tests must cover (mapped to requirement IDs):

- HD-001/HD-002/HD-008: analytic agreement within HD-G1/HD-G2 at the default
  case.
- HD-008/HD-010: spatial convergence near order 2 with measured rate
  (`[1.9, 2.1]`).
- HD-002: first-mode decay matching `exp(-alpha (pi/L)^2 t)` within relative
  `1e-4`.
- HD-001: boundary conditions exactly zero (`boundary_max == 0.0`).
- HD-004–HD-007: invalid inputs rejected (`TypeError`/`ValueError` with
  descriptive messages).
- HD-015: seed determinism — identical manifest and seed reproduce identical
  summaries.
- HD-013/HD-014: manifest round-trip (`to_dict`/`from_dict` preserves all
  heat-diffusion fields; `experiment_id` changes when content changes).
- HD-014: reproducibility — re-running the same manifest reproduces the
  uncertainty summary within tolerance; `seed` affects the result.
- HD-011: fail loudly on non-finite or bad-shape output (simulated by monkeypatch
  or direct constructor misuse).

## 10. Explicit non-claims and non-goals

- This specification does **not** claim any implementation exists.
- No code under `src/qrs/classical/heat_diffusion.py`, no tests, and no runtime
  registration exists yet.
- No claim of real-world predictive accuracy beyond the validated range.
- No parameter sweeps, batch execution, persistence, databases, dashboards, or
  AI-assisted experiment design.
- No modification of existing files under `src/qrs/classical`,
  `src/qrs/quantum`, `src/qrs/core`, or existing tests (additive runtime
  registration only).
- No weakening of tolerances, no suppression of warnings, no new dependencies
  (NumPy and SciPy only), no cloud APIs, no paid services, no new network calls.
- No bitwise portability claim across platforms; results run on Windows and
  Ubuntu CI.

## 11. Approval needed

This spec is a hard stop. Implementation (solver module, tests, runtime
registration, validation record) begins **only** after explicit approval of this
specification. On approval, the next steps are:

1. Implement `src/qrs/classical/heat_diffusion.py` (method of lines, Radau,
   sparse Jacobian, frozen result dataclass, strict validation).
2. Add tests under `tests/` covering section 9.
3. Additive runtime registration in `src/qrs/runtime/manifest.py`
   (`heat_diffusion` model, defaults, validation, `seed` operational).
4. Update `docs/scientific-methods/NUMERICAL_METHODS.md`,
   `docs/validation/SCIENTIFIC_VALIDATION.md`, and
   `docs/roadmap/IMPLEMENTATION_ROADMAP.md` to mark the domain implemented.
5. Run `.venv\Scripts\python.exe -m ruff check .`,
   `ruff format --check .`, `pytest tests -q`.
6. Commit locally only on `phase3-heat-diffusion`; no push, merge, PR, or
   history rewrite.
