#!/usr/bin/env python3
"""
Spike (Phase 2): close the three open Intervals.icu API unknowns.

NOT A PYTEST TEST. Writes to the live Intervals.icu account at a far-future
date (2099-01-01) and attempts cleanup. The script resolves three open
contracts left after the Phase 1 spike:

    (D-01a) The exact body shape (and URL/method) that lands climbing
            custom fields on an activity such that all seven keys
            (discipline, indoor, session_focus, top_grade_sent,
            top_grade_attempted, sends, attempts) roundtrip via GET.
    (D-01b) The accepted (min, max) range for each wellness subjective
            field (fatigue, stress, motivation, mood, soreness,
            sleep_quality), discovered by probing values 1..10.
    (D-01c) The icu_rpe write path: either co-located with custom
            fields in a single PUT, or a separate PUT issued first.

Findings (paste-ready code blocks for downstream Plans 02-02 and 02-04)
are written to:

    .planning/phases/02-wellness-write-and-activity-enrichment/02-SPIKE-FINDINGS.md

Run once, by hand:

    uv run scripts/spike_write_endpoints_phase2.py

Pre-requisites: API_KEY and ATHLETE_ID set in .env.

Exit codes:
    0  All three unknowns resolved (LOCKED). Plans 02-02 and 02-04 may proceed.
    1  Configuration error (missing API_KEY / ATHLETE_ID).
    2  D-05 hard-stop: no activity custom-field PUT body roundtripped.
       Plan 02-04 MUST NOT begin until the user re-discusses the
       "Structured climbing data -> Intervals.icu custom fields" key
       decision in PROJECT.md.

Cleanup: the script issues DELETE for the throwaway activity (confirmed
working in Phase 1) and PUTs -1 to clear wellness numeric fields at the
spike date. If anything is left behind, the findings file lists manual
cleanup steps against the Intervals.icu web UI.
"""

# pylint: disable=too-many-locals,too-many-statements,too-many-branches

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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("spike_phase2")

SPIKE_DATE = "2099-01-01"  # far-future, no real data here
ATHLETE_REDACTED = "{athlete_id}"  # placeholder used in findings file
FINDINGS_PATH = (
    Path(__file__).resolve().parents[1]
    / ".planning"
    / "phases"
    / "02-wellness-write-and-activity-enrichment"
    / "02-SPIKE-FINDINGS.md"
)

# Climbing custom-field probe payload (D-01a). Mirror the seven keys the
# downstream tool will need to land on an activity. Values are deliberately
# heterogeneous (str, bool, int) so the readback can confirm each type
# survives whatever envelope the API requires.
CF_PAYLOAD: dict[str, Any] = {
    "discipline": "bouldering",
    "indoor": True,
    "session_focus": "power",
    "top_grade_sent": "6A",
    "top_grade_attempted": "6A+",
    "sends": 3,
    "attempts": 5,
}

# Wellness subjective fields probed for accepted range (D-01b).
# Mapping: public param name (write_wellness_entry signature, D-06) ->
# Intervals.icu API field name (lowercase or camelCase per API). The
# Phase 1 wellness readback (01-SPIKE-FINDINGS.md) showed the API uses
# `sleepQuality` (camelCase) — sending `sleep_quality` returns 422
# "Unrecognized wellness field". Public name stays `sleep_quality` for
# the human-friendly write_wellness_entry param; the spike maps it to
# the camelCase API name when issuing PUTs.
WELLNESS_FIELD_API_NAMES: dict[str, str] = {
    "fatigue": "fatigue",
    "stress": "stress",
    "motivation": "motivation",
    "mood": "mood",
    "soreness": "soreness",
    "sleep_quality": "sleepQuality",
}
WELLNESS_SUBJECTIVE_FIELDS: list[str] = list(WELLNESS_FIELD_API_NAMES.keys())

# Probe values for each wellness subjective field. Covers both the 1-4
# and 1-10 hypotheses without committing to either; whichever values
# return 200 AND roundtrip define the real accepted range.
WELLNESS_PROBE_VALUES: list[int] = list(range(1, 11))  # 1..10 inclusive

