"""Versioned result envelopes for completed QRS experiments.

An envelope binds a manifest to the summary of the result it produced, the
outcome of the runtime's validation checks, and any relative artefact paths.
It deliberately stores flat scalar summaries only: Phase 2 does not persist
arrays or write result files. Full trajectories remain available in the
in-memory result objects returned by the physics functions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from numbers import Integral
from typing import Any, Final

from qrs.runtime.manifest import ExperimentManifest
from qrs.runtime.serialization import Scalar, canonical_json_dumps, freeze_scalar_mapping

SCHEMA_VERSION: Final[int] = 1
"""Envelope schema version understood by this runtime."""

VALIDATION_STATUSES: Final[frozenset[str]] = frozenset({"passed", "failed"})

_ENVELOPE_FIELDS = frozenset(
    {
        "schema_version",
        "manifest",
        "result_summary",
        "validation_status",
        "validation_details",
        "artefacts",
    }
)


def _validate_schema_version(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"envelope schema_version must be an integer, got {type(value).__name__}")
    version = int(value)
    if version != SCHEMA_VERSION:
        raise ValueError(f"envelope schema_version must be {SCHEMA_VERSION}, got {version}")
    return version


def _validate_validation_status(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(f"validation_status must be a string, got {type(value).__name__}")
    if value not in VALIDATION_STATUSES:
        allowed = ", ".join(sorted(VALIDATION_STATUSES))
        raise ValueError(f"validation_status must be one of {allowed}, got {value!r}")
    return value


def _validate_artefacts(value: object) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(
            f"artefacts must be a sequence of relative paths, got {type(value).__name__}"
        )

    paths: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise TypeError("artefact paths must be non-empty strings")
        if item.startswith("/") or "\\" in item or ":" in item:
            raise ValueError(f"artefact path must be a relative POSIX path, got {item!r}")
        parts = item.split("/")
        if any(part in {"", ".", ".."} for part in parts):
            raise ValueError(f"artefact path must not be empty or traverse directories: {item!r}")
        paths.append(item)
    return tuple(paths)


@dataclass(frozen=True, slots=True)
class ResultEnvelope:
    """Immutable result record tied to one experiment manifest.

    Attributes
    ----------
    schema_version:
        Envelope schema version. Only version ``1`` is accepted.
    manifest:
        The manifest that produced the result.
    result_summary:
        Flat, immutable mapping of scalar result metrics.
    validation_status:
        ``"passed"`` when every runtime check succeeded, otherwise
        ``"failed"``.
    validation_details:
        Flat, immutable mapping describing the checks that ran.
    artefacts:
        Tuple of relative POSIX paths. Phase 2 never writes files, so this is
        empty for runtime-produced envelopes.
    """

    schema_version: int
    manifest: ExperimentManifest
    result_summary: Mapping[str, Scalar]
    validation_status: str
    validation_details: Mapping[str, Scalar]
    artefacts: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _validate_schema_version(self.schema_version))
        if not isinstance(self.manifest, ExperimentManifest):
            raise TypeError(
                f"manifest must be an ExperimentManifest, got {type(self.manifest).__name__}"
            )
        object.__setattr__(
            self, "result_summary", freeze_scalar_mapping(self.result_summary, "result_summary")
        )
        object.__setattr__(
            self,
            "validation_details",
            freeze_scalar_mapping(self.validation_details, "validation_details"),
        )
        object.__setattr__(
            self, "validation_status", _validate_validation_status(self.validation_status)
        )
        object.__setattr__(self, "artefacts", _validate_artefacts(self.artefacts))

    @property
    def experiment_id(self) -> str:
        """Return the identifier of the bound manifest."""

        return self.manifest.experiment_id

    def to_dict(self) -> dict[str, Any]:
        """Return a plain, JSON-compatible dictionary representation."""

        return {
            "schema_version": self.schema_version,
            "manifest": self.manifest.to_dict(),
            "result_summary": dict(self.result_summary),
            "validation_status": self.validation_status,
            "validation_details": dict(self.validation_details),
            "artefacts": list(self.artefacts),
        }

    def canonical_json(self) -> str:
        """Return the canonical JSON encoding of this envelope."""

        return canonical_json_dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ResultEnvelope:
        """Load an envelope from serialised data.

        The nested manifest is loaded with ``ExperimentManifest.from_dict``,
        so its identifier is verified as part of deserialisation.

        Raises
        ------
        TypeError
            If ``data`` is not a mapping, fields are missing or unknown, or a
            field has the wrong type.
        ValueError
            If a field value is invalid or the embedded manifest identifier
            does not match its content.
        """

        if not isinstance(data, Mapping):
            raise TypeError(f"envelope data must be a mapping, got {type(data).__name__}")

        keys = set(data)
        missing = _ENVELOPE_FIELDS - keys
        if missing:
            names = ", ".join(sorted(missing))
            raise TypeError(f"envelope data is missing required fields: {names}")
        unknown = keys - _ENVELOPE_FIELDS
        if unknown:
            names = ", ".join(sorted(str(key) for key in unknown))
            raise TypeError(f"envelope data contains unknown fields: {names}")

        manifest_data = data["manifest"]
        if not isinstance(manifest_data, Mapping):
            raise TypeError(
                f"envelope manifest must be a mapping, got {type(manifest_data).__name__}"
            )
        manifest = ExperimentManifest.from_dict(manifest_data)
        return cls(
            schema_version=data["schema_version"],
            manifest=manifest,
            result_summary=data["result_summary"],
            validation_status=data["validation_status"],
            validation_details=data["validation_details"],
            artefacts=data["artefacts"],
        )
