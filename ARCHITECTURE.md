# QRS Architecture

This is the short architectural entry point. The detailed design is in
[docs/architecture/SYSTEM_ARCHITECTURE.md](docs/architecture/SYSTEM_ARCHITECTURE.md).

## Principle

QRS is a scientific simulator, not an AI chatbot with simulation branding. The
numerical path is deterministic, locally executed, and independent of any
language model:

```text
validated inputs
      |
      v
domain model / equations
      |
      v
classical numerical engine  or  quantum circuit engine
      |
      v
measured results + error metrics + metadata
      |
      v
storage, comparison, visualisation
      |
      v
optional AI explanation (never the source of numerical outcomes)
```

## Implemented layers (Phase 1)

```text
src/qrs/
├── __init__.py          package version and scope statement
├── core/                domain-independent input validation
├── classical/           SciPy harmonic oscillator and heat diffusion
└── quantum/             PennyLane Bell-state circuit
```

- `qrs.core.validation` owns strict scalar validation. It rejects booleans,
  non-real types, NaN, infinity, and non-positive physical parameters.
- `qrs.classical.harmonic_oscillator` owns the classical model, solver call,
  analytical reference solution, energy accounting, and error metrics.
- `qrs.classical.heat_diffusion` owns the classical heat-diffusion model,
  solver call, analytical reference solution, error metrics, and Monte Carlo
  uncertainty propagation.
- `qrs.quantum.bell_state` owns the circuit definition, device execution,
  statevector-derived probabilities, Pauli correlations, CHSH terms, reduced
  state, purity, and independent-reference fidelity.
- `qrs.classical` and `qrs.quantum` do not import each other.
- Neither module imports AI, network, storage, or UI code.

## Planned layers

| Layer | Responsibility | Status |
| --- | --- | --- |
| Domain models | Geopolitics, economics, climate, weather, physics/chemistry/biology, engineering, materials, human systems, transportation, hypothetical scenarios | Planned |
| Data ingestion | Source adapters, provenance, schema validation, versioned datasets | Planned |
| Experiment runtime | Parameter sweeps, scenario definitions, reproducible run manifests | Planned |
| Storage | Experiment metadata, results, datasets, artefact references | Planned |
| Visualisation | Plots, dashboards, interactive exploration | Planned |
| AI orchestration | Experiment setup assistance and explanation only | Planned |

## Dependency rules

1. `core` depends only on the Python standard library.
2. Domain modules may depend on `core`, NumPy, and SciPy but must not depend on
   the UI or AI layers.
3. Quantum modules may depend on `core` and PennyLane but must not depend on
   classical domain models unless an explicit hybrid interface is introduced.
4. The AI layer may read validated results and metadata; it must not compute or
   mutate numerical results.
5. Storage and visualisation consume result objects and never re-implement
   scientific equations.

## Extension blueprint

A new domain module is accepted only when it provides:

- a documented equation or model with explicit units;
- validated inputs with justified physical ranges;
- a deterministic numerical or quantum engine;
- an analytical, independently constructed, or observational reference;
- quantified error metrics and tolerances;
- tests covering valid, invalid, boundary, and convergence behaviour;
- a statement of assumptions and domain of validity.

Phase 1 deliberately implements three prototypes rather than a multi-domain
skeleton, so that the scientific quality bar is demonstrated before it is
scaled.
