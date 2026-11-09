# Implementation Roadmap — QRS

| Field | Value |
| --- | --- |
| Status | Phases 0–2 implemented; Phase 3 next; Phases 4–9 planned |
| Basis | Summary [ROADMAP.md](../../ROADMAP.md) |
| Related | [Project brief](../requirements/PROJECT_BRIEF.md), [System architecture](../architecture/SYSTEM_ARCHITECTURE.md), [Scientific validation](../validation/SCIENTIFIC_VALIDATION.md), [Architectural decisions](../decisions/ARCHITECTURAL_DECISIONS.md) |

> This roadmap is not a schedule. No completion dates or delivery commitments
> are made. A phase begins only when its prerequisites are met and the previous
> phase has been accepted against explicit gates.

## 1. Status legend

- **Implemented** — present, tested, and validated in this repository.
- **Next** — the recommended next milestone.
- **Planned** — designed conceptually, not implemented.
- **Not started** — intentionally deferred.

## 2. Universal phase gates

Every phase, including Phase 2 and later, must satisfy the same gates before it
can be marked implemented:

| Gate | Requirement |
| --- | --- |
| G1 — Scope | Written scope, non-goals, and a statement of what remains unimplemented |
| G2 — Implementation | Deterministic core with validated inputs and explicit units or conventions |
| G3 — Reference | Comparison against an analytical, independently constructed, or observational reference |
| G4 — Error | Quantified error metrics and a justified tolerance; no unmeasured claims |
| G5 — Tests | Unit, scientific or validation, integration, invalid-input, and boundary tests |
| G6 — Tooling | Full pytest run, Ruff lint and format, and package install/build validation |
| G7 — Documentation | Status labels updated across the affected documents and a validation record |
| G8 — Git | Reviewed local commit; any push or pull request separately approved |

A phase that adds structure without validated behaviour does not pass these
gates. Domain count is not a success metric.

## 3. Phase 0 — repository and environment

**Status:** Implemented.

**Scope.** Establish the private repository, branch, Python runtime, and pinned
dependencies.

**Delivered.**

- Private repository `prady4the4bady/Quantum-Reality-Simulator` cloned locally.
- Branch `phase1-foundation` created and checked out.
- Repo-local `.venv` using Python `3.12.10`.
- Exact pins: NumPy `2.5.4`, SciPy `1.18.1`, PennyLane `0.45.1`, pytest
  `9.2.0`, Ruff `0.17.4`.
- `pyproject.toml` and `.gitignore` with build, cache, secret, and generated
  output exclusions.

**Evidence.** The environment and versions are recorded in
[SCIENTIFIC_VALIDATION.md](../validation/SCIENTIFIC_VALIDATION.md).

**Exit criteria (met).**

- `python --version` reports `3.12.10` inside `.venv`.
- `pip show` reports the pinned versions.
- No global configuration was modified.
- No credentials, tokens, or `.env` files exist in the repository.

## 4. Phase 1 — scientific foundation

**Status:** Implemented.

**Scope.** Two small scientific prototypes, shared validation, tests, lint,
documentation, and a local commit.

**Delivered.**

| Area | Deliverable | Evidence |
| --- | --- | --- |
| Classical | Harmonic oscillator `m*x'' + k*x = 0` with scientific analysis | `src/qrs/classical/harmonic_oscillator.py` |
| Quantum | Bell state prepared with `H` and `CNOT` on `default.qubit` | `src/qrs/quantum/bell_state.py` |
| Validation | Strict scalar and input validation | `src/qrs/core/validation.py` |
| Tests | Unit, scientific, integration | 93 parametrized cases passing |
| Examples | Two demonstrations and one smoke check | `examples/` |
| Lint | Ruff lint and format | All checks passed; 16 files formatted |
| Package | Editable install and wheel build | `qrs_simulator-0.1.0-py3-none-any.whl` |
| Documentation | Six categorized documents plus four root documents | `docs/` and repository root |

**Key measured results.** Default oscillator maximum absolute error
`2.0059931493676686e-10 m`; relative energy drift `4.0177161597654276e-10`;
Bell fidelity `0.9999999999999996`; CHSH `2.828427124746189`; purity
`0.4999999999999998`. The full evidence table is in
[SCIENTIFIC_VALIDATION.md](../validation/SCIENTIFIC_VALIDATION.md).

**Exit criteria (met).**

- Both prototypes execute on CPU and match independent references within
  justified tolerances.