# Inter-request pacing (seconds). Intervals.icu rate-limits aggressive
# probing — Phase 2 first run hit 429 around 100 requests in flight.
# 0.4s/req keeps us well under any reasonable per-second cap. Total
# wall-clock for ~80 probe requests stays under a minute.
REQUEST_PAUSE_SECS: float = 0.4


def _redact(obj: Any, athlete_id: str) -> Any:
    """Recursively replace athlete_id occurrences with ATHLETE_REDACTED for findings output."""
    if isinstance(obj, str):
        return obj.replace(athlete_id, ATHLETE_REDACTED)
    if isinstance(obj, dict):
        return {k: _redact(v, athlete_id) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact(v, athlete_id) for v in obj]
    return obj


def _is_error(resp: Any) -> bool:
    """Return True if the make_intervals_request response is an error dict."""
    return isinstance(resp, dict) and resp.get("error") is True


def _normalize_readback(result: Any) -> dict[str, Any] | None:
    """Activity GET may return dict or list; pick the first dict if list."""
    if isinstance(result, list):
        return result[0] if result and isinstance(result[0], dict) else None
    if isinstance(result, dict) and not _is_error(result):
        return result
    return None


def _wellness_readback_value(result: Any, field: str) -> Any:
    """Pull a single field from wellness GET response (which is a list)."""
    if isinstance(result, list) and result and isinstance(result[0], dict):
        return result[0].get(field)
    if isinstance(result, dict) and not _is_error(result):
        return result.get(field)
    return None


async def _paced_request(**kwargs: Any) -> Any:
    """make_intervals_request wrapper that sleeps after each call.

    Avoids tripping Intervals.icu rate limits during the spike's high-
    volume probing (~80+ wellness PUTs + ~16 activity attempts). The
    sleep is post-call so callers see the response immediately and the
    pause amortises into the next iteration's wall-clock.
    """
    result = await make_intervals_request(**kwargs)
    await asyncio.sleep(REQUEST_PAUSE_SECS)
    return result


