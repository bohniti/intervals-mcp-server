"""Unit tests for utils/wellness.py + tools/wellness.py::write_wellness_entry (write tool, lands in Plan 02-03)."""

import asyncio  # noqa: F401  # used by Plan 02-03 stubs once filled
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

import pytest  # pylint: disable=wrong-import-position

from intervals_mcp_server.utils.wellness import (  # pylint: disable=wrong-import-position
    PARAM_TO_API_FIELD,
    WELLNESS_RANGES,
    build_wellness_put_body,
    sleep_hours_to_secs,
)


# --------------------------------------------------------------------------- #
# Helper-layer tests (full bodies — verify utils/wellness.py behavior).
# --------------------------------------------------------------------------- #


def test_sleep_hours_to_secs_basic() -> None:
    assert sleep_hours_to_secs(8.0) == 28800
    assert sleep_hours_to_secs(7.5) == 27000
    assert sleep_hours_to_secs(0) == 0


def test_sleep_hours_to_secs_rejects_negative() -> None:
    with pytest.raises(ValueError):
        sleep_hours_to_secs(-1.0)


def test_build_wellness_put_body_drops_none() -> None:
    body = build_wellness_put_body({"soreness": 3, "fatigue": None, "stress": 2})
    assert body == {"soreness": 3, "stress": 2}


def test_build_wellness_put_body_translates_names() -> None:
    body = build_wellness_put_body({"resting_hr": 51, "sleep_quality": 3})
    assert body == {"restingHR": 51, "sleepQuality": 3}


def test_build_wellness_put_body_converts_sleep_hours() -> None:
    body = build_wellness_put_body({"sleep_hours": 8.0})
    assert body == {"sleepSecs": 28800}


def test_build_wellness_put_body_empty_input_returns_empty() -> None:
    assert build_wellness_put_body({}) == {}


def test_build_wellness_put_body_unknown_key_raises() -> None:
    with pytest.raises(KeyError):
        build_wellness_put_body({"finger_skin": 5})


def test_param_to_api_field_covers_all_public_params() -> None:
    expected = {
        "sleep_hours",
        "sleep_quality",
        "soreness",
        "fatigue",
        "motivation",
        "stress",
        "mood",
        "hrv",
        "resting_hr",
    }
    assert set(PARAM_TO_API_FIELD.keys()) == expected


def test_wellness_helpers() -> None:
    """Suite-meta entry point referenced in 02-VALIDATION.md row 02-02."""
    # Helpers exercised by all tests above; this anchor confirms collection works.
    assert callable(sleep_hours_to_secs)
    assert callable(build_wellness_put_body)
    # MappingProxyType-ish guard: read-only mapping rejects assignment.
    with pytest.raises(TypeError):
        WELLNESS_RANGES["x"] = (1, 5)  # type: ignore[index]


# --------------------------------------------------------------------------- #
# Wave-0 stubs — Plan 02-03 fills these once write_wellness_entry exists.
# Names referenced by 02-VALIDATION.md "Per-Requirement Falsifiable Assertions".
# --------------------------------------------------------------------------- #


def test_signature_aligns_with_wellness_ranges() -> None:
    """Every numeric Optional param in write_wellness_entry's signature must
    have a key in WELLNESS_RANGES, and every WELLNESS_RANGES key must be a
    param. Filled in plan 02-03 once write_wellness_entry exists.
    """
    pytest.skip("filled in plan 02-03 once write_wellness_entry exists")


def test_wellness_tool_registered() -> None:
    pytest.skip("filled in plan 02-03 once write_wellness_entry is registered")


def test_write_wellness_entry_happy_path() -> None:
    pytest.skip("filled in plan 02-03")


def test_write_wellness_entry_rejects_empty_call() -> None:
    pytest.skip("filled in plan 02-03")


def test_write_wellness_entry_rejects_out_of_range() -> None:
    pytest.skip("filled in plan 02-03")


def test_write_wellness_entry_readback_failure_no_readme_pointer() -> None:
    pytest.skip("filled in plan 02-03")


def test_write_wellness_entry_api_error_on_put() -> None:
    pytest.skip("filled in plan 02-03")


def test_write_wellness_entry_unsupplied_field_dropped() -> None:
    pytest.skip("filled in plan 02-03")


def test_subset_upsert_does_not_overwrite_unrelated_fields() -> None:
    pytest.skip("filled in plan 02-03 - WELL-02 assertion in 02-VALIDATION.md")


def test_sleep_hours_converts_to_secs_and_upserts() -> None:
    pytest.skip("filled in plan 02-03 - WELL-01 assertion in 02-VALIDATION.md")


def test_out_of_range_rejects_pre_api() -> None:
    pytest.skip("filled in plan 02-03 - WELL-03 assertion in 02-VALIDATION.md")
