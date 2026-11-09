"""Versioned, deterministic experiment manifests for the QRS runtime.

A manifest is the complete, serialisable description of one experiment: the
model name, validated flat scalar parameters, solver configuration, random
seed metadata, creation time, and the executing environment. The
``experiment_id`` is a SHA-256 hash of the canonical content excluding only
``created_at`` and the identifier itself, so identical content produces
identical identifiers.

The manifest object is frozen and slotted. Field-level validation happens in
``__post_init__``; cross-field identifier integrity is checked when a manifest
is loaded with ``from_dict`` and again by the runner and reproducibility
checks, which also makes tampering detectable.
"""

from __future__ import annotations

import hashlib
import platform
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from numbers import Integral
from types import MappingProxyType
from typing import Any, Final

from qrs.classical.heat_diffusion import HEAT_MAX_ALPHA_RELATIVE_STD
from qrs.core.validation import require_finite_real, require_positive_finite
from qrs.runtime.serialization import Scalar, canonical_json_dumps, freeze_scalar_mapping

SCHEMA_VERSION: Final[int] = 1
"""Manifest schema version understood by this runtime."""

HARMONIC_OSCILLATOR: Final[str] = "harmonic_oscillator"
BELL_STATE: Final[str] = "bell_state"
HEAT_DIFFUSION: Final[str] = "heat_diffusion"
SUPPORTED_MODEL_NAMES: Final[frozenset[str]] = frozenset(
    {HARMONIC_OSCILLATOR, BELL_STATE, HEAT_DIFFUSION}
)

ENVIRONMENT_KEYS: Final[tuple[str, ...]] = (
    "python",
    "numpy",
    "scipy",
    "pennylane",
    "qrs",
    "platform",
)

_ENVIRONMENT_KEY_SET = frozenset(ENVIRONMENT_KEYS)
_MANIFEST_FIELDS = frozenset(
    {
        "schema_version",
        "experiment_id",
        "model_name",
        "parameters",
        "solver_config",
        "seed",
        "created_at",
        "environment",
    }
)
_EXPERIMENT_ID_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_CREATED_AT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
_CREATED_AT_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

_HARMONIC_PARAMETER_DEFAULTS: Final[Mapping[str, Scalar]] = MappingProxyType(
    {
        "mass": 1.0,
        "stiffness": 1.0,
        "initial_displacement": 0.0,
        "initial_velocity": 0.0,
        "t_start": 0.0,
        "t_end": 10.0,
    }
)
_HARMONIC_SOLVER_DEFAULTS: Final[Mapping[str, Scalar]] = MappingProxyType(
    {
        "num_points": 1001,
        "method": "DOP853",
        "rtol": 1e-10,
        "atol": 1e-12,
    }
)

_HEAT_DIFFUSION_PARAMETER_DEFAULTS: Final[Mapping[str, Scalar]] = MappingProxyType(
    {
        "alpha": 1e-6,
        "length": 0.1,
        "t_end": 600.0,
        "num_points": 401,
        "num_output_points": 101,
        "alpha_relative_std": 0.05,
        "num_samples": 10000,
    }
)

_HEAT_DIFFUSION_SOLVER_DEFAULTS: Final[Mapping[str, Scalar]] = MappingProxyType(
    {
        "rtol": 1e-10,
        "atol": 1e-12,
    }
)
_SUPPORTED_INTEGRATION_METHODS: Final[frozenset[str]] = frozenset(
    {"RK45", "RK23", "DOP853", "Radau", "BDF", "LSODA"}
)

type Environment = Mapping[str, str]
"""Flat environment fingerprint captured at manifest creation."""


def capture_environment() -> Environment:
    """Capture the executing Python and scientific package versions.

    Returns
    -------
    Mapping[str, str]
        Immutable mapping with the keys listed in ``ENVIRONMENT_KEYS``.
    """

    import numpy
    import pennylane
    import scipy

    import qrs

    captured = {
        "python": platform.python_version(),
        "numpy": str(numpy.__version__),
        "scipy": str(scipy.__version__),
        "pennylane": str(pennylane.__version__),
        "qrs": str(qrs.__version__),
        "platform": platform.platform(),
    }
    return MappingProxyType(captured)