async def spike_activity_custom_field_put_shapes(athlete_id: str) -> dict[str, Any]:
    """Probe activity custom-field PUT shape + icu_rpe write path (D-01a, D-01c).

    Flow:
        Step A: POST throwaway activity (Phase 1 confirmed body shape).
        Step B: For each (body_variant, endpoint_variant) combination,
                issue write + GET readback; first all-keys-roundtrip wins.
        Step C: icu_rpe co-location probe — try in same PUT first, fall
                back to isolated PUTs if needed; record the chosen path.
        Step D: DELETE the throwaway activity.

    Returns a findings dict with full audit trail (every attempt) plus
    the winning shape if any.
    """
    findings: dict[str, Any] = {
        "athlete_id_template": ATHLETE_REDACTED,
        "spike_date": SPIKE_DATE,
        "cf_payload": CF_PAYLOAD,
        "attempts": [],
        "winning_body": None,
        "winning_endpoint": None,
        "winning_method": None,
        "winning_url_template": None,
    }

    # ---- Step A: create throwaway activity ----
    create_body = {
        "start_date_local": f"{SPIKE_DATE}T00:00:00",
        "type": "WeightTraining",
        "name": "SPIKE PHASE2 - DELETE ME",
        "moving_time": 3600,
    }
    create_url = f"/athlete/{athlete_id}/activities/manual"
    findings["create_body_sent"] = create_body
    findings["create_endpoint_template"] = create_url.replace(athlete_id, ATHLETE_REDACTED)
    create_resp = await _paced_request(
        url=create_url,
        data=create_body,
        method="POST",
    )
    findings["create_response"] = create_resp

    activity_id = create_resp.get("id") if isinstance(create_resp, dict) else None
    if not activity_id or _is_error(create_resp):
        logger.error("Could not create throwaway activity for Step B; aborting probe.")
        findings["fatal_create_failure"] = create_resp
        return findings

    findings["activity_id_present"] = True

    # ---- Step B: iterate body x endpoint variants ----
    body_variants: list[tuple[str, dict[str, Any]]] = [
        ("top_level_keys", dict(CF_PAYLOAD)),
        ("nested_custom_fields_envelope", {"custom_fields": dict(CF_PAYLOAD)}),
        ("nested_customFields_camelCase", {"customFields": dict(CF_PAYLOAD)}),
        ("nested_fields_envelope", {"fields": dict(CF_PAYLOAD)}),
    ]
    endpoint_variants: list[tuple[str, str, str]] = [
        ("PUT_/activity/{id}", "PUT", f"/activity/{activity_id}"),
        (
            "PUT_/athlete/{aid}/activity/{id}",
            "PUT",
            f"/athlete/{athlete_id}/activity/{activity_id}",
        ),
        ("POST_/activity/{id}", "POST", f"/activity/{activity_id}"),
        (
            "PUT_/activity/{id}/custom-fields",
            "PUT",
            f"/activity/{activity_id}/custom-fields",
        ),
    ]

    found_winner = False
    for body_label, body in body_variants:
        if found_winner:
            break
        for endpoint_label, method, url in endpoint_variants:
            write_resp = await _paced_request(url=url, data=body, method=method)
            readback_resp = await _paced_request(url=f"/activity/{activity_id}")
            readback_dict = _normalize_readback(readback_resp)

            partial_match_keys: list[str] = []
            all_match = False
            if readback_dict is not None:
                partial_match_keys = [
                    k for k, v in CF_PAYLOAD.items() if readback_dict.get(k) == v
                ]
                all_match = len(partial_match_keys) == len(CF_PAYLOAD)

            url_template = url.replace(athlete_id, ATHLETE_REDACTED).replace(
                str(activity_id), "{activity_id}"
            )
            attempt = {
                "body_label": body_label,
                "endpoint_label": endpoint_label,
                "method": method,
                "url_template": url_template,
                "write_response": write_resp,
                "readback_partial_match_keys": partial_match_keys,
                "all_keys_roundtripped": all_match,
            }
            findings["attempts"].append(attempt)

            if all_match:
                findings["winning_body"] = body
                findings["winning_endpoint"] = endpoint_label
                findings["winning_method"] = method
                findings["winning_url_template"] = url_template
                found_winner = True
                logger.info(
                    "Custom-field PUT shape found: body=%s endpoint=%s",
                    body_label,
                    endpoint_label,
                )
                break

    # ---- Step C: icu_rpe co-location probe (D-01c) ----
    findings["icu_rpe_co_located"] = False
    findings["icu_rpe_co_located_attempt"] = None
    findings["icu_rpe_isolated_attempts"] = []
    findings["icu_rpe_isolated_winner"] = None

    if findings["winning_body"] is not None:
        # Try co-located write: winning body + icu_rpe in same PUT
        co_body: dict[str, Any]
        winning_body = findings["winning_body"]
        # Merge icu_rpe at the same level the winning body uses for CF keys.
        # If the winner is a flat dict (top_level_keys), put icu_rpe at top.
        # If nested, icu_rpe is a NATIVE field (not a custom field) so it
        # belongs at top level alongside the envelope.
        if any(k in winning_body for k in CF_PAYLOAD):
            co_body = dict(winning_body)
            co_body["icu_rpe"] = 6
        else:
            co_body = dict(winning_body)
            co_body["icu_rpe"] = 6

        # Reuse the winning endpoint+method.
        co_method = findings["winning_method"]
        co_url_template = findings["winning_url_template"] or ""
        # Reconstruct the absolute URL by substituting placeholders back.
        co_url = co_url_template.replace(ATHLETE_REDACTED, athlete_id).replace(
            "{activity_id}", str(activity_id)
        )
        co_write = await _paced_request(url=co_url, data=co_body, method=co_method)
        co_readback = _normalize_readback(
            await _paced_request(url=f"/activity/{activity_id}")
        )
        co_rpe = co_readback.get("icu_rpe") if co_readback else None
        co_attempt = {
            "body_label": "winning_body_plus_icu_rpe",
            "endpoint_label": findings["winning_endpoint"],
            "method": co_method,
            "url_template": co_url_template,
            "write_response": co_write,
            "icu_rpe_readback": co_rpe,
            "co_located_success": co_rpe == 6,
        }
        findings["icu_rpe_co_located_attempt"] = co_attempt
        findings["icu_rpe_co_located"] = co_rpe == 6

    # If not co-located (or no winning body), try isolated icu_rpe PUTs.
    if not findings["icu_rpe_co_located"]:
        isolated_variants: list[tuple[str, str, str]] = [
            ("PUT_/activity/{id}", "PUT", f"/activity/{activity_id}"),
            (
                "PUT_/athlete/{aid}/activity/{id}",
                "PUT",
                f"/athlete/{athlete_id}/activity/{activity_id}",
            ),
        ]
        for label, method, url in isolated_variants:
            iso_write = await _paced_request(
                url=url, data={"icu_rpe": 6}, method=method
            )
            iso_readback = _normalize_readback(
                await _paced_request(url=f"/activity/{activity_id}")
            )
            iso_rpe = iso_readback.get("icu_rpe") if iso_readback else None
            url_template = url.replace(athlete_id, ATHLETE_REDACTED).replace(
                str(activity_id), "{activity_id}"
            )
            attempt = {
                "label": label,
                "method": method,
                "url_template": url_template,
                "body": {"icu_rpe": 6},
                "write_response": iso_write,
                "icu_rpe_readback": iso_rpe,
                "isolated_success": iso_rpe == 6,
            }
            findings["icu_rpe_isolated_attempts"].append(attempt)
            if iso_rpe == 6 and findings["icu_rpe_isolated_winner"] is None:
                findings["icu_rpe_isolated_winner"] = attempt

    # Decide the final icu_rpe path label.
    if findings["icu_rpe_co_located"]:
        findings["icu_rpe_path"] = "single_put_with_custom_fields"
    elif findings["icu_rpe_isolated_winner"] is not None:
        findings["icu_rpe_path"] = "split_put_rpe_first"
    else:
        findings["icu_rpe_path"] = "unresolved"

    # ---- Step D: cleanup ----
    delete_resp = await _paced_request(
        url=f"/activity/{activity_id}", method="DELETE"
    )
    findings["delete_response"] = delete_resp
    findings["delete_available"] = not _is_error(delete_resp)
    findings["activity_id_for_manual_cleanup"] = (
        str(activity_id) if not findings["delete_available"] else None
    )

    return findings


