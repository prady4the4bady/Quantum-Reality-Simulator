# QRS Roadmap

This is the summary roadmap. Detailed phases, prerequisites, and acceptance
criteria are in
[docs/roadmap/IMPLEMENTATION_ROADMAP.md](docs/roadmap/IMPLEMENTATION_ROADMAP.md).

## Status legend

- **Implemented** — present, tested, and validated in this repository.
- **Next** — the recommended next milestone.
- **Planned** — designed conceptually, not implemented.
- **Not started** — intentionally deferred.

## Phase summary

| Phase | Scope | Status |
| --- | --- | --- |
| 0 | Repository, branch, Python 3.12 environment, dependency pinning | Implemented |
| 1 | Classical harmonic oscillator and PennyLane Bell state, docs, tests, lint | Implemented |
| 2 | Experiment runtime: manifests, result envelopes, runner, reproducibility check | Implemented |
| 3 | Second classical domain with real reference data and uncertainty reporting | Implemented |
| 4 | Hybrid classical–quantum interface and noise-aware execution | Planned |
| 5 | Storage, provenance, and reproducibility layer | Planned |
| 6 | Visualisation and scenario comparison | Planned |
| 7 | AI-assisted orchestration, strictly outside the numerical path | Planned |
| 8 | Digital-twin mode and decision/design optimisation | Planned |
| 9 | Additional domains and cross-domain scenarios | Planned |

## Phase 1 acceptance criteria (met)

- Python 3.12.10 virtual environment inside the repository.
- Exact dependency pins recorded in `pyproject.toml`.
- Classical oscillator validated against its exact analytical solution.
- Bell state produced by a genuine PennyLane `default.qubit` circuit.
- Independent reference calculations for quantum correlations.
- Unit, scientific, and integration tests passing.
- Ruff lint and format checks passing.
- Package build validation passing.
- Documentation distinguishes implemented from planned features.
- Local commit only; no push, merge, or pull request.

## Phase 2 acceptance criteria (met)

- Frozen, slotted experiment manifest with `schema_version=1` and deterministic
  SHA-256 `experiment_id`.
- Canonical JSON with sorted keys, fixed separators, UTF-8, and rejection of
  NaN and infinity.
- Manifest validation rejects unknown models, unknown or missing fields, wrong
  types, non-finite numbers, and unsupported schema versions.
- Frozen result envelope containing manifest, scalar result summary,
  validation status and details, artefact references, and schema version.
- `run_manifest` dispatches `harmonic_oscillator` and `bell_state` to the
  existing Phase 1 physics functions and records measured error metrics without
  modifying physics code.
- `check_reproducibility` re-runs a manifest, compares summaries, and rejects
  seed or environment drift unless explicitly allowed.
- Runtime contract documented in
  [docs/runtime/MANIFEST_SPEC.md](docs/runtime/MANIFEST_SPEC.md).
- 249 Phase 2 tests passing; full suite 407 passing; Ruff lint and format
  checks clean.
- Local commit only; no push, merge, or pull request.

## Near-term priorities

1. Treat parameter sweeps and result persistence as explicit future runtime
   extensions; neither is implemented in Phase 2.
2. Keep the AI layer optional, local-first, and unable to alter numerical
   results.

## Phase 3 acceptance criteria (met)

- The domain passes the extension blueprint in
  [docs/architecture/SYSTEM_ARCHITECTURE.md](docs/architecture/SYSTEM_ARCHITECTURE.md).
- Uncertainty is quantified and propagated, not asserted.
- Results are compared with real or independently derived reference values.
- Invalid and out-of-range inputs are rejected.
- Documentation states the domain of validity.

**Delivered.** The heat-diffusion domain solves `u_t = alpha * u_xx` on
`0 < x < L` with zero Dirichlet boundaries and initial profile `sin(pi x/L) +
0.5*sin(3*pi x/L)`, using SI units. The solver uses method of lines with
second-order central differences, `solve_ivp` Radau with `rtol=1e-10`/`atol=1e-12`
(defaults; callers may override via the manifest), and a constant sparse
tridiagonal CSC Jacobian. Results are validated against
the exact analytical solution, and uncertainty is propagated through the
numerical solver via dense-output interpolation at `t_j = alpha_j * t_q / alpha0`.
Tests cover analytic agreement, spatial convergence near order 2, first-mode
decay, boundary conditions, invalid inputs, seed determinism, manifest
round-trip, reproducibility, and UQ agreement with exact moments.

**Evidence.**

- Specification: `docs/domains/HEAT_DIFFUSION_SPEC.md`
- Solver: `src/qrs/classical/heat_diffusion.py`
- Tests: `tests/unit/test_heat_diffusion.py`,
  `tests/scientific/test_heat_diffusion_scientific.py`
- Runtime registration: `src/qrs/runtime/manifest.py`,
  `src/qrs/runtime/runner.py` (additive; existing models unmodified)


## Explicit non-goals for implemented phases

- Simulating all eleven domains.
- Claiming real-world predictive accuracy.
- Parameter sweeps and batch experiment orchestration.
- Experiment persistence, databases, or result storage.
- Dashboards, visualisation, or user-interface work.
- GPU acceleration.
- Cloud or paid inference.
- Multi-user storage or collaboration.
