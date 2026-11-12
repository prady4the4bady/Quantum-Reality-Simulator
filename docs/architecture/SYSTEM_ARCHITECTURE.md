# System Architecture — QRS Phases 1–3

| Field | Value |
| --- | --- |
| Status | Phases 1–3 implemented |
| Scope | Implemented foundation and experiment runtime plus planned layers |
| Related | [Project brief](../requirements/PROJECT_BRIEF.md), [Numerical methods](../scientific-methods/NUMERICAL_METHODS.md), [Runtime specification](../runtime/MANIFEST_SPEC.md), [Decisions](../decisions/ARCHITECTURAL_DECISIONS.md) |

> **Status legend**
> - **Implemented** — present in this repository, tested, and validated.
> - **Planned** — designed conceptually, not implemented.
> - **Absent by design** — intentionally not created in the implemented phases.

## 1. Architectural goals

1. **Scientific correctness before breadth.** A small number of validated models
   is preferred to a large skeleton of unvalidated ones.
2. **Deterministic, local execution.** Numerical results come from NumPy, SciPy,
   and PennyLane running on the local CPU.
3. **Explicit contracts.** Each model returns an immutable result object with
   parameters, arrays, metadata, and error metrics.
4. **Strict boundaries.** Domain code does not depend on storage, UI, or AI
   code. The AI layer can never compute or mutate numerical results.
5. **Reproducibility.** Dependencies are pinned, versions are recorded, and
   commands are documented.
6. **Honest documentation.** Implemented and planned capability are labelled
   separately in every relevant document.

## 2. System context

```text
                        +-----------------------------+
                        |  Developer / researcher    |
                        +--------------+--------------+
                                       |
                                       | local commands
                                       v
+-----------------------------------------------------------------------+
|                        QRS local workspace                            |
|                                                                       |
|  +-------------------+    +-------------------+    +---------------+  |
|  | Classical engine  |    | Quantum engine    |    | Examples and  |  |
|  | SciPy / NumPy     |    | PennyLane / NumPy |    | smoke checks  |  |
|  +---------+---------+    +---------+---------+    +-------+-------+  |
|            |                        |                      |          |
|            +------------+-----------+----------------------+          |
|                         v                                             |
|              +--------------------------+                             |
|              | Immutable result objects |                             |
|              +------------+-------------+                             |
|                           |                                           |
|              +------------v-------------+                             |
|              | Implemented: experiment  |                             |
|              | runtime (manifests,      |                             |
|              | envelopes, checks)       |                             |
|              +------------+-------------+                             |
|                           |                                           |
|              +------------v-------------+                             |
|              | Planned: storage,        |                             |
|              | provenance, visualisation|                             |
|              +--------------------------+                             |
+-----------------------------------------------------------------------+
        |                                                    |
        | optional, never in the numerical path               | planned
        v                                                    v
+-------------------+                              +-------------------+
| AI explanation    |                              | External data     |
| (planned)         |                              | sources (planned) |
+-------------------+                              +-------------------+
```

Phase 1 implemented the oscillator and Bell-state engines, the shared
validation module, the result objects, the examples, and the test suite.
Phase 2 adds the experiment runtime: canonical manifests, result envelopes,
manifest execution, and reproducibility checks. Phase 3 adds the heat-diffusion
engine. Everything downstream of the runtime — persistence, storage,
visualisation, and external data — is planned.

## 3. Layered architecture

### 3.1 Implemented layers

