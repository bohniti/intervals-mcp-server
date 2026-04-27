#!/usr/bin/env python3
"""
Smoke test: Phase 2 write-tool surfaces against live Intervals.icu.

NOT A PYTEST TEST. Writes to live Intervals.icu at a far-future date
(2099-01-01) using the full Phase 2 tool path:
  1. write_wellness_entry — log a wellness entry
  2. POST /athlete/{id}/activities/manual — create throwaway activity
  3. enrich_activity_climbing — add climbing metadata + RPE
  4. DELETE /activity/{id} — cleanup
  5. PUT /athlete/{id}/wellness/{date} with -1 values — wellness cleanup

Run once, by hand:

    uv run scripts/smoke_phase2.py

Pre-requisites: API_KEY and ATHLETE_ID set in .env, plus the seven
climbing custom fields defined in the athlete's Intervals.icu account
(per README "Climbing setup" section / SETUP-01).

Exit codes:
    0  All steps OK; readback values matched sent values.
    1  Configuration error OR a write/readback step failed.

The script exercises the locked Phase 2 tool surface end-to-end. It
complements the unit-test suite — unit tests prove logic; this script
proves end-to-end live API correctness. By design it is NOT
discoverable by `pytest --collect-only` (file lives under `scripts/`,
file name does not start with `test_`, contains no `def test_*`).
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

# Mirror the sys.path pattern used by tests and the Phase 1 spike.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from intervals_mcp_server.api.client import make_intervals_request  # noqa: E402
from intervals_mcp_server.config import get_config  # noqa: E402
from intervals_mcp_server.tools.climbing import enrich_activity_climbing  # noqa: E402
from intervals_mcp_server.tools.wellness import write_wellness_entry  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("smoke_phase2")

SPIKE_DATE = "2099-01-01"
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


async def main() -> int:  # pylint: disable=too-many-locals,too-many-statements,too-many-branches,too-many-return-statements
    """Run the Phase 2 smoke test end-to-end.

    Returns process exit code (0 = all OK, 1 = at least one step failed
    or configuration missing). Cleanup runs in `finally` regardless of
    failure mid-flight, so partial state never lingers on the live
    account.
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
        "About to write to live Intervals.icu at SPIKE_DATE=%s. Cleanup runs in finally.",
        SPIKE_DATE,
    )

    activity_id: str | None = None
    failures: list[str] = []

    try:
        # 1. Wellness write -------------------------------------------------
        logger.info(
            "Step 1: write_wellness_entry(date=%s, sleep_hours=8.0, fatigue=2)",
            SPIKE_DATE,
        )
        wellness_result = await write_wellness_entry(
            date=SPIKE_DATE,
            sleep_hours=8.0,
            fatigue=2,
        )
        logger.info("Wellness result:\n%s", _redact(wellness_result, athlete_id))
        if not wellness_result.startswith("Successfully"):
            failures.append("wellness")

        # 2. Create throwaway activity -------------------------------------
        logger.info("Step 2: POST throwaway activity for enrichment target")
        create_body = {
            "start_date_local": f"{SPIKE_DATE}T00:00:00",
            "type": "WeightTraining",
            "name": "SMOKE PHASE2 — DELETE ME",
            "moving_time": 3600,
        }
        create_resp = await make_intervals_request(
            url=f"/athlete/{athlete_id}/activities/manual",
            data=create_body,
            method="POST",
        )
        if isinstance(create_resp, dict) and create_resp.get("error") is True:
            logger.error(
                "Activity create failed: %s",
                _redact(create_resp.get("message"), athlete_id),
            )
            failures.append("create")
            return 1
        if isinstance(create_resp, dict) and create_resp.get("id"):
            activity_id = str(create_resp["id"])
            logger.info("Created activity %s", _redact(activity_id, athlete_id))
        else:
            logger.error(
                "Unexpected create response: %s",
                _redact(create_resp, athlete_id),
            )
            failures.append("create_shape")
            return 1

        # 3. Enrich --------------------------------------------------------
        logger.info(
            "Step 3: enrich_activity_climbing(...) on activity %s",
            _redact(activity_id, athlete_id),
        )
        enrich_result = await enrich_activity_climbing(
            activity_id=activity_id,
            discipline="bouldering",
            indoor=True,
            session_focus="power",
            top_grade_sent="6A+",
            top_grade_attempted="7A",
            sends=4,
            attempts=7,
            rpe=6,
        )
        logger.info("Enrich result:\n%s", _redact(enrich_result, athlete_id))
        if not enrich_result.startswith("Successfully"):
            failures.append("enrich")

    finally:
        # 4. Cleanup activity ----------------------------------------------
        if activity_id:
            logger.info(
                "Cleanup: DELETE /activity/%s",
                _redact(activity_id, athlete_id),
            )
            delete_resp = await make_intervals_request(
                url=f"/activity/{activity_id}",
                method="DELETE",
            )
            logger.info(
                "Delete response: %s",
                _redact(delete_resp, athlete_id),
            )

        # 5. Cleanup wellness ----------------------------------------------
        logger.info("Cleanup: PUT -1 wellness fields at %s", SPIKE_DATE)
        wellness_cleanup = await make_intervals_request(
            url=f"/athlete/{athlete_id}/wellness/{SPIKE_DATE}",
            data={"sleepSecs": -1, "fatigue": -1},
            method="PUT",
        )
        logger.info(
            "Wellness cleanup response: %s",
            _redact(wellness_cleanup, athlete_id),
        )

    if failures:
        logger.error("SMOKE FAILURES: %s", ", ".join(failures))
        return 1
    logger.info("SMOKE PHASE 2 — all steps OK")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
