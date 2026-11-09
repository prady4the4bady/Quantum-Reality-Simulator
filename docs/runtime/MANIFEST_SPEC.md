# Experiment Runtime Specification — QRS Phase 2

| Field | Value |
| --- | --- |
| Status | Implemented |
| Scope | Manifest schema, result envelope, runner, reproducibility check |
| Related | [System architecture](../architecture/SYSTEM_ARCHITECTURE.md), [Scientific validation](../validation/SCIENTIFIC_VALIDATION.md), [Implementation roadmap](../roadmap/IMPLEMENTATION_ROADMAP.md) |

> This document describes only behaviour that exists in `src/qrs/runtime/`.
> Parameter sweeps, result persistence, databases, dashboards, and AI-assisted
> experiment design are **not implemented**.

## 1. Scope

Phase 2 wraps the two existing Phase 1 physics functions in reproducible
experiment records:

- `harmonic_oscillator` dispatches to `simulate_harmonic_oscillator`.
- `bell_state` dispatches to `simulate_bell_state`.

The runtime adds no physics, changes no physics module, and writes no files.
Full arrays remain in the in-memory result objects returned by the physics
functions; envelopes record flat scalar summaries only.

Public API (`qrs.runtime`):

```python
from qrs.runtime import (
    ExperimentManifest,
    ResultEnvelope,
    capture_environment,
    check_reproducibility,
    run_manifest,
)
```

## 2. Canonical JSON

All runtime serialisation and hashing uses one encoding, implemented by
`qrs.runtime.serialization.canonical_json_dumps`:

- object keys sorted lexicographically;
- compact separators `,` and `:` with no insignificant whitespace;
- UTF-8 text, non-ASCII characters emitted directly (`ensure_ascii=False`);
- NaN and Infinity rejected (`allow_nan=False`);
- only JSON-compatible values accepted.

Consequences:

- the same value has exactly one textual representation;
- `NaN`, `Infinity`, sets, complex numbers, and other non-JSON types are
  rejected rather than coerced;
- the encoding used for hashing and the encoding used for `canonical_json()`
  are identical.

Runtime mappings are frozen into immutable copies. Keys must be non-empty
strings; values must be `None`, booleans, integers, strings, or finite floats.
Booleans are preserved as booleans and are not reinterpreted as integers.

## 3. Manifest schema

`ExperimentManifest` is a frozen, slotted dataclass with exactly these fields:

| Field | Type | Constraint |
| --- | --- | --- |
| `schema_version` | integer | Exactly `1`. Booleans are rejected. |
| `experiment_id` | string | 64-character lowercase SHA-256 hex digest. |
| `model_name` | string | `harmonic_oscillator` or `bell_state`. |
| `parameters` | mapping | Flat scalar mapping validated per model. |
| `solver_config` | mapping | Flat scalar mapping validated per model. |
| `seed` | integer | Non-negative. Booleans are rejected. |
| `created_at` | string | UTC `YYYY-MM-DDTHH:MM:SSZ`, and a real calendar timestamp. |
| `environment` | mapping | Exactly the six keys listed in section 4; non-empty string values. |

Field-level validation runs in `__post_init__`, so constructing the dataclass
directly enforces the same field rules as `create` and `from_dict`.
Identifier integrity is deliberately checked only at loading and execution
boundaries (see section 3.4); this allows tests and callers to construct a
deliberately stale identifier with `dataclasses.replace`.

### 3.1 Identifier

`experiment_id` is the SHA-256 hex digest of the canonical JSON of this payload:

```text
schema_version
model_name
parameters
solver_config
seed
environment
```

`created_at` and `experiment_id` are excluded. The payload is encoded as UTF-8
before hashing. Identical content therefore produces an identical identifier
even when creation times differ.

The identifier is **metadata integrity, not authentication**. Anyone who can
edit a manifest can recompute the hash. It detects accidental or naive
tampering; it is not a signature or a security boundary.

### 3.2 Creation defaults

`ExperimentManifest.create(...)` captures the current environment and current
UTC time unless they are supplied explicitly.

For `harmonic_oscillator`, every optional parameter and solver key is merged
over these defaults, so serialised manifests are self-contained:

| Parameters | Default |
| --- | --- |
| `mass` | `1.0` |
| `stiffness` | `1.0` |
| `initial_displacement` | `0.0` |
| `initial_velocity` | `0.0` |
| `t_start` | `0.0` |
| `t_end` | `10.0` |

| Solver configuration | Default |
| --- | --- |
| `num_points` | `1001` |
| `method` | `DOP853` |
| `rtol` | `1e-10` |
| `atol` | `1e-12` |

For `bell_state`, `parameters` and `solver_config` must be absent, `None`, or
empty mappings. Any key is rejected.

### 3.3 Model-specific validation

`harmonic_oscillator`:

- `mass` and `stiffness` must be positive and finite;
- `initial_displacement`, `initial_velocity`, `t_start`, and `t_end` must be
  finite real numbers;
