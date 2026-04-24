"""Unit tests for utils/climbing.py — enum ↔ CUSTOM_FIELD_KEYS alignment."""

import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

import pytest  # pylint: disable=wrong-import-position

from intervals_mcp_server.utils.climbing import (  # pylint: disable=wrong-import-position
    CUSTOM_FIELD_KEYS,
    Discipline,
    FieldSpec,
    SessionFocus,
)


def test_discipline_values_are_lowercase_snake_case() -> None:
    for d in Discipline:
        assert d.value == d.value.lower()
        assert " " not in d.value


def test_session_focus_values_are_lowercase() -> None:
    for f in SessionFocus:
        assert f.value == f.value.lower()
        assert " " not in f.value


def test_discipline_options_match_custom_field_spec() -> None:
    spec_options = CUSTOM_FIELD_KEYS["discipline"].options
    assert spec_options == tuple(d.value for d in Discipline)


def test_session_focus_options_match_custom_field_spec() -> None:
    spec_options = CUSTOM_FIELD_KEYS["session_focus"].options
    assert spec_options == tuple(f.value for f in SessionFocus)


def test_custom_field_keys_covers_seven_fields() -> None:
    assert set(CUSTOM_FIELD_KEYS.keys()) == {
        "discipline",
        "indoor",
        "session_focus",
        "top_grade_sent",
        "top_grade_attempted",
        "sends",
        "attempts",
    }


def test_custom_field_spec_types_are_valid() -> None:
    for spec in CUSTOM_FIELD_KEYS.values():
        assert isinstance(spec, FieldSpec)
        assert spec.field_type in {"select", "bool", "text", "integer"}
        if spec.field_type == "select":
            assert spec.options, f"select field {spec.key} must have options"
        else:
            assert spec.options == (), f"non-select field {spec.key} must not have options"


def test_custom_field_keys_is_read_only() -> None:
    with pytest.raises(TypeError):
        CUSTOM_FIELD_KEYS["new_field"] = FieldSpec(key="new_field", field_type="text")  # type: ignore[index]
