"""Unit + integration tests for utils/status.py and tools/status.py.

Covers STAT-01 (single tool, three sections), STAT-02 (CTL/ATL/TSB + wellness
blend), STAT-03 (RPE data-quality flag with naming), STAT-04 (400-600 token
budget verified via tiktoken cl100k_base per CONTEXT D-12).
"""

import asyncio
import inspect
import os
import pathlib
import sys
from datetime import datetime, timedelta
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

import pytest  # pylint: disable=wrong-import-position

from intervals_mcp_server.utils.status import (  # pylint: disable=wrong-import-position
    MIN_RPE_SAMPLE,
    RPE_MISSING_THRESHOLD,
    TSB_BANDS,
    WINDOW_DAYS_LONG_TERM,
    WINDOW_DAYS_RPE,
    WINDOW_DAYS_WEEKLY,
    compute_rpe_coverage,
    format_longterm_section,
    format_status_report,
    format_today_section,
    format_weekly_section,
    tsb_band,
)

# ---------------------------------------------------------------------------
# Section 1 — Fixture helpers
# ---------------------------------------------------------------------------


def _make_fake_wellness_entries(
    end_date: str = "2026-04-28",
    days: int = 42,
    *,
    ctl_seed: float = 50.0,
    atl_seed: float = 45.0,
    extra_fields: bool = True,
) -> list[dict[str, Any]]:
    """List of wellness daily entries with ctl/atl populated.

    Newest entry has date == end_date; oldest is `days-1` days earlier.
    Mirrors the Intervals.icu /athlete/{id}/wellness shape from Phase 1
    spike findings.

    When extra_fields=True (default), each entry also has sleepSecs,
    soreness, fatigue, hrv, and restingHR populated so the wellness-blend
    bullets in format_today_section have data to render.
    """
    end = datetime.strptime(end_date, "%Y-%m-%d")
    entries: list[dict[str, Any]] = []
    for i in range(days):
        d = (end - timedelta(days=i)).strftime("%Y-%m-%d")
        entry: dict[str, Any] = {
            "id": d,
            "date": d,
            "ctl": ctl_seed + i * 0.1,
            "atl": atl_seed + i * 0.05,
        }
        if extra_fields:
            entry["sleepSecs"] = int((7.5 + (i % 3) * 0.25) * 3600)
            entry["soreness"] = 2 + (i % 3 == 0)
            entry["fatigue"] = 2 + (i % 4 == 0)
            entry["hrv"] = 55 + (i % 5)
            entry["restingHR"] = 52 + (i % 4)
        entries.append(entry)
    return entries


def _make_fake_climbing_activity(
    activity_id: str,
    date: str,
    *,
    icu_rpe: int | None = 7,
) -> dict[str, Any]:
    """Climbing activity (type=WeightTraining) with optional rpe."""
    return {
        "id": activity_id,
        "type": "WeightTraining",
        "start_date_local": f"{date}T00:00:00",
        "icu_rpe": icu_rpe,
    }


# ---------------------------------------------------------------------------
# Section 2 — utils/status.py unit tests
# ---------------------------------------------------------------------------

# --- 2a. tsb_band — every D-03 boundary ---


@pytest.mark.parametrize(
    "tsb,expected",
    [
        (100.0, "Burnt out / Detraining"),
        (25.1, "Burnt out / Detraining"),
        (25.0, "Fresh"),
        (10.0, "Fresh"),
        (5.1, "Fresh"),
        (5.0, "Balanced"),
        (0.0, "Balanced"),
        (-9.9, "Balanced"),
        (-10.0, "Balanced"),
        (-10.1, "Fatigued (productive load)"),
        (-20.0, "Fatigued (productive load)"),
        (-25.0, "Fatigued (productive load)"),
        (-25.1, "Risk"),
        (-100.0, "Risk"),
    ],
)
def test_tsb_band_every_boundary(tsb: float, expected: str) -> None:
    """CONTEXT D-03 — every band boundary value returns the locked label."""
    assert tsb_band(tsb) == expected


