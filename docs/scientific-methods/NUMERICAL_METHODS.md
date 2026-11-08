# Numerical and Scientific Methods — QRS Phase 1

| Field | Value |
| --- | --- |
| Status | Phase 1, implemented methods only |
| Scope | Classical harmonic oscillator; Bell-state circuit |
| Related | [System architecture](../architecture/SYSTEM_ARCHITECTURE.md), [Scientific validation](../validation/SCIENTIFIC_VALIDATION.md) |

> This document describes **what the code actually computes**. It does not
> describe planned models. Planned extensions are confined to the final section
> and are explicitly labelled.

## 1. Conventions

### 1.1 Units

The classical model uses SI units consistently.

| Quantity | Symbol | Unit |
| --- | --- | --- |
| Mass | `m` | kilogram (kg) |
| Spring stiffness | `k` | newton per metre (N/m) |
| Displacement | `x` | metre (m) |
| Velocity | `v` | metre per second (m/s) |
| Time | `t` | second (s) |
| Energy | `E` | joule (J) |

The quantum model is unitless. Amplitudes are dimensionless complex numbers,
and probabilities are dimensionless real numbers in `[0, 1]`.

### 1.2 Floating-point type

All classical arrays are `numpy.float64`. All quantum statevectors and density
matrices are `numpy.complex128`, with real-valued probabilities and
expectation values converted to Python `float`. No lower-precision dtype is
used anywhere in the numerical path.

### 1.3 Determinism

Neither prototype uses random numbers, sampling, or wall-clock-dependent
behaviour. Identical inputs, dependency versions, and platform floating-point
semantics produce identical outputs. The Bell-state circuit is executed
analytically, so there is no shot noise.

## 2. Classical harmonic oscillator

### 2.1 Model

The implemented equation is the undamped, unforced, one-dimensional harmonic
oscillator:

```text
m * x''(t) + k * x(t) = 0,    m > 0,  k > 0
```

It is integrated as the equivalent first-order system:

```text
x' = v
v' = -(k / m) * x
```

with the state vector `[x, v]`.

The angular frequency is:

```text
omega = sqrt(k / m)
```

### 2.2 Exact reference solution

For initial conditions `x(t0) = x0` and `v(t0) = v0`, the analytical solution
used as the reference is:

```text
x(t) = x0 * cos(omega * (t - t0)) + (v0 / omega) * sin(omega * (t - t0))

v(t) = -x0 * omega * sin(omega * (t - t0)) + v0 * cos(omega * (t - t0))
```

This solution is evaluated at exactly the same time samples as the numerical
solution. It is an independent check of the integrator, not a fit to the
numerical output.

### 2.3 Energy

Total mechanical energy at each sample is:

```text
E(t) = 0.5 * m * v(t)^2 + 0.5 * k * x(t)^2
```

For the exact undamped oscillator, `E(t) = E(t0)` for all `t`. Two energy
metrics are reported:

```text
max_abs_energy_drift      = max |E(t) - E(t0)|
max_relative_energy_drift = max_abs_energy_drift / E(t0)
```

If `E(t0) = 0` (the oscillator is at rest at the equilibrium position), the
relative drift is defined as `0.0`, because there is no positive energy scale.
The absolute drift is still reported.

### 2.4 Displacement error metrics

```text
max_abs_displacement_error      = max |x_numeric(t) - x_exact(t)|
max_relative_displacement_error = max_abs_displacement_error / max |x_exact(t)|
```

The relative error is normalized by the **maximum analytical displacement
amplitude** over the interval, not by each point's instantaneous value. This
avoids division by near-zero displacements at zero crossings. If the analytical
displacement is identically zero, the relative error is `0.0` when the absolute
error is zero and `inf` otherwise.

Both metrics are computed over every requested sample, including the endpoints.

### 2.5 Integration method

The solver is `scipy.integrate.solve_ivp`. The time grid passed as `t_eval` is:

```text
numpy.linspace(t_start, t_end, num_points, dtype=numpy.float64)
```

It includes both endpoints. The integrator chooses its own internal adaptive
steps; `t_eval` only controls where the solution is reported.

Supported methods:

| Method | Type | Order / character | Notes |
| --- | --- | --- | --- |
| `RK45` | Explicit Runge–Kutta | 5(4) | General-purpose default in SciPy, not QRS default |
| `RK23` | Explicit Runge–Kutta | 3(2) | Lower order, useful for convergence comparison |
| `DOP853` | Explicit Runge–Kutta | 8(7) | **QRS default**, high accuracy for smooth non-stiff problems |
| `Radau` | Implicit Runge–Kutta | 5 | Suitable for stiff problems; more expensive per step |
| `BDF` | Implicit multistep | Variable | Suitable for stiff problems |
| `LSODA` | Automatic switching | Variable | Switches between Adams and BDF |

Default tolerances are `rtol = 1e-10` and `atol = 1e-12`. Both must be finite
and strictly positive. The chosen default method is `DOP853` because the model
is smooth, non-stiff, and low-dimensional; an explicit high-order method gives
small error at modest cost. Implicit methods remain selectable so that method
agreement can be tested rather than assumed.

### 2.6 Why this is a suitable test problem

The linear oscillator has a closed-form solution, bounded periodic motion, and
a conserved energy. These properties make it possible to test:

- absolute and relative trajectory accuracy;
- energy conservation;
- convergence under tightening tolerances;
- agreement across independent integration algorithms;
- determinism.

The model is deliberately simple. It is a numerical and software foundation,
not a validated model of a real structure, machine, or natural system.

### 2.7 Algorithm

```text
1. Validate mass, stiffness, initial displacement, initial velocity.
2. Validate that t_span has exactly two finite values with t_end > t_start.
3. Validate num_points >= 2, method in the supported set, rtol > 0, atol > 0.
4. Build the uniform time grid including both endpoints.
5. Integrate the first-order system with solve_ivp(t_eval=time).
6. Fail with RuntimeError if integration fails, the returned shape is not
   (2, num_points), or any value is non-finite.
7. Compute energy at every sample.
8. Evaluate the analytical displacement and velocity at the same samples.
9. Compute absolute/relative displacement errors and energy drift.
10. Return an immutable HarmonicOscillatorResult.
```

### 2.8 Validation domain and limitations

- Constant mass and stiffness only. There is no time-dependent parameter,
  damping, driving force, nonlinear spring, or external field.
- One spatial dimension and one degree of freedom only.
- `m > 0` and `k > 0`; zero or negative values are rejected.
- The model is not stiff in its default parameter range, so the stiff solvers
  are supported but not required by the reference case.
- No uncertainty propagation, parameter fitting, or empirical calibration.
- The reported error is error against the ideal analytical model, not error
  against a physical experiment.

## 3. Quantum Bell state

### 3.1 Target state

The implemented state is:

```text
|Phi+> = (|00> + |11>) / sqrt(2)
```

### 3.2 Circuit

```text
wire 0: -- H -------- control --------
wire 1: ------------- target (X) -----
```

Circuit construction:

1. `qml.Hadamard(wires=0)` prepares
   `(|0> + |1>) / sqrt(2)` on wire 0.
2. `qml.CNOT(wires=[0, 1])` flips wire 1 when wire 0 is `|1>`, producing
   `(|00> + |11>) / sqrt(2)`.

No rotation angles, state initialization, or post-selection are used. The
state is produced by the circuit, not inserted as a statevector.

### 3.3 Device and execution

| Setting | Value |
| --- | --- |
| Device | `default.qubit` |
| Wires | `(0, 1)` |
| Execution | Analytic statevector, no shots |
| Interface | `None` (no automatic differentiation) |
| Hardware | Local CPU |
| Noise model | None |

The device is created once per call. Three QNodes share that device:

- `state_circuit` returns `qml.state()`;
- `expectation_circuit` returns `qml.expval(observable)` for a supplied
  observable;
- `reduced_state_circuit` returns `qml.density_matrix(wires=[0])`.

Each QNode prepares the same Bell state before measurement.

### 3.4 Basis ordering convention

PennyLane's `default.qubit` uses big-endian computational-basis ordering for the
wire order `(0, 1)`. The statevector index and bitstring mapping is:

| Index | Bitstring | Wire 0 | Wire 1 | Amplitude for `|Phi+>` |
| --- | --- | --- | --- | --- |
| 0 | `00` | 0 | 0 | `1/sqrt(2)` |
| 1 | `01` | 0 | 1 | `0` |
| 2 | `10` | 1 | 0 | `0` |
| 3 | `11` | 1 | 1 | `1/sqrt(2)` |

The bitstring for index `i` is `format(i, "02b")`. Character position `k` in a
bitstring corresponds to wire `k`. This convention is part of the public result
contract: `BellStateResult.bitstrings` is `("00", "01", "10", "11")`.

Confusing this ordering with little-endian ordering would swap the labels of
indices 1 and 2. For `|Phi+>` those two amplitudes are zero, so the
probabilities would look unchanged; the convention is nevertheless documented
and tested because it becomes observable for other states.

### 3.5 Statevector validation

Before any result is reported, the device state is checked:

```text
shape == (4,)
all amplitudes finite
abs(sum |amplitude|^2 - 1) <= 1e-12
```

A failure raises `RuntimeError`. Probabilities are then derived as:

```text
p_i = |amplitude_i|^2
```

They are never hardcoded and are not renormalized after the check.

### 3.6 Pauli correlations

Five two-qubit expectation values are measured on the device:

```text
ZZ = <Z_0 Z_1>
XX = <X_0 X_1>
YY = <Y_0 Y_1>
ZX = <Z_0 X_1>
XZ = <X_0 Z_1>
```

For the ideal `|Phi+>` state:

| Correlation | Exact value |
| --- | --- |
| `ZZ` | `+1` |
| `XX` | `+1` |
| `YY` | `-1` |
| `ZX` | `0` |
| `XZ` | `0` |

### 3.7 CHSH convention

The implemented CHSH expression is:

```text
S = E(Z, B0) + E(Z, B1) + E(X, B0) - E(X, B1)
```

with the wire-1 observables:

```text
B0 = (Z + X) / sqrt(2)
B1 = (Z - X) / sqrt(2)
```

The four terms are measured as expectation values of `Z_0 ⊗ B0`, `Z_0 ⊗ B1`,
`X_0 ⊗ B0`, and `X_0 ⊗ B1`. The Hamiltonians are constructed explicitly with
coefficients `+1/sqrt(2)` and `-1/sqrt(2)`; the CHSH value is then the signed
sum above.

Each term expands over the measured two-qubit correlations. Because `B1` enters
with a minus sign on `X`, the expansion order matters:

```text
E(Z, B0) = ( E(Z0 Z1) + E(Z0 X1) ) / sqrt(2)
E(Z, B1) = ( E(Z0 Z1) - E(Z0 X1) ) / sqrt(2)
E(X, B0) = ( E(X0 Z1) + E(X0 X1) ) / sqrt(2)
E(X, B1) = ( E(X0 Z1) - E(X0 X1) ) / sqrt(2)
```

For `|Phi+>`, `E(Z0 Z1) = +1`, `E(X0 X1) = +1`, and the cross terms
`E(Z0 X1) = E(X0 Z1) = 0`. Substituting:

```text
E(Z, B0) = +1/sqrt(2)
E(Z, B1) = +1/sqrt(2)
E(X, B0) = +1/sqrt(2)
E(X, B1) = -1/sqrt(2)
```

Therefore:

```text
S = E(Z, B0) + E(Z, B1) + E(X, B0) - E(X, B1)
  = 1/sqrt(2) + 1/sqrt(2) + 1/sqrt(2) - (-1/sqrt(2))
  = 4/sqrt(2)
  = 2*sqrt(2)
  ≈ 2.8284271247461903
```

The measured QRS terms are `+0.7071067811865474`, `+0.7071067811865474`,
`+0.7071067811865471`, and `-0.7071067811865471`, summing to
`2.828427124746189`, consistent with `2*sqrt(2)` within floating-point
round-off. The classical (local-hidden-variable) bound is `|S| <= 2`; the ideal
quantum value violates it.

### 3.8 Reduced state and purity

The single-qubit reduced density matrix of wire 0 is returned by
`qml.density_matrix(wires=[0])`. For `|Phi+>`:

```text
rho_0 = Tr_1(|Phi+><Phi+|) = I / 2 = diag(0.5, 0.5)
```

Purity is:

```text
purity = Tr(rho_0^2)
```

For the maximally mixed reduced state, `purity = 0.5`. A pure product state
would give `purity = 1`. Purity is computed from the device-returned matrix,
not assumed.

### 3.9 Independent reference and fidelity

The reference state is constructed with NumPy, **without PennyLane**:

```text
reference = zeros(4, dtype=complex128)
reference[0] = 1 / sqrt(2)
reference[3] = 1 / sqrt(2)
```

This encodes `(|00> + |11>) / sqrt(2)` in the same index convention. Fidelity
is the pure-state overlap:

```text
fidelity = |<reference|state>|^2
```

clipped to `[0, 1]` to absorb floating-point round-off. The reference is
independent of the circuit construction; it tests the device output against an
analytically written vector.

### 3.10 Algorithm

```text
1. Create default.qubit device on wires (0, 1).
2. Define state, expectation, and reduced-density QNodes that each apply
   H(0) then CNOT(0, 1).
3. Execute the state QNode analytically.
4. Validate shape (4,), finiteness, and norm squared within 1e-12.
5. Derive probabilities as |amplitude|^2 and build bitstrings.
6. Measure ZZ, XX, YY, ZX, XZ.
7. Build B0 and B1 Hamiltonians and measure the four CHSH terms.
8. Sum the terms with the documented signs to obtain S.
9. Measure the wire-0 reduced density matrix; validate shape and finiteness.
10. Compute purity = Tr(rho_0^2).
11. Build the NumPy reference vector and compute fidelity.
12. Return an immutable BellStateResult.
```

### 3.11 Assumptions and limitations

- Ideal, noiseless statevector simulation. No decoherence, gate error, readout
  error, or hardware calibration is modelled.
- No measurement sampling. Probabilities and correlations are exact
  expectation values, not finite-shot estimates.
- No mid-circuit measurement, reset, or classical control.
- No entanglement measure beyond the reduced-state purity and the CHSH value.
- The CHSH value depends on the stated measurement convention; it is not a
  convention-free property.
- The circuit is fixed. There is no parameterized gate, variational loop, or
  transpilation.
- Two qubits only.

## 4. Cross-cutting numerical practices

### 4.1 Validation before computation

Physical inputs are validated before the solver or device is invoked. Booleans
are rejected explicitly because Python treats `bool` as a subclass of `int`.
NaN and infinity are rejected. Invalid inputs raise `TypeError` or `ValueError`
with the parameter name in the message.

### 4.2 Failure handling

Backend failures and contract violations raise `RuntimeError`. The code does
not return partially valid results, silently clip values, or fall back to a
different method.

### 4.3 Reproducibility

- Exact pins: NumPy 2.5.4, SciPy 1.18.1, PennyLane 0.45.1, pytest 9.2.0,
  Ruff 0.17.4.
- Python 3.12.x, validated with 3.12.10.
- CPU only.
- No network access in the numerical path.
- No random seeds are needed.

Floating-point results in the last few bits may differ across operating
systems, CPUs, and linear-algebra libraries. Tests therefore use justified
tolerances rather than bitwise equality, except where deterministic output is
asserted within a single run.

### 4.4 Separation from AI

Neither numerical module imports an AI client, a language model, or a network
library. Any future explanation layer must consume validated result objects and
must not contribute to numerical outcomes.

## 5. Planned methods (not implemented)

The following are **planned**, not present in the codebase:

- damped and driven oscillators, nonlinear springs, and time-dependent
  parameters;
- uncertainty propagation and parameter estimation;
- hybrid classical–quantum workflows;
- noisy quantum simulation, shot-based sampling, and error mitigation;
- parameterized quantum circuits and variational algorithms;
- additional quantum states and multi-qubit circuits;
- real-world data assimilation and model calibration;
- experiment manifests, provenance, and result serialisation;
- visualisation and scenario comparison.

No planned method should be described as working until it has an
implementation, an independent reference, and measured validation evidence.
