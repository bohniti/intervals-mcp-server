"""
Wellness-related MCP tools for Intervals.icu.

This module contains tools for retrieving athlete wellness data
(`get_wellness_data`) and for logging new wellness entries with hard
range validation, drop-None upsert semantics, and readback verification
(`write_wellness_entry`).
"""

from typing import Any

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.formatting import format_wellness_entry
from intervals_mcp_server.utils.validation import (
    resolve_athlete_id,
    resolve_date_params,
    validate_date,
)
from intervals_mcp_server.utils.wellness import (
    WELLNESS_RANGES,
    build_wellness_put_body,
)

# Import mcp instance from shared module for tool registration
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401

config = get_config()


@mcp.tool()
async def get_wellness_data(
    athlete_id: str | None = None,
    api_key: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    include_all_fields: bool = False,
) -> str:
    """Get wellness data for an athlete from Intervals.icu.

    By default returns standard wellness fields (training metrics, vitals, sleep,
    subjective scores, etc.). Set include_all_fields=True to also include any
    additional or custom fields configured by the user in Intervals.icu.

    Args:
        athlete_id: The Intervals.icu athlete ID (optional, will use ATHLETE_ID from .env if not provided)
        api_key: The Intervals.icu API key (optional, will use API_KEY from .env if not provided)
        start_date: Start date in YYYY-MM-DD format (optional, defaults to 30 days ago)
        end_date: End date in YYYY-MM-DD format (optional, defaults to today)
        include_all_fields: If True, include additional and custom fields beyond the standard set (optional, defaults to False)
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    start_date, end_date = resolve_date_params(start_date, end_date)

    params = {"oldest": start_date, "newest": end_date}

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/wellness", api_key=api_key, params=params
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error fetching wellness data: {result.get('message')}"

    if not result:
        return (
            f"No wellness data found for athlete {athlete_id_to_use} in the specified date range."
        )

    wellness_summary = "Wellness Data:\n\n"

    if isinstance(result, dict):
        for date_str, data in result.items():
            if isinstance(data, dict) and "date" not in data:
                data["date"] = date_str
            wellness_summary += format_wellness_entry(data, include_all_fields=include_all_fields) + "\n\n"
    elif isinstance(result, list):
        for entry in result:
            if isinstance(entry, dict):
                wellness_summary += format_wellness_entry(entry, include_all_fields=include_all_fields) + "\n\n"

    return wellness_summary


@mcp.tool()
async def write_wellness_entry(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-return-statements,too-many-branches
    date: str,
    sleep_hours: float | None = None,
    sleep_quality: int | None = None,
    soreness: int | None = None,
    fatigue: int | None = None,
    motivation: int | None = None,
    stress: int | None = None,
    mood: int | None = None,
    hrv: float | None = None,
    resting_hr: int | None = None,
    athlete_id: str | None = None,
    api_key: str | None = None,
) -> str:
    """Log a wellness entry for an athlete on a given date.

    Before calling this tool, ask the user for any subset of:
    - sleep hours (e.g., 7.5)
    - sleep quality, soreness, fatigue, motivation, stress, mood (subjective
      integer scales — exact valid ranges are locked from the Phase 2 spike
      and enforced before any HTTP call)
    - HRV (ms), resting HR (bpm)

    Fields NOT supplied are not sent — they preserve existing values for
    that day (upsert semantics: Intervals.icu treats `null` as "clear",
    so unsupplied fields must be omitted from the PUT body, not nulled).
    At least one wellness field must be set; a call with only `date` is
    rejected.

    After the PUT, the tool reads the entry back and verifies every supplied
    field roundtripped — if a value is missing or different, the tool returns
    an error rather than silently succeeding (Pitfall #2 wellness flavour).

    Args:
        date: Date in YYYY-MM-DD format. Required.
        sleep_hours: Hours of sleep last night (e.g. 8.0). Converted to
            sleepSecs internally; passed through to the API as integer
            seconds.
        sleep_quality: Subjective sleep quality.
        soreness: Subjective soreness.
        fatigue: Subjective fatigue.
        motivation: Subjective motivation.
        stress: Subjective stress.
        mood: Subjective mood.
        hrv: Heart-rate variability in ms (pass-through).
        resting_hr: Resting heart rate in bpm (pass-through; mapped to
            `restingHR` API field).
        athlete_id: Optional Intervals.icu athlete ID (falls back to
            ATHLETE_ID env var).
        api_key: Optional Intervals.icu API key (falls back to API_KEY
            env var).

    Returns:
        A human-readable success string with the rendered wellness entry,
        OR a clear error string naming the failure (out-of-range value,
        empty call, API error, readback mismatch).
    """
    # Date format check first — fail fast before HTTP.
    try:
        validate_date(date)
    except ValueError as exc:
        return f"Error: {exc}"

    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    # Build candidate dict mirroring the public-param surface
    # (key = public name, value = raw input).
    candidates: dict[str, Any] = {
        "sleep_hours": sleep_hours,
        "sleep_quality": sleep_quality,
        "soreness": soreness,
        "fatigue": fatigue,
        "motivation": motivation,
        "stress": stress,
        "mood": mood,
        "hrv": hrv,
        "resting_hr": resting_hr,
    }

    # Hard pre-API validation against the locked range table (D-07 / WELL-03).
    for name, value in candidates.items():
        if value is None:
            continue
        if name in WELLNESS_RANGES:
            min_v, max_v = WELLNESS_RANGES[name]
            if not min_v <= value <= max_v:
                return (
                    f"Error: {name}={value} out of range; expected "
                    f"{min_v}..{max_v} (locked from spike findings)."
                )
        elif name in {"sleep_quality", "soreness", "fatigue", "motivation", "stress", "mood"}:
            # Subjective field with no locked range — Plan 02-01 marked it unresolved.
            return (
                f"Error: {name} is not yet supported — its valid range was "
                f"not confirmed by the Phase 2 spike. Re-probe before re-enabling."
            )
        # sleep_hours, hrv, resting_hr have no enum-style range; pass through (negative
        # sleep_hours is caught by sleep_hours_to_secs in build_wellness_put_body).

    # No verify-fields guard here — wellness fields are native to Intervals.icu's
    # wellness model. The verify gate exists only to protect climbing custom-field
    # writes from silent failure (D-21 / Pitfall #2).
    if all(v is None for v in candidates.values()):
        return "Error: at least one wellness field must be supplied (date alone is not enough)."

    # build_wellness_put_body drops None entries and translates names (D-09).
    try:
        body = build_wellness_put_body(candidates)
    except (KeyError, ValueError) as exc:
        # Defensive — should not happen because we control the candidate keys.
        return f"Error building wellness body: {exc}"

    # PUT — single HTTP boundary.
    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/wellness/{date}",
        api_key=api_key,
        data=body,
        method="PUT",
    )
    if isinstance(result, dict) and "error" in result:
        return f"Error writing wellness entry: {result.get('message', 'Unknown error')}"

    # Readback (D-11). GET single date and verify each supplied field roundtripped.
    readback = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/wellness",
        api_key=api_key,
        params={"oldest": date, "newest": date},
    )
    if isinstance(readback, dict) and "error" in readback:
        return f"Error reading back wellness entry: {readback.get('message', 'Unknown error')}"

    if isinstance(readback, list) and readback:
        entry = readback[0] if isinstance(readback[0], dict) else {}
    elif isinstance(readback, dict):
        entry = readback
    else:
        entry = {}
    if not entry:
        return f"Error: readback returned no wellness entry for {date}."

    # Per-field equality check on supplied fields only (D-15 thinking applied to wellness).
    mismatches: list[str] = []
    for api_name, sent_value in body.items():
        got = entry.get(api_name)
        if got != sent_value:
            mismatches.append(f"  {api_name}: sent {sent_value!r}, got {got!r}")
    if mismatches:
        # Wellness fields are native — do NOT include the README pointer (per <specifics>).
        return (
            f"Error: wellness fields did not roundtrip for {date}:\n"
            + "\n".join(mismatches)
        )

    return (
        f"Successfully wrote wellness entry for {date}.\n\n"
        + format_wellness_entry(entry)
    )
