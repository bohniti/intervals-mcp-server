"""
Climbing-related MCP tools for Intervals.icu.

This module contains the climbing tools: custom-field prerequisite
verification (`verify_custom_fields_setup`) and activity enrichment
(`enrich_activity_climbing`) — adds discipline, grades, session focus,
sends, attempts, and the native icu_rpe field to an existing activity
with discipline-aware grade validation, default-deny re-enrichment,
and readback verification.
"""

from typing import Any

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.tools.activities import add_activity_message  # D-22 — public, allowed
from intervals_mcp_server.utils.climbing import CUSTOM_FIELD_KEYS, Discipline, SessionFocus
from intervals_mcp_server.utils.formatting import format_climbing_activity
from intervals_mcp_server.utils.grades import validate_grade
from intervals_mcp_server.utils.validation import resolve_athlete_id

# Import mcp instance from shared module for tool registration
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401

config = get_config()


_README_POINTER = (
    "See README section 'Climbing setup — required Intervals.icu custom fields' "
    "for setup instructions."
)


# Activity readback parameters for the custom-field definitions heuristic.
# We inspect recent activities for the top-level presence of CUSTOM_FIELD_KEYS
# entries. Intervals.icu only returns a custom-field key on an activity when
# the field is (a) defined in the athlete account AND (b) has been populated
# on that activity, so we probe a reasonably sized window of recent work.
_READBACK_ACTIVITY_LIMIT = 50


async def _verify_custom_fields_setup_impl(
    athlete_id_to_use: str,
    api_key: str | None,
) -> tuple[bool, list[str], str]:
    """List which required climbing custom fields are defined in the athlete account.

    Strategy (per 01-SPIKE-FINDINGS.md): there is no definitions endpoint that
    exposes user-defined custom fields by key. `/sport-settings` returns
    sport-level config only; `/custom-fields` and `/activity-fields` are 404.
    We therefore use the readback heuristic: GET a window of recent activities
    and check whether each `CUSTOM_FIELD_KEYS` entry appears as a top-level
    key on any activity. A key present on ANY recent activity is considered
    defined; a key absent from ALL recent activities is reported missing.

    Returns:
        (ok, missing_field_keys, human_message)
            - ok: True if every CUSTOM_FIELD_KEYS key is defined
            - missing_field_keys: list of keys missing (empty when ok=True)
            - human_message: human-readable status string for MCP clients
    """
    required = set(CUSTOM_FIELD_KEYS.keys())

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/activities",
        api_key=api_key,
        params={"limit": _READBACK_ACTIVITY_LIMIT},
    )

    if isinstance(result, dict) and "error" in result:
        msg = f"Error fetching recent activities for readback: {result.get('message')}"
        return False, list(CUSTOM_FIELD_KEYS.keys()), msg

    defined_keys: set[str] = set()
    if isinstance(result, list):
        for activity in result:
            if isinstance(activity, dict):
                for key in required:
                    if key in activity:
                        defined_keys.add(key)

    # Build the missing list in CUSTOM_FIELD_KEYS insertion order for stable output.
    missing = [k for k in CUSTOM_FIELD_KEYS if k not in defined_keys]
    ok = not missing

    if ok:
        human_message = (
            "All required climbing custom fields are present "
            f"({len(required)}/{len(required)} defined)."
        )
    else:
        lines: list[str] = [
            "Missing required Intervals.icu custom fields "
            f"({len(missing)} of {len(required)} required):",
        ]
        for key in missing:
            spec = CUSTOM_FIELD_KEYS[key]
            opts = (
                f" options: {', '.join(spec.options)}"
                if spec.field_type == "select"
                else ""
            )
            lines.append(f"- {key} ({spec.field_type}){opts}")
        lines.append("")
        lines.append(_README_POINTER)
        human_message = "\n".join(lines)

    return ok, missing, human_message