- Invalid inputs are rejected with descriptive errors.
- Classical, quantum, integration, and full test runs pass.
- Ruff lint and format checks pass.
- The package installs and builds.
- Documentation distinguishes implemented from planned capability.
- A local commit records the foundation; nothing is pushed.

## 5. Phase 2 — experiment runtime

**Status:** Implemented.

**Goal.** Make experiments reproducible and comparable before adding scientific
domains. Phase 2 is infrastructure for trustworthy results, not new physics.

**Prerequisites.**

- Phase 1 accepted.
- Agreement on a minimal manifest and result-envelope schema.
- A decision on serialisation format and schema versioning.

**Delivered.**

| Area | Deliverable | Evidence |
| --- | --- | --- |
| Manifest | Frozen slotted `ExperimentManifest`, `schema_version=1`, deterministic SHA-256 `experiment_id` | `src/qrs/runtime/manifest.py` |
| Canonical JSON | Sorted keys, fixed separators, UTF-8, NaN and infinity rejected | `src/qrs/runtime/serialization.py` |
| Envelope | Frozen `ResultEnvelope` with manifest, scalar summary, validation status and details, artefact references | `src/qrs/runtime/envelope.py` |
| Runner | `run_manifest` dispatches `harmonic_oscillator` and `bell_state` to existing Phase 1 physics and records measured metrics | `src/qrs/runtime/runner.py` |
| Reproducibility | `check_reproducibility` re-runs a manifest, compares summaries, and rejects seed or environment drift unless allowed | `src/qrs/runtime/runner.py` |
| Validation | Rejects unknown models, unknown or missing fields, wrong types, non-finite numbers, and unsupported schema versions | `src/qrs/runtime/manifest.py` |
| Tests | 249 Phase 2 cases covering serialisation, manifests, envelopes, and integration | `tests/unit/`, `tests/integration/test_runtime.py` |
| Documentation | Implemented runtime contract | `docs/runtime/MANIFEST_SPEC.md` |
| Lint | Ruff lint and format checks | Clean for the repository |

**Scope delivered.**

1. Versioned experiment manifests containing the model identifier, validated
   parameters, solver configuration, environment, seed, and UTC creation
   timestamp.
2. Result envelopes containing the manifest, a flat scalar result summary,
   validation status, validation details, and artefact references.
3. Deterministic canonical serialisation and round-trip tests.
4. Manifest execution for both existing models without modifying physics code.
5. A reproducibility check that re-runs the same manifest and compares result
   summaries within a documented tolerance.
6. Rejection of malformed, incomplete, or version-incompatible manifests with
   descriptive errors.

**Explicitly deferred.**

- Parameter sweeps and batch experiment orchestration. The original Phase 2
  sketch included sweeps; they are not implemented and are not part of the
  accepted runtime contract.
- Persistence, databases, storage backends, and result-file writing.
- Schema migration beyond rejecting unsupported versions.
- New physical or quantum domains.
- Dashboards, plotting, or user interfaces.
- AI-assisted experiment design or explanation.
- Bitwise portability claims across platforms.

**Key measured results.** Both models run through `run_manifest` with validation
passing under their documented tolerances. The full suite reports `342 passed`
(93 Phase 1 cases plus 249 Phase 2 cases). Repeated manifests produce identical
summaries under the reproducibility check.

**Exit criteria (met).**

- A manifest round-trips without loss of validated parameters.
- Identifiers are deterministic and change when validated content changes.
- A result envelope round-trips and rejects incompatible schema versions.
- Re-running a manifest reproduces the recorded result within a documented
  tolerance.
- Invalid manifests fail with `TypeError` or `ValueError`, not silent fallback.
- Tests cover round-trip, deterministic identifiers, every rejection case,
  successful reproduction, tampered seed or environment failure, and
  integration.
- Full pytest and Ruff checks pass.
- Documentation states that manifests, envelopes, and reproducibility checks are
  implemented, while sweeps and persistence are not.
- A local commit records the runtime; nothing is pushed.

**Risks and limitations.**

- Over-designing storage before the schema is stable; no storage was added.
- Treating a manifest as a security boundary; it is an integrity record, not an
  authentication mechanism.
- Environment drift is rejected by default rather than silently tolerated.
- Only two deterministic models are supported; the seed does not change their
  numerical results.

## 6. Phase 3 — second classical domain

**Status:** Next.

**Goal.** Demonstrate that the foundation generalises beyond one equation,
using real reference data and explicit uncertainty.

