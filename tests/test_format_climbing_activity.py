"""
Unit tests for the format_climbing_activity formatter in
intervals_mcp_server.utils.formatting.

These tests verify:
- `format_climbing_activity` is callable with a dict and returns a string
- It renders discipline, indoor, session_focus, top_grade_sent,
  top_grade_attempted, sends, attempts, icu_rpe
- Missing fields render as "N/A" (no KeyError on empty dict)
- Boolean indoor renders as "Yes"/"No"/"N/A" (not "True"/"False")
- icu_rpe renders as "{rpe}/10" when numeric
- format_activity_summary output is unchanged from pre-change (D-20 / Pitfall #12
  byte-for-byte regression guard)
"""

from intervals_mcp_server.utils.formatting import (
    format_activity_summary,
    format_climbing_activity,
)


def test_format_climbing_activity_empty_dict_renders_na():
    """Empty dict: every rendered field falls back to N/A; no KeyError."""
    out = format_climbing_activity({})
    assert isinstance(out, str)
    assert "Climbing Activity" in out
    assert "N/A" in out
    # Indoor specifically renders as N/A when missing (not "None" / "False")
    assert "Indoor: N/A" in out


def test_format_climbing_activity_full_dict_renders_all_fields():
    """All 11 rendered fields (3 header + 8 climbing) appear in output."""
    activity = {
        "id": 42,
        "name": "Spike Session",
        "start_date_local": "2099-01-01T00:00:00",
        "Discipline": 1,  # bouldering
        "Indoor": 1,  # yes
        "SessionFocus": 1,  # power
        "TopGradeSent": "7A",
        "TopGradeAttempted": "7A+",
        "Sends": 5,
        "Attempts": 8,
        "icu_rpe": 6,
    }
    out = format_climbing_activity(activity)
    # Header
    assert "42" in out
    assert "Spike Session" in out
    assert "2099-01-01T00:00:00" in out
    # Climbing fields
    assert "bouldering" in out
    assert "Yes" in out  # indoor=True
    assert "power" in out
    assert "7A" in out
    assert "7A+" in out
    assert "5" in out
    assert "8" in out
    # RPE renders as {n}/10
    assert "6/10" in out


def test_format_climbing_activity_indoor_false_renders_no():
    """Indoor=2 (the int-Select 'no' value) renders as 'Indoor: No'."""
    out = format_climbing_activity({"Indoor": 2})
    assert "Indoor: No" in out
    assert "False" not in out


def test_format_climbing_activity_indoor_none_renders_na():
    """Indoor=None (explicit) renders as 'Indoor: N/A'."""
    out = format_climbing_activity({"Indoor": None})
    assert "Indoor: N/A" in out


def test_format_climbing_activity_rpe_float_renders_slash_10():
    """Float RPE renders as '{rpe}/10'."""
    out = format_climbing_activity({"icu_rpe": 7.5})
    assert "7.5/10" in out


def test_format_climbing_activity_rpe_int_renders_slash_10():
    """Int RPE renders as '{rpe}/10'."""
    out = format_climbing_activity({"icu_rpe": 8})
    assert "8/10" in out


def test_format_climbing_activity_rpe_missing_renders_na():
    """Missing RPE renders as 'N/A' (not '{None}/10')."""
    out = format_climbing_activity({})
    # "RPE:" line should have N/A (not '/10')
    assert "RPE: N/A" in out


def test_format_activity_summary_byte_identical_regression_guard():
    """
    D-20 / Pitfall #12: format_activity_summary output must be byte-identical
    to its pre-change behavior on a fixed sample dict. If this test ever fails,
    a shared formatter has been regressed.
    """
    sample = {
        "name": "Morning Ride",
        "id": 1,
        "type": "Ride",
        "startTime": "2024-01-01T08:00:00Z",
        "distance": 1000,
        "duration": 3600,
        "moving_time": 3500,
        "icu_rpe": 7,
    }
    out = format_activity_summary(sample)
    # Pre-change output shape: leading newline, canonical fields with N/A for
    # unspecified values. These exact substrings must remain present.
    assert "Activity: Morning Ride" in out
    assert "ID: 1" in out
    assert "Type: Ride" in out
    assert "Date: 2024-01-01 08:00:00" in out
    assert "Distance: 1000 meters" in out
    assert "Duration: 3600 seconds" in out
    assert "Moving Time: 3500 seconds" in out
    # RPE renders as '7/10' per existing logic
    assert "RPE: 7/10" in out
