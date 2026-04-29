"""
Training status MCP tool for Intervals.icu.

Single read-only tool — `get_training_status` — that returns one plain-text
report blending CTL/ATL/TSB training-load metrics, recent wellness signals,
and an RPE-coverage data-quality flag. Read-only: two GETs, no writes.

Reads:
- GET /athlete/{id}/wellness?oldest=...&newest=...  (42-day window — covers
  Today / This Week / Long-Term Trend in one call per CONTEXT D-04)
- GET /athlete/{id}/activities?oldest=...&newest=...  (14-day window — for
  the climbing-RPE coverage check per CONTEXT D-09)
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.status import (
    MIN_RPE_SAMPLE,
    RPE_MISSING_THRESHOLD,
    WINDOW_DAYS_LONG_TERM,
    WINDOW_DAYS_RPE,
    WINDOW_DAYS_WEEKLY,
    compute_rpe_coverage,
    format_longterm_section,
    format_status_report,
    format_today_section,
    format_weekly_section,
)
from intervals_mcp_server.utils.validation import resolve_athlete_id, validate_date

# Import mcp instance from shared module for tool registration
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401

config = get_config()


@mcp.tool()
async def get_training_status(
    athlete_id: str | None = None,
    api_key: str | None = None,
    as_of_date: str | None = None,
) -> str:
    """Return a plain-text training-status report.

    Blends CTL/ATL/TSB training-load metrics, recent sleep/soreness/fatigue/
    HRV/RHR wellness signals, and a climbing RPE-coverage data-quality flag
    into a single ~400-600 token string with three labeled sections:

        ## Today              <- readiness (TSB band + number, walk-back note,
                                  wellness blend)
        ## This Week          <- 7-day CTL/ATL trend
        ## Long-Term Trend    <- 42-day CTL/ATL trajectory

    The report ALWAYS returns a string — sparse data is rendered as a
    one-line per-section note (CONTEXT D-13), never an exception. Hard
    failure modes (invalid date, missing athlete_id, HTTP 4xx/5xx) return
    'Error: ...' strings.

    Args:
        athlete_id: Optional Intervals.icu athlete ID. Falls back to ATHLETE_ID
            env var.
        api_key: Optional Intervals.icu API key. Falls back to API_KEY env var.
        as_of_date: Optional 'YYYY-MM-DD' anchor. Defaults to today (UTC). Lets
            Claude ask 'what was my readiness on 2026-04-21'.

    Returns:
        One plain-text report (~400-600 tokens). Always returns; never raises.
    """
    # Default as_of_date to today UTC, then validate format up front
    # (CONTEXT D-19 / Pitfall #4 — never use system clock for any user-facing
    # date downstream; the resolved string IS the contract).
    if as_of_date is None:
        as_of_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        validate_date(as_of_date)
    except ValueError as exc:
        return f"Error: {exc}"

    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    # Window math — all dates derived from validated as_of_date string,
    # never from the clock (D-19).
    as_of_dt = datetime.strptime(as_of_date, "%Y-%m-%d")
    longterm_start = (as_of_dt - timedelta(days=WINDOW_DAYS_LONG_TERM - 1)).strftime("%Y-%m-%d")
    weekly_start = (as_of_dt - timedelta(days=WINDOW_DAYS_WEEKLY - 1)).strftime("%Y-%m-%d")
    rpe_start = (as_of_dt - timedelta(days=WINDOW_DAYS_RPE - 1)).strftime("%Y-%m-%d")

    # Single wellness GET covers ALL THREE sections (D-04).
    wellness_result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/wellness",
        api_key=api_key,
        params={"oldest": longterm_start, "newest": as_of_date},
    )
    if isinstance(wellness_result, dict) and "error" in wellness_result:
        return f"Error fetching wellness data: {wellness_result.get('message', 'Unknown error')}"

    wellness_entries: list[dict[str, Any]] = []
    if isinstance(wellness_result, dict):
        for date_str, data in wellness_result.items():
            if isinstance(data, dict):
                # Mirror tools/wellness.py:74-78 — backfill date if absent.
                if "date" not in data:
                    data["date"] = date_str
                wellness_entries.append(data)
    elif isinstance(wellness_result, list):
        for entry in wellness_result:
            if isinstance(entry, dict):
                wellness_entries.append(entry)
    # else: leave wellness_entries empty -> graceful empty paths handle it

    activities_result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/activities",
        api_key=api_key,
        params={"oldest": rpe_start, "newest": as_of_date},
    )
    if isinstance(activities_result, dict) and "error" in activities_result:
        return f"Error fetching activities: {activities_result.get('message', 'Unknown error')}"

    # D-09 — filter to climbing activities only (type == "WeightTraining").
    # Defensive checks per security_constraint T-04-02 — pathological response shapes.
    climbing_activities: list[dict[str, Any]] = []
    if isinstance(activities_result, list):
        for activity in activities_result:
            if not isinstance(activity, dict):
                continue
            if activity.get("type") != "WeightTraining":
                continue
            climbing_activities.append(activity)

    # Walk-back: find the most recent wellness entry on or before as_of_date
    # that has BOTH ctl AND atl. Cap at 7 days. (CONTEXT D-07.)
    today_entry: dict[str, Any] | None = None
    walk_back_days = 0
    # Index entries by date string for O(1) lookup.
    entries_by_date: dict[str, dict[str, Any]] = {}
    for e in wellness_entries:
        d = e.get("date") or e.get("id")
        if isinstance(d, str):
            entries_by_date[d] = e

    for offset in range(WINDOW_DAYS_WEEKLY):  # 0..6 (max walk-back = 7 days, D-07)
        candidate_date = (as_of_dt - timedelta(days=offset)).strftime("%Y-%m-%d")
        candidate = entries_by_date.get(candidate_date)
        if candidate is None:
            continue
        ctl = candidate.get("ctl")
        atl = candidate.get("atl")
        if isinstance(ctl, (int, float)) and isinstance(atl, (int, float)):
            today_entry = candidate
            walk_back_days = offset
            break

    # 7-day wellness blend window for the Today section.
    weekly_window_entries = [
        e for e in wellness_entries
        if isinstance(e.get("date"), str) and e["date"] >= weekly_start
        and e["date"] <= as_of_date
    ]

    today_section = format_today_section(today_entry, weekly_window_entries, walk_back_days)

    weekly_section = format_weekly_section(weekly_window_entries)

    longterm_section = format_longterm_section(wellness_entries)  # already 42-day window

    missing, total = compute_rpe_coverage(climbing_activities)
    rpe_warning: str | None = None
    if total < MIN_RPE_SAMPLE:
        # D-11 — suppress the threshold warning on small samples; cue the user instead.
        rpe_warning = (
            f"> RPE coverage: low activity volume "
            f"(< {MIN_RPE_SAMPLE} sessions in last {WINDOW_DAYS_RPE} days)."
        )
    elif total > 0 and (missing / total) > RPE_MISSING_THRESHOLD:
        # D-08 / STAT-03 — explicit data-quality warning naming RPE.
        pct = round((missing / total) * 100)
        rpe_warning = (
            f"> Data-quality: {missing} of {total} climbing activities in the "
            f"last {WINDOW_DAYS_RPE} days lack RPE ({pct}% missing). The "
            f"readiness signal may be noisy because RPE feeds rpeTSS / icu_rpe."
        )

    return format_status_report(today_section, weekly_section, longterm_section, rpe_warning)