**Prerequisites.**

- Phase 2 accepted.
- A domain selected on the basis of data availability, an independent
  reference, and a defensible validity range.
- A written model specification with units and assumptions.

**Scope (planned).**

- Implement one additional classical domain.
- Compare against real observations or an independently constructed reference.
- Report uncertainty rather than a single point estimate.
- Document calibration, validity limits, and failure modes.

**Out of scope.**

- Claiming real-world predictive accuracy beyond the validated range.
- Adding several domains at once.
- Domain-specific user interfaces.

**Acceptance gates.**

- The domain passes the extension blueprint in
  [SYSTEM_ARCHITECTURE.md](../architecture/SYSTEM_ARCHITECTURE.md).
- Uncertainty is quantified and propagated, not asserted.
- Results are compared with real or independently derived reference values.
- Invalid and out-of-range inputs are rejected.
- Documentation states the domain of validity.

**Open decision.** The second domain has not been selected. Selection is a
Phase 3 prerequisite, not an assumption of this roadmap.

## 7. Phase 4 — hybrid classical–quantum interface and noise-aware execution

**Status:** Planned.

**Goal.** Connect classical inputs to quantum circuits and represent noise and
sampling honestly.

**Prerequisites.**

- Phases 2 and 3 accepted.
- A documented interface contract between classical outputs and quantum inputs.
- A decision on noise models and shot policy.

**Scope (planned).**

- Define a typed interface for passing classical results into circuit
  parameters.
- Support shot-based execution in addition to analytic execution.
- Add configurable noise models on local simulators.
- Report statistical uncertainty from finite shots.
- Keep analytic and noisy results clearly distinguished.

**Out of scope.**

- Mandatory physical quantum hardware.
- GPU quantum backends.
- Error mitigation claims without measured evidence.
- Presenting noisy results as ideal statevector results.

**Acceptance gates.**

- Ideal and noisy paths are distinguishable in the result contract.
- Shot-based results include uncertainty and are reproducible under a recorded
  seed.
- Noise-model parameters are validated.
- No physical-hardware access is required for tests.
- Documentation does not claim hardware validation.

## 8. Phase 5 — storage, provenance, and reproducibility

**Status:** Planned.

**Goal.** Persist experiments and results with provenance sufficient to audit
and reproduce them.

**Prerequisites.**

- Phase 2 manifest and envelope schema accepted and versioned.
- A decision on storage technology and artefact layout.

**Scope (planned).**

- Local persistence of manifests, results, and referenced artefacts.
- Environment capture and content hashes.
- Schema migrations with explicit compatibility rules.
- Export and import round-trip tests.
- Clear separation between source data, generated data, and caches.

**Out of scope.**

- Multi-user access control, authentication, or collaboration.
- Mandatory cloud storage.
- Committing generated artefacts to Git.

**Acceptance gates.**

- Stored records can be located, loaded, and verified.
- Schema versions are explicit and migration behaviour is tested.
- Missing or corrupted artefacts are detected, not silently ignored.
- Storage is local-first; no external service is mandatory.

## 9. Phase 6 — visualisation and scenario comparison

**Status:** Planned.

**Goal.** Make validated results inspectable and comparable without turning
visuals into evidence.

**Prerequisites.**

- Phase 5 accepted.
- Stable result envelopes and artefact references.

**Scope (planned).**

- Plot displacement, velocity, energy, probabilities, and correlations from
  recorded results.
- Compare scenarios side by side with identical axes and documented units.
- Export figures with provenance metadata linking back to a manifest.
- Label ideal, noisy, and measured data distinctly.

**Out of scope.**

- A web application or multi-user dashboard.
- Decorative or unexplained visualisations.
- Plots generated from fabricated or unrecorded values.

**Acceptance gates.**

- Every figure traces to a manifest and result record.
- Axes, units, and uncertainty are labelled.
- Visual comparison does not replace numerical comparison.
- No UI framework is introduced merely to display results.

## 10. Phase 7 — AI-assisted orchestration

**Status:** Planned.

**Goal.** Offer optional assistance for experiment setup and explanation
without allowing a language model to produce scientific results.

**Prerequisites.**

- Phases 2–6 accepted.
- A decision on provider and local fallback.
- A written boundary between assistance and numerical execution.

**Scope (planned).**

- Optional natural-language help for constructing manifests and explaining
  recorded results.
- Strictly downstream of validated numerical outputs.
- Fully usable platform with AI disabled.
- Local-first default; no paid API required for core function.

