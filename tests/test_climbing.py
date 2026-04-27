"""Unit tests for utils/climbing.py — enum ↔ CUSTOM_FIELD_KEYS alignment."""

import asyncio
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


# ---------------------------------------------------------------------------
# Tool-layer tests for verify_custom_fields_setup (SETUP-02).
# Appended by Plan 05 after the utility-layer tests above.
#
# Shape note (Case B — readback heuristic per 01-SPIKE-FINDINGS.md):
# _verify_custom_fields_setup_impl inspects recent activity dicts for the
# top-level presence of CUSTOM_FIELD_KEYS entries. The fake responses below
# are therefore lists of activity dicts, NOT lists of definition dicts.
# ---------------------------------------------------------------------------


def _make_fake_all_present() -> list[dict[str, object]]:
    """Fake activities-list response: every required CUSTOM_FIELD_KEYS key is
    present as a top-level field on at least one activity.
    """
    activity: dict[str, object] = {
        "id": "i1",
        "name": "Session with all climbing fields",
        "type": "WeightTraining",
    }
    for key in CUSTOM_FIELD_KEYS:
        activity[key] = None  # presence is enough for the heuristic
    return [activity]


def _make_fake_missing(missing_keys: set[str]) -> list[dict[str, object]]:
    """Fake activities-list response where `missing_keys` do NOT appear on
    any returned activity, but all other CUSTOM_FIELD_KEYS do.
    """
    activity: dict[str, object] = {
        "id": "i1",
        "name": "Session with partial fields",
        "type": "WeightTraining",
    }
    for key in CUSTOM_FIELD_KEYS:
        if key not in missing_keys:
            activity[key] = None
    return [activity]


def test_verify_tool_registered() -> None:
    """verify_custom_fields_setup must be importable from the server module."""
    from intervals_mcp_server.server import (  # noqa: F401
        verify_custom_fields_setup as server_verify,
    )
    from intervals_mcp_server.tools.climbing import (
        verify_custom_fields_setup as tool_verify,
    )
    assert server_verify is tool_verify


def test_verify_custom_fields_setup_all_present(monkeypatch: pytest.MonkeyPatch) -> None:
    from intervals_mcp_server.tools.climbing import verify_custom_fields_setup

    sample = _make_fake_all_present()

    async def fake_request(*_args: object, **_kwargs: object) -> object:
        return sample

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )
    result = asyncio.run(verify_custom_fields_setup(athlete_id="i1"))
    assert "All required" in result


def test_verify_custom_fields_setup_all_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    from intervals_mcp_server.tools.climbing import verify_custom_fields_setup

    async def fake_request(*_args: object, **_kwargs: object) -> object:
        return []  # no activities -> nothing defined

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )
    result = asyncio.run(verify_custom_fields_setup(athlete_id="i1"))
    assert result.startswith("Missing required Intervals.icu custom fields")
    for key in CUSTOM_FIELD_KEYS:
        assert key in result, f"missing field {key} must be named in error"
    assert "See README section 'Climbing setup" in result


def test_verify_custom_fields_setup_some_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    from intervals_mcp_server.tools.climbing import verify_custom_fields_setup

    missing = {"sends", "attempts", "indoor"}
    sample = _make_fake_missing(missing)

    async def fake_request(*_args: object, **_kwargs: object) -> object:
        return sample

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )
    result = asyncio.run(verify_custom_fields_setup(athlete_id="i1"))
    for key in missing:
        assert key in result, f"missing field {key} must be named"
    assert "See README section 'Climbing setup" in result


def test_verify_custom_fields_setup_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from intervals_mcp_server.tools.climbing import verify_custom_fields_setup

    async def fake_request(*_args: object, **_kwargs: object) -> object:
        return {"error": True, "message": "boom", "status_code": 500}

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )
    result = asyncio.run(verify_custom_fields_setup(athlete_id="i1"))
    assert result.startswith("Error") or "error" in result.lower()
    # Must NOT claim success when the upstream errored
    assert "All required" not in result


def test_verify_internal_helper_returns_tuple(monkeypatch: pytest.MonkeyPatch) -> None:
    from intervals_mcp_server.tools.climbing import _verify_custom_fields_setup_impl

    async def fake_request(*_args: object, **_kwargs: object) -> object:
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )
    ok, missing, message = asyncio.run(
        _verify_custom_fields_setup_impl("i1", None)
    )
    assert ok is False
    assert isinstance(missing, list)
    assert len(missing) == len(CUSTOM_FIELD_KEYS)
    assert isinstance(message, str)
    assert ok is (len(missing) == 0)


