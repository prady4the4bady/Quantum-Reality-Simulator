# Project Brief — Quantum Reality Simulator (QRS)

| Field | Value |
| --- | --- |
| Document status | Provisional; Phase 1 baseline |
| Source | Derived from the user-provided project specification |
| Repository | `prady4the4bady/Quantum-Reality-Simulator` (private) |
| Phase | 1 — scientific foundation |
| Date | 2026-11-08 |

> This brief is derived from the user-supplied specification for a
> multi-domain simulation platform. It is **not** derived from pre-existing
> repository content: the repository was created empty and contained no prior
> README, architecture document, or `Simulator.txt` file. Statements below are
> explicitly marked as implemented or planned.

## 1. Purpose

QRS is intended to become a local-first simulation platform that combines:

- classical numerical simulation of physical and human systems;
- genuine quantum-circuit simulation;
- domain-specific scientific models with explicit assumptions and units;
- reproducible experiment management;
- storage, comparison, and visualisation of results;
- optional AI assistance for experiment setup and explanation, never for
  producing numerical outcomes.

The long-term ambition is broad. Phase 1 deliberately reduces that ambition to
a small, rigorously validated foundation so that scientific quality is
demonstrated before scope is expanded.

## 2. Problem statement

Large simulation projects commonly fail in predictable ways:

1. **Scope inflation.** Many domains are scaffolded before any one model is
   validated.
2. **Simulation theatre.** Attractive interfaces or language-model output are
   presented as scientific evidence.
3. **Unstated assumptions.** Units, conventions, and validity ranges are left
   implicit.
4. **Unverified numerics.** Results are not compared with analytical or
   independently constructed references.
5. **Weak reproducibility.** Environments, parameters, and versions are not
   pinned.

QRS Phase 1 addresses these failure modes directly by implementing two small,
independently testable scientific prototypes with measured error and explicit
limitations.

## 3. Phase 1 objective

Establish a credible scientific and engineering foundation consisting of:

- one classical numerical model: the undamped, unforced harmonic oscillator
  `m*x'' + k*x = 0`, integrated with SciPy and validated against its exact
  analytical solution;
- one quantum model: the Bell state
  `|Phi+> = (|00> + |11>) / sqrt(2)`, prepared and measured with PennyLane on a
  CPU statevector device;
- a shared input-validation layer;
- documentation that separates implemented from planned capability;
- automated tests, linting, and package-build validation;
- a local Git commit on a dedicated branch, with no push.

## 4. Scope

### 4.1 In scope (Phase 1, implemented)

| Item | Description | Status |
| --- | --- | --- |
| Classical oscillator | `m*x'' + k*x = 0` with `m > 0`, `k > 0`, finite initial conditions | Implemented |
| Analytical reference | Closed-form displacement and velocity for the same initial conditions | Implemented |
| Energy accounting | `E = 0.5*m*v^2 + 0.5*k*x^2`, absolute and relative drift | Implemented |
| Configurable solver | SciPy `solve_ivp`, six methods, configurable tolerances and sample count | Implemented |
| Strict validation | Reject booleans, non-real types, NaN, infinity, non-positive mass/stiffness, invalid time spans | Implemented |
| Bell-state circuit | Hadamard on wire 0, CNOT control 0 target 1, analytic `default.qubit` execution | Implemented |
| State analysis | Statevector, basis probabilities, five Pauli correlations | Implemented |
| Entanglement analysis | Single-qubit reduced density matrix and purity | Implemented |
| CHSH evaluation | Four expectation terms and `S` under a documented convention | Implemented |
| Independent quantum reference | Explicit `(1, 0, 0, 1)/sqrt(2)` reference and fidelity | Implemented |
| Test suite | Unit, scientific, and integration tests | Implemented |
| Documentation | Requirements, architecture, methods, validation, decisions, roadmap | Implemented |
| Tooling | Exact dependency pins, Pytest configuration, Ruff lint and format | Implemented |

### 4.2 Out of scope (Phase 1, planned or deferred)