**Out of scope.**

- AI-generated numerical values presented as measurements.
- AI inside `qrs.classical` or `qrs.quantum`.
- Mandatory network access or cloud inference.
- Autonomous modification of stored results.

**Acceptance gates.**

- Numerical outputs are identical with AI enabled and disabled.
- AI components cannot write to numerical result fields.
- Core tests run without network access or model availability.
- Assistance is labelled as explanation, not evidence.

## 11. Phase 8 — digital-twin mode and decision/design optimisation

**Status:** Planned.

**Goal.** Support calibrated scenario exploration and design optimisation on
top of validated models.

**Prerequisites.**

- A calibrated model with documented uncertainty and validity limits.
- Phase 5 provenance and Phase 6 comparison.
- A written statement of what the twin does and does not represent.

**Scope (planned).**

- State representation for a calibrated scenario.
- Parameter and design sweeps with explicit objectives and constraints.
- Uncertainty-aware comparison of candidate designs.
- Decision reports that cite their underlying manifests.

**Out of scope.**

- Claims of predictive accuracy outside the calibrated range.
- Safety-critical or regulated decision-making without domain validation.
- Real-time control of physical systems.

**Acceptance gates.**

- Optimisation objectives and constraints are explicit and validated.
- Results retain provenance and uncertainty.
- The twin is described as a model, not as the physical system.

## 12. Phase 9 — additional domains and cross-domain scenarios

**Status:** Planned.

**Goal.** Expand coverage only after the single-domain and hybrid foundations
are trusted.

**Prerequisites.**

- Phases 3–8 accepted as applicable.
- Each candidate domain passes the extension blueprint independently.

**Scope (planned).**

- Add further domains one at a time, each with its own reference and
  validation record.
- Define explicit coupling contracts for cross-domain scenarios.
- Report cross-domain uncertainty and dependency assumptions.

**Out of scope.**

- Reaching a target domain count for its own sake.
- Coupling domains without documented interfaces.
- Reusing tolerances from unrelated models.

**Acceptance gates.**

- Each domain independently satisfies the universal gates in Section 2.
- Cross-domain couplings have documented units, assumptions, and error
  propagation.
- No domain is described as implemented before its validation record exists.

## 13. Cross-phase non-goals

The following remain out of scope until a later, separately approved decision:

- simulating all eleven domains named in the wider specification;
- claiming real-world predictive accuracy without validation;
- GPU acceleration or CUDA-dependent libraries;
- paid APIs or mandatory cloud inference;
- user interfaces, web services, or collaboration features;
- committing credentials, generated artefacts, or caches;
- weakening tolerances, suppressing warnings, or skipping tests to obtain a
  green build;
- creating empty packages to signal future capability.

## 14. Sequencing rationale

Phase 2 precedes any new domain for three reasons:

1. **Schema stability.** Adding domains before the manifest and result envelope
   are stable would force repeated migrations.
2. **Reproducibility.** A second domain is only credible if its parameters,
   environment, and outputs can be recorded and replayed.
3. **Comparability.** Cross-domain work in later phases depends on a common
   result contract, not on ad hoc arrays.

Phase 3 precedes Phase 4 because hybrid work needs at least one classical model
with demonstrated uncertainty handling. Phase 7 is deliberately late: AI
assistance is only meaningful once there are validated results to explain.

## 15. Traceability

| Phase | Primary requirement source | Status |
| --- | --- | --- |
| 0 | FR-X1 (environment and pins) | Implemented |
| 1 | FR-C1–C9, FR-Q1–Q9, FR-X2–X6 | Implemented |
| 2 | Outcomes and gates in section 5; runtime contract in [MANIFEST_SPEC.md](../runtime/MANIFEST_SPEC.md) | Implemented |
| 3 | Requirements to be written before work starts | Next |
| 4–9 | Requirements to be written per phase | Planned |

Phase 3 and later requirement identifiers do not exist yet. This roadmap
defines outcomes and gates; it does not invent requirement numbers.

## 16. Change control

- Status changes require evidence, not intention. A phase moves to
  **Implemented** only when its acceptance gates are met and recorded.
- The summary [ROADMAP.md](../../ROADMAP.md) and this document must be updated
  together.
- Removing or reordering a phase requires a recorded decision in
  [ARCHITECTURAL_DECISIONS.md](../decisions/ARCHITECTURAL_DECISIONS.md).
- Implemented phases are not rewritten to look as if they were always planned;
  the history stays honest.