def test_tsb_bands_constant_has_five_entries() -> None:
    """The constants table should document all five bands (grep-discoverable
    even though tsb_band uses chained-if internally)."""
    assert len(TSB_BANDS) == 5
    labels = {band[2] for band in TSB_BANDS}
    assert labels == {
        "Burnt out / Detraining",
        "Fresh",
        "Balanced",
        "Fatigued (productive load)",
        "Risk",
    }


def test_window_and_threshold_constants_locked() -> None:
    """CONTEXT D-06, D-08, D-11 — window sizes and thresholds must match spec values."""
    # Window sizes (D-06)
    assert WINDOW_DAYS_WEEKLY == 7
    assert WINDOW_DAYS_LONG_TERM == 42
    assert WINDOW_DAYS_RPE == 14
    # RPE thresholds (D-08, D-11)
    assert RPE_MISSING_THRESHOLD == 0.30
    assert MIN_RPE_SAMPLE == 3


# --- 2b. compute_rpe_coverage — D-10 semantics ---


def test_compute_rpe_coverage_empty() -> None:
    assert compute_rpe_coverage([]) == (0, 0)


def test_compute_rpe_coverage_all_present() -> None:
    activities = [{"icu_rpe": 7}, {"icu_rpe": 8}, {"icu_rpe": 5}]
    assert compute_rpe_coverage(activities) == (0, 3)


def test_compute_rpe_coverage_all_missing() -> None:
    activities: list[dict[str, Any]] = [{}, {"icu_rpe": None}, {"id": "x"}]
    assert compute_rpe_coverage(activities) == (3, 3)


def test_compute_rpe_coverage_mixed_with_zero_is_data() -> None:
    """CONTEXT D-10 — a literal icu_rpe == 0 IS logged data (NOT missing)."""
    activities: list[dict[str, Any]] = [
        {"icu_rpe": 7},          # present
        {"icu_rpe": None},       # missing
        {},                       # missing (key absent)
        {"icu_rpe": 0},          # PRESENT — D-10 explicit
    ]
    assert compute_rpe_coverage(activities) == (2, 4)


# --- 2c. format_today_section — graceful + happy + walk-back ---


def test_format_today_section_no_entry() -> None:
    """CONTEXT D-13 — no wellness within 7 days renders the locked one-liner."""
    out = format_today_section(None, [], 0)
    assert out == "## Today\n- No wellness data in last 7 days.\n"


def test_format_today_section_no_ctl_or_atl() -> None:
    """CONTEXT D-13 — entry exists but ctl/atl absent renders the second locked one-liner."""
    out = format_today_section({"date": "2026-04-28", "ctl": None, "atl": None}, [], 0)
    assert out == "## Today\n- No CTL/ATL trend data in last 7 days.\n"


def test_format_today_section_happy_path() -> None:
    """CONTEXT D-02 — readiness shows TSB number AND verbal band."""
    out = format_today_section({"ctl": 50.0, "atl": 47.0}, [], 0)
    assert "## Today" in out
    assert "Readiness: Balanced (TSB +3.0)" in out, out


def test_format_today_section_walk_back_note() -> None:
    """CONTEXT D-07 — walk-back surfaces 'Latest fitness data: N day(s) ago.' line."""
    out = format_today_section({"ctl": 50.0, "atl": 47.0}, [], 3)
    assert "Latest fitness data: 3 day(s) ago." in out, out


def test_format_today_section_negative_tsb_signed_format() -> None:
    """The TSB number must be signed (D-02 — claude reads magnitude)."""
    out = format_today_section({"ctl": 40.0, "atl": 50.0}, [], 0)
    # tsb = -10.0 -> "Balanced" band (boundary inclusive on upper side, exclusive on lower)
    assert "Readiness: Balanced (TSB -10.0)" in out, out