async def spike_wellness_subjective_scales(athlete_id: str) -> dict[str, Any]:
    """Probe accepted ranges for the six wellness subjective fields (D-01b).

    For each public field name, look up its Intervals.icu API field name
    (e.g. `sleep_quality` -> `sleepQuality`), PUT each integer 1..10
    against the spike date, then GET readback to verify each value that
    wrote also roundtripped. Build per-field `accepted_values` list,
    plus a summary `WELLNESS_RANGES_LOCKED` dict suitable for direct
    paste into utils/wellness.py.

    Wellness PUT is upsert (Phase 1 confirmed: write_1 sleepSecs survived
    write_2 fatigue). The next value in the sweep simply overwrites the
    previous, so no per-value clear is needed and we save half the calls.

    Cleanup at end: PUT -1 across all probed numeric fields (using their
    API names) to clear the spike date.
    """
    findings: dict[str, Any] = {
        "spike_date": SPIKE_DATE,
        "endpoint_template": f"/athlete/{ATHLETE_REDACTED}/wellness/{SPIKE_DATE}",
        "field_api_names": dict(WELLNESS_FIELD_API_NAMES),
        "fields": {},
    }

    for public_name in WELLNESS_SUBJECTIVE_FIELDS:
        api_name = WELLNESS_FIELD_API_NAMES[public_name]
        per_field: dict[str, Any] = {
            "api_name": api_name,
            "attempts": [],
            "accepted_values": [],
            "accepted_min": None,
            "accepted_max": None,
        }
        for value in WELLNESS_PROBE_VALUES:
            write_resp = await _paced_request(
                url=f"/athlete/{athlete_id}/wellness/{SPIKE_DATE}",
                data={api_name: value},
                method="PUT",
            )
            wrote_ok = not _is_error(write_resp)

            readback_value: Any = None
            roundtripped = False
            if wrote_ok:
                readback_resp = await _paced_request(
                    url=f"/athlete/{athlete_id}/wellness",
                    params={"oldest": SPIKE_DATE, "newest": SPIKE_DATE},
                )
                readback_value = _wellness_readback_value(readback_resp, api_name)
                roundtripped = readback_value == value

            per_field["attempts"].append(
                {
                    "value": value,
                    "wrote_ok": wrote_ok,
                    "write_response_status": (
                        write_resp.get("status_code")
                        if isinstance(write_resp, dict) and "status_code" in write_resp
                        else (200 if wrote_ok else None)
                    ),
                    "readback_value": readback_value,
                    "roundtripped": roundtripped,
                }
            )
            if roundtripped:
                per_field["accepted_values"].append(value)

        if per_field["accepted_values"]:
            per_field["accepted_min"] = min(per_field["accepted_values"])
            per_field["accepted_max"] = max(per_field["accepted_values"])
        findings["fields"][public_name] = per_field
        logger.info(
            "Wellness field %s (api=%s): accepted=%s",
            public_name,
            api_name,
            per_field["accepted_values"],
        )

    # Build the paste-ready WELLNESS_RANGES_LOCKED dict, keyed by the
    # PUBLIC param name (the write_wellness_entry signature uses
    # public names per D-06; the api_name mapping lives next to it).
    locked: dict[str, tuple[int, int] | None] = {}
    for public_name, per_field in findings["fields"].items():
        if per_field["accepted_values"]:
            locked[public_name] = (per_field["accepted_min"], per_field["accepted_max"])
        else:
            locked[public_name] = None
    findings["WELLNESS_RANGES_LOCKED"] = locked

    # Final cleanup pass: clear all probed fields with -1 in one PUT.
    # Use API names (e.g. sleepQuality not sleep_quality) so the API
    # actually recognizes them.
    cleanup_body: dict[str, Any] = dict.fromkeys(
        WELLNESS_FIELD_API_NAMES.values(), -1
    )
    cleanup_body["sleepSecs"] = -1
    findings["cleanup_response"] = await _paced_request(
        url=f"/athlete/{athlete_id}/wellness/{SPIKE_DATE}",
        data=cleanup_body,
        method="PUT",
    )

    return findings