The following are **not implemented** and must not be described as working:

- the eleven simulation domains named in the wider specification;
- real-world data ingestion, source adapters, or dataset versioning;
- digital-twin state management;
- scenario, optimisation, or decision-support workflows;
- experiment persistence, databases, or run manifests;
- plotting, dashboards, or any user interface;
- web, desktop, or API services;
- multi-user access control or collaboration;
- GPU acceleration or CUDA-dependent libraries;
- noisy quantum hardware execution or error mitigation;
- AI-assisted orchestration or natural-language interfaces;
- any claim of real-world predictive accuracy.

## 5. Functional requirements (Phase 1)

### 5.1 Classical

- **FR-C1** — Integrate `m*x'' + k*x = 0` for constant `m > 0`, `k > 0`.
- **FR-C2** — Accept initial displacement and velocity in SI units.
- **FR-C3** — Accept a time span `(t_start, t_end)` with `t_end > t_start`.
- **FR-C4** — Evaluate at a user-specified number of uniformly spaced times,
  including both endpoints.
- **FR-C5** — Return numerical displacement, velocity, and total mechanical
  energy at every evaluation time.
- **FR-C6** — Return the analytical displacement and velocity for the same
  initial conditions.
- **FR-C7** — Return maximum absolute and relative displacement error, and
  maximum absolute and relative energy drift.
- **FR-C8** — Reject invalid physical inputs with descriptive `TypeError` or
  `ValueError` exceptions.
- **FR-C9** — Fail loudly with `RuntimeError` if integration fails, returns the
  wrong shape, or returns non-finite values.

### 5.2 Quantum

- **FR-Q1** — Prepare `|Phi+>` with `H` on wire 0 and `CNOT(0, 1)`.
- **FR-Q2** — Execute on PennyLane `default.qubit` analytically (no shots).
- **FR-Q3** — Derive probabilities from the returned statevector; never
  hardcode them.
- **FR-Q4** — Return the statevector, bitstrings, and basis probabilities.
- **FR-Q5** — Return `ZZ`, `XX`, `YY`, `ZX`, and `XZ` correlations.
- **FR-Q6** — Return the four CHSH terms and `S`.
- **FR-Q7** — Return the wire-0 reduced density matrix and its purity.
- **FR-Q8** — Return fidelity against an independently constructed reference.
- **FR-Q9** — Validate statevector shape, finiteness, and normalization before
  reporting results.

### 5.3 Cross-cutting

- **FR-X1** — Provide a repo-local virtual environment and exact dependency
  pins.
- **FR-X2** — Provide automated unit, scientific, and integration tests.
- **FR-X3** — Provide lint and formatting checks.
- **FR-X4** — Provide runnable examples and an end-to-end smoke check.
- **FR-X5** — Document implemented versus planned capability in every
  top-level document.
- **FR-X6** — Keep the numerical path independent of any language model.

## 6. Quality requirements

| Requirement | Target | Phase 1 evidence |
| --- | --- | --- |
| Analytical agreement (oscillator) | Maximum absolute error `< 1e-8 m` | `2.006e-10 m` |
| Energy conservation | Maximum relative drift `< 1e-8` | `4.018e-10` |
| Bell-state normalization | `abs(sum(p) - 1) < 1e-12` | `sum(p) = 0.9999999999999998` |
| Bell fidelity | `> 1 - 1e-12` | `0.9999999999999996` |
| CHSH violation | `S > 2` | `2.828427124746189` |
| Determinism | Repeated Bell runs identical | Statevector and CHSH identical |
| Test suite | All tests pass | 93 passed |
| Lint | Zero Ruff findings | All checks passed |
| Formatting | All files formatted | 16 files already formatted |

## 7. Constraints and operating rules

1. Python **3.12.x**, validated with **3.12.10**, in a repo-local `.venv`.
2. CPU only. No CUDA, GPU quantum backend, paid API, or mandatory cloud
   service.
3. No language model in the numerical path. The active coding model writes
   code and documentation; it does not generate scientific results.
