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
| 2 | Experiment runtime: parameter sweeps, run manifests, result serialisation | Next |
| 3 | Second classical domain with real reference data and uncertainty reporting | Planned |
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

## Near-term priorities

1. Define a stable result and experiment metadata schema before adding domains.
2. Add reproducibility manifests (parameters, versions, seeds, timestamps,
   platform).
3. Select the second domain based on data availability and the ability to
   validate against an independent reference.
4. Introduce uncertainty quantification before claiming predictive value.
5. Keep the AI layer optional, local-first, and unable to alter numerical
   results.

## Explicit non-goals for Phase 1

- Simulating all eleven domains.
- Claiming real-world predictive accuracy.
- GPU acceleration.
- Cloud or paid inference.
- User interface work.
- Multi-user storage or collaboration.
