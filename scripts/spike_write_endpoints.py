#!/usr/bin/env python3
"""
Spike: confirm write-path contracts for Intervals.icu wellness + activities.

NOT A PYTEST TEST. Writes to live Intervals.icu at a far-future date
(2099-01-01) and attempts cleanup. Findings (body shapes, upsert
semantics, endpoint availability, custom-field-definitions endpoint
discovery) are written to:

    .planning/phases/01-foundation-and-write-path-spike/01-SPIKE-FINDINGS.md

Run once, by hand:

    uv run scripts/spike_write_endpoints.py

Pre-requisites: API_KEY and ATHLETE_ID set in .env.
Cleanup: script attempts DELETE for the created activity; if unavailable,
findings file lists manual cleanup steps against the Intervals.icu web UI.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

# Mirror the sys.path pattern used by tests/test_make_intervals_request.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from intervals_mcp_server.api.client import make_intervals_request  # noqa: E402
from intervals_mcp_server.config import get_config  # noqa: E402
from intervals_mcp_server.utils.formatting import format_climbing_activity  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("spike")

SPIKE_DATE = "2099-01-01"  # far-future, no real data here
ATHLETE_REDACTED = "{athlete_id}"  # placeholder used in findings file
FINDINGS_PATH = (
    Path(__file__).resolve().parents[1]
    / ".planning"
    / "phases"
    / "01-foundation-and-write-path-spike"
    / "01-SPIKE-FINDINGS.md"
)

# Candidate endpoints for custom-field definitions (Assumption A5 / Open Q1).
DEFINITIONS_CANDIDATES = [
    "/athlete/{id}/custom-fields",
    "/athlete/{id}/activity-fields",
    "/athlete/{id}/sport-settings",
]


def _redact(obj: Any, athlete_id: str) -> Any:
    """Recursively replace athlete_id occurrences with ATHLETE_REDACTED for findings output."""
    if isinstance(obj, str):
        return obj.replace(athlete_id, ATHLETE_REDACTED)
    if isinstance(obj, dict):
        return {k: _redact(v, athlete_id) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact(v, athlete_id) for v in obj]
    return obj


async def spike_wellness_put(athlete_id: str) -> dict[str, Any]:
    """Probe PUT /athlete/{id}/wellness/{date}. Verify upsert vs replace semantics.

    Flow:
    1. PUT partial body {sleepSecs, soreness}, readback.
    2. PUT a DIFFERENT partial body {fatigue}, readback — check if sleepSecs survived.
    3. Cleanup: PUT -1 into numeric fields (forum cookbook) to blank them.
    """
    findings: dict[str, Any] = {
        "endpoint": f"/athlete/{ATHLETE_REDACTED}/wellness/{SPIKE_DATE}",
    }

    write_body_1 = {"sleepSecs": 28800, "soreness": 3}
    findings["write_1_body_sent"] = write_body_1
    findings["write_1_response"] = await make_intervals_request(
        url=f"/athlete/{athlete_id}/wellness/{SPIKE_DATE}",
        data=write_body_1,
        method="PUT",
    )

    readback_1 = await make_intervals_request(
        url=f"/athlete/{athlete_id}/wellness",
        params={"oldest": SPIKE_DATE, "newest": SPIKE_DATE},
    )
    findings["readback_after_write_1"] = readback_1

    write_body_2 = {"fatigue": 5}
    findings["write_2_body_sent"] = write_body_2
    findings["write_2_response"] = await make_intervals_request(
        url=f"/athlete/{athlete_id}/wellness/{SPIKE_DATE}",
        data=write_body_2,
        method="PUT",
    )

    readback_2 = await make_intervals_request(
        url=f"/athlete/{athlete_id}/wellness",
        params={"oldest": SPIKE_DATE, "newest": SPIKE_DATE},
    )
    findings["readback_after_write_2"] = readback_2

    # Upsert semantic check — did sleepSecs from write_1 survive write_2?
    survived: bool | None = None
    if isinstance(readback_2, list) and readback_2:
        first = readback_2[0]
        if isinstance(first, dict):
            survived = first.get("sleepSecs") == 28800
    elif isinstance(readback_2, dict) and "sleepSecs" in readback_2:
        survived = readback_2.get("sleepSecs") == 28800
    findings["upsert_semantics_confirmed"] = survived

    # Cleanup attempt: blank numeric fields with -1 per forum cookbook (A3).
    findings["cleanup_response"] = await make_intervals_request(
        url=f"/athlete/{athlete_id}/wellness/{SPIKE_DATE}",
        data={"sleepSecs": -1, "soreness": -1, "fatigue": -1},
        method="PUT",
    )

    return findings


async def spike_activity_create(athlete_id: str) -> dict[str, Any]:
    """Probe activity-create endpoint. Confirm body shape, type value, custom-field write path.

    Flow:
    1. POST to /activities/manual with a minimal body; if 404, fall back to /activities.
    2. Capture activity id; readback via GET /activity/{id}.
    3. PUT a custom field (discipline) at top level, readback — A2 check.
    4. Try DELETE /activity/{id}; if unavailable, record for manual cleanup.
    """
    findings: dict[str, Any] = {}

    create_body = {
        # Format: YYYY-MM-DDT00:00:00 (e.g. start_date_local = "2099-01-01T00:00:00");
        # events.py pattern; Pitfall #4.
        "start_date_local": f"{SPIKE_DATE}T00:00:00",
        "type": "WeightTraining",  # forum A4
        "name": "SPIKE — DELETE ME",
        "moving_time": 3600,
    }
    findings["create_body_sent"] = create_body

    primary_url = f"/athlete/{athlete_id}/activities/manual"
    findings["endpoint_primary"] = primary_url.replace(athlete_id, ATHLETE_REDACTED)
    result = await make_intervals_request(
        url=primary_url, data=create_body, method="POST"
    )
    findings["primary_response"] = result

    # Fallback on 404 — try the plain /activities endpoint (A1)
    if isinstance(result, dict) and result.get("status_code") == 404:
        fallback_url = f"/athlete/{athlete_id}/activities"
        findings["endpoint_fallback"] = fallback_url.replace(
            athlete_id, ATHLETE_REDACTED
        )
        result = await make_intervals_request(
            url=fallback_url, data=create_body, method="POST"
        )
        findings["fallback_response"] = result

    activity_id = (
        result.get("id") if isinstance(result, dict) and "error" not in result else None
    )
    findings["activity_id_present"] = activity_id is not None

    if activity_id:
        readback = await make_intervals_request(url=f"/activity/{activity_id}")
        findings["readback"] = readback

        # A2: custom-field write as top-level keys on the activity
        cf_write = await make_intervals_request(
            url=f"/activity/{activity_id}",
            data={"discipline": "bouldering", "icu_rpe": 6},
            method="PUT",
        )
        findings["custom_field_write_response"] = cf_write

        readback_after_cf = await make_intervals_request(url=f"/activity/{activity_id}")
        findings["readback_after_custom_field_put"] = readback_after_cf

        roundtripped = (
            isinstance(readback_after_cf, dict)
            and readback_after_cf.get("discipline") == "bouldering"
            and readback_after_cf.get("icu_rpe") == 6
        )
        findings["custom_field_roundtripped"] = roundtripped

        if isinstance(readback_after_cf, dict):
            findings["rendered_readback"] = format_climbing_activity(readback_after_cf)

        # Cleanup — try DELETE
        del_result = await make_intervals_request(
            url=f"/activity/{activity_id}", method="DELETE"
        )
        findings["delete_response"] = del_result
        findings["delete_available"] = not (
            isinstance(del_result, dict) and del_result.get("error")
        )
        findings["activity_id_for_manual_cleanup"] = (
            activity_id if not findings["delete_available"] else None
        )

    return findings


async def spike_custom_field_definitions(athlete_id: str) -> dict[str, Any]:
    """Probe candidate custom-field-definitions endpoints. Record first 2xx response verbatim."""
    findings: dict[str, Any] = {"candidates_tried": []}
    for pattern in DEFINITIONS_CANDIDATES:
        url = pattern.format(id=athlete_id)
        result = await make_intervals_request(url=url)
        findings["candidates_tried"].append(
            {
                "endpoint": pattern.format(id=ATHLETE_REDACTED),
                "status_code": result.get("status_code")
                if isinstance(result, dict) and "error" in result
                else 200,
                "response": result
                if not (isinstance(result, dict) and "error" in result)
                else None,
                "error_message": result.get("message")
                if isinstance(result, dict) and "error" in result
                else None,
            }
        )
        # First successful 2xx wins
        if not (isinstance(result, dict) and "error" in result):
            findings["winning_endpoint"] = pattern.format(id=ATHLETE_REDACTED)
            findings["winning_response_shape"] = result
            break
    else:
        findings["winning_endpoint"] = None
        findings["fallback_note"] = (
            "No definitions endpoint returned 2xx. verify_custom_fields_setup "
            "must use readback-heuristic (PUT probe field to throwaway activity "
            "at SPIKE_DATE, readback, delete) or parse an existing activity's "
            "field set to infer definitions."
        )
    return findings


def write_findings(
    wellness: dict[str, Any],
    activity: dict[str, Any],
    definitions: dict[str, Any],
    athlete_id: str,
) -> None:
    """Dump findings to 01-SPIKE-FINDINGS.md with copy-pasteable code fences.

    Redacts athlete_id everywhere.
    """
    FINDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    wellness_redacted = _redact(wellness, athlete_id)
    activity_redacted = _redact(activity, athlete_id)
    definitions_redacted = _redact(definitions, athlete_id)
    content = [
        "# Spike findings — write-path probes\n\n",
        f"**Spike date (target):** {SPIKE_DATE}\n\n",
        "All occurrences of the live athlete id are redacted to "
        f"`{ATHLETE_REDACTED}`.\n\n",
        "## Wellness PUT\n\n",
        "```json\n",
        json.dumps(wellness_redacted, indent=2, default=str),
        "\n```\n\n",
        "## Activity POST + custom-field PUT\n\n",
        "```json\n",
        json.dumps(activity_redacted, indent=2, default=str),
        "\n```\n\n",
        "## Custom-field definitions endpoint discovery\n\n",
        "```json\n",
        json.dumps(definitions_redacted, indent=2, default=str),
        "\n```\n\n",
        "## Manual cleanup (if DELETE unavailable)\n\n",
        f"- Wellness at {SPIKE_DATE}: cleared with `-1` values in spike; verify in Intervals.icu UI.\n",
        f"- Activity id for manual cleanup: "
        f"{activity.get('activity_id_for_manual_cleanup')}\n",
    ]
    FINDINGS_PATH.write_text("".join(content), encoding="utf-8")


async def main() -> None:
    config = get_config()
    if not config.athlete_id or not config.api_key:
        logger.error(
            "API_KEY and ATHLETE_ID must be set in .env before running the spike."
        )
        sys.exit(1)

    logger.info("Spike target date: %s", SPIKE_DATE)
    logger.info("Spike running against athlete: %s", ATHLETE_REDACTED)

    wellness = await spike_wellness_put(config.athlete_id)
    activity = await spike_activity_create(config.athlete_id)
    definitions = await spike_custom_field_definitions(config.athlete_id)
    write_findings(wellness, activity, definitions, config.athlete_id)

    logger.info("Findings written to %s", FINDINGS_PATH)


if __name__ == "__main__":
    asyncio.run(main())
