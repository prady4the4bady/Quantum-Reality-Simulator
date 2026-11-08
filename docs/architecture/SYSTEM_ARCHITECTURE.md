# System Architecture — QRS Phase 1

| Field | Value |
| --- | --- |
| Status | Phase 1 baseline |
| Scope | Implemented foundation plus planned layers |
| Related | [Project brief](../requirements/PROJECT_BRIEF.md), [Numerical methods](../scientific-methods/NUMERICAL_METHODS.md), [Decisions](../decisions/ARCHITECTURAL_DECISIONS.md) |

> **Status legend**
> - **Implemented** — present in this repository, tested, and validated.
> - **Planned** — designed conceptually, not implemented.
> - **Absent by design** — intentionally not created in Phase 1.

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

Phase 1 implements the two engines, the shared validation module, the result
objects, the examples, and the test suite. Everything downstream of the result
objects is planned.

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
| Domain modules                                                |
| qrs.classical.harmonic_oscillator                               |
| qrs.quantum.bell_state                                         |
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
| Experiment runtime | Parameter sweeps, scenarios, reproducible manifests | Domain models, `core` | Planned |
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
| `src/qrs/quantum/bell_state.py` | Bell-state circuit, device execution, correlations, CHSH, purity, fidelity | `simulate_bell_state`, `BellStateResult` |
| `examples/classical_harmonic_oscillator.py` | Human-readable oscillator run | `main()` |
| `examples/bell_state.py` | Human-readable Bell-state run | `main()` |
| `examples/verify_foundation.py` | End-to-end smoke check with non-zero exit on failure | `main()` |
| `tests/unit/` | Interface, validation, and contract tests | Pytest |
| `tests/scientific/` | Agreement with analytical or independent references | Pytest |
| `tests/integration/` | Both prototypes exercised together | Pytest |

### 4.2 Absent by design

- `src/qrs/experiments/` — no experiment runtime exists yet.
- `src/qrs/validation/` — scientific validation lives in `tests/scientific`;
  a separate runtime validation package has no real content yet.
- `src/qrs/utils/` — generic dumping grounds are prohibited; helpers belong to
  the module that owns them.
- `src/qrs/ai/`, `src/qrs/storage/`, `src/qrs/visualisation/` — planned, not
  scaffolded.
- Web, desktop, or API entry points — not part of Phase 1.

## 5. Dependency rules

1. `qrs.core` depends only on the Python standard library.
2. `qrs.classical` may depend on `qrs.core`, NumPy, and SciPy.
3. `qrs.quantum` may depend on `qrs.core`, NumPy, and PennyLane.
4. `qrs.classical` and `qrs.quantum` must not import each other. A hybrid
   interface, when introduced, must be an explicit new module.
5. No numerical module may import an AI client, network client, UI framework,
   or storage backend.
6. Storage and visualisation consume result objects; they do not re-implement
   scientific equations.
7. The AI layer may read validated results and metadata. It must not compute,
   alter, or fabricate numerical outcomes.
8. Tests may import public APIs and, where necessary, module-private constants
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
```

There is no edge from `qrs.classical` to `qrs.quantum` or vice versa.

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

Validation is performed before expensive computation. Errors include the
offending parameter name so callers can act without inspecting a traceback.

## 9. Determinism and reproducibility

- The classical model is deterministic for identical inputs, versions, and
  platform floating-point behaviour.
- The Bell-state circuit is analytic and deterministic. The integration test
  asserts that repeated runs return identical statevectors and CHSH values.
- Random seeds are not used in Phase 1. No sampling or shot noise is involved.
- Exact dependency pins are recorded in `pyproject.toml`.
- Python `3.12.x` is required; validation used `3.12.10`.
- Platform: Windows, CPU only. The code itself is platform-neutral, but measured
  floating-point results can differ in the last bits across platforms.

## 10. Security boundary

Phase 1 has no network service, authentication, authorisation, database, or
file upload surface. The security boundary is therefore the local process and
the repository contents:

- no credentials or `.env` files are committed;
- no telemetry or cloud calls;
- no AI or network imports in numerical modules;
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

## 12. Planned interfaces (not implemented)

The following are sketches only. They do not exist in the codebase.

```text
ExperimentManifest
  parameters
  environment (python, packages, platform)
  seed
  model identifier
  created_at

ResultEnvelope
  manifest reference
  model result object
  validation status
  artefact references (plots, arrays, reports)
```

These names are illustrative. No schema, serialisation format, or storage
technology has been selected. Defining that schema is Phase 2 work.

## 13. Architectural constraints on future work

- Do not add a domain without a reference implementation and tests.
- Do not put AI calls inside `qrs.classical` or `qrs.quantum`.
- Do not introduce a web framework merely to display results.
- Do not create empty packages for future domains.
- Do not weaken tolerances to accommodate a new environment.
- Do not make any external service mandatory for core simulation.
- Do not commit generated artefacts, caches, or credentials.