```text
+---------------------------------------------------------------+
| Presentation and tooling (examples, CLI-style scripts)        |
| examples/classical_harmonic_oscillator.py                     |
| examples/bell_state.py                                        |
| examples/verify_foundation.py                                 |
+-------------------------------+-------------------------------+
                                |
+-------------------------------v-------------------------------+
| Experiment runtime                                            |
| qrs.runtime.serialization   canonical JSON                    |
| qrs.runtime.manifest        ExperimentManifest                |
| qrs.runtime.envelope        ResultEnvelope                    |
| qrs.runtime.runner          run_manifest, check_reproducibility|
+-------------------------------+-------------------------------+
                                |
+-------------------------------v-------------------------------+
| Domain modules                                                |
| qrs.classical.harmonic_oscillator                             |
| qrs.classical.heat_diffusion                                  |
| qrs.quantum.bell_state                                        |
+-------------------------------+-------------------------------+
                                |
+-------------------------------v-------------------------------+
| Shared core                                                   |
| qrs.core.validation                                           |
+-------------------------------+-------------------------------+
                                |
+-------------------------------v-------------------------------+
| Scientific libraries                                          |
| NumPy 2.5.4 | SciPy 1.18.1 | PennyLane 0.45.1                |
+---------------------------------------------------------------+
```

### 3.2 Planned layers

| Layer | Responsibility | Depends on | Status |
| --- | --- | --- | --- |
| Domain models | Geopolitics, economics, climate, weather, physics, chemistry, biology, engineering, materials, human systems, transportation, hypothetical scenarios | `core`, NumPy, SciPy | Planned |
| Data ingestion | Source adapters, provenance, schema validation, versioned datasets | `core`, domain schemas | Planned |
| Parameter sweeps | Batch manifests, scenario comparison, aggregated summaries | `runtime`, domain models | Planned |
| Storage | Run metadata, result arrays, dataset and artefact references | Experiment runtime | Planned |
| Visualisation | Plots, dashboards, interactive comparison | Storage, result objects | Planned |
| AI orchestration | Experiment setup assistance and natural-language explanation | Storage, result objects | Planned |

## 4. Module inventory

### 4.1 Implemented modules

| Path | Responsibility | Public API |
| --- | --- | --- |
| `src/qrs/__init__.py` | Package identity and scope statement | `__version__` |
| `src/qrs/core/validation.py` | Strict scalar validation | `require_finite_real`, `require_positive_finite` |
| `src/qrs/classical/harmonic_oscillator.py` | Classical model, integration, analytical reference, metrics | `simulate_harmonic_oscillator`, `HarmonicOscillatorResult` |
| `src/qrs/classical/heat_diffusion.py` | Classical heat diffusion, integration, analytical reference, metrics, Monte Carlo uncertainty | `simulate_heat_diffusion`, `propagate_uncertainty`, `heat_diffusion_dense_solution`, `HeatDiffusionResult`, `HeatDiffusionUncertainty` |
| `src/qrs/quantum/bell_state.py` | Bell-state circuit, device execution, correlations, CHSH, purity, fidelity | `simulate_bell_state`, `BellStateResult` |
| `src/qrs/runtime/serialization.py` | Canonical JSON and immutable scalar mappings | `canonical_json_dumps`, `freeze_scalar_mapping` |
| `src/qrs/runtime/manifest.py` | Manifest schema, environment capture, deterministic identifier | `ExperimentManifest`, `capture_environment` |
| `src/qrs/runtime/envelope.py` | Immutable result envelope and nested manifest verification | `ResultEnvelope` |
| `src/qrs/runtime/runner.py` | Manifest dispatch, result summaries, validation, reproducibility | `run_manifest`, `check_reproducibility` |
| `examples/classical_harmonic_oscillator.py` | Human-readable oscillator run | `main()` |
| `examples/bell_state.py` | Human-readable Bell-state run | `main()` |
| `examples/verify_foundation.py` | End-to-end smoke check with non-zero exit on failure | `main()` |
| `tests/unit/` | Interface, validation, runtime contract, and serialisation tests | Pytest |
| `tests/scientific/` | Agreement with analytical or independent references | Pytest |
| `tests/integration/` | All three domains and the runtime exercised together | Pytest |

### 4.2 Absent by design