# --- 2d. format_weekly_section / format_longterm_section — graceful + happy ---


def test_format_weekly_section_empty() -> None:
    """CONTEXT D-13 — exact one-liner when no data."""
    assert format_weekly_section([]) == "## This Week\n- No CTL/ATL trend data in last 7 days.\n"


def test_format_weekly_section_single_entry_is_empty() -> None:
    """Need at least 2 entries to compute a delta — single entry renders empty path."""
    out = format_weekly_section([{"date": "2026-04-28", "ctl": 50.0, "atl": 45.0}])
    assert out == "## This Week\n- No CTL/ATL trend data in last 7 days.\n"


def test_format_weekly_section_happy_path() -> None:
    out = format_weekly_section([
        {"date": "2026-04-22", "ctl": 50.0, "atl": 45.0},
        {"date": "2026-04-28", "ctl": 52.0, "atl": 48.0},
    ])
    assert "## This Week" in out
    assert "CTL: 50.0 → 52.0 (+2.0)" in out, out
    assert "ATL: 45.0 → 48.0 (+3.0)" in out, out
    assert "TSB (end of week): +4.0" in out, out


def test_format_weekly_section_handles_pathological_types() -> None:
    """Security T-04-02 — non-numeric ctl/atl should be filtered, not crash."""
    out = format_weekly_section([
        {"date": "2026-04-22", "ctl": "N/A", "atl": 45.0},  # bad ctl
        {"date": "2026-04-28", "ctl": 52.0, "atl": None},   # bad atl
    ])
    # Both rows are filtered out -> graceful empty path.
    assert out == "## This Week\n- No CTL/ATL trend data in last 7 days.\n"


def test_format_longterm_section_empty() -> None:
    """CONTEXT D-13 — exact one-liner when no data, mentions 42 days."""
    assert format_longterm_section([]) == "## Long-Term Trend\n- No CTL/ATL trend data in last 42 days.\n"


def test_format_longterm_section_happy_path() -> None:
    entries = _make_fake_wellness_entries(end_date="2026-04-28", days=42, extra_fields=False)
    out = format_longterm_section(entries)
    assert "## Long-Term Trend" in out
    assert "over 42 days" in out, out
    # Mean line shows two means
    assert "42d mean CTL:" in out, out
    assert "mean ATL:" in out, out


# --- 2e. format_status_report — concatenation orchestrator ---


def test_format_status_report_no_warning() -> None:
    out = format_status_report(
        "## Today\n- A\n",
        "## This Week\n- B\n",
        "## Long-Term Trend\n- C\n",
        None,
    )
    assert out == "## Today\n- A\n\n## This Week\n- B\n\n## Long-Term Trend\n- C\n"


def test_format_status_report_with_warning_appends() -> None:
    out = format_status_report(
        "## Today\n- A\n",
        "## This Week\n- B\n",
        "## Long-Term Trend\n- C\n",
        "> Note: warning text",
    )
    assert out.endswith("> Note: warning text\n"), repr(out)
    # Sections still present in order
    assert out.index("## Today") < out.index("## This Week") < out.index("## Long-Term Trend")


# ---------------------------------------------------------------------------
# Section 3 — tools/status.py integration tests
# NOTE: These tests import from intervals_mcp_server.tools.status which is
# produced by Plan 04-02 (running in a sibling worktree in Wave 2).
# In isolation (before merge), these tests will fail at IMPORT TIME with
# ModuleNotFoundError. This is expected and documented.
# The orchestrator runs the full test suite after both Wave 2 worktrees merge —
# that is where Section B is validated.
# ---------------------------------------------------------------------------

# --- 3a. Tool registration sanity ---


