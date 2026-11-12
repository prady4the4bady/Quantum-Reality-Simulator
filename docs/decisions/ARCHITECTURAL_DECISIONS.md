# Architectural Decisions — QRS

| Field | Value |
| --- | --- |
| Status | Phase 1 baseline; decisions recorded from the implemented foundation |
| Scope | Decisions that constrain Phase 1 and near-term work |
| Date | 2026-11-08 |
| Related | [Project brief](../requirements/PROJECT_BRIEF.md), [System architecture](../architecture/SYSTEM_ARCHITECTURE.md), [Numerical methods](../scientific-methods/NUMERICAL_METHODS.md), [Scientific validation](../validation/SCIENTIFIC_VALIDATION.md), [Roadmap](../roadmap/IMPLEMENTATION_ROADMAP.md) |

> **Status legend**
> - **Accepted** — in force for the current codebase.
> - **Superseded** — replaced by a later decision.
> - **Proposed** — under consideration; not implemented.

This document records *why* the Phase 1 foundation looks the way it does. It is
not a changelog. Each decision states its context, the choice made, and the
consequences that follow. Decisions that were not made are listed as deferred
rather than presented as settled.

## Decision index

| ID | Decision | Status |
| --- | --- | --- |
| ADR-001 | Build on the existing private repository | Accepted |
| ADR-002 | Commit locally on `phase1-foundation`; no push | Accepted |
| ADR-003 | Python 3.12.10 in a repo-local `.venv` | Accepted |
| ADR-004 | Exact pins for direct dependencies | Accepted |
| ADR-005 | Limit Phase 1 to two validated prototypes | Accepted |
| ADR-006 | DOP853 as the default oscillator solver | Accepted |
| ADR-007 | Analytic PennyLane `default.qubit` execution | Accepted |
| ADR-008 | Big-endian wire and basis ordering | Accepted |
| ADR-009 | Explicit CHSH measurement convention | Accepted |
| ADR-010 | Immutable result objects as module contracts | Accepted |
| ADR-011 | Strict validation at the public boundary | Accepted |
| ADR-012 | No placeholder packages or modules | Accepted |
| ADR-013 | AI excluded from the numerical path | Accepted |
| ADR-014 | Categorized documentation with status labels | Accepted |
| ADR-015 | No licence selected in Phase 1 | Deferred |
| ADR-016 | Measured, justified tolerances; never weakened | Accepted |
| ADR-017 | Local-first, CPU-only execution | Accepted |

## ADR-001 — Build on the existing private repository

**Context.** The owner maintains the private repository
`prady4the4bady/Quantum-Reality-Simulator`. It was verified to be private and
empty before any local work began. Creating another repository would split the
project identity and risk divergent history.

**Decision.** Use the existing repository. Clone it with `gh repo clone` and
keep `origin` pointed at it. Do not create a second repository, and do not
overwrite pre-existing content — none existed at clone time.

**Consequences.**

- The project has one canonical remote.
- The GitHub CLI account was verified as `prady4the4bady` before cloning.
- No credentials are stored in the repository or printed in logs.
- If the remote is later found to contain unrelated work, this decision must be
  revisited before any push.

