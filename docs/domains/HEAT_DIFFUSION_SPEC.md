# Heat Diffusion Domain Specification — QRS Phase 3

| Field | Value |
| --- | --- |
| Status | **Implemented** (merged via PR #2 at commit bcbb04541eb20a259b36537353325c273fb3d28b; follow-up fixes merged via PR #3 at commit dd4aa2f370caf6e1834896fc038e0d629f09c207) |
| Scope | Solver, tests, runtime registration, and documentation |
| Related | [System architecture](../architecture/SYSTEM_ARCHITECTURE.md), [Numerical methods](../scientific-methods/NUMERICAL_METHODS.md), [Scientific validation](../validation/SCIENTIFIC_VALIDATION.md), [Implementation roadmap](../roadmap/IMPLEMENTATION_ROADMAP.md), [Experiment runtime](../runtime/MANIFEST_SPEC.md) |

This document describes the implemented Phase 3 heat-diffusion domain. The
solver lives at `src/qrs/classical/heat_diffusion.py`, tests at
`tests/unit/test_heat_diffusion.py` and
`tests/scientific/test_heat_diffusion_scientific.py`, and runtime registration
at `src/qrs/runtime/manifest.py` and `src/qrs/runtime/runner.py`.

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

$$
\frac{\partial u}{\partial t} = \alpha \frac{\partial^2 u}{\partial x^2},
\qquad 0 < x < L, \quad t > 0,
$$

with homogeneous Dirichlet boundary conditions

$$
u(0,t) = 0, \qquad u(L,t) = 0,
$$

and initial profile

$$
u(x,0) = \sin\!\left(\frac{\pi x}{L}\right)
       + 0.5\,\sin\!\left(\frac{3\pi x}{L}\right).
$$

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
- Grid points `num_points` must be an odd integer `>= 3` (so that `L/2` lies exactly on a grid point).
- The problem is linear, parabolic, and stiff for fine grids; the proposed
  solver is an implicit method suitable for stiff systems.
- No heat sources, no time-varying diffusivity, no radiation or convection.

The domain of validity is `alpha > 0`, `L > 0`, `t >= 0`, `num_points` an odd integer `>= 3`.
Inputs outside this range are rejected with a descriptive error (see
requirements HD-004–HD-007).

## 3. Exact reference solution

Separation of variables gives the exact Fourier sine-series solution

$$
u(x,t) =
e^{-\alpha (\pi/L)^2 t} \sin\!\left(\frac{\pi x}{L}\right)
+ 0.5\,e^{-9\alpha (\pi/L)^2 t} \sin\!\left(\frac{3\pi x}{L}\right).
$$

Only the first two sine modes are present because the initial condition
contains only `n = 1` and `n = 3`. The first-mode decay rate is
`\alpha (\pi/L)^2` and the third-mode decay rate is `9\alpha (\pi/L)^2`.

This is an independently constructed analytical reference; the numerical
solver must reproduce it within the documented tolerances.

## 4. Spatial discretisation error bound

The semi-discrete operator uses second-order central differences:

$$
\frac{du_i}{dt} = \frac{\alpha}{dx^2}\left(u_{i-1} - 2u_i + u_{i+1}\right),
\qquad dx = \frac{L}{N-1},
$$

where `N = num_points`. For sine mode `n` with wavenumber `k = n\pi/L`, the
discrete eigenvalue is

$$
\lambda_n^{\text{disc}} = -\frac{2\alpha}{dx^2}\left(1 - \cos(k\,dx)\right).
$$

Using `1 - cos(z) = z^2/2 - z^4/24 + O(z^6)`,

$$
\lambda_n^{\text{disc}}
= -\alpha k^2\left(1 - \frac{(k\,dx)^2}{12} + O((k\,dx)^4)\right).
$$

So the **relative rate error** for mode `n` is

$$
\varepsilon_k = \frac{(k\,dx)^2}{12} + O((k\,dx)^4).
$$

The numerical solution decays slightly more slowly than the exact one:

$$
u_n^{\text{num}}(t) \approx u_n^{\text{exact}}(t)\,
\exp\!\left(\alpha k^2 t\,\varepsilon_k\right)
\approx u_n^{\text{exact}}(t)\left(1 + \alpha k^2 t\,\varepsilon_k\right).
$$

For the candidate default case (`\alpha = 1e-6`, `L = 0.1`, `t_end = 600`,
`N = 401`, `dx = 2.5e-4`), the dominant mode is `n = 1`:

- `k = \pi/L = 31.4159 m^{-1}`, `k dx = 0.007854`
- `\varepsilon_k = (0.007854)^2 / 12 = 5.1404e-6` (matches the measured
  relative rate error `-5.140408e-06`)
- `\alpha k^2 t_end = 0.592176`
- Peak relative error `\approx 0.592176 \times 5.1404e-6 = 3.04e-6`
- Peak absolute error at `x = L/2` `\approx 0.5507 \times 3.04e-6 = 1.68e-6`
  (matches the measured `1.683722e-06`)

Because `\varepsilon_k \propto dx^2`, the peak error scales as `dx^2`, which
is why acceptance thresholds HD-G1–HD-G3 are expressed as absolute bounds and
why the runner's validation thresholds in Section 8 scale with `dx^2` times a
safety factor.

## 5. Requirement identifiers

| ID | Requirement |
| --- | --- |
| HD-001 | Solve `u_t = alpha * u_xx` on `0 < x < L` with zero Dirichlet boundaries. |
| HD-002 | Initial profile `sin(pi x/L) + 0.5*sin(3*pi x/L)`. |
| HD-003 | All quantities in SI units; diffusivity in m²/s, length in m, time in s. |
| HD-004 | Reject `alpha <= 0` or non-finite `alpha`. |
| HD-005 | Reject `L <= 0` or non-finite `L`. |
| HD-006 | Reject `t_end < 0` or non-finite `t_end`; require `t_end >= t_start` (with `t_start = 0`). |
| HD-007 | Require `num_points` an odd integer `>= 3` (booleans rejected). |
| HD-008 | Method of lines with second-order central differences in space. |
| HD-009 | Time integration with `solve_ivp` Radau, `rtol=1e-10`, `atol=1e-12`. |
| HD-010 | Constant sparse tridiagonal CSC Jacobian supplied to Radau. |
| HD-011 | Frozen slotted result dataclass; fail loudly (raise) on bad shape or non-finite output. |
| HD-012 | Strict validation via `qrs.core.validation` (`require_finite_real`, `require_positive_finite`). |
| HD-013 | Additive runtime registration of `heat_diffusion` in the manifest; `seed` made operational for Monte Carlo. |
| HD-014 | Uncertainty contract: `alpha ~ Normal`, relative standard deviation, `N` Monte Carlo samples from `numpy.random.default_rng(seed)`, report mean, standard deviation, and 95% interval at a chosen point and time. |
| HD-015 | Determinism: identical manifest and seed reproduce identical summaries. |

## 6. Numerical method

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

## 7. Default case and measured acceptance gates

The default case is:

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

### 7.1 Deterministic acceptance gates

These gates are based on measured scratch runs, not guesses.

| Gate | Condition | Measured reference |
| --- | --- | --- |
| HD-G1 | Max abs error vs exact over `[0, t_end]` | `<= 1e-5` (measured `8.768433e-06` at `t = 114.0`) |
| HD-G2 | Error at `t_end` | `<= 2e-6` (measured `1.613656e-06`) |
| HD-G3 | `u(L/2, 600)` vs exact | diff `<= 2e-6` (measured `1.086219e-06`) |
| HD-G4 | Boundary max abs value | `== 0.0` (measured `0.0`) |
| HD-G5 | Initial profile max abs error | `<= 1e-12` (measured `3.062e-16`) |
| HD-G6 | Solution range | `min >= -1e-12` and `max` finite (measured `min = 0.0`, `max = 1.075812584993856`) |

HD-G1–HD-G3 follow from the `dx^2` error bound in Section 4: at `N = 401` the
peak absolute error is bounded by approximately `1.68e-6`, comfortably within
the `1e-5` / `2e-6` / `2e-6` limits.

### 7.2 Spatial convergence (measured)

Second-order convergence in space. Observed order is computed as

$$
\text{order} = \frac{\log(e_{\text{coarse}} / e_{\text{fine}})}
{\log(dx_{\text{coarse}} / dx_{\text{fine}})},
\qquad dx = \frac{L}{N-1}.
$$

Measured max error over time at `num_output_points = 101`:

| N | dx (m) | Max abs error | Observed order |
| --- | --- | --- | --- |
| 51 | `2.000000e-03` | `5.596093e-04` | — |
| 101 | `1.000000e-03` | `1.402979e-04` | `1.99543` |
| 201 | `5.000000e-04` | `3.507249e-05` | `2.00004` |
| 401 | `2.500000e-04` | `8.768433e-06` | `1.99997` |

Measured error at `t_end`:

| N | dx (m) | Max abs error at `t_end` | Observed order |
| --- | --- | --- | --- |
| 51 | `2.000000e-03` | `1.034228e-04` | — |
| 101 | `1.000000e-03` | `2.581960e-05` | `2.002016` |
| 201 | `5.000000e-04` | `6.455170e-06` | `1.999939` |
| 401 | `2.500000e-04` | `1.613656e-06` | `2.000123` |

Acceptance: measured order in `[1.9, 2.1]` (near order 2).

### 7.3 First-mode decay (measured)

Projection onto the first sine mode at `N = 401`:
- max `|projection - exp(-alpha (pi/L)^2 t)|` = `1.683722e-06` at `t = 600`.
- `projection(600) = 0.5531239176363335` vs exact `0.5531222339142945`.
- measured rate `9.869553667292098e-4 s^-1` vs exact `9.869604401089355e-4 s^-1`
  (relative `-5.140408e-06`).
- discrete first-mode norm `0.1` (matches analytical normalisation).

Acceptance: relative rate error `<= 1e-4` (measured `5.140408e-06`).

### 7.4 Performance (informational, not a gate)

Sparse Jacobian timings at `N = 51/101/201/401`:
`0.309 / 0.354 / 0.344 / 0.429` s. Dense Jacobian at `N = 401`: `20.147` s,
max solution difference `4.55e-15`, identical `nfev = 2157`. The sparse Jacobian
is required for the default case to be viable in tests.

## 8. Uncertainty contract

### 8.1 Model

Diffusivity is uncertain:

$$
\alpha \sim \mathrm{Normal}(\alpha_0,\;(\alpha_0 \cdot \alpha\_relative\_std)^2).
$$

Candidate default: `\alpha_0 = 1e-6`, `\alpha_relative_std = 0.05`, so
`\sigma_\alpha = 5e-8`. The allowed range is `0 < alpha_relative_std <= 0.15`;
larger values make a non-positive sampled alpha likely with 10000 samples, so
the run raises at runtime (HD-004). Any sampled `\alpha <= 0` is rejected
before the solver is called (no filtering).

### 8.2 Solver-based Monte Carlo propagation (primary)

The PDE depends only on the product `\alpha t`, so

$$
u(\alpha_j, x_q, t_q) = u(\alpha_0, x_q, t_j),
\qquad t_j = \alpha_j \frac{t_q}{\alpha_0}.
$$

Procedure:

1. Run `solve_ivp` **once** at `\alpha_0` with dense output over
   `[0, t_max]` where `t_max = max(1.25 * t_end, max(t_j))`, so every `t_j`
   is inside the integration window.
2. Draw `num_samples` samples `\alpha_j \sim \mathrm{Normal}(\alpha_0, \sigma_\alpha)`
   using `numpy.random.default_rng(seed)`; reject any `\alpha_j <= 0`.
3. For each sample, evaluate `t_j = \alpha_j * t_q / \alpha_0` and interpolate
   the dense solution at `(x_q, t_j)` with `x_q = L/2 = 0.05 m`, `t_q = 600 s`.
4. Report the sample mean, sample standard deviation (`ddof=1`), the standard
   error of the mean, and the central 95% interval (2.5th and 97.5th
   percentiles).

### 8.3 Interpolation-error gate

The interpolation error is measured by comparing the interpolated dense-output
value against the exact solution at each sampled `t_j`:

| Gate | Condition | Measured reference |
| --- | --- | --- |
| HD-G7 | Max interpolation error vs exact at sampled times | `<= 2e-6` (measured `1.505806e-06`) |

The integration window `t_max = max(1.25 * t_end, max(t_j))` covers all sampled
`t_j`.

### 8.4 Analytic reference UQ (comparison only)

The closed-form quantity of interest at `x_q = L/2` (since
`sin(3*pi*x_q/L) = sin(3*pi/2) = -1`) is

$$
q(\alpha) = e^{-\alpha (\pi/L)^2 t_q} - 0.5\,e^{-9\alpha (\pi/L)^2 t_q}.
$$

Its exact lognormal moments are computed analytically and used **only** to
cross-check the solver-based Monte Carlo; they are not the reported result.

At `x_q = L/2`, `t_q = 600`, `\alpha ~ N(1e-6, (5e-8)^2)`:

| Moment | Value |
| --- | --- |
| Exact mean | `0.5508541291876023` |
| Exact standard deviation | `0.01571695033833832` |
| Exact variance | `2.470225279377931e-04` |
| Cov(`E1`, `E3`) | `2.201001713660186e-05` |
| Nominal `q(1e-6)` | `0.5506991968905726` |

### 8.5 Measured Monte Carlo statistics (seed 0, 10000 samples, solver-based)

| Statistic | Value |
| --- | --- |
| Sample mean | `0.5507552509129310` |
| Sample std (`ddof=1`) | `0.01569055194620832` |
| Standard error of mean | `1.569055e-04` |
| 95% interval | `[0.5205535308353868, 0.5820822860582533]` |
| Mean error vs exact | `-9.9878e-05` |
| Min sampled `\alpha` | `8.050289134972830e-07` |

Acceptance: solver-based mean within `4` standard errors of the exact mean;
solver-based std within `5%` of the exact std; the 95% interval contains the
nominal value `q(1e-6) = 0.5506991968905726`.

Cross-checked seeds 1 and 2 (10000 samples each) give consistent results within
sampling variation.

## 9. Manifest and runner integration (additive)

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
  positive finite; `t_end` finite and `>= 0`; `num_points` an odd integer `>= 3`;
  `num_output_points` integer `>= 2`; `alpha_relative_std` in `(0, 0.15]`;
  `num_samples` integer `>= 2`; `rtol`/`atol` positive finite; unknown or
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
  `method`, plus uncertainty fields `uq_mean`, `uq_std`, `uq_stderr`, `uq_interval_low`,
  `uq_interval_high`, `num_samples`, `seed`.
- Validation thresholds use the analytic error bound from Section 4 with a
  documented safety factor of `1.5`. For initial sine modes n=1 (amplitude 1)
  and n=3 (amplitude 0.5):

      eps_n = (n * pi / (N - 1))**2 / 12
      bound = sum(a_n * eps_n) * exp(-1)
      threshold = 1.5 * bound

  so coarse grids are not wrongly marked failed:

  | Check | Pass condition |
  | --- | --- |
  | `max_abs_error` | `< 1.5 * bound` |
  | `max_abs_error_t_end` | `< 1.5 * bound` |
  | `boundary_max` | `== 0.0` |

  The bound scales as `dx^2` and relaxes quadratically for coarser grids.
- `check_reproducibility` compares summaries key by key under a documented
  tolerance; changing `seed` changes the Monte Carlo summary and therefore the
  reproducibility comparison (unlike existing models where `seed` is metadata).

## 10. Proposed tests

Tests must cover (mapped to requirement IDs):

- HD-001/HD-002/HD-008: analytic agreement within HD-G1/HD-G2 at the default
  case.
- HD-008/HD-010: spatial convergence near order 2 with measured rate
  (`[1.9, 2.1]`) computed from `dx = L/(N-1)`.
- HD-002: first-mode decay matching `exp(-alpha (pi/L)^2 t)` within relative
  `1e-4`.
- HD-001: boundary conditions exactly zero (`boundary_max == 0.0`).
- HD-004–HD-007: invalid inputs rejected (`TypeError`/`ValueError` with
  descriptive messages); sampled `alpha <= 0` raises.
- HD-015: seed determinism — identical manifest and seed reproduce identical
  summaries.
- HD-013/HD-014: manifest round-trip (`to_dict`/`from_dict` preserves all
  heat-diffusion fields; `experiment_id` changes when content changes).
- HD-014: reproducibility — re-running the same manifest reproduces the
  uncertainty summary within tolerance; `seed` affects the result.
- HD-011: fail loudly on non-finite or bad-shape output (simulated by monkeypatch
  or direct constructor misuse).
- A coarse grid (`N = 51`) must pass validation (scaled thresholds).
- UQ via the solver must agree with the exact moments within `4` standard errors.

## 11. Explicit non-claims and non-goals

- This specification describes the implemented domain; the code, tests, and
  runtime registration all exist.
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

## 12. Implementation status

The domain is implemented (merged via PR #2 at commit bcbb04541eb20a259b36537353325c273fb3d28b; follow-up fixes merged via PR #3 at commit dd4aa2f370caf6e1834896fc038e0d629f09c207).

Implementation summary:

1. `src/qrs/classical/heat_diffusion.py` — method of lines, Radau
   (rtol=1e-10, atol=1e-12), sparse Jacobian, frozen result dataclass,
   strict validation, dense-output solver for UQ, `propagate_uncertainty()`.
2. `tests/unit/test_heat_diffusion.py` and
   `tests/scientific/test_heat_diffusion_scientific.py` — cover section 10.
3. `src/qrs/runtime/manifest.py` — `heat_diffusion` model, defaults,
   validation, `seed` operational for Monte Carlo.
4. `src/qrs/runtime/runner.py` — dispatch, summary, analytic-bound validation
   thresholds.
5. `docs/scientific-methods/NUMERICAL_METHODS.md`,
   `docs/validation/SCIENTIFIC_VALIDATION.md`, and
   `docs/roadmap/IMPLEMENTATION_ROADMAP.md` updated to mark the domain
   implemented.
6. `.venv\Scripts\python.exe -m ruff check .`, `ruff format --check .`,
   `pytest tests -q` all pass.
7. The domain was merged via PR #2 (merge commit bcbb04541eb20a259b36537353325c273fb3d28b) and follow-up fixes via PR #3 (merge commit dd4aa2f370caf6e1834896fc038e0d629f09c207).
