# Quantum Reality Simulator (QRS)

QRS is a local-first, modular simulation platform intended to combine classical
numerical computing, genuine quantum-circuit simulation, domain-specific
scientific models, data management, experiment storage, and visualisation.

**Current status: Phase 1 scientific foundation plus the Phase 2 experiment
runtime.** Two small, independently tested prototypes are implemented and
wrapped in reproducible manifest and result-envelope records. The wider
multi-domain platform is planned, not implemented. Parameter sweeps, experiment
persistence, storage, visualisation, and all domain simulators remain
unimplemented. Nothing in this repository should be interpreted as a working
geopolitical, economic, climate, or other domain simulator yet.

## Implemented

| Capability | Implementation | Status |
| --- | --- | --- |
| Classical harmonic oscillator `m*x'' + k*x = 0` | SciPy `solve_ivp`, analytical comparison, energy tracking | Implemented and validated |
| Quantum Bell state `|Phi+> = (|00> + |11>)/sqrt(2)` | PennyLane `default.qubit`, H + CNOT, statevector and correlations | Implemented and validated |
| Shared scalar validation | `qrs.core.validation` | Implemented |
| Experiment runtime | `qrs.runtime`: canonical manifests, result envelopes, manifest runner, reproducibility check | Implemented and tested |
| Automated tests | Pytest unit, scientific, and integration suites | Implemented, 342 tests passing |
| Lint and formatting | Ruff | Implemented, clean |

## Not implemented yet

The following are planned only: the eleven simulation domains, real-world data
ingestion, digital-twin state management, scenario and optimisation workflows,
parameter sweeps, experiment persistence, storage, visualisation, AI-assisted
orchestration, and any web or desktop interface. See [ROADMAP.md](ROADMAP.md)
and [docs/runtime/MANIFEST_SPEC.md](docs/runtime/MANIFEST_SPEC.md).

The language model is never part of the numerical path. All reported scientific
results come from locally executed NumPy, SciPy, and PennyLane computation.

## Requirements

- Python **3.12.x** (validated with 3.12.10).
- A CPU is sufficient. No CUDA libraries, GPU quantum backends, paid APIs, or
  cloud inference are required or used.
- Windows was used for validation of the implemented phases; the code is
  platform-neutral.

## Quick start (Windows PowerShell)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Run the two scientific examples:

```powershell
.venv\Scripts\python.exe examples\classical_harmonic_oscillator.py
.venv\Scripts\python.exe examples\bell_state.py
```

Run the end-to-end smoke check:

```powershell
.venv\Scripts\python.exe examples\verify_foundation.py
```

## Verification

```powershell
# Classical suite
.venv\Scripts\python.exe -m pytest tests\unit\test_validation.py tests\unit\test_harmonic_oscillator.py tests\scientific\test_harmonic_oscillator_scientific.py -q

# Quantum suite
.venv\Scripts\python.exe -m pytest tests\unit\test_bell_state.py tests\scientific\test_bell_state_scientific.py -q

# Full suite
.venv\Scripts\python.exe -m pytest tests -q

# Lint and formatting
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
```

Latest verified results are recorded in
[docs/validation/SCIENTIFIC_VALIDATION.md](docs/validation/SCIENTIFIC_VALIDATION.md)
and the runtime contract in
[docs/runtime/MANIFEST_SPEC.md](docs/runtime/MANIFEST_SPEC.md).

## Headline validated results

| Quantity | Measured value |
| --- | --- |
| Classical max absolute displacement error (`m=1 kg`, `k=4 N/m`, 1001 samples) | `2.0059931493676686e-10 m` |
| Classical max relative energy drift (same run) | `4.018e-10` |
| Bell-state probabilities (device-derived) | `[0.5, 0.0, 0.0, 0.5]` |
| Bell fidelity against independent reference | `0.9999999999999996` |
| CHSH value `S` | `2.828427124746189` (`2*sqrt(2)`) |
| Reduced-state purity `Tr(rho_0^2)` | `0.4999999999999998` |

These numbers demonstrate numerical correctness and agreement with analytical
or independently constructed references. They do **not** by themselves establish
physical validity against real-world observations. See
[docs/validation/SCIENTIFIC_VALIDATION.md](docs/validation/SCIENTIFIC_VALIDATION.md)
for the four levels of validation used by this project.

## Repository layout

```text
Quantum-Reality-Simulator/
├── README.md
├── ARCHITECTURE.md
├── ROADMAP.md
├── SECURITY.md
├── pyproject.toml
├── .gitignore
├── docs/
│   ├── requirements/PROJECT_BRIEF.md
│   ├── architecture/SYSTEM_ARCHITECTURE.md
│   ├── scientific-methods/NUMERICAL_METHODS.md
│   ├── validation/SCIENTIFIC_VALIDATION.md
│   ├── runtime/MANIFEST_SPEC.md
│   ├── decisions/ARCHITECTURAL_DECISIONS.md
│   └── roadmap/IMPLEMENTATION_ROADMAP.md
├── src/qrs/
│   ├── core/          # shared validation helpers
│   ├── classical/     # SciPy harmonic oscillator
│   ├── quantum/       # PennyLane Bell state
│   └── runtime/       # manifests, envelopes, runner, reproducibility
├── tests/
│   ├── unit/
│   ├── scientific/
│   └── integration/
└── examples/
```

`experiments/`, `validation/`, and `utils/` packages are intentionally absent.
They will be created when they contain real functionality, not as empty
placeholders.

## Documentation map

| Document | Purpose |
| --- | --- |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Short architectural entry point |
| [docs/requirements/PROJECT_BRIEF.md](docs/requirements/PROJECT_BRIEF.md) | Provisional brief derived from the user-supplied specification |
| [docs/architecture/SYSTEM_ARCHITECTURE.md](docs/architecture/SYSTEM_ARCHITECTURE.md) | Layers, module boundaries, dependency rules |
| [docs/scientific-methods/NUMERICAL_METHODS.md](docs/scientific-methods/NUMERICAL_METHODS.md) | Equations, numerical methods, conventions, assumptions |
| [docs/validation/SCIENTIFIC_VALIDATION.md](docs/validation/SCIENTIFIC_VALIDATION.md) | Measured validation evidence and limitations |
| [docs/runtime/MANIFEST_SPEC.md](docs/runtime/MANIFEST_SPEC.md) | Manifest, envelope, runner, and reproducibility specification |
| [docs/decisions/ARCHITECTURAL_DECISIONS.md](docs/decisions/ARCHITECTURAL_DECISIONS.md) | Architecture decision records |
| [docs/roadmap/IMPLEMENTATION_ROADMAP.md](docs/roadmap/IMPLEMENTATION_ROADMAP.md) | Phased plan and acceptance criteria |
| [SECURITY.md](SECURITY.md) | Security policy and operational restrictions |

## Scientific integrity rules

1. Numerical outcomes come from executed scientific code, never from an LLM.
2. Inputs are validated before use; booleans are not accepted as physical
   scalars.
3. Every solver result is compared with an analytical or independently
   constructed reference.
4. Numerical tolerances are justified and are never weakened to make a test
   pass.
5. Implemented features and planned features are labelled separately.
6. Limitations and warnings are reported rather than hidden.

## License

No license has been selected yet. Do not redistribute this repository until a
license is added.

## Security

Do not commit credentials, `.env` files, API keys, or generated artefacts. See
[SECURITY.md](SECURITY.md). The implemented phases run entirely offline and use
no paid or cloud inference services.