def test_status_tool_registered() -> None:
    """D-16 — get_training_status is async; signature has 3 optional params."""
    from intervals_mcp_server.tools.status import get_training_status  # type: ignore[import-not-found]

    assert inspect.iscoroutinefunction(get_training_status)
    sig = inspect.signature(get_training_status)
    assert list(sig.parameters) == ["athlete_id", "api_key", "as_of_date"], list(sig.parameters)
    for p in sig.parameters.values():
        assert p.default is None, (p.name, p.default)


# --- 3b. Hard validation paths (no HTTP) ---


def test_invalid_as_of_date_returns_error_no_http(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-19 — bad date format returns error WITHOUT calling make_intervals_request."""
    from intervals_mcp_server.tools.status import get_training_status  # type: ignore[import-not-found]

    counter = {"calls": 0}

    async def fake_request(*args: Any, **kwargs: Any) -> Any:
        counter["calls"] += 1
        return []

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.status.make_intervals_request", fake_request)

    result = asyncio.run(get_training_status(athlete_id="i1", as_of_date="not-a-date"))
    assert result == "Error: Invalid date format. Please use YYYY-MM-DD.", result
    assert counter["calls"] == 0


def test_missing_athlete_id_returns_error_no_http(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-22 carry-forward — missing athlete_id returns the canonical resolve error WITHOUT HTTP."""
    from intervals_mcp_server.tools.status import get_training_status  # type: ignore[import-not-found]

    monkeypatch.setenv("ATHLETE_ID", "")
    # Patch the module-level config snapshot — config is captured at import time.
    monkeypatch.setattr("intervals_mcp_server.tools.status.config.athlete_id", "")

    counter = {"calls": 0}

    async def fake_request(*args: Any, **kwargs: Any) -> Any:
        counter["calls"] += 1
        return []

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.status.make_intervals_request", fake_request)

    result = asyncio.run(get_training_status(as_of_date="2026-04-28"))
    assert "No athlete ID provided" in result, result
    assert counter["calls"] == 0


# --- 3c. Happy path — full data, three sections, two HTTP calls ---


def test_happy_path_three_sections_and_two_http_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """STAT-01 — full data renders three sections; exactly 2 GETs (D-04, D-09)."""
    from intervals_mcp_server.tools.status import get_training_status  # type: ignore[import-not-found]

    counters = {"wellness_get": 0, "activities_get": 0}
    captured_params: dict[str, dict[str, Any]] = {}

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and url.endswith("/wellness"):
            counters["wellness_get"] += 1
            captured_params["wellness"] = dict(params or {})
            return _make_fake_wellness_entries(end_date="2026-04-28", days=42)
        if method == "GET" and url.endswith("/activities"):
            counters["activities_get"] += 1
            captured_params["activities"] = dict(params or {})
            return [
                _make_fake_climbing_activity(f"i{i}", "2026-04-28", icu_rpe=7)
                for i in range(8)
            ]
        return []

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.status.make_intervals_request", fake_request)

    result = asyncio.run(get_training_status(athlete_id="i1", as_of_date="2026-04-28"))

    assert "## Today" in result
    assert "## This Week" in result
    assert "## Long-Term Trend" in result
    assert counters["wellness_get"] == 1
    assert counters["activities_get"] == 1

    # D-04 — 42-day window
    assert captured_params["wellness"]["newest"] == "2026-04-28"
    expected_longterm_start = (
        datetime(2026, 4, 28) - timedelta(days=WINDOW_DAYS_LONG_TERM - 1)
    ).strftime("%Y-%m-%d")
    assert captured_params["wellness"]["oldest"] == expected_longterm_start

    # D-09 — 14-day window
    assert captured_params["activities"]["newest"] == "2026-04-28"
    expected_rpe_start = (
        datetime(2026, 4, 28) - timedelta(days=WINDOW_DAYS_RPE - 1)
    ).strftime("%Y-%m-%d")
    assert captured_params["activities"]["oldest"] == expected_rpe_start


# --- 3d. Walk-back path (D-07) ---


def test_walk_back_when_today_lacks_ctl_atl(monkeypatch: pytest.MonkeyPatch) -> None:
    """CONTEXT D-07 — when today's entry has no ctl/atl, walk back up to 7 days."""
    from intervals_mcp_server.tools.status import get_training_status  # type: ignore[import-not-found]

    # Today (2026-04-28) entry lacks ctl/atl; entry from 3 days back has them.
    entries = _make_fake_wellness_entries(end_date="2026-04-28", days=10, extra_fields=False)
    # Wipe ctl/atl on the 3 most recent entries (today, day-1, day-2)
    for i in range(3):
        entries[i]["ctl"] = None
        entries[i]["atl"] = None
    # entries[3] is 2026-04-25 — the walk-back should land here (3 days ago).

    async def fake_request(url: str, **kwargs: Any) -> Any:
        if url.endswith("/wellness"):
            return entries
        return []

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.status.make_intervals_request", fake_request)

    result = asyncio.run(get_training_status(athlete_id="i1", as_of_date="2026-04-28"))
    # Today section should reference walk-back
    assert "Latest fitness data: 3 day(s) ago." in result, result


# --- 3e. RPE coverage flag (STAT-03 + D-08 + D-11) ---


def test_rpe_warning_fires_when_more_than_30_pct_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """STAT-03 / D-08 — >30% climbing activities lack icu_rpe AND >= MIN_RPE_SAMPLE
    -> explicit warning naming RPE."""
    from intervals_mcp_server.tools.status import get_training_status  # type: ignore[import-not-found]

    # 5 climbing activities, 3 lack RPE -> 60% missing, >= 3 sample = warning fires.
    activities = [
        _make_fake_climbing_activity("a1", "2026-04-22", icu_rpe=7),
        _make_fake_climbing_activity("a2", "2026-04-23", icu_rpe=None),
        _make_fake_climbing_activity("a3", "2026-04-24", icu_rpe=None),
        _make_fake_climbing_activity("a4", "2026-04-25", icu_rpe=None),
        _make_fake_climbing_activity("a5", "2026-04-26", icu_rpe=8),
    ]

    async def fake_request(url: str, **kwargs: Any) -> Any:
        if url.endswith("/wellness"):
            return _make_fake_wellness_entries(end_date="2026-04-28", days=42)
        if url.endswith("/activities"):
            return activities
        return []

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.status.make_intervals_request", fake_request)

    result = asyncio.run(get_training_status(athlete_id="i1", as_of_date="2026-04-28"))
    # STAT-03 — warning naming RPE
    assert "lack RPE" in result, result
    assert "RPE feeds rpeTSS / icu_rpe" in result, result
    # Suppression note must NOT also appear
    assert "low activity volume" not in result, result


def test_small_sample_suppresses_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    """CONTEXT D-11 — fewer than MIN_RPE_SAMPLE climbing activities -> low-volume note,
    NOT the threshold warning."""
    from intervals_mcp_server.tools.status import get_training_status  # type: ignore[import-not-found]

    # 2 climbing activities, both missing RPE — 100% but sample < 3.
    activities = [
        _make_fake_climbing_activity("a1", "2026-04-25", icu_rpe=None),
        _make_fake_climbing_activity("a2", "2026-04-26", icu_rpe=None),
    ]

    async def fake_request(url: str, **kwargs: Any) -> Any:
        if url.endswith("/wellness"):
            return _make_fake_wellness_entries(end_date="2026-04-28", days=42)
        if url.endswith("/activities"):
            return activities
        return []

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.status.make_intervals_request", fake_request)

    result = asyncio.run(get_training_status(athlete_id="i1", as_of_date="2026-04-28"))
    assert "low activity volume" in result, result
    assert "< 3 sessions in last 14 days" in result, result
    # Threshold warning text must NOT appear
    assert "RPE feeds rpeTSS / icu_rpe" not in result, result


def test_non_climbing_activities_excluded_from_rpe_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-09 — only type=='WeightTraining' counts; runs/rides ignored."""
    from intervals_mcp_server.tools.status import get_training_status  # type: ignore[import-not-found]

    # 3 non-climbing activities (Run, Ride, Swim) plus 1 climbing with RPE.
    activities = [
        {"id": "r1", "type": "Run", "icu_rpe": None, "start_date_local": "2026-04-25T00:00:00"},
        {"id": "r2", "type": "Ride", "icu_rpe": None, "start_date_local": "2026-04-26T00:00:00"},
        {"id": "r3", "type": "Swim", "icu_rpe": None, "start_date_local": "2026-04-27T00:00:00"},
        _make_fake_climbing_activity("a1", "2026-04-28", icu_rpe=7),
    ]

    async def fake_request(url: str, **kwargs: Any) -> Any:
        if url.endswith("/wellness"):
            return _make_fake_wellness_entries(end_date="2026-04-28", days=42)
        if url.endswith("/activities"):
            return activities
        return []

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.status.make_intervals_request", fake_request)

    result = asyncio.run(get_training_status(athlete_id="i1", as_of_date="2026-04-28"))
    # Only 1 climbing activity counted -> small-sample suppression text.
    assert "low activity volume" in result, result


# --- 3f. Empty-data graceful path ---


def test_empty_data_renders_three_graceful_notes(monkeypatch: pytest.MonkeyPatch) -> None:
    """CONTEXT D-13 — empty wellness AND empty activities -> all three graceful one-liners."""
    from intervals_mcp_server.tools.status import get_training_status  # type: ignore[import-not-found]

    async def fake_request(url: str, **kwargs: Any) -> Any:
        return []

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.status.make_intervals_request", fake_request)

    result = asyncio.run(get_training_status(athlete_id="i1", as_of_date="2026-04-28"))
    assert "## Today\n- No wellness data in last 7 days." in result, result
    assert "## This Week\n- No CTL/ATL trend data in last 7 days." in result, result
    assert "## Long-Term Trend\n- No CTL/ATL trend data in last 42 days." in result, result


# --- 3g. HTTP error paths ---


def test_wellness_http_error_returns_error_string(monkeypatch: pytest.MonkeyPatch) -> None:
    from intervals_mcp_server.tools.status import get_training_status  # type: ignore[import-not-found]

    async def fake_request(url: str, **kwargs: Any) -> Any:
        if url.endswith("/wellness"):
            return {"error": True, "status_code": 503, "message": "upstream timeout"}
        return []

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.status.make_intervals_request", fake_request)

    result = asyncio.run(get_training_status(athlete_id="i1", as_of_date="2026-04-28"))
    assert result.startswith("Error fetching wellness data:"), result
    assert "upstream timeout" in result


def test_activities_http_error_returns_error_string(monkeypatch: pytest.MonkeyPatch) -> None:
    from intervals_mcp_server.tools.status import get_training_status  # type: ignore[import-not-found]

    async def fake_request(url: str, **kwargs: Any) -> Any:
        if url.endswith("/wellness"):
            return _make_fake_wellness_entries()
        if url.endswith("/activities"):
            return {"error": True, "status_code": 502, "message": "bad gateway"}
        return []

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.status.make_intervals_request", fake_request)

    result = asyncio.run(get_training_status(athlete_id="i1", as_of_date="2026-04-28"))
    assert result.startswith("Error fetching activities:"), result
    assert "bad gateway" in result


# ---------------------------------------------------------------------------
# Section 4 — Token budget tests (STAT-04, CONTEXT D-12)
# ---------------------------------------------------------------------------


def _count_tokens_cl100k(text: str) -> int:
    """STAT-04 / CONTEXT D-12 — cl100k_base is the Claude-/GPT-compatible encoding."""
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def test_token_budget_full_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """STAT-04 — representative full-data report renders in 400-600 tokens."""
    from intervals_mcp_server.tools.status import get_training_status  # type: ignore[import-not-found]

    activities = [
        _make_fake_climbing_activity(f"a{i}", "2026-04-28", icu_rpe=(7 if i % 2 == 0 else None))
        for i in range(8)
    ]

    async def fake_request(url: str, **kwargs: Any) -> Any:
        if url.endswith("/wellness"):
            return _make_fake_wellness_entries(end_date="2026-04-28", days=42)
        if url.endswith("/activities"):
            return activities
        return []

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.status.make_intervals_request", fake_request)

    result = asyncio.run(get_training_status(athlete_id="i1", as_of_date="2026-04-28"))
    n = _count_tokens_cl100k(result)
    assert 400 <= n <= 600, (
        f"Token count {n} outside 400-600 band. Report:\n{result}"
    )


def test_token_budget_empty_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """STAT-04 — empty-data variant ALSO lands in the band (or below — empty
    reports may legitimately be smaller; the constraint is 'not too big').

    NOTE: the success criterion in ROADMAP is 'within 400-600 tokens' — for
    the empty case the report is shorter (just three graceful notes), which
    is still valid; we assert UPPER bound only (<= 600). The lower bound is
    a design constraint for full data, not for legitimately-empty data.
    """
    from intervals_mcp_server.tools.status import get_training_status  # type: ignore[import-not-found]

    async def fake_request(url: str, **kwargs: Any) -> Any:
        return []

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.status.make_intervals_request", fake_request)

    result = asyncio.run(get_training_status(athlete_id="i1", as_of_date="2026-04-28"))
    n = _count_tokens_cl100k(result)
    assert n <= 600, f"Empty-data report exceeded 600 tokens ({n}):\n{result}"
    # Sanity floor — should still render something
    assert n >= 30, f"Empty-data report unexpectedly tiny ({n}):\n{result}"


# ---------------------------------------------------------------------------
# Section 5 — Pathological-data defensive tests
# ---------------------------------------------------------------------------


def test_pathological_wellness_response_does_not_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    """T-04-02 — wellness response with non-list, non-dict, and bad-typed entries
    renders a graceful report without raising."""
    from intervals_mcp_server.tools.status import get_training_status  # type: ignore[import-not-found]

    async def fake_request(url: str, **kwargs: Any) -> Any:
        if url.endswith("/wellness"):
            return [
                {"date": "2026-04-28", "ctl": "N/A", "atl": None},  # bad types
                "not-a-dict",                                         # bad element
                {"date": "2026-04-27", "ctl": 50.0, "atl": 45.0},    # one good entry
                {"date": "2026-04-26"},                               # missing ctl/atl
            ]
        return []

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.status.make_intervals_request", fake_request)

    # Should NOT raise. Returns a string (graceful where data is missing,
    # rendered where one entry is good).
    result = asyncio.run(get_training_status(athlete_id="i1", as_of_date="2026-04-28"))
    assert isinstance(result, str)
    assert "## Today" in result
    assert "## This Week" in result
    assert "## Long-Term Trend" in result


def test_pathological_activities_response_does_not_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    """T-04-02 — activities response with non-list, non-dict, missing type."""
    from intervals_mcp_server.tools.status import get_training_status  # type: ignore[import-not-found]

    async def fake_request(url: str, **kwargs: Any) -> Any:
        if url.endswith("/wellness"):
            return _make_fake_wellness_entries()
        if url.endswith("/activities"):
            return [
                "not-a-dict",
                {},
                {"id": "x"},  # no type
                {"type": "Ride"},  # not climbing
                _make_fake_climbing_activity("a1", "2026-04-28", icu_rpe=7),
            ]
        return []

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.status.make_intervals_request", fake_request)

    result = asyncio.run(get_training_status(athlete_id="i1", as_of_date="2026-04-28"))
    assert isinstance(result, str)
    # Only 1 climbing activity counted -> small-sample suppression.
    assert "low activity volume" in result, result