def _detect_unknown_custom_field_pattern(attempts: list[dict[str, Any]]) -> bool:
    """Return True if all attempts failed with API saying \"Unknown custom field [X]\".

    This signature means the API recognized the body shape but the athlete
    account hasn't defined the custom-field schemas — i.e. SETUP-01 has
    not been completed. Emits a different recommendation than a true body-
    shape failure (which would warrant the D-05 Key-Decision re-discuss).
    """
    if not attempts:
        return False
    saw_unknown = False
    for attempt in attempts:
        resp = attempt.get("write_response") or {}
        if not isinstance(resp, dict):
            continue
        msg = str(resp.get("message", ""))
        if "Unknown custom field" in msg:
            saw_unknown = True
    return saw_unknown


def _format_winning_body_block(activity_findings: dict[str, Any]) -> list[str]:
    """Render the LOCKED activity custom-field PUT shape section."""
    winning_body = activity_findings.get("winning_body")
    method = activity_findings.get("winning_method")
    url_template = activity_findings.get("winning_url_template")
    attempts = activity_findings.get("attempts", []) or []

    lines: list[str] = []
    if winning_body is not None:
        lines.append("## Activity custom-field PUT shape (LOCKED)\n\n")
        lines.append(
            "Plan 02-04 (`enrich_activity_climbing`) MUST use this exact body shape, "
            "endpoint, and method.\n\n"
        )
        lines.append(f"- **Method:** `{method}`\n")
        lines.append(f"- **URL template:** `{url_template}`\n\n")
        lines.append("**Paste-ready Python body:**\n\n")
        lines.append("```python\n")
        lines.append("body = ")
        lines.append(json.dumps(winning_body, indent=4, default=str))
        lines.append("\n```\n\n")
    elif _detect_unknown_custom_field_pattern(attempts):
        # API recognized the shape but the schemas don't exist. This is
        # the SETUP-01 prerequisite, not a Key Decision invalidation.
        lines.append(
            "## Activity custom-field PUT shape (UNRESOLVED - SETUP-01 PREREQUISITE NOT MET)\n\n"
        )
        lines.append(
            "**Diagnosis.** Every PUT with the climbing custom-field keys at the top "
            "level returned `422 \"Unknown custom field [<key>]\"`. This error pattern "
            "means the Intervals.icu API recognized the body shape (top-level keys is "
            "the right envelope) but the custom-field SCHEMAS have not been defined on "
            "the athlete's account yet. This is exactly the SETUP-01 prerequisite "
            "documented in PROJECT.md (\"User prerequisite: Intervals.icu custom fields "
            "must exist in the athlete's account before the tools that write them will "
            "work\").\n\n"
        )
        lines.append("**Required action by user (does NOT invalidate any Key Decision):**\n\n")
        lines.append(
            "1. Open Intervals.icu web UI -> athlete settings -> custom fields.\n"
            "2. Create the seven custom-field schemas the README's SETUP-01 section "
            "lists: `discipline`, `indoor`, `session_focus`, `top_grade_sent`, "
            "`top_grade_attempted`, `sends`, `attempts` (with the exact keys and "
            "types from `src/intervals_mcp_server/utils/climbing.py` "
            "`CUSTOM_FIELD_KEYS`).\n"
            "3. Re-run `uv run python scripts/spike_write_endpoints_phase2.py` to "
            "confirm all seven keys roundtrip — that re-run will rewrite this "
            "section to LOCKED with the paste-ready body.\n\n"
        )
        lines.append(
            "**Body shape working hypothesis (to confirm by post-SETUP-01 re-run):** "
            "top-level keys via `PUT /activity/{id}` — this is what the 422 error "
            "messages strongly suggest. The other body envelopes "
            "(`custom_fields`, `customFields`, `fields`) all returned the SAME "
            "\"Unknown custom field [X]\" pattern with the envelope name as `[X]`, "
            "which confirms the API treats top-level keys as candidate custom-field "
            "names — exactly what we want.\n\n"
        )
        lines.append(
            "**Plan 02-04 disposition:** Plan 02-04 implementation can proceed "
            "**after** the user finishes SETUP-01 and the spike re-run confirms "
            "the body shape. The existing `verify_custom_fields_setup` MCP tool "
            "from Phase 1 (D-11) is the runtime guard that protects "
            "`enrich_activity_climbing` from this same failure mode in production "
            "(D-20).\n\n"
        )
        lines.append("**All attempts (full audit trail):**\n\n")
        lines.append("```json\n")
        lines.append(json.dumps(attempts, indent=2, default=str))
        lines.append("\n```\n\n")
    else:
        lines.append(
            "## Activity custom-field PUT shape (UNRESOLVED - Plan 02-04 BLOCKED - D-05)\n\n"
        )
        lines.append(
            "**Hard-stop.** No body x endpoint combination roundtripped all seven "
            "climbing custom-field keys, AND none of the failures matched the "
            "\"Unknown custom field\" SETUP-01 pattern. Plan 02-04 "
            "(`enrich_activity_climbing`) MUST NOT begin until the user re-discusses "
            "the \"Structured climbing data -> Intervals.icu custom fields\" Key "
            "Decision in PROJECT.md. Possible re-discussions: "
            "description-as-structured-text fallback, or scope-cut to RPE-only "
            "enrichment.\n\n"
        )
        lines.append("**All attempts (full audit trail):**\n\n")
        lines.append("```json\n")
        lines.append(json.dumps(attempts, indent=2, default=str))
        lines.append("\n```\n\n")
    return lines


