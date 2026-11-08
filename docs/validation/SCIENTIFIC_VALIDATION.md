# Scientific Validation — QRS Phase 1

| Field | Value |
| --- | --- |
| Status | Phase 1 validation record; measured on 2026-11-08 |
| Scope | Classical harmonic oscillator; PennyLane Bell state |
| Environment | Windows, CPU only, Python 3.12.10, repo-local `.venv` |
| Related | [Project brief](../requirements/PROJECT_BRIEF.md), [System architecture](../architecture/SYSTEM_ARCHITECTURE.md), [Numerical methods](../scientific-methods/NUMERICAL_METHODS.md), [Decisions](../decisions/ARCHITECTURAL_DECISIONS.md) |

> This document records what was **actually executed and measured**. It does
> not claim real-world predictive validity. The wider QRS platform, including
> all eleven simulation domains, is planned and is not implemented. See
> [IMPLEMENTATION_ROADMAP.md](../roadmap/IMPLEMENTATION_ROADMAP.md).

## 1. Purpose

Phase 1 must demonstrate that QRS can produce numerical results that agree with
an independent reference and that its code rejects invalid scientific inputs.
This document records:

- the exact environment and dependency versions;
- the commands used;
- the measured error and conservation metrics;
- the convergence and solver-robustness evidence;
- the independently constructed quantum reference values;
- the justification for every tolerance used in the test suite;
- the limitations that prevent over-interpretation of the results.

The guiding rule is simple: a claim is made only where there is a recorded
measurement to support it.

## 2. Four levels of validation

The README refers to four levels of validation. They are:

| Level | Name | What it establishes | Examples |
| --- | --- | --- | --- |
| 1 | Analytical or independent agreement | The computed result matches a reference that was not produced by the code under test | Closed-form oscillator solution; NumPy Pauli-matrix reference for the Bell state |
| 2 | Invariants and conservation | Quantities that must be preserved are preserved | Mechanical energy, statevector normalization, reduced-state purity, Tsirelson bound |
| 3 | Convergence and robustness | Error responds correctly to tighter tolerances and to independent numerical methods | Tolerance sweep; RK45/DOP853/Radau agreement; period and phase-space checks |
| 4 | Contract, validation, and determinism | Invalid inputs fail loudly, output shapes and dtypes are correct, and repeated runs are stable | Type/range rejection tests; normalization checks; repeated Bell runs identical |

Passing all four levels supports the claim that the Phase 1 implementation is
numerically correct **for the implemented ideal models**. It does not support a
claim that either model predicts a real physical system.

## 3. Environment

### 3.1 Platform

| Item | Value |
| --- | --- |
| Operating system | Windows (`win32`), 64-bit |
| Processor capability used | CPU only |
| GPU requirement | None |
| CUDA libraries | Not installed, not required |
| Python | 3.12.10 |
| Virtual environment | Repo-local `.venv` |
| pip | 26.3 |
| Network use at runtime | None |
| Paid or cloud inference | None |

### 3.2 Pinned dependencies

Versions were verified with `python -m pip list --format=freeze` inside the
repository virtual environment.

| Package | Version | Role |
| --- | --- | --- |
| NumPy | 2.5.4 | Arrays, linear algebra, independent quantum reference |
| SciPy | 1.18.1 | `solve_ivp` ODE integration |
| PennyLane | 0.45.1 | `default.qubit` statevector circuit execution |
| pytest | 9.2.0 | Unit, scientific, and integration tests |
| Ruff | 0.17.4 | Linting and formatting |

Installation command:

```powershell
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Exact pins live in [`pyproject.toml`](../../pyproject.toml). The package
requires Python `>=3.12,<3.13`.

### 3.3 Build validation

The project was built with a PEP 517 isolated build:

```powershell
.venv\Scripts\python.exe -m pip wheel . --no-deps -w dist
```

Result: `qrs_simulator-0.1.0-py3-none-any.whl` (11,772 bytes). The wheel
contains only:

```text
qrs/__init__.py
qrs/classical/__init__.py
qrs/classical/harmonic_oscillator.py
qrs/core/__init__.py
qrs/core/validation.py
qrs/quantum/__init__.py
qrs/quantum/bell_state.py
qrs_simulator-0.1.0.dist-info/*
```

Editable installation also succeeded. `dist/` is generated output and is ignored
by Git; it is not committed.

## 4. Test-suite inventory and captured output

### 4.1 Inventory

The suite contains 42 test functions that expand to 93 parametrized cases.

| File | Cases | Group |
| --- | --- | --- |
| `tests/unit/test_validation.py` | 24 | Classical/shared |
| `tests/unit/test_harmonic_oscillator.py` | 47 | Classical |
| `tests/scientific/test_harmonic_oscillator_scientific.py` | 6 | Classical |
| `tests/unit/test_bell_state.py` | 9 | Quantum |
| `tests/scientific/test_bell_state_scientific.py` | 6 | Quantum |
| `tests/integration/test_foundation.py` | 1 | Integration |
| **Total** | **93** | |

Classical group total: 77. Quantum group total: 15. Integration total: 1.

### 4.2 Captured runs

The following output was captured on 2026-11-08. Durations depend on the
machine and are shown as reported.

Classical group first:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\test_validation.py tests\unit\test_harmonic_oscillator.py tests\scientific\test_harmonic_oscillator_scientific.py -q
```

```text
77 passed in 1.06s
```

Quantum group second:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\test_bell_state.py tests\scientific\test_bell_state_scientific.py -q
```

```text
15 passed in 2.23s
```

Integration test:

```powershell
.venv\Scripts\python.exe -m pytest tests\integration\test_foundation.py -q
```

```text
1 passed in 2.13s
```

Full suite:

```powershell
.venv\Scripts\python.exe -m pytest tests -q
```

```text
93 passed in 2.45s
```

Lint and formatting:

```powershell
.venv\Scripts\python.exe -m ruff check src tests examples
.venv\Scripts\python.exe -m ruff format --check src tests examples
```

```text
All checks passed!
16 files already formatted
```

No warning filters are configured, no warnings were suppressed, and no tests
were skipped in these runs.

## 5. Classical validation

### 5.1 Model and reference

The implemented equation is the undamped, unforced harmonic oscillator

```text
m*x''(t) + k*x(t) = 0,    m > 0, k > 0,
```

integrated as the first-order system

```text
x' = v
v' = -(k/m)*x
```

with SI units. For initial displacement `x0` and velocity `v0`, the analytical
reference is

```text
x(t) = x0*cos(omega*t) + (v0/omega)*sin(omega*t)
v(t) = -x0*omega*sin(omega*t) + v0*cos(omega*t)
omega = sqrt(k/m)
E(t) = 0.5*m*v(t)^2 + 0.5*k*x(t)^2
```

The numerical trajectory is compared element-wise against this reference on the
same uniform time grid. This is validation level 1 for the classical model.

### 5.2 Default demonstration run

Parameters: `m = 1 kg`, `k = 4 N/m`, `x0 = 1 m`, `v0 = 0 m/s`,
`t = 0` to `10 s`, `n = 1001`, default method DOP853, default tolerances
`rtol = 1e-10`, `atol = 1e-12`.

| Metric | Measured value |
| --- | --- |
| Angular frequency | `2.0 rad/s` |
| Initial energy | `2.0 J` |
| Maximum absolute displacement error | `2.0059931493676686e-10 m` |
| Maximum relative displacement error | `2.0059931493676686e-10` |
| Maximum absolute energy drift | `8.035432319530855e-10 J` |
| Maximum relative energy drift | `4.0177161597654276e-10` |

The run spans approximately 3.18 oscillation periods. Error remains at the
`1e-10` scale, far below the `1e-8` acceptance threshold used by the tests.

### 5.3 Scientific accuracy cases

All cases use DOP853 with default tolerances unless stated otherwise.

| Case | Parameters | Max abs. displacement error | Max rel. displacement error | Max abs. energy drift | Max rel. energy drift |
| --- | --- | --- | --- | --- | --- |
| Default example | `m=1, k=4, x0=1, v0=0, t=0..10, n=1001` | `2.006e-10 m` | `2.006e-10` | `8.035e-10 J` | `4.018e-10` |
| Accuracy B | `m=2, k=8, x0=0.3, v0=-0.4, t=0..5, n=501` | `5.8284377324469e-11 m` | `1.6165261815092379e-10` | `1.9930590511307855e-10 J` | `3.832805867559203e-10` |
| Accuracy C | `m=0.5, k=2, x0=0.2, v0=0.1, t=2.5..7.5, n=101` | `2.8185398459612543e-11 m` | `1.367315928330003e-10` | `1.664574728055257e-11 J` | `3.9166464189535447e-10` |

Case C starts at `t = 2.5 s`, so the implementation is not relying on a
zero-start special case. Case B uses a non-zero initial velocity. Relative
displacement error is normalised by `max(abs(x_exact))`; relative energy drift is
normalised by the initial energy.

All measured values are below `1e-8`, the threshold asserted by the scientific
tests.

### 5.4 Convergence under tighter tolerances

Convergence was measured with DOP853, fixed `atol = 1e-12`, accuracy case B.
The table reports maximum absolute displacement error against the analytical
solution.

| `rtol` | Max abs. displacement error | Ratio to previous |
| --- | --- | --- |
| `1e-4` | `5.2370579729454914e-05 m` | — |
| `1e-6` | `6.433420692286695e-07 m` | `1.23e-02` |
| `1e-8` | `6.099065474884924e-09 m` | `9.48e-03` |
| `1e-10` | `5.8284377324469e-11 m` | `9.56e-03` |
| `1e-12` | `2.1206925104877428e-12 m` | `3.64e-02` |

Each hundred-fold tightening of `rtol` reduces the error by roughly two orders
of magnitude until the `atol` floor and floating-point rounding dominate. This
is the expected behaviour for a controlled adaptive integrator and is validation
level 3 for convergence.

The test `test_tighter_tolerances_reduce_discretization_error` additionally
asserts that the fine solution is at least ten times more accurate than the
coarse solution for the same case.

### 5.5 Solver-method comparison

Accuracy case B, default tolerances `rtol = 1e-10`, `atol = 1e-12`. No method
was specially tuned.

| Method | Max abs. displacement error | Max rel. energy drift |
| --- | --- | --- |
| RK45 | `4.050354496243358e-11 m` | `2.5582805105109136e-10` |
| RK23 | `2.7938140689798274e-10 m` | `1.7806984519398181e-09` |
| DOP853 | `5.8284377324469e-11 m` | `3.832805867559203e-10` |
| Radau | `4.391986774265888e-12 m` | `2.4400567036982814e-11` |
| BDF | `3.964251926724671e-09 m` | `2.461695505559738e-08` |
| LSODA | `1.8006562907402213e-10 m` | `1.1073731675227148e-09` |

Two observations matter and are not hidden:

1. All six methods stay below `1e-8` in displacement error for this smooth
   problem, so the result is not an artefact of one integrator.
2. BDF's energy drift (`2.46e-08`) exceeds the `1e-8` threshold used elsewhere.
   BDF is retained as an exposed option but is not the default, and the
   method-agreement test deliberately compares only RK45, DOP853, and Radau.
   DOP853 is the default because it combines high order, low drift, and
   non-stiff suitability for this problem.

### 5.6 Additional classical invariants

| Check | Test | Measured / asserted outcome |
| --- | --- | --- |
| Energy conservation over 20 s | `test_energy_is_conserved_within_solver_tolerance` | relative drift `< 1e-8` |
| Periodicity | `test_oscillation_period_matches_two_pi_over_omega` | returns to `x = 1 m`, `v = 0 m/s` after one period within `1e-10` |
| Phase-space orbit | `test_phase_space_orbit_keeps_energy_invariant` | `x^2 + (v/omega)^2` constant within `1e-8` |
| Method agreement | `test_independent_methods_agree_with_analytic_reference` | RK45, DOP853, Radau agree with the analytical solution and each other within `1e-8` |

These are validation level 2 checks for the classical model.

## 6. Quantum validation

### 6.1 Circuit and conventions

The implemented circuit is:

```text
wire 0:  H
wire 0:  control
wire 1:  target   (CNOT)
```

Executed analytically on PennyLane `default.qubit` with wires `(0, 1)`; no
shots, no sampling, no noise model, no hardware.

`default.qubit` uses big-endian basis ordering. For wires `(0, 1)` the
statevector order is `|00>, |01>, |10>, |11>`, and the first character of each
bitstring corresponds to wire 0. This convention is tested directly rather than
assumed silently.

The target state is

```text
|Phi+> = (|00> + |11>) / sqrt(2).
```

Probabilities are computed from the device-returned statevector as
`abs(amplitude)^2`. They are never hardcoded in the implementation; the
expected values appear only in tests and documentation.

### 6.2 Measured state

| Quantity | Measured value |
| --- | --- |
| Statevector order | `|00>, |01>, |10>, |11>` |
| Amplitude at `|00>` | `0.7071067811865475 + 0j` |
| Amplitude at `|01>` | `0` |
| Amplitude at `|10>` | `0` |
| Amplitude at `|11>` | `0.7071067811865475 + 0j` |
| Probabilities | `[0.4999999999999999, 0.0, 0.0, 0.4999999999999999]` |
| Sum of probabilities | `0.9999999999999998` |
| Fidelity against independent reference | `0.9999999999999996` |
| Wire order | `(0, 1)` |
| Bitstrings | `("00", "01", "10", "11")` |

The exact reference state used for fidelity is the independently constructed
vector `(1, 0, 0, 1)/sqrt(2)`, normalized in double precision. It is not
obtained from PennyLane.

### 6.3 Pauli correlations

All correlations are device expectation values, compared in the tests against
an independent NumPy construction using explicit Pauli matrices and Kronecker
products.

| Correlation | Measured value | Expected for `|Phi+>` |
| --- | --- | --- |
| `<ZZ>` | `0.9999999999999998` | `+1` |
| `<XX>` | `0.9999999999999996` | `+1` |
| `<YY>` | `-0.9999999999999996` | `-1` |
| `<ZX>` | `0.0` | `0` |
| `<XZ>` | `0.0` | `0` |

The `YY = -1` sign follows from the standard Pauli convention
`Y = [[0, -i], [i, 0]]` and is checked against the independent reference.
An implementation that silently changed the sign convention would fail.

### 6.4 CHSH evaluation

The documented convention is

```text
S = E(Z, B0) + E(Z, B1) + E(X, B0) - E(X, B1)

B0 = (Z + X) / sqrt(2)      on wire 1
B1 = (Z - X) / sqrt(2)      on wire 1
```

Measured terms:

| Term | Measured value | Ideal value |
| --- | --- | --- |
| `E(Z, B0)` | `0.7071067811865474` | `1/sqrt(2)` |
| `E(Z, B1)` | `0.7071067811865474` | `1/sqrt(2)` |
| `E(X, B0)` | `0.7071067811865471` | `1/sqrt(2)` |
| `E(X, B1)` | `-0.7071067811865471` | `-1/sqrt(2)` |
| `S` | `2.828427124746189` | `2*sqrt(2) = 2.8284271247461903` |

The measured value violates the classical bound `S <= 2` and reaches the
Tsirelson bound `2*sqrt(2)` within floating-point precision. The test asserts
agreement with `2*sqrt(2)` at `abs = 1e-12` and `S > 2`.

This is a simulation of an ideal Bell test under a stated measurement
convention. It is not a loophole-free physical experiment and says nothing
about the performance of noisy hardware.

### 6.5 Entanglement and reference checks

| Quantity | Measured value | Meaning |
| --- | --- | --- |
| Wire-0 reduced density matrix | `diag(0.4999999999999999, 0.4999999999999999)` | Maximally mixed marginal |
| Purity `Tr(rho_0^2)` | `0.4999999999999998` | `0.5` indicates maximal entanglement for a pure two-qubit state |
| Concurrence from purity | `1.0` within `1e-12` | Maximally entangled |
| Fidelity to `|Phi+>` | `0.9999999999999996` | Matches the independently constructed state |

The concurrence is computed in the test as
`sqrt(2 * (1 - Tr(rho_A^2)))`, which is valid for a pure two-qubit state.

### 6.6 Independent quantum reference

The scientific test module does not call PennyLane to build its reference.
Instead it:

1. Defines the Pauli matrices explicitly.
2. Constructs two-qubit operators with `kron(P, I)` for wire 0 and
   `kron(I, P)` for wire 1, matching the documented big-endian convention.
3. Builds the reference state `(1, 0, 0, 1)/sqrt(2)`.
4. Computes expectations with `real(vdot(state, operator @ state))`.
5. Builds `B0` and `B1` explicitly and evaluates all four CHSH terms.

This makes the quantum check a genuine level-1 comparison rather than a
comparison of PennyLane with itself.

## 7. Tolerance justification

### 7.1 Classical tolerances

| Tolerance | Where used | Justification |
| --- | --- | --- |
| `rtol = 1e-10`, `atol = 1e-12` (defaults) | Public solver defaults | Demanding but practical for a smooth, non-stiff ODE; measured error is `~5.8e-11` on the standard accuracy case |
| `1e-8` absolute displacement | Scientific accuracy tests | Approximately 170x the measured error on case B and 350x on case C, leaving room for platform-level last-bit differences while still rejecting any material regression |
| `1e-8` relative energy drift | Energy conservation tests | Approximately 25x the measured default drift, while still catching a solver or equation sign error immediately |
| `1e-10` periodicity | Period test | One-period return to the initial state; measured agreement is at the `1e-10` level |
| Relative tolerance in convergence test | `fine < coarse / 10` | A weaker factor than the measured improvement (roughly 100x), so the test checks the expected trend without being brittle |

The tolerances are not loosened to accommodate failures. They are set from the
observed error of a controlled method and remain far below any threshold at
which the physical conclusions would change.

### 7.2 Quantum tolerances

| Tolerance | Where used | Justification |
| --- | --- | --- |
| `atol = 1e-12` | Statevector, probabilities, correlations, CHSH terms, density matrix, purity | Double precision has machine epsilon `~2.2e-16`. A two-qubit analytic circuit accumulates only a few rounding operations. Measured deviations are `~1e-16` to `~4e-16`, so `1e-12` provides roughly four orders of magnitude of headroom for platform variation while still detecting any structural error |
| `abs = 1e-12` for `2*sqrt(2)` | Tsirelson-bound test | The measured CHSH value differs from the exact expression by `~1.3e-15`; `1e-12` is a strict but portable bound |
| Exact array equality | Determinism test | Both runs execute the same deterministic computation in the same process; no sampling is involved. Exact equality is appropriate here and is not used to compare against an independent reference |

No tolerance is used to hide a warning or an exception. Input-validation tests
assert the exception type and message content.

## 8. Verbatim example output

The following is the captured output of the three runnable examples. Values are
formatted for display by the example scripts; the unrounded values are recorded
in the tables above.

### 8.1 Classical example

```text
Classical harmonic oscillator
  mass                   : 1 kg
  stiffness              : 4 N/m
  angular frequency      : 2.000000 rad/s
  integration method     : DOP853
  samples                : 1001
  initial energy         : 2.000000 J
  max |x_num - x_exact|  : 2.006e-10 m
  max relative x error   : 2.006e-10
  max absolute E drift   : 8.035e-10 J
  max relative E drift   : 4.018e-10

  t (s)      x (m)        v (m/s)      E (J)
    0.0000    1.000000    0.000000   2.000000
    5.0000   -0.839072    1.088042   2.000000
   10.0000    0.408082   -1.825891   2.000000
```

### 8.2 Quantum example

```text
Bell state |Phi+> on PennyLane default.qubit
  wire order             : (0, 1)

  basis    probability      amplitude
  |00>      0.500000      +0.707107+0.000000j
  |01>      0.000000      +0.000000+0.000000j
  |10>      0.000000      +0.000000+0.000000j
  |11>      0.500000      +0.707107+0.000000j

  Pauli correlations
    <ZZ>                 : +1.000000
    <XX>                 : +1.000000
    <YY>                 : -1.000000
    <ZX>                 : +0.000000
    <XZ>                 : +0.000000

  CHSH terms
    E(Z, B0)             : +0.707107
    E(Z, B1)             : +0.707107
    E(X, B0)             : +0.707107
    E(X, B1)             : -0.707107
    S                    : +2.828427

  Entanglement and reference checks
    reduced rho (wire 0) : [[(0.4999999999999999+0j), 0j], [0j, (0.4999999999999999+0j)]]
    purity Tr(rho^2)     : 0.500000
    fidelity to |Phi+>   : 1.000000000000000
```

### 8.3 End-to-end smoke check

```text
classical max |x error| : 2.006e-10 m
classical relative E    : 4.018e-10
Bell probabilities      : [0.4999999999999999, 0.0, 0.0, 0.4999999999999999]
Bell fidelity           : 1.000000000000000
CHSH S                  : 2.828427124746189

All phase-1 foundation checks passed.
```

The smoke check exits non-zero if any assertion fails, so success is meaningful
in automated use.

## 9. Limitations and non-claims

The measured evidence must be read together with these limitations.

### 9.1 Classical model

- The oscillator is ideal: constant mass, constant stiffness, no damping, no
  forcing, no nonlinearity, no external perturbation.
- It is not a validated model of any specific bridge, building, vehicle, or
  material. It is a reference problem for the numerical pipeline.
- SI units are used consistently, but no uncertainty propagation is
  implemented.
- The analytical comparison is itself evaluated in double precision; it is not
  a symbolic proof.
- Only one-dimensional motion is implemented.

### 9.2 Quantum model

- Execution is an ideal analytic statevector simulation. There are no shots,
  no sampling noise, no decoherence, no gate errors, and no hardware.
- The CHSH result depends on the documented measurement convention and on the
  ideal preparation. It is not a loophole-free Bell test.
- No error mitigation, tomography, or noise model is implemented.
- No GPU or CUDA backend is used or required.
- Scaling to larger circuits is untested in Phase 1.

### 9.3 Validation scope

- Measurements were taken on one Windows machine with the pinned versions
  above. Floating-point results can differ in the final bits on other
  platforms, which is why absolute tolerances are used instead of bitwise
  equality for reference comparisons.
- Test durations are environment-dependent and are not a performance claim.
- No real-world observational data was used anywhere in Phase 1. Therefore no
  statement about predictive accuracy is made or implied.
- The name "Quantum Reality Simulator" describes long-term intent, not a
  validated capability. Phase 1 is a scientific foundation.

## 10. Reproducing this record

From the repository root on Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -e ".[dev]"

.venv\Scripts\python.exe -m pytest tests\unit\test_validation.py tests\unit\test_harmonic_oscillator.py tests\scientific\test_harmonic_oscillator_scientific.py -q
.venv\Scripts\python.exe -m pytest tests\unit\test_bell_state.py tests\scientific\test_bell_state_scientific.py -q
.venv\Scripts\python.exe -m pytest tests\integration\test_foundation.py -q
.venv\Scripts\python.exe -m pytest tests -q

.venv\Scripts\python.exe -m ruff check src tests examples
.venv\Scripts\python.exe -m ruff format --check src tests examples

.venv\Scripts\python.exe examples\classical_harmonic_oscillator.py
.venv\Scripts\python.exe examples\bell_state.py
.venv\Scripts\python.exe examples\verify_foundation.py
```

To reproduce the convergence and method tables, call the public API with the
parameters listed in Sections 5.4 and 5.5. `simulate_harmonic_oscillator` accepts
`method`, `rtol`, and `atol` keyword arguments; the measured values can be read
directly from the returned result fields.

## 11. Traceability summary

| Requirement | Evidence |
| --- | --- |
| FR-C1 – FR-C9 | Tables in Section 5; classical test group (77 cases) |
| FR-Q1 – FR-Q9 | Tables in Section 6; quantum test group (15 cases) |
| FR-X1 | Environment and pins in Section 3 |
| FR-X2 | 93 passing cases in Section 4 |
| FR-X3 | Ruff output in Section 4.2 |
| FR-X4 | Verbatim example output in Section 8 |
| FR-X5 | This document and the labelled documents it links to |
| FR-X6 | Numerical modules import no AI or network client; the architecture forbids it |

## 12. Status declaration

Phase 1 is **implemented and validated as an ideal two-model foundation**.

Everything beyond the two models, the shared validation helpers, the tests, the
examples, and the documentation is **planned**. In particular, the eleven
simulation domains, real-world data ingestion, storage, visualisation, digital
twin behaviour, optimisation, and AI orchestration do not exist in this
repository yet.