async def _enrich_impl(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-return-statements,too-many-branches,too-many-locals,too-many-statements
    activity_id: str,
    *,
    discipline: str | None = None,
    indoor: bool | None = None,
    session_focus: str | None = None,
    top_grade_sent: str | None = None,
    top_grade_attempted: str | None = None,
    sends: int | None = None,
    attempts: int | None = None,
    rpe: int | None = None,
    override: bool = False,
    athlete_id: str | None = None,
    api_key: str | None = None,
    _skip_conflict_scan: bool = False,
) -> str:
    """Internal climbing-enrichment helper used by both the public tool and the
    Phase 3 create/complete tools. See `enrich_activity_climbing` for the
    public docstring covering behavior; the only structural difference is the
    `_skip_conflict_scan` flag (D-12) which short-circuits the pre-PUT GET +
    conflict-scan + override-audit when called immediately after a POST that
    just produced a fresh activity with no prior values.
    """
    # --- 1. At-least-one-supplied (D-12) ------------------------------------
    climbing_fields = (
        discipline,
        indoor,
        session_focus,
        top_grade_sent,
        top_grade_attempted,
        sends,
        attempts,
        rpe,
    )
    if all(v is None for v in climbing_fields):
        return (
            "Error: nothing to write — at least one climbing field or rpe "
            "must be supplied."
        )

    # --- 2. resolve_athlete_id ----------------------------------------------
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    # --- 3. Grade↔discipline coupling + grade validation (D-12 / D-13) ------
    disc_enum: Discipline | None = None
    if discipline is not None:
        try:
            disc_enum = Discipline(discipline)
        except ValueError:
            return (
                f"Error: unknown discipline {discipline!r}; expected one of "
                f"{[d.value for d in Discipline]}."
            )

    if top_grade_sent is not None or top_grade_attempted is not None:
        if disc_enum is None:
            return (
                "Error: discipline must be supplied when a grade is set "
                "(grade validation depends on it)."
            )
        for grade in (top_grade_sent, top_grade_attempted):
            if grade is not None:
                try:
                    validate_grade(grade, disc_enum)
                except ValueError as exc:
                    return f"Error: {exc}"

    # --- 4. session_focus enum check ----------------------------------------
    if session_focus is not None:
        try:
            SessionFocus(session_focus)
        except ValueError:
            return (
                f"Error: unknown session_focus {session_focus!r}; expected one of "
                f"{[f.value for f in SessionFocus]}."
            )

    # --- 5. rpe range check (D-12 / CLIMB-07) -------------------------------
    if rpe is not None and not 1 <= rpe <= 10:
        return f"Error: rpe={rpe} out of range; expected 1..10."

    # --- 6. Conditional verify-fields guard (D-20 / CLIMB-10) ---------------
    custom_field_supplied = any(
        v is not None
        for v in (
            discipline,
            indoor,
            session_focus,
            top_grade_sent,
            top_grade_attempted,
            sends,
            attempts,
        )
    )
    if custom_field_supplied:
        ok, _missing, human_message = await _verify_custom_fields_setup_impl(
            athlete_id_to_use, api_key
        )
        if not ok:
            return human_message
    # RPE-only writes skip this guard — icu_rpe is native, not a user-defined
    # custom field (D-21 carry-forward).

    # --- 7. GET activity (conflict scan) (D-14) -----------------------------
    pre: dict[str, Any] = {}
    if not _skip_conflict_scan:
        pre_get = await make_intervals_request(
            url=f"/activity/{activity_id}",
            api_key=api_key,
        )
        if isinstance(pre_get, dict) and "error" in pre_get:
            return (
                f"Error fetching activity for conflict scan: "
                f"{pre_get.get('message', 'Unknown error')}"
            )
        if isinstance(pre_get, list) and pre_get:
            pre = pre_get[0] if isinstance(pre_get[0], dict) else {}
        elif isinstance(pre_get, dict):
            pre = pre_get
        if not pre:
            return f"Error: activity {activity_id} not found."

    # --- 8. Build supplied pairs (API field name → sent value) --------------
    # `rpe` maps to API name `icu_rpe`. All other supplied params keep their name.
    supplied_pairs: dict[str, Any] = {}
    if discipline is not None:
        supplied_pairs["discipline"] = discipline
    if indoor is not None:
        supplied_pairs["indoor"] = indoor
    if session_focus is not None:
        supplied_pairs["session_focus"] = session_focus
    if top_grade_sent is not None:
        supplied_pairs["top_grade_sent"] = top_grade_sent
    if top_grade_attempted is not None:
        supplied_pairs["top_grade_attempted"] = top_grade_attempted
    if sends is not None:
        supplied_pairs["sends"] = sends
    if attempts is not None:
        supplied_pairs["attempts"] = attempts
    if rpe is not None:
        supplied_pairs["icu_rpe"] = rpe

    # --- 9. Conflict scan (D-14) --------------------------------------------
    conflicts: list[tuple[str, Any, Any]] = []
    for api_name, sent_value in supplied_pairs.items():
        existing = pre.get(api_name)
        if existing is not None and existing != sent_value:
            conflicts.append((api_name, existing, sent_value))

    if not _skip_conflict_scan and conflicts and not override:
        lines = [
            f"Error: activity {activity_id} already has values for fields below.",
            "Pass override=True to overwrite (an audit trail will be written).",
            "Conflicting fields:",
        ]
        for name, existing_val, sent in conflicts:
            lines.append(f"  {name}: {existing_val!r} (already set; sent: {sent!r})")
        return "\n".join(lines)

    # --- 10. Audit on override (D-14 / Pitfall #10) -------------------------
    if not _skip_conflict_scan and conflicts and override:
        parts = [f"{name}: {old}→{new}" for name, old, new in conflicts]
        content = "[enrich override] " + ", ".join(parts) + " (prior values preserved here)"
        await add_activity_message(
            activity_id=activity_id,
            content=content,
            api_key=api_key,
        )
        # Audit is fire-and-forget; downstream readback still verifies the write.

    # --- 11. PUT writes (D-16 — branch locked by Task 0) --------------------
    # D-16 path: SPLIT-PUT (per 02-SPIKE-FINDINGS.md)
    # Send icu_rpe first (separate PUT) and custom fields second (top-level
    # keys via PUT /activity/{id}). Custom-field shape is the working
    # hypothesis per 02-SPIKE-FINDINGS.md "Activity custom-field PUT shape" —
    # the API accepted top-level keys structurally (422 "Unknown custom field
    # [<key>]" indicates schemas need to be set up by the user; the body
    # envelope is correct).
    if rpe is not None:
        rpe_result = await make_intervals_request(
            url=f"/activity/{activity_id}",
            api_key=api_key,
            data={"icu_rpe": rpe},
            method="PUT",
        )
        if isinstance(rpe_result, dict) and "error" in rpe_result:
            return (
                f"Error writing icu_rpe: "
                f"{rpe_result.get('message', 'Unknown error')}"
            )
    if custom_field_supplied:
        cf_body = {k: v for k, v in supplied_pairs.items() if k != "icu_rpe"}
        cf_result = await make_intervals_request(
            url=f"/activity/{activity_id}",
            api_key=api_key,
            data=cf_body,
            method="PUT",
        )
        if isinstance(cf_result, dict) and "error" in cf_result:
            # Partial-failure error per D-16 (I-03 fix: single conditional).
            landed = f"icu_rpe={rpe}" if rpe is not None else "nothing"
            return (
                f"Error: partial enrichment — icu_rpe wrote successfully but "
                f"custom-field write failed: {cf_result.get('message', 'Unknown error')}. "
                f"Activity {activity_id} now has {landed} but no climbing metadata."
            )

    # --- 12. Readback (D-15) ------------------------------------------------
    post_get = await make_intervals_request(
        url=f"/activity/{activity_id}",
        api_key=api_key,
    )
    if isinstance(post_get, dict) and "error" in post_get:
        return (
            f"Error reading back activity after enrichment: "
            f"{post_get.get('message', 'Unknown error')}"
        )
    post: dict[str, Any]
    if isinstance(post_get, list) and post_get:
        post = post_get[0] if isinstance(post_get[0], dict) else {}
    elif isinstance(post_get, dict):
        post = post_get
    else:
        post = {}
    if not post:
        return f"Error: readback failed — activity {activity_id} not found after PUT."

    # --- 13/14. Per-field equality (supplied only) + README pointer (D-15) -
    custom_field_api_names = {
        "discipline",
        "indoor",
        "session_focus",
        "top_grade_sent",
        "top_grade_attempted",
        "sends",
        "attempts",
    }
    mismatches: list[str] = []
    cf_mismatched = False
    for api_name, sent_value in supplied_pairs.items():
        got = post.get(api_name)
        if got != sent_value:
            mismatches.append(f"  {api_name}: sent {sent_value!r}, got {got!r}")
            if api_name in custom_field_api_names:
                cf_mismatched = True

    if mismatches:
        msg = (
            f"Error: enrichment fields did not roundtrip on activity {activity_id}:\n"
            + "\n".join(mismatches)
        )
        if cf_mismatched:
            msg += "\n\n" + _README_POINTER
        return msg

    # --- 15. Success --------------------------------------------------------
    return (
        f"Successfully enriched activity {activity_id}.\n\n"
        + format_climbing_activity(post)
    )