def _utc_timestamp() -> str:
    """Return the current UTC time in the documented manifest format."""

    return datetime.now(UTC).strftime(_CREATED_AT_FORMAT)


def _validate_schema_version(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"schema_version must be an integer, got {type(value).__name__}")
    version = int(value)
    if version < SCHEMA_VERSION:
        raise ValueError(f"schema_version {version} is older than the supported version 1")
    if version > SCHEMA_VERSION:
        raise ValueError(f"schema_version {version} is newer than the supported version 1")
    return version


def _validate_model_name(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(f"model_name must be a string, got {type(value).__name__}")
    if value not in SUPPORTED_MODEL_NAMES:
        supported = ", ".join(sorted(SUPPORTED_MODEL_NAMES))
        raise ValueError(f"unknown model_name {value!r}; choose from {supported}")
    return value


def _validate_experiment_id(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(f"experiment_id must be a string, got {type(value).__name__}")
    if not _EXPERIMENT_ID_PATTERN.fullmatch(value):
        raise ValueError("experiment_id must be a 64-character lowercase SHA-256 hex digest")
    return value


def _validate_seed(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"seed must be an integer, got {type(value).__name__}")
    seed = int(value)
    if seed < 0:
        raise ValueError(f"seed must be non-negative, got {seed}")
    return seed


def _validate_created_at(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(f"created_at must be a string, got {type(value).__name__}")
    if not _CREATED_AT_PATTERN.fullmatch(value):
        raise ValueError("created_at must be UTC in the form YYYY-MM-DDTHH:MM:SSZ")
    try:
        datetime.strptime(value, _CREATED_AT_FORMAT)
    except ValueError as exc:
        raise ValueError(f"created_at is not a valid UTC timestamp: {value!r}") from exc
    return value


def _validate_environment(value: object) -> Environment:
    frozen = freeze_scalar_mapping(value, "environment")
    missing = _ENVIRONMENT_KEY_SET - set(frozen)
    if missing:
        names = ", ".join(sorted(missing))
        raise ValueError(f"environment is missing required keys: {names}")
    unknown = set(frozen) - _ENVIRONMENT_KEY_SET
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(f"environment contains unknown keys: {names}")
    for key, item in frozen.items():
        if not isinstance(item, str) or not item:
            raise TypeError(f"environment[{key!r}] must be a non-empty string")
    return MappingProxyType({key: frozen[key] for key in ENVIRONMENT_KEYS})  # type: ignore[misc]


def _validate_harmonic_parameters(parameters: Mapping[str, Scalar]) -> None:
    allowed = frozenset(_HARMONIC_PARAMETER_DEFAULTS)
    unknown = set(parameters) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(f"unknown harmonic_oscillator parameter(s): {names}")
    missing = allowed - set(parameters)
    if missing:
        names = ", ".join(sorted(missing))
        raise ValueError(f"harmonic_oscillator is missing parameter(s): {names}")

    require_positive_finite(parameters["mass"], "parameters['mass']")
    require_positive_finite(parameters["stiffness"], "parameters['stiffness']")
    require_finite_real(parameters["initial_displacement"], "parameters['initial_displacement']")
    require_finite_real(parameters["initial_velocity"], "parameters['initial_velocity']")
    start = require_finite_real(parameters["t_start"], "parameters['t_start']")
    end = require_finite_real(parameters["t_end"], "parameters['t_end']")
    if end <= start:
        raise ValueError(f"t_end must be greater than t_start, got ({start}, {end})")


def _validate_harmonic_solver_config(solver_config: Mapping[str, Scalar]) -> None:
    allowed = frozenset(_HARMONIC_SOLVER_DEFAULTS)
    unknown = set(solver_config) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(f"unknown harmonic_oscillator solver_config key(s): {names}")
    missing = allowed - set(solver_config)
    if missing:
        names = ", ".join(sorted(missing))
        raise ValueError(f"harmonic_oscillator is missing solver_config key(s): {names}")

    num_points = solver_config["num_points"]
    if isinstance(num_points, bool) or not isinstance(num_points, Integral):
        raise TypeError("solver_config['num_points'] must be an integer")
    if int(num_points) < 2:
        raise ValueError(f"solver_config['num_points'] must be at least 2, got {num_points!r}")

    method = solver_config["method"]
    if not isinstance(method, str) or not method:
        raise TypeError("solver_config['method'] must be a non-empty string")
    if method not in _SUPPORTED_INTEGRATION_METHODS:
        supported = ", ".join(sorted(_SUPPORTED_INTEGRATION_METHODS))
        raise ValueError(f"unsupported solver_config['method'] {method!r}; choose from {supported}")

    require_positive_finite(solver_config["rtol"], "solver_config['rtol']")
    require_positive_finite(solver_config["atol"], "solver_config['atol']")


def _validate_heat_diffusion_parameters(parameters: Mapping[str, Scalar]) -> None:
    allowed = frozenset(_HEAT_DIFFUSION_PARAMETER_DEFAULTS)
    unknown = set(parameters) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(f"unknown heat_diffusion parameter(s): {names}")
    missing = allowed - set(parameters)
    if missing:
        names = ", ".join(sorted(missing))
        raise ValueError(f"heat_diffusion is missing parameter(s): {names}")

    require_positive_finite(parameters["alpha"], "parameters['alpha']")
    require_positive_finite(parameters["length"], "parameters['length']")
    t_end = require_finite_real(parameters["t_end"], "parameters['t_end']")
    if t_end < 0.0:
        raise ValueError(f"parameters['t_end'] must be non-negative, got {t_end!r}")

    num_points = parameters["num_points"]
    if isinstance(num_points, bool) or not isinstance(num_points, Integral):
        raise TypeError("parameters['num_points'] must be an integer")
    if int(num_points) < 3:
        raise ValueError(f"parameters['num_points'] must be at least 3, got {num_points!r}")
    if int(num_points) % 2 == 0:
        raise ValueError(
            "parameters['num_points'] must be odd so that L/2 lies "
            f"on a grid point, got {num_points!r}"
        )

    num_output_points = parameters["num_output_points"]
    if isinstance(num_output_points, bool) or not isinstance(num_output_points, Integral):
        raise TypeError("parameters['num_output_points'] must be an integer")
    if int(num_output_points) < 2:
        raise ValueError(
            f"parameters['num_output_points'] must be at least 2, got {num_output_points!r}"
        )

    alpha_relative_std = require_positive_finite(
        parameters["alpha_relative_std"], "parameters['alpha_relative_std']"
    )
    if alpha_relative_std > HEAT_MAX_ALPHA_RELATIVE_STD:
        raise ValueError(
            f"parameters['alpha_relative_std'] must be at most "
            f"{HEAT_MAX_ALPHA_RELATIVE_STD} (larger values make a "
            f"non-positive sampled alpha likely), got {alpha_relative_std!r}"
        )

    num_samples = parameters["num_samples"]
    if isinstance(num_samples, bool) or not isinstance(num_samples, Integral):
        raise TypeError("parameters['num_samples'] must be an integer")
    if int(num_samples) < 2:
        raise ValueError(f"parameters['num_samples'] must be at least 2, got {num_samples!r}")


def _validate_heat_diffusion_solver_config(solver_config: Mapping[str, Scalar]) -> None:
    allowed = frozenset(_HEAT_DIFFUSION_SOLVER_DEFAULTS)
    unknown = set(solver_config) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(f"unknown heat_diffusion solver_config key(s): {names}")
    missing = allowed - set(solver_config)
    if missing:
        names = ", ".join(sorted(missing))
        raise ValueError(f"heat_diffusion is missing solver_config key(s): {names}")

    require_positive_finite(solver_config["rtol"], "solver_config['rtol']")
    require_positive_finite(solver_config["atol"], "solver_config['atol']")


def _validate_bell_parameters(parameters: Mapping[str, Scalar]) -> None:
    if parameters:
        names = ", ".join(sorted(parameters))
        raise ValueError(f"bell_state does not accept parameters, got: {names}")


def _validate_bell_solver_config(solver_config: Mapping[str, Scalar]) -> None:
    if solver_config:
        names = ", ".join(sorted(solver_config))
        raise ValueError(f"bell_state does not accept solver_config keys, got: {names}")


def _validate_model_fields(
    model_name: str,
    parameters: Mapping[str, Scalar],
    solver_config: Mapping[str, Scalar],
) -> None:
    if model_name == HARMONIC_OSCILLATOR:
        _validate_harmonic_parameters(parameters)
        _validate_harmonic_solver_config(solver_config)
    elif model_name == BELL_STATE:
        _validate_bell_parameters(parameters)
        _validate_bell_solver_config(solver_config)
    elif model_name == HEAT_DIFFUSION:
        _validate_heat_diffusion_parameters(parameters)
        _validate_heat_diffusion_solver_config(solver_config)
    else:  # pragma: no cover - model names are validated before this call
        raise ValueError(f"unknown model_name {model_name!r}")


def _hash_content(
    *,
    schema_version: int,
    model_name: str,
    parameters: Mapping[str, Scalar],
    solver_config: Mapping[str, Scalar],
    seed: int,
    environment: Environment,
) -> str:
    payload = {
        "schema_version": schema_version,
        "model_name": model_name,
        "parameters": dict(parameters),
        "solver_config": dict(solver_config),
        "seed": seed,
        "environment": dict(environment),
    }
    encoded = canonical_json_dumps(payload).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class ExperimentManifest:
    """Immutable description of one reproducible experiment.

    Attributes
    ----------
    schema_version:
        Manifest schema version. Only version ``1`` is accepted.
    experiment_id:
        Lowercase SHA-256 hex digest of the canonical manifest content.
    model_name:
        One of ``harmonic_oscillator``, ``bell_state``, or ``heat_diffusion``.
    parameters:
        Flat, immutable mapping of model parameters with JSON scalar values.
    solver_config:
        Flat, immutable mapping of solver settings with JSON scalar values.
    seed:
        Non-negative integer metadata. Neither implemented model uses
        randomness, so the seed does not alter numerical results.
    created_at:
        Creation time in UTC, formatted ``YYYY-MM-DDTHH:MM:SSZ``.
    environment:
        Immutable Python and package version fingerprint.
    """

    schema_version: int
    experiment_id: str
    model_name: str
    parameters: Mapping[str, Scalar]
    solver_config: Mapping[str, Scalar]
    seed: int
    created_at: str
    environment: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _validate_schema_version(self.schema_version))
        object.__setattr__(self, "experiment_id", _validate_experiment_id(self.experiment_id))
        object.__setattr__(self, "model_name", _validate_model_name(self.model_name))
        object.__setattr__(self, "parameters", freeze_scalar_mapping(self.parameters, "parameters"))
        object.__setattr__(
            self, "solver_config", freeze_scalar_mapping(self.solver_config, "solver_config")
        )
        object.__setattr__(self, "seed", _validate_seed(self.seed))
        object.__setattr__(self, "created_at", _validate_created_at(self.created_at))
        object.__setattr__(self, "environment", _validate_environment(self.environment))
        _validate_model_fields(self.model_name, self.parameters, self.solver_config)

    @classmethod
    def create(
        cls,
        *,
        model_name: str,
        parameters: Mapping[str, Any] | None = None,
        solver_config: Mapping[str, Any] | None = None,
        seed: int = 0,
        created_at: str | None = None,
        environment: Mapping[str, Any] | None = None,
    ) -> ExperimentManifest:
        """Create a manifest, filling documented defaults for the model.

        Harmonic-oscillator manifests receive every optional parameter and
        solver key explicitly so the serialised content is self-contained.
        Bell-state manifests require empty ``parameters`` and ``solver_config``.
        """

        model = _validate_model_name(model_name)
        timestamp = _utc_timestamp() if created_at is None else _validate_created_at(created_at)
        validated_seed = _validate_seed(seed)
        captured = capture_environment() if environment is None else environment

        if model == HARMONIC_OSCILLATOR:
            merged_parameters: dict[str, Scalar] = dict(_HARMONIC_PARAMETER_DEFAULTS)
            if parameters is not None:
                merged_parameters.update(_require_mapping(parameters, "parameters"))
            merged_solver: dict[str, Scalar] = dict(_HARMONIC_SOLVER_DEFAULTS)
            if solver_config is not None:
                merged_solver.update(_require_mapping(solver_config, "solver_config"))
        elif model == HEAT_DIFFUSION:
            merged_parameters = dict(_HEAT_DIFFUSION_PARAMETER_DEFAULTS)
            if parameters is not None:
                merged_parameters.update(_require_mapping(parameters, "parameters"))
            merged_solver = dict(_HEAT_DIFFUSION_SOLVER_DEFAULTS)
            if solver_config is not None:
                merged_solver.update(_require_mapping(solver_config, "solver_config"))
        else:
            merged_parameters = dict(_require_empty_mapping(parameters, "parameters", model))
            merged_solver = dict(_require_empty_mapping(solver_config, "solver_config", model))

        frozen_parameters = freeze_scalar_mapping(merged_parameters, "parameters")
        frozen_solver = freeze_scalar_mapping(merged_solver, "solver_config")
        frozen_environment = _validate_environment(captured)
        _validate_model_fields(model, frozen_parameters, frozen_solver)

        identifier = _hash_content(
            schema_version=SCHEMA_VERSION,
            model_name=model,
            parameters=frozen_parameters,
            solver_config=frozen_solver,
            seed=validated_seed,
            environment=frozen_environment,
        )
        return cls(
            schema_version=SCHEMA_VERSION,
            experiment_id=identifier,
            model_name=model,
            parameters=frozen_parameters,
            solver_config=frozen_solver,
            seed=validated_seed,
            created_at=timestamp,
            environment=frozen_environment,
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ExperimentManifest:
        """Load a manifest from serialised data and verify its identifier.

        Raises
        ------
        TypeError
            If ``data`` is not a mapping, required fields are missing, unknown
            fields are present, or a field has the wrong type.
        ValueError
            If a field value is invalid or the stored ``experiment_id`` does
            not match the canonical content.
        """

        if not isinstance(data, Mapping):
            raise TypeError(f"manifest data must be a mapping, got {type(data).__name__}")

        keys = set(data)
        missing = _MANIFEST_FIELDS - keys
        if missing:
            names = ", ".join(sorted(missing))
            raise TypeError(f"manifest data is missing required fields: {names}")
        unknown = keys - _MANIFEST_FIELDS
        if unknown:
            names = ", ".join(sorted(str(key) for key in unknown))
            raise TypeError(f"manifest data contains unknown fields: {names}")

        manifest = cls(**dict(data))
        manifest.verify_experiment_id()
        return manifest

    def to_dict(self) -> dict[str, Any]:
        """Return a plain, JSON-compatible dictionary representation."""

        return {
            "schema_version": self.schema_version,
            "experiment_id": self.experiment_id,
            "model_name": self.model_name,
            "parameters": dict(self.parameters),
            "solver_config": dict(self.solver_config),
            "seed": self.seed,
            "created_at": self.created_at,
            "environment": dict(self.environment),
        }

    def canonical_json(self) -> str:
        """Return the canonical JSON encoding of this manifest."""

        return canonical_json_dumps(self.to_dict())

    def verify_experiment_id(self) -> None:
        """Raise ``ValueError`` unless ``experiment_id`` matches the content."""

        expected = _hash_content(
            schema_version=self.schema_version,
            model_name=self.model_name,
            parameters=self.parameters,
            solver_config=self.solver_config,
            seed=self.seed,
            environment=self.environment,
        )
        if self.experiment_id != expected:
            raise ValueError(
                "experiment_id does not match the canonical manifest content; "
                f"expected {expected}, got {self.experiment_id}"
            )


def _require_mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping, got {type(value).__name__}")
    return value


def _require_empty_mapping(
    value: Mapping[str, Any] | None,
    name: str,
    model_name: str,
) -> Mapping[str, Any]:
    if value is None:
        return {}
    mapping = _require_mapping(value, name)
    if mapping:
        keys = ", ".join(sorted(str(key) for key in mapping))
        raise ValueError(f"{model_name} requires empty {name}; got: {keys}")
    return mapping
