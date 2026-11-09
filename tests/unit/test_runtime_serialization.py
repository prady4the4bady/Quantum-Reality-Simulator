"""Unit tests for canonical serialisation helpers."""

from __future__ import annotations

import json
import math
from typing import Any

import pytest

from qrs.runtime.serialization import canonical_json_dumps, freeze_scalar_mapping


def test_canonical_json_sorts_keys_and_uses_compact_separators() -> None:
    text = canonical_json_dumps({"b": 1, "a": [True, None]})

    assert text == '{"a":[true,null],"b":1}'


def test_canonical_json_preserves_unicode() -> None:
    assert canonical_json_dumps({"label": "mu \u03bc"}) == '{"label":"mu \u03bc"}'


def test_canonical_json_round_trip() -> None:
    payload = {"schema": 1, "values": [1, 2.5, "x"], "nested": {"a": False}}

    assert json.loads(canonical_json_dumps(payload)) == payload


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_canonical_json_rejects_non_finite_numbers(value: float) -> None:
    with pytest.raises(ValueError):
        canonical_json_dumps({"x": value})


def test_canonical_json_rejects_non_json_type() -> None:
    with pytest.raises(TypeError):
        canonical_json_dumps({"x": {1, 2}})


def test_freeze_scalar_mapping_copies_and_normalises_values() -> None:
    source: dict[str, Any] = {
        "integer": 3,
        "floating": 2,
        "boolean": True,
        "nothing": None,
        "text": "x",
    }

    frozen = freeze_scalar_mapping(source, "value")

    assert dict(frozen) == {
        "integer": 3,
        "floating": 2.0,
        "boolean": True,
        "nothing": None,
        "text": "x",
    }
    source["integer"] = 9
    assert frozen["integer"] == 3
    with pytest.raises(TypeError):
        frozen["new"] = 1.0  # type: ignore[index]


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_freeze_scalar_mapping_rejects_non_finite_numbers(value: float) -> None:
    with pytest.raises(ValueError, match=r"value\['x'\] must be finite"):
        freeze_scalar_mapping({"x": value}, "value")


@pytest.mark.parametrize("key", ["", 1, None])
def test_freeze_scalar_mapping_rejects_invalid_keys(key: object) -> None:
    with pytest.raises(TypeError, match="keys must be non-empty strings"):
        freeze_scalar_mapping({key: 1.0}, "value")


def test_freeze_scalar_mapping_rejects_nested_values() -> None:
    with pytest.raises(TypeError, match="must be a JSON scalar"):
        freeze_scalar_mapping({"x": [1.0]}, "value")


def test_freeze_scalar_mapping_rejects_non_mapping() -> None:
    with pytest.raises(TypeError, match="value must be a mapping"):
        freeze_scalar_mapping([("x", 1.0)], "value")  # type: ignore[arg-type]