4. No credentials, `.env` files, tokens, or private keys in the repository.
5. No global configuration changes and no administrator privileges.
6. Phase 1 is committed locally only. No push, merge, pull request, deletion,
   or force operation without separate explicit approval.
7. No empty placeholder packages. A module exists only when it has real,
   tested functionality.
8. Do not weaken tolerances, suppress warnings, or skip tests to obtain a green
   build.

## 8. Users and stakeholders

| Role | Interest |
| --- | --- |
| Project owner / developer-researcher | A trustworthy local foundation for further simulation work |
| Future contributor | Clear module boundaries, conventions, and validation bar |
| Reviewer | Reproducible commands and measured evidence, not claims |
| Prospective user | An honest statement of what does and does not work |

Phase 1 serves a single local developer. It provides no multi-user,
authentication, or service surface.

## 9. Success criteria

Phase 1 succeeds when all of the following are true:

- [x] The repository, branch, and environment are established as specified.
- [x] Both scientific prototypes execute successfully on CPU.
- [x] Both prototypes match independent references within justified
      tolerances.
- [x] Invalid inputs are rejected with descriptive errors.
- [x] Unit, scientific, and integration tests pass.
- [x] Ruff lint and format checks pass.
- [x] The package installs and builds.
- [x] Documentation distinguishes implemented from planned features.
- [x] A local commit records the foundation; nothing is pushed.

## 10. Assumptions

- The user-provided specification is the authority for long-term scope; this
  brief is a Phase 1 interpretation.
- SI units are used throughout the classical model.
- The harmonic oscillator is the ideal linear, undamped, unforced case. It is
  not a validated model of a specific real structure.
- The quantum simulation is an ideal statevector simulation without noise,
  decoherence, or sampling.
- `2*sqrt(2)` is the correct ideal CHSH value for `|Phi+>` under the documented
  measurement convention.
- PennyLane `default.qubit` uses big-endian basis ordering for the wire order
  `(0, 1)`.

## 11. Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Scope expands before the foundation is trusted | Low-quality breadth | Phase 1 implements only two validated prototypes |
| Results are mistaken for real-world predictions | Misleading conclusions | Documentation states limitations and non-goals |
| Floating-point differences across platforms | Fragile tests | Tolerances are measured and justified; no bitwise equality for floats |
| Dependency drift | Irreproducible results | Exact pins in `pyproject.toml` |
| Language model treated as a numerical authority | Fabricated results | AI is excluded from the numerical path |
| Accidental credential or artefact commit | Security exposure | `.gitignore`, manual diff review, no `.env` files |

## 12. Deliverables

- Working package `qrs-simulator` version `0.1.0`.
- `src/qrs` with `core`, `classical`, and `quantum` packages.
- `tests` with unit, scientific, and integration suites.
- `examples` with two demonstrations and one end-to-end smoke check.
- Six categorized documents under `docs/`, plus root `README.md`,
  `ARCHITECTURE.md`, `ROADMAP.md`, and `SECURITY.md`.
- `pyproject.toml` and `.gitignore`.
- A local commit on `phase1-foundation`.

## 13. Traceability

| Requirement group | Implementation | Evidence |
| --- | --- | --- |
| FR-C1 – FR-C9 | `src/qrs/classical/harmonic_oscillator.py` | `tests/unit/test_harmonic_oscillator.py`, `tests/scientific/test_harmonic_oscillator_scientific.py` |
| FR-Q1 – FR-Q9 | `src/qrs/quantum/bell_state.py` | `tests/unit/test_bell_state.py`, `tests/scientific/test_bell_state_scientific.py` |
| FR-X1 | `pyproject.toml`, `.venv` | Version output recorded in validation document |
| FR-X2 | `tests/` | 93 passed |
| FR-X3 | `pyproject.toml` Ruff configuration | Ruff clean |
| FR-X4 | `examples/` | Example and smoke-check output |
| FR-X5 | Root documents and `docs/` | This document set |
| FR-X6 | Architecture and source review | No AI or network imports in numerical modules |
