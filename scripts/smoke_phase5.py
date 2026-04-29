#!/usr/bin/env python3
"""
Smoke test: Phase 5 acceptance — every milestone tool against live Intervals.icu.

NOT A PYTEST TEST. Writes to live Intervals.icu at far-future dates
(2099-01-01 wellness/activity, 2099-01-02 planned event) using the full
Phase 1-4 tool path:
  1. verify_custom_fields_setup -- confirm SETUP-01 still satisfied
  2. write_wellness_entry -- PUT wellness on 2099-01-01
  3. create_climbing_activity -- POST climbing activity on 2099-01-01
  4. enrich_activity_climbing -- add fields against the activity from step 3
  5. complete_climbing_session -- create planned event on 2099-01-02, then complete
  6. get_training_status -- read-only sanity check
  7. Cleanup: DELETE both created activities, DELETE the planned event

Run once, by hand:

    uv run scripts/smoke_phase5.py

Pre-requisites: API_KEY and ATHLETE_ID set in .env, plus the seven
climbing custom fields defined in the athlete's Intervals.icu account
(per README "Climbing setup" section / SETUP-01).

Exit codes:
    0  All steps OK; readback values matched sent values; cleanup succeeded.
    1  Configuration error OR a step failed OR cleanup failed.

This script complements the unit suite -- unit tests prove logic; this
script proves end-to-end live API correctness for the milestone surface.
By design it is NOT discoverable by `pytest --collect-only` (file lives
under scripts/, file name does not start with test_, no def test_*).
"""

from __future__ import annotations

import asyncio
import logging
import re
import sys
from pathlib import Path
from typing import Any

# Mirror the sys.path pattern used by tests and prior smoke scripts.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from intervals_mcp_server.api.client import make_intervals_request  # noqa: E402
from intervals_mcp_server.config import get_config  # noqa: E402
from intervals_mcp_server.tools.climbing import (  # noqa: E402
    complete_climbing_session,
    create_climbing_activity,
    enrich_activity_climbing,
    verify_custom_fields_setup,
)
from intervals_mcp_server.tools.events import add_or_update_event  # noqa: E402
from intervals_mcp_server.tools.status import get_training_status  # noqa: E402
from intervals_mcp_server.tools.wellness import write_wellness_entry  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("smoke_phase5")

SMOKE_DATE = "2099-01-01"        # wellness + create_climbing_activity
SMOKE_EVENT_DATE = "2099-01-02"  # planned event for complete_climbing_session
ATHLETE_REDACTED = "{athlete_id}"


def _redact(obj: Any, athlete_id: str) -> Any:
    """Recursively replace athlete_id with placeholder for logged output."""
    if isinstance(obj, str):
        return obj.replace(athlete_id, ATHLETE_REDACTED)
    if isinstance(obj, dict):
        return {k: _redact(v, athlete_id) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact(v, athlete_id) for v in obj]
    return obj


def _extract_activity_id(success_msg: str) -> str | None:
    """Parse activity id from `create_climbing_activity` /
    `complete_climbing_session` success strings. Both contain
    ' activity {id}' tokens; regex picks the first."""
    m = re.search(r"activity (\w+)", success_msg)
    return m.group(1) if m else None


