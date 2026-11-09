"""Unit tests for deterministic, validated experiment manifests."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

import pytest

from qrs.runtime.manifest import (
    BELL_STATE,
    ENVIRONMENT_KEYS,
    HARMONIC_OSCILLATOR,
    ExperimentManifest,
    capture_environment,
)

CREATED_AT = "2026-01-02T03:04:05Z"
ENVIRONMENT: Mapping[str, str] = MappingProxyType(
    {
        "python": "3.12.10",
        "numpy": "2.5.4",
        "scipy": "1.18.1",
        "pennylane": "0.45.1",
        "qrs": "0.1.0",
        "platform": "test-platform",
    }
)

HARMONIC_PARAMETER_DEFAULTS = {
    "mass": 1.0,
    "stiffness": 1.0,
    "initial_displacement": 0.0,
    "initial_velocity": 0.0,
    "t_start": 0.0,
    "t_end": 10.0,
}
HARMONIC_SOLVER_DEFAULTS = {
    "num_points": 1001,
    "method": "DOP853",
    "rtol": 1e-10,
    "atol": 1e-12,
}


def create_manifest(**overrides: Any) -> ExperimentManifest:
    """Create a harmonic manifest with fixed, reproducible content."""

    options: dict[str, Any] = {
        "model_name": HARMONIC_OSCILLATOR,
        "created_at": CREATED_AT,
        "environment": ENVIRONMENT,
    }
    options.update(overrides)
    return ExperimentManifest.create(**options)


def test_capture_environment_records_documented_keys() -> None:
    environment = capture_environment()

    assert tuple(environment) == ENVIRONMENT_KEYS
    assert all(isinstance(value, str) and value for value in environment.values())
    with pytest.raises(TypeError):
        environment["python"] = "other"  # type: ignore[index]


def test_create_populates_harmonic_defaults() -> None:
    manifest = create_manifest()

    assert manifest.schema_version == 1
    assert manifest.model_name == HARMONIC_OSCILLATOR
    assert dict(manifest.parameters) == HARMONIC_PARAMETER_DEFAULTS
    assert dict(manifest.solver_config) == HARMONIC_SOLVER_DEFAULTS
    assert manifest.seed == 0
    assert manifest.created_at == CREATED_AT
    assert len(manifest.experiment_id) == 64
    assert manifest.experiment_id == manifest.experiment_id.lower()


def test_create_merges_harmonic_overrides_with_defaults() -> None:
    manifest = create_manifest(
        parameters={"mass": 2.0, "stiffness": 4.0},
        solver_config={"num_points": 101},
    )

    assert manifest.parameters["mass"] == 2.0
    assert manifest.parameters["stiffness"] == 4.0
    assert manifest.parameters["initial_displacement"] == 0.0
    assert manifest.solver_config["num_points"] == 101
    assert manifest.solver_config["method"] == "DOP853"
    assert set(manifest.parameters) == set(HARMONIC_PARAMETER_DEFAULTS)
    assert set(manifest.solver_config) == set(HARMONIC_SOLVER_DEFAULTS)


def test_create_bell_state_manifest_has_empty_mappings() -> None:
    manifest = create_manifest(model_name=BELL_STATE)

    assert manifest.model_name == BELL_STATE
    assert dict(manifest.parameters) == {}
    assert dict(manifest.solver_config) == {}


def test_create_bell_state_rejects_non_empty_parameters() -> None:
    with pytest.raises(ValueError, match="bell_state requires empty parameters"):
        create_manifest(model_name=BELL_STATE, parameters={"mass": 1.0})


def test_create_bell_state_rejects_non_empty_solver_config() -> None:
    with pytest.raises(ValueError, match="bell_state requires empty solver_config"):
        create_manifest(model_name=BELL_STATE, solver_config={"num_points": 10})


def test_identical_content_produces_identical_identifier() -> None:
    first = create_manifest()
    second = create_manifest()

    assert first.experiment_id == second.experiment_id


def test_created_at_does_not_change_identifier() -> None:
    first = create_manifest(created_at="2026-01-02T03:04:05Z")
    second = create_manifest(created_at="2030-12-31T23:59:59Z")

    assert first.created_at != second.created_at
    assert first.experiment_id == second.experiment_id


def test_identifier_matches_independent_canonical_hash() -> None:
    manifest = create_manifest()
    payload = manifest.to_dict()
    payload.pop("experiment_id")
    payload.pop("created_at")
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")

    assert manifest.experiment_id == hashlib.sha256(encoded).hexdigest()


def test_identifier_depends_on_parameter_values() -> None:
    baseline = create_manifest()
    changed = create_manifest(parameters={"stiffness": 2.0})

    assert baseline.experiment_id != changed.experiment_id


def test_identifier_depends_on_solver_config() -> None:
    baseline = create_manifest()
    changed = create_manifest(solver_config={"num_points": 501})

    assert baseline.experiment_id != changed.experiment_id


def test_identifier_depends_on_seed() -> None:
    baseline = create_manifest()
    changed = create_manifest(seed=7)

    assert baseline.experiment_id != changed.experiment_id


def test_identifier_depends_on_environment() -> None:
    baseline = create_manifest()
    changed = create_manifest(environment={**ENVIRONMENT, "platform": "other-platform"})

    assert baseline.experiment_id != changed.experiment_id


def test_identifier_is_independent_of_mapping_insertion_order() -> None:
    baseline = create_manifest()
    reordered_parameters = dict(reversed(list(baseline.parameters.items())))
    reordered_solver = dict(reversed(list(baseline.solver_config.items())))

    reordered = create_manifest(
        parameters=reordered_parameters,
        solver_config=reordered_solver,
    )

    assert reordered.experiment_id == baseline.experiment_id


def test_from_dict_round_trip() -> None:
    manifest = create_manifest(seed=5, parameters={"mass": 1.5})

    restored = ExperimentManifest.from_dict(manifest.to_dict())

    assert restored == manifest
    assert restored.experiment_id == manifest.experiment_id


def test_canonical_json_round_trip() -> None:
    manifest = create_manifest(seed=3)

    assert json.loads(manifest.canonical_json()) == manifest.to_dict()


def test_to_dict_returns_plain_copies() -> None:
    manifest = create_manifest()
    data = manifest.to_dict()

    assert isinstance(data["parameters"], dict)
    assert isinstance(data["solver_config"], dict)
    assert isinstance(data["environment"], dict)
    data["parameters"]["mass"] = 99.0
    data["environment"]["python"] = "0.0.0"
    data["seed"] = 42

    assert manifest.parameters["mass"] == 1.0
    assert manifest.environment["python"] == ENVIRONMENT["python"]
    assert manifest.seed == 0


def test_manifest_is_frozen_and_slotted() -> None:
    manifest = create_manifest()

    with pytest.raises(dataclasses.FrozenInstanceError):
        manifest.seed = 1  # type: ignore[misc]
    assert not hasattr(manifest, "__dict__")
    assert isinstance(manifest.parameters, MappingProxyType)
    assert isinstance(manifest.solver_config, MappingProxyType)
    with pytest.raises(TypeError):
        manifest.parameters["mass"] = 2.0  # type: ignore[index]


def test_environment_is_stored_in_documented_order() -> None:
    reversed_environment = dict(reversed(list(ENVIRONMENT.items())))

    manifest = create_manifest(environment=reversed_environment)

    assert tuple(manifest.environment) == ENVIRONMENT_KEYS


def test_from_dict_accepts_reordered_environment_with_same_identifier() -> None:
    manifest = create_manifest()
    data = manifest.to_dict()
    data["environment"] = dict(reversed(list(data["environment"].items())))

    restored = ExperimentManifest.from_dict(data)

    assert restored.experiment_id == manifest.experiment_id
    assert tuple(restored.environment) == ENVIRONMENT_KEYS


def test_create_rejects_unknown_model_name() -> None:
    with pytest.raises(ValueError, match="unknown model_name"):
        create_manifest(model_name="harmonic")


def test_create_rejects_non_string_model_name() -> None:
    with pytest.raises(TypeError, match="model_name must be a string"):
        create_manifest(model_name=1)


@pytest.mark.parametrize("seed", [-1, -100])
def test_create_rejects_negative_seed(seed: int) -> None:
    with pytest.raises(ValueError, match="seed must be non-negative"):
        create_manifest(seed=seed)


@pytest.mark.parametrize("seed", [1.0, True, "0", None])
def test_create_rejects_non_integer_seed(seed: object) -> None:
    with pytest.raises(TypeError, match="seed must be an integer"):
        create_manifest(seed=seed)


@pytest.mark.parametrize(
    "created_at",
    [
        "2026-01-02T03:04:05",
        "2026-01-02T03:04:05+00:00",
        "2026-13-01T00:00:00Z",
        "not-a-date",
    ],
)
def test_create_rejects_invalid_created_at(created_at: str) -> None:
    with pytest.raises(ValueError, match="created_at"):
        create_manifest(created_at=created_at)


def test_create_rejects_non_string_created_at() -> None:
    with pytest.raises(TypeError, match="created_at must be a string"):
        create_manifest(created_at=1)


@pytest.mark.parametrize(
    "environment",
    [
        {key: value for key, value in ENVIRONMENT.items() if key != "numpy"},
        {**ENVIRONMENT, "extra": "value"},
    ],
)
def test_create_rejects_environment_with_wrong_keys(environment: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="environment"):
        create_manifest(environment=environment)


@pytest.mark.parametrize("value", ["", 1, None])
def test_create_rejects_non_string_environment_values(value: object) -> None:
    with pytest.raises(TypeError, match="environment"):
        create_manifest(environment={**ENVIRONMENT, "numpy": value})


def test_create_rejects_non_mapping_environment() -> None:
    with pytest.raises(TypeError, match="environment must be a mapping"):
        create_manifest(environment=[])


def test_create_rejects_non_mapping_parameters() -> None:
    with pytest.raises(TypeError, match="parameters must be a mapping"):
        create_manifest(parameters=[])


def test_create_rejects_non_mapping_solver_config() -> None:
    with pytest.raises(TypeError, match="solver_config must be a mapping"):
        create_manifest(solver_config=[])


def test_create_rejects_unknown_harmonic_parameter() -> None:
    with pytest.raises(ValueError, match="unknown harmonic_oscillator parameter"):
        create_manifest(parameters={"damping": 0.1})


def test_create_rejects_unknown_harmonic_solver_key() -> None:
    with pytest.raises(ValueError, match="unknown harmonic_oscillator solver_config key"):
        create_manifest(solver_config={"max_step": 0.1})


def test_manifest_rejects_missing_harmonic_parameter() -> None:
    manifest = create_manifest()

    with pytest.raises(ValueError, match="missing parameter"):
        dataclasses.replace(manifest, parameters={"mass": 1.0})


def test_manifest_rejects_missing_harmonic_solver_key() -> None:
    manifest = create_manifest()

    with pytest.raises(ValueError, match="missing solver_config key"):
        dataclasses.replace(manifest, solver_config={"num_points": 10})


def test_manifest_rejects_inverted_time_span() -> None:
    with pytest.raises(ValueError, match="t_end must be greater than t_start"):
        create_manifest(parameters={"t_start": 10.0, "t_end": 10.0})


@pytest.mark.parametrize("value", [0.0, -1.0, math.nan, math.inf])
def test_create_rejects_invalid_mass(value: float) -> None:
    with pytest.raises(ValueError):
        create_manifest(parameters={"mass": value})


@pytest.mark.parametrize("value", [True, "1.0", None])
def test_create_rejects_non_numeric_mass(value: object) -> None:
    with pytest.raises(TypeError):
        create_manifest(parameters={"mass": value})


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_create_rejects_non_finite_initial_displacement(value: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        create_manifest(parameters={"initial_displacement": value})


def test_create_rejects_non_numeric_initial_velocity() -> None:
    with pytest.raises(TypeError, match="initial_velocity"):
        create_manifest(parameters={"initial_velocity": "fast"})


@pytest.mark.parametrize("num_points", [1, 0, -5])
def test_create_rejects_too_few_points(num_points: int) -> None:
    with pytest.raises(ValueError, match="num_points"):
        create_manifest(solver_config={"num_points": num_points})


@pytest.mark.parametrize("num_points", [True, 2.0, "100"])
def test_create_rejects_non_integer_num_points(num_points: object) -> None:
    with pytest.raises(TypeError, match=r"solver_config\['num_points'\] must be an integer"):
        create_manifest(solver_config={"num_points": num_points})


@pytest.mark.parametrize("method", ["", 1, None])
def test_create_rejects_non_string_method(method: object) -> None:
    with pytest.raises(TypeError, match=r"solver_config\['method'\] must be a non-empty string"):
        create_manifest(solver_config={"method": method})


def test_create_rejects_unsupported_method() -> None:
    with pytest.raises(ValueError, match="unsupported solver_config"):
        create_manifest(solver_config={"method": "Euler"})


@pytest.mark.parametrize("key", ["rtol", "atol"])
@pytest.mark.parametrize("value", [0.0, -1.0, math.nan, math.inf])
def test_create_rejects_invalid_tolerances(key: str, value: float) -> None:
    with pytest.raises(ValueError):
        create_manifest(solver_config={key: value})


@pytest.mark.parametrize("key", ["rtol", "atol"])
def test_create_rejects_boolean_tolerances(key: str) -> None:
    with pytest.raises(TypeError):
        create_manifest(solver_config={key: True})


def test_from_dict_rejects_non_mapping() -> None:
    with pytest.raises(TypeError, match="manifest data must be a mapping"):
        ExperimentManifest.from_dict([("schema_version", 1)])  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "field",
    [
        "schema_version",
        "experiment_id",
        "model_name",
        "parameters",
        "solver_config",
        "seed",
        "created_at",
        "environment",
    ],
)
def test_from_dict_rejects_missing_field(field: str) -> None:
    data = create_manifest().to_dict()
    del data[field]

    with pytest.raises(TypeError, match="missing required fields"):
        ExperimentManifest.from_dict(data)


def test_from_dict_rejects_unknown_field() -> None:
    data = create_manifest().to_dict()
    data["extra"] = "value"

    with pytest.raises(TypeError, match="unknown fields"):
        ExperimentManifest.from_dict(data)


@pytest.mark.parametrize("version", [0, -1, 2, 99])
def test_from_dict_rejects_unsupported_schema_version(version: int) -> None:
    data = create_manifest().to_dict()
    data["schema_version"] = version

    with pytest.raises(ValueError, match="schema_version"):
        ExperimentManifest.from_dict(data)


@pytest.mark.parametrize("version", [0, 2])
def test_manifest_rejects_unsupported_schema_version_on_construction(version: int) -> None:
    manifest = create_manifest()

    with pytest.raises(ValueError, match="schema_version"):
        dataclasses.replace(manifest, schema_version=version)


def test_manifest_rejects_boolean_schema_version() -> None:
    manifest = create_manifest()

    with pytest.raises(TypeError, match="schema_version must be an integer"):
        dataclasses.replace(manifest, schema_version=True)


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("schema_version", "1", TypeError),
        ("experiment_id", 1, TypeError),
        ("experiment_id", "not-a-hash", ValueError),
        ("experiment_id", "A" * 64, ValueError),
        ("model_name", 1, TypeError),
        ("seed", 1.0, TypeError),
        ("seed", -1, ValueError),
        ("created_at", 1, TypeError),
        ("parameters", [], TypeError),
        ("solver_config", [], TypeError),
        ("environment", [], TypeError),
    ],
)
def test_from_dict_rejects_wrong_field_types(
    field: str,
    value: object,
    error: type[Exception],
) -> None:
    data = create_manifest().to_dict()
    data[field] = value

    with pytest.raises(error):
        ExperimentManifest.from_dict(data)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_from_dict_rejects_non_finite_parameter(value: float) -> None:
    data = create_manifest().to_dict()
    data["parameters"]["mass"] = value

    with pytest.raises(ValueError, match="finite"):
        ExperimentManifest.from_dict(data)


def test_from_dict_rejects_missing_harmonic_parameter() -> None:
    data = create_manifest().to_dict()
    del data["parameters"]["mass"]

    with pytest.raises(ValueError, match="missing parameter"):
        ExperimentManifest.from_dict(data)


def test_from_dict_rejects_bell_state_parameters() -> None:
    data = create_manifest(model_name=BELL_STATE).to_dict()
    data["parameters"] = {"mass": 1.0}

    with pytest.raises(ValueError, match="does not accept parameters"):
        ExperimentManifest.from_dict(data)


def test_verify_experiment_id_accepts_intact_manifest() -> None:
    create_manifest().verify_experiment_id()


def test_stale_identifier_is_rejected_after_seed_tampering() -> None:
    manifest = create_manifest()
    tampered = dataclasses.replace(manifest, seed=1)

    assert tampered.experiment_id == manifest.experiment_id
    with pytest.raises(ValueError, match="experiment_id does not match"):
        tampered.verify_experiment_id()
    with pytest.raises(ValueError, match="experiment_id does not match"):
        ExperimentManifest.from_dict(tampered.to_dict())


def test_stale_identifier_is_rejected_after_parameter_tampering() -> None:
    manifest = create_manifest()
    tampered = dataclasses.replace(
        manifest,
        parameters={**manifest.parameters, "mass": 2.0},
    )

    assert tampered.experiment_id == manifest.experiment_id
    with pytest.raises(ValueError, match="experiment_id does not match"):
        ExperimentManifest.from_dict(tampered.to_dict())


def test_stale_identifier_is_rejected_after_environment_tampering() -> None:
    manifest = create_manifest()
    tampered = dataclasses.replace(
        manifest,
        environment={**manifest.environment, "numpy": "0.0.0"},
    )

    assert tampered.experiment_id == manifest.experiment_id
    with pytest.raises(ValueError, match="experiment_id does not match"):
        ExperimentManifest.from_dict(tampered.to_dict())