- `src/qrs/experiments/` — the runtime lives in `qrs.runtime`; no separate
  experiments package, parameter-sweep engine, or persistence layer exists.
- `src/qrs/validation/` — scientific validation lives in `tests/scientific`;
  runtime validation lives in `qrs.runtime.runner`.
- `src/qrs/utils/` — generic dumping grounds are prohibited; helpers belong to
  the module that owns them.
- `src/qrs/ai/`, `src/qrs/storage/`, `src/qrs/visualisation/` — planned, not
  scaffolded.
- Web, desktop, or API entry points — not part of the implemented phases.

## 5. Dependency rules

1. `qrs.core` depends only on the Python standard library.
2. `qrs.classical` may depend on `qrs.core`, NumPy, and SciPy.
3. `qrs.quantum` may depend on `qrs.core`, NumPy, and PennyLane.
4. `qrs.runtime` may depend on `qrs.core`, `qrs.classical`, `qrs.quantum`, and
   the Python standard library. It must not reimplement physics, and it must
   not import AI, network, UI, or storage libraries.
5. `qrs.classical` and `qrs.quantum` must not import each other. A hybrid
   interface, when introduced, must be an explicit new module.
6. No numerical module may import an AI client, network client, UI framework,
   or storage backend.
7. Storage and visualisation consume result objects; they do not re-implement
   scientific equations.
8. The AI layer may read validated results and metadata. It must not compute,
   alter, or fabricate numerical outcomes.
9. Tests may import public APIs and, where necessary, module-private constants
   for convention checks. Tests must not depend on implementation details that
   are not part of the documented contract.

### 5.1 Dependency graph (implemented)

```text
examples/*  --->  qrs.classical  --->  qrs.core
     |                 |
     |                 +------------> numpy, scipy
     |
     +---------->  qrs.quantum   --->  qrs.core
                       |
                       +------------> numpy, pennylane

qrs.runtime  --->  qrs.classical
     |        --->  qrs.quantum
     |        --->  qrs.core
     +------------>  Python standard library
```

There is no edge from `qrs.classical` to `qrs.quantum` or vice versa. The
runtime calls the existing public physics functions and does not modify them.

## 6. Data flow

### 6.1 Classical oscillator

```text
keyword arguments
      |
      v
validation (mass, stiffness, initial conditions, time span,
            sample count, method, tolerances)
      |
      v
first-order system  x' = v,  v' = -(k/m) x
      |
      v
scipy.integrate.solve_ivp(method=DOP853 by default, t_eval=uniform grid)
      |
      +------------------------------+
      |                              |
      v                              v
numerical x(t), v(t)          analytical x(t), v(t)
      |                              |
      +--------------+---------------+
                     |
                     v
energy history, absolute/relative errors, energy drift
                     |
                     v
immutable HarmonicOscillatorResult
```

### 6.2 Bell state

```text
PennyLane device: default.qubit(wires=(0, 1))
      |
      v
H(0); CNOT(0, 1)
      |
      +--> qml.state() ----------> statevector (4 amplitudes)
      +--> qml.expval(...) ------> Pauli correlations and CHSH terms
      +--> qml.density_matrix([0]) -> reduced density matrix
      |
      v
shape, finiteness, normalization checks
      |
      v
probabilities = |amplitude|^2
purity        = Tr(rho_0^2)
fidelity      = |<reference|state>|^2
      |
      v
immutable BellStateResult
```

## 7. Result contracts

### 7.1 `HarmonicOscillatorResult`

Frozen dataclass with `slots=True`. All arrays are `numpy.float64` and share
the shape of the requested time grid.

