"""Canonical JSON encoding and flat scalar freezing for runtime records.

Canonical JSON here means UTF-8 text produced with sorted object keys, compact
separators, and ``allow_nan=False``. The same encoding is used for hashing
manifests and for serialising envelopes, so an object has exactly one textual
representation.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from numbers import Integral, Real
from types import MappingProxyType
from typing import Any

type Scalar = str | int | float | bool | None
"""JSON scalar accepted in flat runtime mappings."""


def canonical_json_dumps(value: Any) -> str:
    """Return the canonical JSON text for ``value``.

    Parameters
    ----------
    value:
        JSON-compatible object. Mapping keys must be strings.

    Raises
    ------
    TypeError
        If ``value`` contains a non-JSON type such as a set or complex number.
    ValueError
        If a float is NaN or infinite. Canonical JSON never contains
        non-finite numbers.
    """

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def freeze_scalar_mapping(value: Mapping[str, Any], name: str) -> Mapping[str, Scalar]:
    """Validate a flat scalar mapping and return an immutable copy.

    Parameters
    ----------
    value:
        Candidate mapping. Keys must be non-empty strings. Values must be
        ``None``, booleans, integers, finite floats, or strings.
    name:
        Human-readable field name used in error messages.

    Raises
    ------
    TypeError
        If ``value`` is not a mapping, a key is invalid, or a value is not a
        JSON scalar.
    ValueError
        If a numeric value is NaN or infinite.
    """

    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping, got {type(value).__name__}")

    frozen: dict[str, Scalar] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key:
            raise TypeError(f"{name} keys must be non-empty strings, got {key!r}")
        label = f"{name}[{key!r}]"
        if item is None or isinstance(item, (bool, str)):
            frozen[key] = item
        elif isinstance(item, Integral):
            frozen[key] = int(item)
        elif isinstance(item, Real):
            number = float(item)
            if not math.isfinite(number):
                raise ValueError(f"{label} must be finite, got {number!r}")
            frozen[key] = number
        else:
            raise TypeError(f"{label} must be a JSON scalar, got {type(item).__name__}")

    return MappingProxyType(frozen)