# ---------------------------------------------------------------------------
# Formatter tests for format_climbing_activity (CLIMB-10 — formatting flavour).
# Phase 2 contribution: the existing Phase 1 renderer already covers all 11
# fields including icu_rpe. These tests lock the current behaviour so any
# future edit that drops or reshapes a field fails fast.
# ---------------------------------------------------------------------------


def test_format_climbing_activity_renders_icu_rpe() -> None:
    """CLIMB-10 (formatting flavour): post-enrichment readback renders icu_rpe
    and all supplied climbing fields without regressing the 11 existing fields.
    """
    from intervals_mcp_server.utils.formatting import format_climbing_activity

    fully_populated = {
        "id": "i142495224",
        "name": "Bouldering session",
        "start_date_local": "2099-01-01T00:00:00",
        "discipline": "bouldering",
        "indoor": True,
        "session_focus": "power",
        "top_grade_sent": "6A+",
        "top_grade_attempted": "7A",
        "sends": 4,
        "attempts": 7,
        "icu_rpe": 6,
    }
    rendered = format_climbing_activity(fully_populated)
    # All 11 fields render with their values.
    assert "Climbing Activity" in rendered
    assert "ID: i142495224" in rendered
    assert "Name: Bouldering session" in rendered
    assert "Date: 2099-01-01T00:00:00" in rendered
    assert "Discipline: bouldering" in rendered
    assert "Indoor: Yes" in rendered
    assert "Session focus: power" in rendered
    assert "Top grade sent: 6A+" in rendered
    assert "Top grade attempted: 7A" in rendered
    assert "Sends: 4" in rendered
    assert "Attempts: 7" in rendered
    assert "RPE: 6/10" in rendered


def test_format_climbing_activity_handles_empty_activity() -> None:
    """Defensive — a freshly-created activity with no climbing fields renders
    structurally with N/A placeholders (carry-forward from Phase 1 behavior).
    """
    from intervals_mcp_server.utils.formatting import format_climbing_activity

    rendered = format_climbing_activity({})
    # 11-field structural assertion — N/A placeholders for missing data.
    assert rendered.count("N/A") >= 9, rendered  # 9 fields use N/A; 'indoor' renders as "N/A"; rpe as "N/A"
    assert "Climbing Activity" in rendered
    assert "Indoor: N/A" in rendered
    assert "RPE: N/A" in rendered


def test_format_climbing_activity_indoor_false_renders_no() -> None:
    """`indoor: False` must render as 'No', not 'N/A' or 'False'."""
    from intervals_mcp_server.utils.formatting import format_climbing_activity

    rendered = format_climbing_activity({"indoor": False})
    assert "Indoor: No" in rendered


def test_format_climbing_activity_rpe_float_renders() -> None:
    """API may return icu_rpe as float; the renderer accepts both int and float."""
    from intervals_mcp_server.utils.formatting import format_climbing_activity

    rendered = format_climbing_activity({"icu_rpe": 6.0})
    assert "RPE: 6.0/10" in rendered


def test_format_climbing_activity_renders_existing_fields_unchanged() -> None:
    """I-07 fix: snapshot regression guard. For a fixed Phase-1-shaped input, the renderer
    output MUST byte-equal a captured expected string. Replaces the previous regex-based
    'function body unchanged' check that silently passed on missing keywords.

    If the renderer body changes in a way that alters output, this test fails — that is
    the only correct way to detect regression.
    """
    from intervals_mcp_server.utils.formatting import format_climbing_activity

    snapshot_input = {
        "id": "phase1-snapshot",
        "name": "Phase 1 baseline",
        "start_date_local": "2025-01-01T00:00:00",
    }
    actual = format_climbing_activity(snapshot_input)

    # Captured by running format_climbing_activity(snapshot_input) once with the
    # current Phase-1-shaped renderer body. Any future edit to the renderer that
    # alters this output for the same input must update this expected string in
    # the same commit, making the regression intentional and reviewable.
    expected = (
        "Climbing Activity\n"
        "  ID: phase1-snapshot\n"
        "  Name: Phase 1 baseline\n"
        "  Date: 2025-01-01T00:00:00\n"
        "  Discipline: N/A\n"
        "  Indoor: N/A\n"
        "  Session focus: N/A\n"
        "  Top grade sent: N/A\n"
        "  Top grade attempted: N/A\n"
        "  Sends: N/A\n"
        "  Attempts: N/A\n"
        "  RPE: N/A\n"
    )
    assert actual == expected, (
        f"format_climbing_activity output drifted from the captured snapshot.\n"
        f"Expected:\n{expected!r}\n"
        f"Actual:\n{actual!r}"
    )