| Field | Meaning |
| --- | --- |
| `mass`, `stiffness` | Validated model parameters |
| `angular_frequency` | `sqrt(k/m)` |
| `initial_displacement`, `initial_velocity` | Validated initial conditions |
| `initial_energy` | `0.5*k*x0^2 + 0.5*m*v0^2` |
| `time` | Uniform evaluation times including both endpoints |
| `displacement`, `velocity` | Numerical solution |
| `energy` | Total mechanical energy at each time |
| `analytic_displacement`, `analytic_velocity` | Exact reference |
| `max_abs_displacement_error` | `max(abs(x_num - x_exact))` |
| `max_relative_displacement_error` | `max_abs_error / max(abs(x_exact))` |
| `max_abs_energy_drift` | `max(abs(E(t) - E(0)))` |
| `max_relative_energy_drift` | `max_abs_energy_drift / E(0)` |
| `method` | SciPy method used |

### 7.2 `BellStateResult`

Frozen dataclass with `slots=True`.

| Field | Meaning |
| --- | --- |
| `statevector` | Complex device state, ordered `|00>, |01>, |10>, |11>` |
| `probabilities` | `abs(amplitude)^2`, index-aligned with `bitstrings` |
| `bitstrings` | `("00", "01", "10", "11")`; character 0 is wire 0 |
| `zz_correlation`, `xx_correlation`, `yy_correlation`, `zx_correlation`, `xz_correlation` | Device-measured Pauli correlations |
| `e_z_b0`, `e_z_b1`, `e_x_b0`, `e_x_b1` | CHSH expectation terms |
| `chsh_value` | `E(Z,B0) + E(Z,B1) + E(X,B0) - E(X,B1)` |
| `reduced_density_matrix` | Wire-0 reduced state, shape `(2, 2)` |
| `purity` | `Tr(rho_0^2)` |
| `reference_statevector` | Independent `(1,0,0,1)/sqrt(2)` |
| `fidelity` | `|<reference|state>|^2` |
| `wire_order` | `(0, 1)` |

## 8. Error handling strategy

| Condition | Exception | Rationale |
| --- | --- | --- |
| Wrong type, boolean supplied as a scalar | `TypeError` | Type errors are programming errors |
| Non-finite physical parameter | `ValueError` | NaN/infinity are invalid values |
| Non-positive mass or stiffness | `ValueError` | Outside the model's domain |
| `t_span` malformed or non-increasing | `TypeError` / `ValueError` | Invalid integration interval |
| Unsupported solver method | `ValueError` with the allowed set | Actionable message |
| Solver failure | `RuntimeError` | Environmental or numerical failure, not bad input |
| Device returns wrong shape or non-finite data | `RuntimeError` | Contract violation by the backend |
| Device state not normalized | `RuntimeError` | Scientific integrity check |
| Malformed manifest field or unknown field | `TypeError` / `ValueError` | Invalid schema or value |
| Unsupported manifest or envelope schema version | `ValueError` | No silent migration exists |
| `experiment_id` does not match manifest content | `ValueError` | Detects tampering or stale identifiers |
| Recorded and current environments differ | `RuntimeError` | Reproduction would not be like-for-like |
| Manifest run or reproducibility check fails validation | `RuntimeError` | A failed validation is not a valid result |

Validation is performed before expensive computation. Errors include the
offending parameter name so callers can act without inspecting a traceback.

## 9. Determinism and reproducibility

- The classical model is deterministic for identical inputs, versions, and
  platform floating-point behaviour.
- The Bell-state circuit is analytic and deterministic. The integration test
  asserts that repeated runs return identical statevectors and CHSH values.
- Both the harmonic oscillator and the Bell-state models are deterministic, so
  `seed` is non-negative metadata and does not affect their numerical results.
  For `heat_diffusion`, `seed` seeds `numpy.random.default_rng(seed)` for the
  Monte Carlo diffusivity sampling, so changing it changes the `uq_*` summary
  values.
- `ExperimentManifest` records the model, validated parameters, solver
  configuration, seed, creation timestamp, and exact environment versions for
  Python, NumPy, SciPy, PennyLane, QRS, and the platform.