- `t_end` must be strictly greater than `t_start`;
- unknown or missing parameter keys are rejected;
- `num_points` must be an integer of at least `2` (booleans rejected);
- `method` must be a non-empty string from `RK45`, `RK23`, `DOP853`, `Radau`,
  `BDF`, or `LSODA`;
- `rtol` and `atol` must be positive and finite;
- unknown or missing solver keys are rejected.

`bell_state`:

- `parameters` must be empty;
- `solver_config` must be empty.

### 3.4 Loading and integrity checks

`ExperimentManifest.from_dict(data)`:

1. requires a mapping;
2. rejects missing or unknown top-level fields with `TypeError`;
3. constructs the dataclass, applying all field and model validation;
4. recomputes the identifier and raises `ValueError` if it does not match.

`verify_experiment_id()` performs step 4 on demand. `run_manifest` and
`check_reproducibility` call it before executing any physics.

`to_dict()` returns a plain, JSON-compatible dictionary with copied mappings.
`canonical_json()` encodes that full dictionary, including `created_at` and
`experiment_id`. The identifier hash is computed over the six-key payload in
section 3.1, not over `canonical_json()` of the full manifest.

### 3.5 Manifest rejection summary

| Condition | Error |
| --- | --- |
| Manifest data is not a mapping | `TypeError` |
| Missing or unknown manifest fields | `TypeError` |
| `schema_version` is a boolean or non-integer | `TypeError` |
| `schema_version` is less than or greater than `1` | `ValueError` |
| `experiment_id` is not 64 lowercase hex characters | `ValueError` |
| Stored identifier does not match content | `ValueError` |
| `model_name` is not a string | `TypeError` |
| `model_name` is unknown | `ValueError` |
| Parameters or solver configuration are not mappings | `TypeError` |
| Mapping key is empty or not a string | `TypeError` |
| Mapping value is not a JSON scalar | `TypeError` |
| Numeric mapping value is NaN or infinite | `ValueError` |
| `seed` is a boolean or non-integer | `TypeError` |
| `seed` is negative | `ValueError` |
| `created_at` has the wrong shape or is not a real timestamp | `ValueError` |
| Environment is missing or has unknown keys | `ValueError` |
| Environment value is not a non-empty string | `TypeError` |
| Harmonic parameters or solver keys are unknown or missing | `ValueError` |
| Harmonic physical or solver value is invalid | `TypeError` or `ValueError` |
| Bell-state parameters or solver configuration are non-empty | `ValueError` |

## 4. Environment fingerprint

`capture_environment()` returns an immutable mapping with exactly these keys,
in this order:

| Key | Source |
| --- | --- |
| `python` | `platform.python_version()` |
| `numpy` | `numpy.__version__` |
| `scipy` | `scipy.__version__` |
| `pennylane` | `pennylane.__version__` |
| `qrs` | `qrs.__version__` |
| `platform` | `platform.platform()` |

Values are stored as strings. Comparison during reproducibility checks is exact
string equality, not version-range matching.

## 5. Result envelope schema

`ResultEnvelope` is a frozen dataclass with exactly these fields:

| Field | Type | Constraint |
| --- | --- | --- |
| `schema_version` | integer | Exactly `1`. Booleans are rejected. |
| `manifest` | `ExperimentManifest` | Bound manifest. |
| `result_summary` | mapping | Flat scalar metrics. |
| `validation_status` | string | `passed` or `failed`. |
| `validation_details` | mapping | Flat scalar check metadata. |
| `artefacts` | sequence of strings | Relative POSIX paths; stored as a tuple. |

`experiment_id` is exposed as a read-only property returning the bound
manifest's identifier.

Artefact paths reject:

- absolute paths and a leading `/`;
- backslashes and colons;
- empty segments and `.` or `..` traversal segments.

Phase 2 runtime envelopes always use `artefacts=()`. The field exists so a
later storage layer can reference files without changing the envelope shape.

`to_dict()` returns plain copies. `canonical_json()` uses the same canonical
encoding as the manifest. `from_dict()` requires exactly the six fields,
rejects unknown or missing fields with `TypeError`, and loads the nested
manifest through `ExperimentManifest.from_dict`, so a stale nested identifier
raises `ValueError`.

## 6. Runner

`run_manifest(manifest)`:

1. requires an `ExperimentManifest` (`TypeError` otherwise);
2. verifies the identifier (`ValueError` on mismatch);
3. dispatches by `model_name`;
4. returns a `ResultEnvelope`.

The harmonic oscillator receives the manifest values directly:

```python
simulate_harmonic_oscillator(
    mass=...,
    stiffness=...,
    initial_displacement=...,
    initial_velocity=...,
    t_span=(t_start, t_end),
    num_points=...,
    method=...,
    rtol=...,
    atol=...,
)
```

The Bell-state model receives no arguments.

Exceptions raised by the physics functions propagate unchanged. The runtime
does not wrap, retry, suppress, or reinterpret them.

