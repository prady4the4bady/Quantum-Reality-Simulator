"""Unit tests for immutable, validated result envelopes."""

from __future__ import annotations

import dataclasses
import json
import math
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

import pytest

from qrs.runtime.envelope import SCHEMA_VERSION, ResultEnvelope
from qrs.runtime.manifest import HARMONIC_OSCILLATOR, ExperimentManifest

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

ENVELOPE_FIELDS = (
    "schema_version",
    "manifest",
    "result_summary",
    "validation_status",
    "validation_details",
    "artefacts",
)


def create_manifest() -> ExperimentManifest:
    return ExperimentManifest.create(
        model_name=HARMONIC_OSCILLATOR,
        created_at=CREATED_AT,
        environment=ENVIRONMENT,
    )


def create_envelope(**overrides: Any) -> ResultEnvelope:
    options: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "manifest": create_manifest(),
        "result_summary": {
            "mass": 1.0,
            "num_points": 1001,
            "method": "DOP853",
            "validated": True,
            "note": None,
        },
        "validation_status": "passed",
        "validation_details": {
            "model_name": HARMONIC_OSCILLATOR,
            "checks_passed": 2,
            "checks_failed": 0,
            "failed_checks": "",
        },
        "artefacts": (),
    }
    options.update(overrides)
    return ResultEnvelope(**options)


def test_construction_normalises_and_freezes_fields() -> None:
    manifest = create_manifest()
    envelope = create_envelope(manifest=manifest)

    assert envelope.schema_version == SCHEMA_VERSION
    assert envelope.manifest is manifest
    assert envelope.validation_status == "passed"
    assert isinstance(envelope.result_summary, MappingProxyType)
    assert isinstance(envelope.validation_details, MappingProxyType)
    assert envelope.artefacts == ()


def test_experiment_id_delegates_to_manifest() -> None:
    manifest = create_manifest()

    envelope = create_envelope(manifest=manifest)

    assert envelope.experiment_id == manifest.experiment_id


def test_accepts_failed_status_and_relative_artefacts() -> None:
    envelope = create_envelope(
        validation_status="failed",
        artefacts=["figures/plot.png", "data/run.csv"],
    )

    assert envelope.validation_status == "failed"
    assert envelope.artefacts == ("figures/plot.png", "data/run.csv")


def test_accepts_all_scalar_summary_types() -> None:
    summary = {
        "none": None,
        "boolean": False,
        "integer": 7,
        "float": 1.5,
        "string": "value",
    }

    envelope = create_envelope(result_summary=summary, validation_details=summary)

    assert dict(envelope.result_summary) == summary
    assert dict(envelope.validation_details) == summary


def test_to_dict_returns_plain_copies() -> None:
    envelope = create_envelope(artefacts=("figures/plot.png",))
    data = envelope.to_dict()

    assert isinstance(data["manifest"], dict)
    assert isinstance(data["result_summary"], dict)
    assert isinstance(data["validation_details"], dict)
    assert isinstance(data["artefacts"], list)
    assert data["artefacts"] == ["figures/plot.png"]

    data["result_summary"]["mass"] = 99.0
    data["validation_details"]["checks_passed"] = 0
    data["artefacts"].append("other.png")
    data["manifest"]["seed"] = 5

    assert envelope.result_summary["mass"] == 1.0
    assert envelope.validation_details["checks_passed"] == 2
    assert envelope.artefacts == ("figures/plot.png",)
    assert envelope.manifest.seed == 0


def test_canonical_json_round_trip() -> None:
    envelope = create_envelope(artefacts=("figures/plot.png",))

    assert json.loads(envelope.canonical_json()) == envelope.to_dict()


def test_from_dict_round_trip() -> None:
    envelope = create_envelope(
        validation_status="failed",
        result_summary={"mass": 2.5, "method": "DOP853"},
        artefacts=("data/run.csv",),
    )

    restored = ResultEnvelope.from_dict(envelope.to_dict())

    assert restored == envelope
    assert restored.experiment_id == envelope.experiment_id


def test_envelope_is_frozen_and_slotted() -> None:
    envelope = create_envelope()

    with pytest.raises(dataclasses.FrozenInstanceError):
        envelope.validation_status = "failed"  # type: ignore[misc]
    assert not hasattr(envelope, "__dict__")
    with pytest.raises(TypeError):
        envelope.result_summary["mass"] = 2.0  # type: ignore[index]
    with pytest.raises(AttributeError):
        envelope.artefacts.append("x.png")  # type: ignore[attr-defined]


@pytest.mark.parametrize("version", [0, -1, 2, 99])
def test_rejects_unsupported_schema_version(version: int) -> None:
    with pytest.raises(ValueError, match="envelope schema_version must be 1"):
        create_envelope(schema_version=version)


@pytest.mark.parametrize("version", [True, False, "1", 1.0, None])
def test_rejects_non_integer_schema_version(version: object) -> None:
    with pytest.raises(TypeError, match="envelope schema_version must be an integer"):
        create_envelope(schema_version=version)


@pytest.mark.parametrize("manifest", [None, {}, "manifest", 1])
def test_rejects_non_manifest(manifest: object) -> None:
    with pytest.raises(TypeError, match="manifest must be an ExperimentManifest"):
        create_envelope(manifest=manifest)


@pytest.mark.parametrize("field", ["result_summary", "validation_details"])
@pytest.mark.parametrize("value", [[], "text", 1, None])
def test_rejects_non_mapping_summaries(field: str, value: object) -> None:
    with pytest.raises(TypeError, match=f"{field} must be a mapping"):
        create_envelope(**{field: value})