- `experiment_id` is a SHA-256 digest of canonical JSON over the schema version,
  model, parameters, solver configuration, seed, and environment. `created_at`
  and the identifier itself are excluded from the hash.
- Canonical JSON uses sorted keys, fixed separators, UTF-8, and rejects NaN and
  infinity. The same manifest content produces the same bytes and identifier.
- `check_reproducibility` re-runs a manifest and compares result summaries.
  Numeric values must agree within an absolute tolerance; non-numeric values
  must match exactly.
- Environment drift is rejected by default. `allow_environment_drift=True`
  skips only that comparison; identifier integrity and summary comparison still
  apply.
- Exact dependency pins are recorded in `pyproject.toml`.
- Python `3.12.x` is required; validation used `3.12.10`.
- Platform: Windows, CPU only. The code itself is platform-neutral, but measured
  floating-point results can differ in the last bits across platforms, so
  reproduction across environments is not claimed.
- `experiment_id` is an integrity identifier, not an authentication signature.

The detailed contract is in
[MANIFEST_SPEC.md](../runtime/MANIFEST_SPEC.md).

## 10. Security boundary

The implemented phases have no network service, authentication, authorisation,
database, or file upload surface. The runtime writes no result files and no
persistence layer exists. The security boundary is therefore the local process
and the repository contents:

- no credentials or `.env` files are committed;
- no telemetry or cloud calls;
- no AI or network imports in numerical or runtime modules;
- manifests and envelopes are not signed and are not an authentication or
  authorisation mechanism;
- no GPU or CUDA requirement;
- no administrator privileges required.

See [SECURITY.md](../../SECURITY.md).

## 11. Extension blueprint

A new domain module is accepted only when it provides:

1. A documented equation or model with explicit units.
2. Validated inputs with justified physical ranges.
3. A deterministic numerical or quantum engine.
4. An analytical, independently constructed, or observational reference.
5. Quantified error metrics and justified tolerances.
6. Tests covering valid, invalid, boundary, convergence, and determinism
   behaviour.
7. A statement of assumptions and domain of validity.
8. Documentation that marks the module as implemented, not planned.

A module that cannot satisfy these conditions is not merged merely to increase
domain count.

## 12. Runtime interfaces (implemented)

`ExperimentManifest` and `ResultEnvelope` are frozen, slotted dataclasses with
`schema_version=1`.

```text
ExperimentManifest
  experiment_id   deterministic SHA-256 identifier
  schema_version  1
  model_name      harmonic_oscillator | bell_state | heat_diffusion
  parameters      immutable scalar mapping
  solver_config   immutable scalar mapping
  seed            non-negative integer metadata
  created_at      UTC timestamp, format YYYY-MM-DDTHH:MM:SSZ
  environment     python, numpy, scipy, pennylane, qrs, platform

ResultEnvelope
  schema_version  1
  manifest        ExperimentManifest
  result_summary  immutable flat scalar mapping
  validation_status   passed | failed
  validation_details  statuses, counts, and check names
  artefacts       tuple of relative POSIX paths; currently empty
```

`run_manifest` dispatches the supported model names to the existing Phase 1
physics functions and records measured metrics. No physics code is modified or
reimplemented. `check_reproducibility` re-runs the manifest and compares result
summaries under a documented tolerance.

No parameter sweep, batch runner, storage backend, database, or result-file
writer exists. Envelope artefact paths are a forward-compatible reference field,
not evidence that artefacts were produced. The authoritative contract is
[MANIFEST_SPEC.md](../runtime/MANIFEST_SPEC.md).

## 13. Architectural constraints on future work

- Do not add a domain without a reference implementation and tests.
- Do not put AI calls inside `qrs.classical` or `qrs.quantum`.
- Do not introduce a web framework merely to display results.
- Do not create empty packages for future domains.
- Do not weaken tolerances to accommodate a new environment.
- Do not make any external service mandatory for core simulation.
- Do not commit generated artefacts, caches, or credentials.