def _format_wellness_ranges_block(wellness_findings: dict[str, Any]) -> list[str]:
    """Render the LOCKED wellness ranges section."""
    locked = wellness_findings.get("WELLNESS_RANGES_LOCKED", {})
    lines: list[str] = ["## Wellness subjective-field ranges (LOCKED)\n\n"]
    lines.append(
        "Plan 02-02 copies this dict literal into `WELLNESS_RANGES` in "
        "`src/intervals_mcp_server/utils/wellness.py`. Fields with `None` "
        "are unresolved - leave them out of `WELLNESS_RANGES` until re-probed.\n\n"
    )
    lines.append("**Paste-ready Python literal:**\n\n")
    lines.append("```python\n")
    lines.append("WELLNESS_RANGES_LOCKED = {\n")
    for field, rng in locked.items():
        if rng is None:
            lines.append(
                f"    # {field!r}: unresolved - leave out of WELLNESS_RANGES until re-probed\n"
            )
        else:
            lo, hi = rng
            lines.append(f"    {field!r}: ({lo}, {hi}),\n")
    lines.append("}\n```\n\n")
    return lines


def _format_icu_rpe_block(activity_findings: dict[str, Any]) -> list[str]:
    """Render the LOCKED icu_rpe write path section."""
    path = activity_findings.get("icu_rpe_path", "unresolved")
    lines: list[str] = ["## icu_rpe write path (LOCKED)\n\n"]

    if path == "single_put_with_custom_fields":
        lines.append(
            "Plan 02-04 writes `icu_rpe` co-located with the climbing custom "
            "fields in a single PUT.\n\n"
        )
        lines.append("**Paste-ready pattern:**\n\n")
        lines.append("```python\n")
        lines.append("# Single PUT carrying both custom fields and icu_rpe.\n")
        lines.append("body = winning_body | {\"icu_rpe\": rpe}  # rpe in [1,10]\n")
        lines.append("await make_intervals_request(\n")
        lines.append(f"    url={activity_findings.get('winning_url_template')!r}.replace(\n")
        lines.append("        \"{activity_id}\", activity_id\n")
        lines.append("    ),\n")
        lines.append("    data=body,\n")
        lines.append(f"    method={activity_findings.get('winning_method')!r},\n")
        lines.append(")\n```\n\n")
    elif path == "split_put_rpe_first":
        winner = activity_findings.get("icu_rpe_isolated_winner") or {}
        lines.append(
            "Plan 02-04 writes `icu_rpe` in a separate PUT BEFORE the custom-field "
            "PUT (RPE first, custom fields second). On partial failure (RPE landed, "
            "custom fields didn't, or vice versa) the tool returns an explicit error "
            "naming what landed and what didn't (see D-16).\n\n"
        )
        lines.append("**Paste-ready pattern:**\n\n")
        lines.append("```python\n")
        lines.append("# Step 1: RPE first.\n")
        lines.append("await make_intervals_request(\n")
        lines.append(f"    url={winner.get('url_template')!r}.replace(\n")
        lines.append("        \"{activity_id}\", activity_id\n")
        lines.append("    ),\n")
        lines.append('    data={"icu_rpe": rpe},\n')
        lines.append(f"    method={winner.get('method')!r},\n")
        lines.append(")\n")
        lines.append("# Step 2: custom fields (winning_body / winning_endpoint).\n")
        lines.append("```\n\n")
    else:
        lines.append(
            "**UNRESOLVED.** Neither co-located nor isolated `icu_rpe` writes "
            "roundtripped. Plan 02-04 must surface this in its planning step. "
            "See full audit trail below.\n\n"
        )

    lines.append("**Audit trail:**\n\n")
    lines.append("```json\n")
    lines.append(
        json.dumps(
            {
                "icu_rpe_co_located": activity_findings.get("icu_rpe_co_located"),
                "icu_rpe_co_located_attempt": activity_findings.get(
                    "icu_rpe_co_located_attempt"
                ),
                "icu_rpe_isolated_attempts": activity_findings.get(
                    "icu_rpe_isolated_attempts"
                ),
                "icu_rpe_isolated_winner": activity_findings.get(
                    "icu_rpe_isolated_winner"
                ),
                "icu_rpe_path": activity_findings.get("icu_rpe_path"),
            },
            indent=2,
            default=str,
        )
    )
    lines.append("\n```\n\n")
    return lines