**Status update.** Local history shows four pull requests (#1–#4) merged as
merge commits into `main` (most recent: `494263a`, PR #4). The repository
`prady4the4bady/Quantum-Reality-Simulator` is public.

## ADR-002 — Commit locally on `phase1-foundation`; no push

**Context.** Phase 1 is a foundation milestone. Publishing it is a separate
decision from recording it.

**Decision.** Create and check out `phase1-foundation`. Record the foundation
in a single local commit with the message
`feat: establish QRS scientific foundation`. Do not push, merge, open a pull
request, delete branches, or force any operation without separate explicit
approval.

**Consequences.**

- The remote remains empty after Phase 1.
- The commit is reviewable locally with `git show` before any publication.
- The first push is a deliberate, separately approved action.
- History is linear because no merge is performed in this phase.

**Status update.** Local history shows four pull requests (#1–#4) merged as
merge commits into `main` (most recent: `494263a`, PR #4). Work is pushed and
merged via PRs rather than remaining local-only.

## ADR-003 — Python 3.12.10 in a repo-local `.venv`

**Context.** The scientific stack must run on Windows on the CPU. A
system-wide interpreter or a global environment would make results depend on
unrelated projects.

**Decision.** Use Python `3.12.10` through the Windows launcher (`py -3.12`)
and create `.venv` inside the repository. Declare
`requires-python = ">=3.12,<3.13"` in `pyproject.toml`. Do not modify global
Python configuration and do not require administrator privileges.

**Consequences.**

- The environment is disposable and reproducible from `pyproject.toml`.
- `.venv/` is ignored by Git.
- Python 3.13 and later are not claimed as supported in Phase 1.
- Recorded floating-point values are specific to the validated environment;
  they may differ in the last bits elsewhere.

## ADR-004 — Exact pins for direct dependencies

**Context.** Unpinned scientific libraries change numerical behaviour across
releases. Phase 1 needs an environment that can be reconstructed exactly.

**Decision.** Pin the direct dependencies exactly:

| Package | Version | Role |
| --- | --- | --- |
| NumPy | `2.5.4` | Arrays, linear algebra, independent quantum reference |
| SciPy | `1.18.1` | `solve_ivp` integration |
| PennyLane | `0.45.1` | Quantum circuit execution |
| pytest | `9.2.0` | Test runner (development extra) |
| Ruff | `0.17.4` | Lint and format checks (development extra) |

The pins live in `pyproject.toml`. Transitive dependencies are resolved by pip
from those pins.

**Consequences.**

- A fresh `.venv` can be rebuilt with `pip install -e ".[dev]"`.
- Transitive versions are not locked by a lockfile in Phase 1; this is a known
  reproducibility gap. Adding a lockfile is deferred.
- Upgrading any pin requires re-running the full validation suite and
  re-recording measured values.

## ADR-005 — Limit Phase 1 to two validated prototypes

**Context.** The wider specification names eleven simulation domains. Building
skeletons for all of them would demonstrate breadth but not scientific
credibility.

**Decision.** Implement exactly two independently testable prototypes:

1. the classical undamped, unforced harmonic oscillator `m*x'' + k*x = 0`;
2. the Bell state `|Phi+> = (|00> + |11>)/sqrt(2)` prepared with PennyLane.

Everything else is planned or explicitly out of scope.

**Consequences.**

- The eleven domains are not implemented and must not be described as working.
- No empty packages are created for future domains.
- Breadth is deferred until the foundation is trusted.

## ADR-006 — DOP853 as the default oscillator solver

**Context.** `scipy.integrate.solve_ivp` offers several methods. The default
choice affects accuracy, cost, and energy behaviour. The model is smooth and
non-stiff.

**Decision.** Default to `DOP853` with `rtol=1e-10` and `atol=1e-12`. Allow
`RK45`, `RK23`, `DOP853`, `Radau`, `BDF`, and `LSODA` through a validated
`method` parameter.

**Consequences.**

- The measured default-case error is `2.0059931493676686e-10 m` and the
  relative energy drift is `4.0177161597654276e-10`.
- BDF is available but is **not** the default: its measured relative energy
  drift on accuracy case B is `2.461695505559738e-08`, which exceeds the
  `1e-8` target. This is disclosed in the scientific validation record rather
  than hidden by loosening the check.
- The method-agreement test covers `RK45`, `DOP853`, and `Radau` only. RK23,
  BDF, and LSODA are accepted by the interface and were measured manually for
  the comparison table, but they are **not** covered by the Phase 1 automated
  scientific test suite. BDF's measured drift remains disclosed as above.
- Tolerances are explicit inputs, not implicit defaults inherited silently.

## ADR-007 — Analytic PennyLane `default.qubit` execution

**Context.** Phase 1 must demonstrate genuine circuit execution without GPU
drivers, cloud access, or sampling noise.

**Decision.** Use PennyLane `default.qubit` with wires `(0, 1)` and analytic
execution (no shots). Prepare the Bell state with `H(0)` followed by
`CNOT(0, 1)`. Derive probabilities from the returned statevector.

**Consequences.**

- Results are deterministic and exactly reproducible on the same platform.
- There is no shot noise, decoherence, hardware noise, or error mitigation.
- No GPU or CUDA dependency is introduced.
- The result is an ideal simulation, not a claim about a physical device.

## ADR-008 — Big-endian wire and basis ordering

**Context.** Multi-qubit statevectors have more than one common ordering
convention. Ambiguity here silently corrupts bitstring-based reasoning.

**Decision.** Fix wire order to `(0, 1)`. Use the basis order
`|00>, |01>, |10>, |11>`. The first character of each bitstring refers to
wire 0.

**Consequences.**

- Bitstring index `i` and statevector index `i` are aligned.
- The prepared state has amplitudes at indices `0` and `3`.
- Tests and documentation use this convention consistently.
- A different convention would require an explicit, documented conversion.

## ADR-009 — Explicit CHSH measurement convention

**Context.** CHSH values depend on how the measurement settings are defined.
Reporting only a number without the convention is not reproducible.

**Decision.** Define

- `B0 = (Z + X)/sqrt(2)`,
- `B1 = (Z - X)/sqrt(2)`,
- `S = E(Z,B0) + E(Z,B1) + E(X,B0) - E(X,B1)`.

For `|Phi+>`, the ideal value is `2*sqrt(2) ≈ 2.8284271247461903`.

**Consequences.**

- The measured value is `2.828427124746189` in the validated environment.
- A different sign convention can yield `-2*sqrt(2)` while representing the
  same physical violation; only the documented convention is claimed.
- The four expectation terms are returned alongside `S` so the value can be
  audited.

## ADR-010 — Immutable result objects as module contracts

**Context.** Callers need a stable, inspectable result shape rather than raw
arrays or tuples.

**Decision.** Return frozen dataclasses with `slots=True`:
`HarmonicOscillatorResult` and `BellStateResult`. Include parameters, arrays,
metadata, and error metrics.

**Consequences.**

- Attribute rebinding is rejected at runtime.
- NumPy array payloads remain mutable in place; "frozen" protects the result
  object, not the arrays. Callers must treat arrays as read-only.
- Adding a field is a contract change and requires documentation and tests.
- No serialisation format is defined in Phase 1.

## ADR-011 — Strict validation at the public boundary

**Context.** Silent coercion of booleans, NaN, or invalid time spans produces
misleading scientific output.

**Decision.** Validate before computation. Reject booleans, non-real scalar
types, NaN, infinity, non-positive mass or stiffness, malformed or
non-increasing time spans, non-positive sample counts, and unsupported solver
methods. Use `TypeError` for wrong types, `ValueError` for invalid values, and
`RuntimeError` for backend contract failures.

**Consequences.**

- Errors name the offending parameter.
- Validation is centralized in `qrs.core.validation` and reused by both
  domains.
- Backend failures are distinguished from user input errors.
- The public functions do not silently clamp, coerce, or guess.

## ADR-012 — No placeholder packages or modules

**Context.** Empty scaffolding creates the appearance of capability without
behaviour.

**Decision.** Create a package or module only when it contains real, tested
functionality. Phase 1 contains only `qrs.core`, `qrs.classical`, and
`qrs.quantum`.

**Consequences.**

- `experiments/`, `validation/`, `utils/`, `ai/`, `storage/`, and
  `visualisation/` do not exist in Phase 1.
- Documentation describes them as planned or absent by design.
- Future phases must add functionality and tests together, not structure alone.

## ADR-013 — AI excluded from the numerical path

**Context.** Language models are useful for explanation and workflow, but
their output is not a measurement or a numerical authority.

**Decision.** No AI call, network request, or model-generated value belongs in
`qrs.classical` or `qrs.quantum`. Numerical results come only from NumPy,
SciPy, and PennyLane. Any future AI layer is optional, local-first, and
downstream of validated results.

**Consequences.**

- The package works fully offline.
- An AI layer cannot alter, invent, or substitute numerical outcomes.
- Phase 1 contains no AI code at all.
- Tests do not depend on model availability or external services.

## ADR-014 — Categorized documentation with status labels

**Context.** A single large document mixes requirements, design, evidence, and
plans, making it easy to mistake intention for implementation.

**Decision.** Maintain six categorized documents under `docs/`:

| Category | Document |
| --- | --- |
| Requirements | [PROJECT_BRIEF.md](../requirements/PROJECT_BRIEF.md) |
| Architecture | [SYSTEM_ARCHITECTURE.md](../architecture/SYSTEM_ARCHITECTURE.md) |
| Scientific methods | [NUMERICAL_METHODS.md](../scientific-methods/NUMERICAL_METHODS.md) |
| Validation | [SCIENTIFIC_VALIDATION.md](../validation/SCIENTIFIC_VALIDATION.md) |
| Decisions | this document |
| Roadmap | [IMPLEMENTATION_ROADMAP.md](../roadmap/IMPLEMENTATION_ROADMAP.md) |

Root `README.md`, `ARCHITECTURE.md`, `ROADMAP.md`, and `SECURITY.md` are short
entry points that link to the detailed documents.

**Consequences.**

- Every document marks features as implemented, planned, or absent by design.
- Measured values are recorded once in the validation document and referenced
  elsewhere.
- Documentation changes that alter claims require re-checking the evidence.

## ADR-015 — No licence selected in Phase 1

**Context.** Choosing a licence is an owner decision with legal consequences.
The repository is public and has no external contributors.

**Decision.** Do not add a licence file in Phase 1. State the absence
explicitly in the README.

**Consequences.**

- Default copyright applies; the project is not offered under an open-source
  licence.
- Redistribution or external use should wait until a licence is chosen.
- A future licence decision must be recorded in this document and in the
  README.

**Status update.** A `LICENSE` file now exists in the repository root.
Copyright (c) 2026 Pradyun Kumar Sinha; all rights reserved; no licence or
permission of any kind is granted. The file is proprietary and confidential.
The repository is public; whether this changes any access assumptions could
not be verified from local data alone.

## ADR-016 — Measured, justified tolerances; never weakened

**Context.** A green test suite obtained by loosening thresholds is not
evidence of correctness.

**Decision.** Choose tolerances from the model, the solver, and independently
measured behaviour. Record the justification. Do not weaken tolerances,
suppress warnings, or skip tests to make a build pass.

**Consequences.**

- The oscillator accuracy target is `< 1e-8 m`; measured default error is
  `2.0059931493676686e-10 m`.
- The energy target is relative drift `< 1e-8`; measured default drift is
  `4.0177161597654276e-10`.
- Bell normalization uses `< 1e-12`; measured sum is `0.9999999999999998`.
- A failure is investigated and reported, not masked.
- Environment-specific failures require an explicit decision, not a quiet
  threshold change.

## ADR-017 — Local-first, CPU-only execution

**Context.** The project must remain usable on the owner's Windows machine
without paid services, GPU drivers, or mandatory cloud inference.

**Decision.** Run all numerical and quantum work on the local CPU. Use only
NumPy, SciPy, and PennyLane. No CUDA libraries, GPU backends, telemetry, paid
APIs, or mandatory network calls.

**Consequences.**

- The package works offline after installation.
- No GPU quantum backend is supported in Phase 1.
- Performance is bounded by the local CPU; this is acceptable for the two
  small prototypes.
- Future optional services must remain optional and outside the core path.

## Deferred decisions

The following are deliberately unresolved. They must be decided before the
phase that depends on them:

| Topic | Needed by | Current state |
| --- | --- | --- |
| Result serialisation format | Phase 2 | Resolved (implemented; canonical JSON, `schema_version=1`) |
| Experiment manifest schema and versioning | Phase 2 | Resolved (implemented; `ExperimentManifest`, deterministic SHA-256 `experiment_id`) |
| Lockfile for transitive dependencies | Phase 2 or earlier | Not present |
| Choice of second classical domain | Phase 3 | Resolved (heat diffusion implemented; see `docs/domains/HEAT_DIFFUSION_SPEC.md`) |
| Noise model and shot policy | Phase 4 | Not designed |
| Storage technology and artefact layout | Phase 5 | Not selected |
| Visualisation stack | Phase 6 | Not selected |
| AI provider and local fallback | Phase 7 | Not selected |
| Licence | Before any public distribution | Not selected |