@pytest.mark.parametrize("field", ["result_summary", "validation_details"])
@pytest.mark.parametrize("value", [[1], {"nested": 1}, 1 + 2j, {1, 2}])
def test_rejects_non_scalar_summary_values(field: str, value: object) -> None:
    with pytest.raises(TypeError, match="must be a JSON scalar"):
        create_envelope(**{field: {"key": value}})


@pytest.mark.parametrize("field", ["result_summary", "validation_details"])
@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_rejects_non_finite_summary_values(field: str, value: float) -> None:
    with pytest.raises(ValueError, match="must be finite"):
        create_envelope(**{field: {"key": value}})


@pytest.mark.parametrize("field", ["result_summary", "validation_details"])
@pytest.mark.parametrize("key", ["", 1, None])
def test_rejects_invalid_summary_keys(field: str, key: object) -> None:
    with pytest.raises(TypeError, match="keys must be non-empty strings"):
        create_envelope(**{field: {key: 1}})


@pytest.mark.parametrize("status", ["", "pass", "PASSED", "unknown", "failed "])
def test_rejects_unknown_validation_status(status: str) -> None:
    with pytest.raises(ValueError, match="validation_status must be one of"):
        create_envelope(validation_status=status)


@pytest.mark.parametrize("status", [1, None, True, ["passed"]])
def test_rejects_non_string_validation_status(status: object) -> None:
    with pytest.raises(TypeError, match="validation_status must be a string"):
        create_envelope(validation_status=status)


@pytest.mark.parametrize("artefacts", ["figures/plot.png", b"data", None, 1])
def test_rejects_non_sequence_artefacts(artefacts: object) -> None:
    with pytest.raises(TypeError, match="artefacts must be a sequence"):
        create_envelope(artefacts=artefacts)


@pytest.mark.parametrize("artefacts", [("",), (1,), (None,), ("plot.png", 2)])
def test_rejects_non_string_or_empty_artefact_items(artefacts: tuple[object, ...]) -> None:
    with pytest.raises(TypeError, match="artefact paths must be non-empty strings"):
        create_envelope(artefacts=artefacts)


@pytest.mark.parametrize(
    "path",
    ["/tmp/plot.png", "C:/plot.png", "figures\\plot.png", "data/run:1.csv"],
)
def test_rejects_absolute_and_windows_artefact_paths(path: str) -> None:
    with pytest.raises(ValueError, match="artefact path must be a relative POSIX path"):
        create_envelope(artefacts=(path,))


@pytest.mark.parametrize(
    "path",
    ["..", ".", "figures/../plot.png", "figures/./plot.png", "figures//plot.png", "figures/"],
)
def test_rejects_traversing_or_empty_artefact_segments(path: str) -> None:
    with pytest.raises(ValueError, match="must not be empty or traverse directories"):
        create_envelope(artefacts=(path,))


def test_accepts_nested_relative_artefact_paths() -> None:
    paths = ("results/2026/plot.png", "README.txt")

    envelope = create_envelope(artefacts=paths)

    assert envelope.artefacts == paths


def test_from_dict_rejects_non_mapping() -> None:
    with pytest.raises(TypeError, match="envelope data must be a mapping"):
        ResultEnvelope.from_dict([("schema_version", 1)])  # type: ignore[arg-type]


@pytest.mark.parametrize("field", ENVELOPE_FIELDS)
def test_from_dict_rejects_missing_field(field: str) -> None:
    data = create_envelope().to_dict()
    del data[field]

    with pytest.raises(TypeError, match="missing required fields"):
        ResultEnvelope.from_dict(data)


def test_from_dict_rejects_unknown_field() -> None:
    data = create_envelope().to_dict()
    data["extra"] = "value"

    with pytest.raises(TypeError, match="unknown fields"):
        ResultEnvelope.from_dict(data)


def test_from_dict_rejects_non_mapping_manifest() -> None:
    data = create_envelope().to_dict()
    data["manifest"] = "manifest"

    with pytest.raises(TypeError, match="envelope manifest must be a mapping"):
        ResultEnvelope.from_dict(data)


@pytest.mark.parametrize("value", ["1", 1.0, True])
def test_from_dict_rejects_wrong_schema_version_type(value: object) -> None:
    data = create_envelope().to_dict()
    data["schema_version"] = value

    with pytest.raises(TypeError, match="envelope schema_version must be an integer"):
        ResultEnvelope.from_dict(data)


@pytest.mark.parametrize(
    ("field", "tamper"),
    [
        ("seed", 1),
        ("parameters", {"mass": 2.0}),
        ("environment", {"numpy": "0.0.0"}),
    ],
)
def test_from_dict_rejects_tampered_nested_manifest(
    field: str,
    tamper: object,
) -> None:
    data = create_envelope().to_dict()
    if field == "parameters":
        data["manifest"][field]["mass"] = 2.0
    elif field == "environment":
        data["manifest"][field]["numpy"] = "0.0.0"
    else:
        data["manifest"][field] = tamper

    with pytest.raises(ValueError, match="experiment_id does not match"):
        ResultEnvelope.from_dict(data)


def test_from_dict_rejects_unknown_nested_manifest_field() -> None:
    data = create_envelope().to_dict()
    data["manifest"]["extra"] = "value"

    with pytest.raises(TypeError, match="unknown fields"):
        ResultEnvelope.from_dict(data)