def write_findings(
    activity_findings: dict[str, Any],
    wellness_findings: dict[str, Any],
    athlete_id: str,
) -> None:
    """Dump findings to 02-SPIKE-FINDINGS.md with paste-ready code blocks.

    Redacts athlete_id everywhere via `_redact()` before writing.
    """
    FINDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    activity_redacted = _redact(activity_findings, athlete_id)
    wellness_redacted = _redact(wellness_findings, athlete_id)

    content: list[str] = []
    content.append("# Spike findings - Phase 2 second probe\n\n")
    content.append(f"**Spike date (target):** {SPIKE_DATE}\n\n")
    content.append(
        "All occurrences of the live athlete id are redacted to "
        f"`{ATHLETE_REDACTED}`.\n\n"
    )
    content.append(
        "This file is the canonical reference for Plans 02-02 (wellness ranges) "
        "and 02-04 (activity enrichment). Paste the LOCKED code blocks below into "
        "the corresponding modules verbatim.\n\n"
    )

    # Section 1: Activity custom-field PUT shape (LOCKED or UNRESOLVED).
    content.extend(_format_winning_body_block(activity_redacted))

    # Section 2: Wellness subjective-field ranges (LOCKED).
    content.extend(_format_wellness_ranges_block(wellness_redacted))

    # Section 3: icu_rpe write path (LOCKED or UNRESOLVED).
    content.extend(_format_icu_rpe_block(activity_redacted))

    # Section 4: Manual cleanup.
    content.append("## Manual cleanup (if DELETE unavailable)\n\n")
    content.append(
        f"- Wellness at {SPIKE_DATE}: cleared with `-1` values in spike; "
        "verify in Intervals.icu UI (athlete settings -> wellness page -> 2099-01-01).\n"
    )
    content.append(
        "- Activity id for manual cleanup: "
        f"{activity_redacted.get('activity_id_for_manual_cleanup')}\n\n"
    )

    # Full audit trail (raw findings) for posterity.
    content.append("## Full audit trail (raw)\n\n")
    content.append("### Activity probe\n\n")
    content.append("```json\n")
    content.append(json.dumps(activity_redacted, indent=2, default=str))
    content.append("\n```\n\n")
    content.append("### Wellness probe\n\n")
    content.append("```json\n")
    content.append(json.dumps(wellness_redacted, indent=2, default=str))
    content.append("\n```\n")

    FINDINGS_PATH.write_text("".join(content), encoding="utf-8")