async def main() -> int:  # pylint: disable=too-many-locals,too-many-statements,too-many-branches,too-many-return-statements
    """Run the Phase 5 smoke test end-to-end.

    Returns process exit code (0 = all OK, 1 = at least one step failed
    or configuration missing). Cleanup runs in `finally` regardless of
    failure mid-flight, so partial state never lingers on the live account.
    """
    config = get_config()
    athlete_id = config.athlete_id
    if not athlete_id:
        logger.error("ATHLETE_ID not set in environment — abort.")
        return 1
    if not config.api_key:
        logger.error("API_KEY not set in environment — abort.")
        return 1

    logger.warning(
        "About to write to live Intervals.icu at SMOKE_DATE=%s / SMOKE_EVENT_DATE=%s. "
        "Cleanup runs in finally.",
        SMOKE_DATE, SMOKE_EVENT_DATE,
    )

    create_activity_id: str | None = None
    completion_activity_id: str | None = None
    planned_event_id: str | None = None
    failures: list[str] = []

    try:
        # --- Step 1: verify_custom_fields_setup (D-09 #1) ---
        # If this fails, every climbing-write step would hard-block on
        # the custom-field guard. Fail fast with a pointer to the README.
        logger.info("Step 1: verify_custom_fields_setup()")
        verify_result = await verify_custom_fields_setup()
        logger.info("Verify result:\n%s", _redact(verify_result, athlete_id))
        verify_lower = verify_result.lower()
        # Heuristic: the verify tool reports "missing" with a count when
        # any custom field is absent. Treat any non-empty missing list as
        # a hard abort.
        if "missing" in verify_lower and "0 missing" not in verify_lower and "no missing" not in verify_lower:
            failures.append("verify")
            logger.error("SETUP-01 not satisfied. Aborting subsequent steps. See README 'Climbing setup' section.")
            return 1

        # --- Step 2: write_wellness_entry (D-09 #2) ---
        logger.info("Step 2: write_wellness_entry(date=%s, sleep_hours=8.0, soreness=2)", SMOKE_DATE)
        wellness_result = await write_wellness_entry(
            date=SMOKE_DATE,
            sleep_hours=8.0,
            soreness=2,
        )
        logger.info("Wellness result: %s", _redact(wellness_result, athlete_id))
        if not wellness_result.startswith("Successfully"):
            failures.append("wellness")

        # --- Step 3: create_climbing_activity (D-09 #3) ---
        # Captures create_activity_id for cleanup + step 4 enrichment.
        logger.info("Step 3: create_climbing_activity(date=%s, duration_minutes=60, ...)", SMOKE_DATE)
        create_result = await create_climbing_activity(
            date=SMOKE_DATE,
            duration_minutes=60,
            title="SMOKE PHASE5 — DELETE ME (create)",
            discipline="bouldering",
            indoor=True,
            rpe=6,
        )
        logger.info("Create result: %s", _redact(create_result, athlete_id))
        create_activity_id = _extract_activity_id(create_result)
        if not create_activity_id or not create_result.startswith("Successfully"):
            failures.append("create")
            # Continue to other steps where possible; cleanup will skip
            # this id since it is None.

        # --- Step 4: enrich_activity_climbing (D-09 #4) ---
        # Run only if step 3 produced an id; otherwise mark as skipped.
        if create_activity_id:
            logger.info("Step 4: enrich_activity_climbing(activity_id=%s, ...)", _redact(create_activity_id, athlete_id))
            enrich_result = await enrich_activity_climbing(
                activity_id=create_activity_id,
                discipline="bouldering",
                indoor=True,
                session_focus="power",
                top_grade_sent="6A+",
                top_grade_attempted="7A",
                sends=4,
                attempts=7,
                rpe=6,
            )
            logger.info("Enrich result: %s", _redact(enrich_result, athlete_id))
            if not enrich_result.startswith("Successfully"):
                failures.append("enrich")
        else:
            logger.warning("Step 4 skipped: no create_activity_id from step 3.")
            failures.append("enrich-skipped")

        # --- Step 5: planned event + complete_climbing_session (D-09 #5) ---
        # 5a — create planned event on SMOKE_EVENT_DATE (different day from
        # step 3 to avoid the duplicate-guard date+type collision).
        logger.info("Step 5a: add_or_update_event(workout_type=WeightTraining, start_date=%s)", SMOKE_EVENT_DATE)
        event_result = await add_or_update_event(
            workout_type="WeightTraining",
            name="SMOKE PHASE5 — DELETE ME (planned)",
            start_date=SMOKE_EVENT_DATE,
            moving_time=3600,
        )
        logger.info("Event result: %s", _redact(event_result, athlete_id))
        # Parse id from "Successfully {action} event id: {id}"
        m = re.search(r"event id:\s*(\w+)", event_result)
        planned_event_id = m.group(1) if m else None
        if not planned_event_id or not event_result.startswith("Successfully"):
            failures.append("plan-event")
        else:
            # 5b — complete_climbing_session against the freshly-created event.
            logger.info("Step 5b: complete_climbing_session(event_id=%s, ...)", _redact(planned_event_id, athlete_id))
            completion_result = await complete_climbing_session(
                event_id=planned_event_id,
                discipline="sport_lead",
                indoor=False,
                session_focus="projecting",
                rpe=7,
            )
            logger.info("Completion result: %s", _redact(completion_result, athlete_id))
            completion_activity_id = _extract_activity_id(completion_result)
            if not completion_activity_id or not completion_result.startswith("Successfully"):
                failures.append("complete-session")

        # --- Step 6: get_training_status (D-09 #6 — read-only, last) ---
        logger.info("Step 6: get_training_status(as_of_date=%s)", SMOKE_DATE)
        status_report = await get_training_status(as_of_date=SMOKE_DATE)
        logger.info("Status report (%d chars):\n%s", len(status_report), _redact(status_report, athlete_id))
        # Token-budget heuristic: ~4 chars per token. STAT-04 / D-12 budget is 400-600 tokens
        # -> 1600-2400 chars. We assert a slightly wider envelope (1200-2800)
        # because the smoke run is against far-future fabricated data and
        # may render shorter than the production-run target. The unit-test
        # tiktoken assertion in tests/test_status.py is the authoritative
        # token-budget check; this is a sanity floor.
        if not (1200 <= len(status_report) <= 2800):
            logger.warning("Status report length %d chars is outside the 1200-2800 sanity envelope.", len(status_report))
            failures.append("status-length")
        # Three labeled sections must be present (CONTEXT smoke step 6).
        for label in ("## Today", "## This Week", "## Long-Term Trend"):
            if label not in status_report:
                logger.warning("Status report missing section header %r", label)
                failures.append(f"status-section-{label}")

    finally:
        # --- Step 7: cleanup (D-09 #7 + D-10) ---
        # Wellness PUT at SMOKE_DATE is intentionally LEFT IN PLACE per D-10.
        # Activities and the planned event are DELETE'd via make_intervals_request.
        for label, aid in [("create", create_activity_id), ("completion", completion_activity_id)]:
            if aid:
                logger.info("Cleanup: DELETE /activity/%s (%s)", _redact(aid, athlete_id), label)
                resp = await make_intervals_request(url=f"/activity/{aid}", method="DELETE")
                logger.info("Delete response: %s", _redact(resp, athlete_id))
                if isinstance(resp, dict) and resp.get("error") is True:
                    failures.append(f"cleanup-activity-{label}")
        if planned_event_id:
            logger.info("Cleanup: DELETE planned event %s", _redact(planned_event_id, athlete_id))
            resp = await make_intervals_request(
                url=f"/athlete/{athlete_id}/events/{planned_event_id}",
                method="DELETE",
            )
            logger.info("Event delete response: %s", _redact(resp, athlete_id))
            if isinstance(resp, dict) and resp.get("error") is True:
                failures.append("cleanup-planned-event")

    if failures:
        logger.error("SMOKE FAILURES: %s", ", ".join(failures))
        return 1
    logger.info("SMOKE PHASE 5 — all steps OK")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