### 6.1 Harmonic oscillator summary

`result_summary` contains:

`mass`, `stiffness`, `angular_frequency`, `initial_displacement`,
`initial_velocity`, `initial_energy`, `t_start`, `t_end`, `num_points`,
`max_abs_displacement_error`, `max_relative_displacement_error`,
`max_abs_energy_drift`, `max_relative_energy_drift`, `method`.

Validation checks:

| Check | Pass condition |
| --- | --- |
| `displacement_error` | `max_abs_displacement_error < 1e-8` |
| `relative_energy_drift` | `max_relative_energy_drift < 1e-8` |

The tolerance matches the Phase 1 validation convention. It is not weakened by
the runtime.

### 6.2 Bell-state summary

`result_summary` contains:

`fidelity`, `purity`, `chsh_value`, `zz_correlation`, `xx_correlation`,
`yy_correlation`, `zx_correlation`, `xz_correlation`, `e_z_b0`, `e_z_b1`,
`e_x_b0`, `e_x_b1`, `probability_sum`.

Validation checks, each compared against an independent scalar reference with
absolute tolerance `1e-12`:

| Check | Pass condition |
| --- | --- |
| `fidelity` | `|fidelity - 1| <= 1e-12` |
| `purity` | `|purity - 0.5| <= 1e-12` |
| `normalization` | `|probability_sum - 1| <= 1e-12` |
| `chsh_value` | `|chsh_value - 2*sqrt(2)| <= 1e-12` |
| `zz_correlation` | `|zz_correlation - 1| <= 1e-12` |
| `xx_correlation` | `|xx_correlation - 1| <= 1e-12` |
| `yy_correlation` | `|yy_correlation + 1| <= 1e-12` |
| `zx_correlation` | `|zx_correlation| <= 1e-12` |
| `xz_correlation` | `|xz_correlation| <= 1e-12` |

### 6.3 Validation details

Every envelope records:

| Key | Meaning |
| --- | --- |
| `model_name` | Executed model. |
| `tolerance` | `1e-8` for the oscillator, `1e-12` for Bell. |
| `checks` | Comma-joined check names in execution order. |
| `checks_passed` | Count of passing checks. |
| `checks_failed` | Count of failing checks. |
| `failed_checks` | Comma-joined failing names; empty when all pass. |

`validation_status` is `passed` only when every check passes; otherwise it is
`failed`. A failed validation is still returned as a valid envelope rather than
raised. `run_manifest` does not compare against a previous run; that is the
reproducibility check's job.

### 6.4 Seeds

Neither implemented model uses randomness or sampling. `seed` is non-negative
metadata and does not change numerical output. It is included in the
`experiment_id` hash, so changing it produces a different manifest identity and
is detectable.

## 7. Reproducibility check

```python
check_reproducibility(
    manifest,
    tolerance=1e-12,
    *,
    allow_environment_drift=False,
) -> tuple[ResultEnvelope, ResultEnvelope]
```

The check:

1. requires an `ExperimentManifest` and a positive, finite `tolerance`;
2. requires `allow_environment_drift` to be a boolean;
3. verifies the manifest identifier;
4. unless drift is allowed, compares all six recorded environment entries with
   the current environment using exact string equality;
5. executes the manifest twice with `run_manifest`;
6. confirms the seed and environment recorded in both envelopes still match the
   input manifest;
7. requires both runs to have `validation_status == "passed"`;
8. compares result summaries key by key.

Summary comparison rules:

- key sets must be identical;
- booleans must match exactly;
- integers and floats must be finite and agree within absolute `tolerance`
  (`difference <= tolerance` passes);
- strings and `None` must match exactly;
- a non-finite numeric value fails.

The function returns the two envelopes in execution order. It does not compare
against a stored historical result, because Phase 2 has no result store.

### 7.1 Failure behaviour

| Condition | Error |
| --- | --- |
| Wrong argument type | `TypeError` |
| Tolerance is not positive and finite | `ValueError` |
| Manifest identifier is stale | `ValueError` |
| Recorded and current environments differ | `RuntimeError` |
| Seed or environment changed between runs | `RuntimeError` |
| Either run failed validation | `RuntimeError` |
| Summary keys differ | `RuntimeError` |
| Numeric difference exceeds tolerance | `RuntimeError` |
| Non-finite numeric summary value | `RuntimeError` |
| Non-numeric summary values differ | `RuntimeError` |

`allow_environment_drift=True` skips only step 4. Identifier verification,
validation status, and summary comparison still apply.

## 8. Explicit non-goals

The following are not implemented and are not claimed:

- parameter sweeps or batch execution;
- persistence of manifests, envelopes, arrays, or artefacts;
- databases, servers, authentication, or multi-user access;
- plotting, dashboards, or user interfaces;
- AI-assisted experiment design or explanation;
- bitwise portability of floating-point results across platforms;
- cryptographic signing or tamper-proof provenance.

The identifier detects content changes; it does not make a manifest trusted.