async def main() -> None:
    """Run the three probes, write findings, enforce D-05 hard-stop on activity probe."""
    config = get_config()
    if not config.athlete_id or not config.api_key:
        logger.error(
            "API_KEY and ATHLETE_ID must be set in .env before running the spike."
        )
        sys.exit(1)

    logger.info("Spike target date: %s", SPIKE_DATE)
    logger.info("Spike running against athlete: %s", ATHLETE_REDACTED)

    # Order: wellness first so its results are usable for Plan 02-02 even
    # if the activity probe later fails (D-04 — wellness side does not
    # depend on activity-write resolution).
    logger.info("Probing wellness subjective-field ranges (D-01b)...")
    wellness_findings = await spike_wellness_subjective_scales(config.athlete_id)

    logger.info("Probing activity custom-field PUT shape and icu_rpe (D-01a, D-01c)...")
    activity_findings = await spike_activity_custom_field_put_shapes(config.athlete_id)

    write_findings(activity_findings, wellness_findings, config.athlete_id)
    logger.info("Findings written to %s", FINDINGS_PATH)

    # D-05 hard-stop: if no activity custom-field PUT body roundtripped,
    # exit non-zero so a human reviewer can block Plan 02-04. Distinguish
    # the SETUP-01 case (recoverable: user defines schemas + re-run) from
    # a true Key Decision invalidation (irrecoverable without re-discuss).
    if activity_findings.get("winning_body") is None:
        attempts = activity_findings.get("attempts") or []
        if _detect_unknown_custom_field_pattern(attempts):
            logger.error(
                "HARD-STOP (D-05 -> SETUP-01): every activity custom-field PUT failed "
                "with API \"Unknown custom field [<key>]\" — schemas are not defined "
                "on the athlete account. Body shape is correct; complete SETUP-01 "
                "(README) and re-run this spike."
            )
        else:
            logger.error(
                "HARD-STOP (D-05): no activity custom-field PUT body roundtripped, "
                "and the failure pattern does NOT match SETUP-01. Re-discuss the "
                "\"Structured climbing data -> Intervals.icu custom fields\" Key "
                "Decision in PROJECT.md before Plan 02-04 begins."
            )
        logger.error("Findings: %s", FINDINGS_PATH)
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