@mcp.tool()
async def verify_custom_fields_setup(
    athlete_id: str | None = None,
    api_key: str | None = None,
) -> str:
    """Verify that required Intervals.icu climbing custom fields are defined.

    Before the climbing tools can write discipline, grades, session focus,
    sends, and attempts, the following custom fields must exist in the
    athlete's Intervals.icu account settings:

      - discipline (select: bouldering, sport_lead, top_rope, trad)
      - indoor (bool)
      - session_focus (select: power, endurance, technique, projecting, mileage)
      - top_grade_sent (text)
      - top_grade_attempted (text)
      - sends (integer)
      - attempts (integer)

    See the README section "Climbing setup — required Intervals.icu custom
    fields" for the full table and step-by-step setup instructions.

    Args:
        athlete_id: The Intervals.icu athlete ID (optional, uses ATHLETE_ID
            from .env if not provided).
        api_key: The Intervals.icu API key (optional, uses API_KEY from .env
            if not provided).

    Returns:
        A human-readable string reporting which required fields are defined
        and which (if any) are missing by name. If any required field is
        missing, the write tools added in Phase 2+ will refuse to run
        against this athlete account.
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    _ok, _missing, human_message = await _verify_custom_fields_setup_impl(
        athlete_id_to_use, api_key
    )
    return human_message


@mcp.tool()
async def enrich_activity_climbing(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-return-statements,too-many-branches,too-many-locals,too-many-statements
    activity_id: str,
    discipline: str | None = None,
    indoor: bool | None = None,
    session_focus: str | None = None,
    top_grade_sent: str | None = None,
    top_grade_attempted: str | None = None,
    sends: int | None = None,
    attempts: int | None = None,
    rpe: int | None = None,
    override: bool = False,
    athlete_id: str | None = None,
    api_key: str | None = None,
) -> str:
    """Enrich an existing Intervals.icu activity with climbing metadata + RPE.

    Use this tool when the activity already exists on Intervals.icu (e.g.
    Garmin-synced) and needs climbing details added. For brand-new climbing
    sessions without a prior record, see `create_climbing_activity`
    (Phase 3, not yet implemented).

    Before calling this tool, ask the user for any subset of:
    - discipline (bouldering / sport_lead / top_rope / trad)
    - indoor (true if gym, false if outdoors)
    - session_focus (power / endurance / technique / projecting / mileage)
    - top_grade_sent (Font for boulders e.g. "6A+", French sport for routes
      e.g. "6a+"). Sends only — successful completions.
    - top_grade_attempted (same scales — anything tried, including unsent)
    - sends (integer count of clean completions)
    - attempts (integer count of attempts including sends)
    - rpe (1-10 — Rate of Perceived Exertion; written to native icu_rpe)

    Validation is hard and runs BEFORE any HTTP call:
    - At least one climbing field or rpe must be supplied
    - If a grade is set, discipline must also be set (grade validation
      depends on it)
    - Font grades are rejected on sport_lead/top_rope/trad disciplines;
      French sport grades are rejected on bouldering
    - rpe must be 1..10

    Re-enrichment safeguard (Pitfall #10): if any supplied field already
    has a different non-null value on the activity, the tool refuses to
    proceed unless `override=True`. On override, an audit message is
    written to the activity's message log naming each old→new pair before
    the write.

    Custom-field schema guard (CLIMB-10): if any of the seven climbing
    custom fields is supplied, the tool first verifies the athlete's
    Intervals.icu account has those custom fields defined (via the same
    helper used by `verify_custom_fields_setup`). RPE-only writes skip
    this guard — `icu_rpe` is native, not user-defined.

    After the writes, the tool reads the activity back and verifies every
    supplied field roundtripped — if any value is missing or different,
    an error is returned naming each non-landing field.

    Args:
        activity_id: The Intervals.icu activity ID to enrich. Required.
        discipline: bouldering / sport_lead / top_rope / trad.
        indoor: True for gym, False for outdoors.
        session_focus: power / endurance / technique / projecting / mileage.
        top_grade_sent: Hardest grade sent (Font/French as appropriate).
        top_grade_attempted: Hardest grade attempted (Font/French).
        sends: Total successful sends.
        attempts: Total attempts (including sends).
        rpe: Rate of Perceived Exertion (1-10) — writes to native icu_rpe.
        override: If True, allow overwriting fields that already have
            different non-null values on the activity. An audit message
            is written to the activity log.
        athlete_id: Optional athlete ID (falls back to ATHLETE_ID env).
        api_key: Optional API key (falls back to API_KEY env).

    Returns:
        Success string with the rendered enriched activity, OR an error
        string naming the failure path (validation / verify-fields /
        re-enrichment conflict / API error / readback mismatch).
    """
    return await _enrich_impl(
        activity_id,
        discipline=discipline,
        indoor=indoor,
        session_focus=session_focus,
        top_grade_sent=top_grade_sent,
        top_grade_attempted=top_grade_attempted,
        sends=sends,
        attempts=attempts,
        rpe=rpe,
        override=override,
        athlete_id=athlete_id,
        api_key=api_key,
        # _skip_conflict_scan defaults False — public tool always scans (D-12).
    )


# ---------------------------------------------------------------------------
# Title-template helper for create_climbing_activity (D-16).
# ---------------------------------------------------------------------------

_DISCIPLINE_HUMAN: dict[str, str] = {
    "bouldering": "Bouldering",
    "sport_lead": "Sport lead",
    "top_rope": "Top rope",
    "trad": "Trad",
}


def _build_default_name(date: str, discipline: str | None) -> str:
    """Build the default activity name when the user did not supply one (D-16).

    - With discipline: 'Climbing — {Discipline} — {date}' (e.g., 'Climbing — Bouldering — 2026-04-27')
    - Without discipline: 'Climbing — {date}'

    Discipline values are mapped to human-readable form via _DISCIPLINE_HUMAN
    so enum-style 'sport_lead' does not appear verbatim in the Intervals.icu UI.
    Unknown discipline values fall back to the no-discipline template (no crash).
    """
    if discipline and discipline in _DISCIPLINE_HUMAN:
        return f"Climbing — {_DISCIPLINE_HUMAN[discipline]} — {date}"
    return f"Climbing — {date}"


@mcp.tool()
async def create_climbing_activity(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-return-statements,too-many-branches,too-many-locals,too-many-statements
    date: str,
    duration_minutes: int,
    name: str | None = None,
    discipline: str | None = None,
    indoor: bool | None = None,
    session_focus: str | None = None,
    top_grade_sent: str | None = None,
    top_grade_attempted: str | None = None,
    sends: int | None = None,
    attempts: int | None = None,
    rpe: int | None = None,
    athlete_id: str | None = None,
    api_key: str | None = None,
) -> str:
    """Create a climbing activity from scratch on Intervals.icu (CLIMB-02).

    Use this tool when the user climbed without a Garmin watch and without
    a prior planned calendar event. For Garmin-synced activities use
    `enrich_activity_climbing`. For completing a planned event from the
    calendar use `complete_climbing_session`.

    Before POSTing, the tool runs a duplicate guard (CLIMB-09): it GETs
    activities for `date` and refuses with the existing activity id(s) if a
    `WeightTraining` activity is already present that day. This prevents
    accidental duplicates on MCP reconnect or LLM retry.

    Activity type is hardcoded to `WeightTraining` — Phase 1 spike
    confirmed this works for climbing on Intervals.icu and feeds rpeTSS.
    Generic non-climbing manual activities are out of scope for v1.

    `duration_minutes` is converted internally to `moving_time` (seconds);
    pass minutes ('how many minutes did you climb?'), not seconds.

    `name` defaults to a discipline-aware template:
      - With discipline: 'Climbing — Bouldering — 2026-04-27'
      - Without discipline: 'Climbing — 2026-04-27'
      - User-supplied `name` is used verbatim.

    If any climbing field (discipline, indoor, session_focus, top_grade_sent,
    top_grade_attempted, sends, attempts, rpe) is supplied, after the POST
    succeeds the tool calls into the same enrichment logic as
    `enrich_activity_climbing` (validation, custom-field guard, split-PUT
    of icu_rpe and custom fields, readback verification) — single-shot.
    If only `date` and `duration_minutes` are supplied (plus optional name),
    the tool returns success after the POST without writing climbing fields.

    Atomicity (D-09): if the POST succeeds but the post-POST enrichment
    fails, the activity is NOT deleted. The error names the new activity_id
    and hints at `enrich_activity_climbing(activity_id={id}, override=True,
    ...)` so the user (via Claude) can retry adding metadata.

    Args:
        date: Activity date in YYYY-MM-DD format. Required. The tool
            constructs `start_date_local` as f'{date}T00:00:00' (local
            midnight, no timezone) — never derived from system time
            (Pitfall #4).
        duration_minutes: Total climbing time in minutes. Required.
            Converted to seconds for the API.
        name: Optional activity title; defaults to a discipline-aware
            template if absent.
        discipline: bouldering / sport_lead / top_rope / trad.
        indoor: True for gym, False for outdoors.
        session_focus: power / endurance / technique / projecting / mileage.
        top_grade_sent: Hardest grade sent (Font/French as appropriate).
        top_grade_attempted: Hardest grade attempted.
        sends: Total successful sends.
        attempts: Total attempts (including sends).
        rpe: Rate of Perceived Exertion (1-10), written to native icu_rpe.
        athlete_id: Optional athlete ID (falls back to ATHLETE_ID env).
        api_key: Optional API key (falls back to API_KEY env).

    Returns:
        Success string ('Successfully created activity {id} on {date}.' or
        the enriched success from `_enrich_impl` when climbing fields were
        supplied), OR an error string naming the failure path
        (duplicate-guard hit / POST error / enrichment-fail-after-POST).
    """
    # --- 1. resolve_athlete_id (D-22 carry-forward) -------------------------
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    # --- 2. Duplicate guard (CLIMB-09 / Pitfall #1 / D-01..D-04) ------------
    dup_params: dict[str, Any] = {"oldest": date, "newest": date}
    dup_result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/activities",
        api_key=api_key,
        params=dup_params,
    )
    if isinstance(dup_result, dict) and "error" in dup_result:
        return (
            f"Error checking for duplicate activities: "
            f"{dup_result.get('message', 'Unknown error')}"
        )

    matches: list[dict[str, Any]] = []
    if isinstance(dup_result, list):
        for activity in dup_result:
            if not isinstance(activity, dict):
                continue
            if activity.get("type") != "WeightTraining":
                continue
            sdl = activity.get("start_date_local") or ""
            if isinstance(sdl, str) and sdl.startswith(date):
                matches.append(activity)

    if matches:
        # D-02 / D-04 — refuse with all matches; Claude reads the list and decides.
        lines = [
            f"Error: a WeightTraining activity already exists on {date}; "
            f"refusing to create a duplicate.",
            "Matching activities:",
        ]
        for a in matches:
            lines.append(
                f'  {a.get("id")} — "{a.get("name", "Unnamed")}" ({a.get("start_date_local")})'
            )
        lines.append(
            "Call enrich_activity_climbing(activity_id=..., ...) to add "
            "climbing metadata to an existing activity."
        )
        return "\n".join(lines)

    # --- 3. Build POST body (D-13..D-17) ------------------------------------
    # Pitfall #4 / D-17 — start_date_local is built from user-supplied date,
    # NEVER from datetime.utcnow() or any system clock. Format matches
    # events.py::_prepare_event_data.
    activity_name = name if name is not None else _build_default_name(date, discipline)
    create_body: dict[str, Any] = {
        "start_date_local": f"{date}T00:00:00",
        "type": "WeightTraining",            # D-15 — hardcoded for v1 climbing
        "name": activity_name,
        "moving_time": duration_minutes * 60,  # D-14 — minutes → seconds
    }

    # --- 4. POST manual activity --------------------------------------------
    create_resp = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/activities/manual",
        api_key=api_key,
        data=create_body,
        method="POST",
    )
    if isinstance(create_resp, dict) and "error" in create_resp:
        # D-10 — POST is atomic; surface the API error verbatim.
        return f"Error creating activity: {create_resp.get('message', 'Unknown error')}"
    if not isinstance(create_resp, dict) or not create_resp.get("id"):
        return f"Error: unexpected response from activity create: {create_resp!r}"
    new_activity_id = str(create_resp["id"])

    # --- 5. Single-shot enrich after POST (D-08, D-09, D-12) ----------------
    any_enrich_field = any(
        v is not None
        for v in (
            discipline, indoor, session_focus,
            top_grade_sent, top_grade_attempted,
            sends, attempts, rpe,
        )
    )
    if not any_enrich_field:
        # No climbing metadata supplied — return the create-only success.
        return f"Successfully created activity {new_activity_id} on {date}."

    enrich_result = await _enrich_impl(
        new_activity_id,
        discipline=discipline,
        indoor=indoor,
        session_focus=session_focus,
        top_grade_sent=top_grade_sent,
        top_grade_attempted=top_grade_attempted,
        sends=sends,
        attempts=attempts,
        rpe=rpe,
        override=False,                # fresh activity has no prior values
        athlete_id=athlete_id_to_use,
        api_key=api_key,
        _skip_conflict_scan=True,      # D-12 — fresh-POST optimization
    )
    if not enrich_result.startswith("Successfully"):
        # D-09 — POST landed but enrichment failed; do NOT delete the activity.
        return (
            f"Created activity {new_activity_id} but enrichment failed:\n"
            f"{enrich_result}\n\n"
            f"Call enrich_activity_climbing(activity_id={new_activity_id}, "
            f"override=True, ...) to retry adding climbing metadata."
        )
    return enrich_result


@mcp.tool()
async def complete_climbing_session(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-return-statements,too-many-branches,too-many-locals,too-many-statements
    event_id: str,
    discipline: str | None = None,
    indoor: bool | None = None,
    session_focus: str | None = None,
    top_grade_sent: str | None = None,
    top_grade_attempted: str | None = None,
    sends: int | None = None,
    attempts: int | None = None,
    rpe: int | None = None,
    athlete_id: str | None = None,
    api_key: str | None = None,
) -> str:
    """Complete a planned climbing event by creating a linked activity (CLIMB-01).

    Use this tool when the user has a planned climbing session on the
    Intervals.icu calendar and wants to mark it done. The tool fetches
    the planned event server-side, POSTs a manual activity linked to it
    via `paired_event_id`, and (if climbing fields are supplied)
    enriches the new activity in a single tool call.

    The planned event STAYS on the calendar — completion creates a linked
    activity, it does not delete the planned event (PROJECT.md Key
    Decision). This preserves planned-vs-actual history.

    Date, type, and name in the new activity all come VERBATIM from the
    planned event — there is no separate `date` or `type` parameter for
    the user to drift from the event. The user supplies only the
    climbing-specific fields (discipline, RPE, grades, etc.).

    Already-paired guard: if the planned event already has a
    `paired_event_id` (i.e., it has already been completed), the tool
    refuses with a hint to call `enrich_activity_climbing` on the
    paired activity instead. This is the second-layer guard against
    accidental duplicates beyond the date+type check.

    Duplicate guard (CLIMB-09): the tool also runs the same date+type
    duplicate check as `create_climbing_activity` — if a `WeightTraining`
    activity already exists on the event's date independent of the event
    pairing, refuse with the existing activity id(s).

    Readback verification: after POST, the tool reads the new activity
    back and confirms `paired_event_id == event_id`. If the link did
    not take, an error is returned naming the activity_id and the
    mismatch — strong signal that explicit-set was ignored.

    Atomicity (D-09): if POST succeeds but enrichment or paired-event
    readback fails, the activity is NOT deleted. The error names the
    new activity_id and hints at retry via `enrich_activity_climbing`.

    Args:
        event_id: Planned event ID on the Intervals.icu calendar.
            Required. The tool reads `start_date_local`, `type`, `name`,
            and `moving_time` from this event verbatim.
        discipline: bouldering / sport_lead / top_rope / trad.
        indoor: True for gym, False for outdoors.
        session_focus: power / endurance / technique / projecting / mileage.
        top_grade_sent: Hardest grade sent (Font/French as appropriate).
        top_grade_attempted: Hardest grade attempted.
        sends: Total successful sends.
        attempts: Total attempts (including sends).
        rpe: Rate of Perceived Exertion (1-10), written to native icu_rpe.
        athlete_id: Optional athlete ID (falls back to ATHLETE_ID env).
        api_key: Optional API key (falls back to API_KEY env).

    Returns:
        Success string ('Successfully completed session: created activity
        {id} paired to event {event_id}.' or the enriched success when
        climbing fields are supplied), OR an error string naming the
        failure path (event-not-found / already-paired / duplicate-guard
        hit / POST error / paired_event_id readback mismatch /
        enrichment-fail-after-POST).
    """
    # --- 1. resolve_athlete_id ----------------------------------------------
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    # --- 2. GET the planned event (D-05) ------------------------------------
    # URL pattern matches `tools/events.py::get_event_by_id` (singular `/event/{id}`).
    event_get = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/event/{event_id}",
        api_key=api_key,
    )
    if isinstance(event_get, dict) and "error" in event_get:
        return f"Error fetching planned event: {event_get.get('message', 'Unknown error')}"
    if not isinstance(event_get, dict) or not event_get:
        return f"Error: planned event {event_id} not found."

    # --- 3. Already-paired guard (CONTEXT specifics) ------------------------
    existing_pair = event_get.get("paired_event_id")
    if existing_pair:
        return (
            f"Event {event_id} is already paired to activity {existing_pair}. "
            f"Call enrich_activity_climbing(activity_id={existing_pair}, ...) "
            f"to add climbing metadata."
        )

    # --- 4. Extract event values (D-07: event is source of truth) -----------
    event_start_date_local = event_get.get("start_date_local")
    event_type = event_get.get("type") or "WeightTraining"  # fallback for v1 climbing
    event_name = event_get.get("name") or f"Climbing — {event_id}"
    if not isinstance(event_start_date_local, str) or not event_start_date_local:
        return f"Error: planned event {event_id} has no start_date_local."
    # Date prefix for the duplicate-guard filter (and for the success message).
    event_date = event_start_date_local.split("T", 1)[0]

    # --- 5. Duplicate guard (CLIMB-09 / D-03 — both tools enforce) ----------
    dup_params: dict[str, Any] = {"oldest": event_date, "newest": event_date}
    dup_result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/activities",
        api_key=api_key,
        params=dup_params,
    )
    if isinstance(dup_result, dict) and "error" in dup_result:
        return (
            f"Error checking for duplicate activities: "
            f"{dup_result.get('message', 'Unknown error')}"
        )

    matches: list[dict[str, Any]] = []
    if isinstance(dup_result, list):
        for activity in dup_result:
            if not isinstance(activity, dict):
                continue
            if activity.get("type") != "WeightTraining":
                continue
            sdl = activity.get("start_date_local") or ""
            if isinstance(sdl, str) and sdl.startswith(event_date):
                matches.append(activity)

    if matches:
        # D-02 / D-04 — same multi-line refusal as create_climbing_activity.
        lines = [
            f"Error: a WeightTraining activity already exists on {event_date}; "
            f"refusing to create a duplicate.",
            "Matching activities:",
        ]
        for a in matches:
            lines.append(
                f'  {a.get("id")} — "{a.get("name", "Unnamed")}" ({a.get("start_date_local")})'
            )
        lines.append(
            "Call enrich_activity_climbing(activity_id=..., ...) to add "
            "climbing metadata to an existing activity."
        )
        return "\n".join(lines)

    # --- 6. Build POST body with explicit paired_event_id (D-06, D-07) ------
    post_body: dict[str, Any] = {
        "start_date_local": event_start_date_local,  # verbatim from event
        "type": event_type,                          # verbatim from event
        "name": event_name,                          # verbatim from event
        "paired_event_id": event_id,                 # D-06 — explicit
    }
    # `moving_time` from the event if provided; else 0 (Intervals.icu accepts 0
    # per Phase 1 spike when the event did not declare a duration).
    event_moving_time = event_get.get("moving_time")
    if isinstance(event_moving_time, int) and event_moving_time > 0:
        post_body["moving_time"] = event_moving_time
    else:
        post_body["moving_time"] = 0

    # --- 7. POST the linked activity ----------------------------------------
    create_resp = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/activities/manual",
        api_key=api_key,
        data=post_body,
        method="POST",
    )
    if isinstance(create_resp, dict) and "error" in create_resp:
        return f"Error creating activity: {create_resp.get('message', 'Unknown error')}"
    if not isinstance(create_resp, dict) or not create_resp.get("id"):
        return f"Error: unexpected response from activity create: {create_resp!r}"
    new_activity_id = str(create_resp["id"])

    # --- 8. Readback verifies paired_event_id (specifics) -------------------
    verify_get = await make_intervals_request(
        url=f"/activity/{new_activity_id}",
        api_key=api_key,
    )
    if isinstance(verify_get, dict) and "error" in verify_get:
        return (
            f"Created activity {new_activity_id} but paired-event readback failed: "
            f"{verify_get.get('message', 'Unknown error')}. "
            f"The link from event {event_id} to activity {new_activity_id} may not have taken."
        )
    verify_dict: dict[str, Any] = {}
    if isinstance(verify_get, list) and verify_get and isinstance(verify_get[0], dict):
        verify_dict = verify_get[0]
    elif isinstance(verify_get, dict):
        verify_dict = verify_get
    if not verify_dict:
        return (
            f"Error reading back created activity {new_activity_id} "
            f"for paired_event_id verification."
        )
    got_pair = verify_dict.get("paired_event_id")
    if got_pair != event_id:
        return (
            f"Error: paired_event_id mismatch on activity {new_activity_id}: "
            f"sent {event_id!r}, got {got_pair!r}. "
            f"The link from event {event_id} to activity may not have taken."
        )

    # --- 9. Single-shot enrich after POST + readback (D-08, D-09, D-12) -----
    any_enrich_field = any(
        v is not None
        for v in (
            discipline, indoor, session_focus,
            top_grade_sent, top_grade_attempted,
            sends, attempts, rpe,
        )
    )
    if not any_enrich_field:
        return (
            f"Successfully completed session: created activity {new_activity_id} "
            f"paired to event {event_id}."
        )

    enrich_result = await _enrich_impl(
        new_activity_id,
        discipline=discipline,
        indoor=indoor,
        session_focus=session_focus,
        top_grade_sent=top_grade_sent,
        top_grade_attempted=top_grade_attempted,
        sends=sends,
        attempts=attempts,
        rpe=rpe,
        override=False,
        athlete_id=athlete_id_to_use,
        api_key=api_key,
        _skip_conflict_scan=True,  # D-12 — fresh-POST optimization
    )
    if not enrich_result.startswith("Successfully"):
        # D-09 — POST landed but enrichment failed; do NOT delete the activity.
        return (
            f"Created activity {new_activity_id} (paired to event {event_id}) "
            f"but enrichment failed:\n{enrich_result}\n\n"
            f"Call enrich_activity_climbing(activity_id={new_activity_id}, "
            f"override=True, ...) to retry adding climbing metadata."
        )
    return enrich_result
