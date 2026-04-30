# Phase 3: Activity Creation and Session Completion - Pattern Map

**Mapped:** 2026-04-28
**Files analyzed:** 5 (3 modified, 1 new test, 1 optional new script)
**Analogs found:** 5 / 5

---

## File Classification

| New/Modified File | Action | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|--------|------|-----------|----------------|---------------|
| `src/intervals_mcp_server/tools/climbing.py` | MODIFY | tool (MCP) | request-response (POST + PUT + GET; orchestrator) | `tools/climbing.py::enrich_activity_climbing` (same file, in-place refactor) + `tools/events.py::_prepare_event_data` (POST body shape) + `tools/activities.py::get_activities` (duplicate-guard GET) | exact (self-analog for `_enrich_impl`; sibling-file analogs for POST body + GET filter) |
| `tests/test_climbing_create.py` | CREATE | test | request-response (mocked) | `tests/test_climbing_write.py` | exact (same module, same mock seam, same `monkeypatch` + `asyncio.run` pattern) |
| `src/intervals_mcp_server/utils/formatting.py` | POSSIBLE MODIFY (additive) | formatter | data transform | `utils/formatting.py::format_climbing_activity` (existing function in same file, line 552–599) | exact (extend existing renderer additively) |
| `src/intervals_mcp_server/utils/climbing.py` | POSSIBLE MODIFY (additive) | utility (enums + map) | static data | `utils/climbing.py::Discipline` enum + `CUSTOM_FIELD_KEYS` (existing, lines 28–34, 60–98) | exact (additive sibling to existing `Discipline` enum) |
| `scripts/smoke_phase3.py` | OPTIONAL CREATE | script (live smoke) | live request-response | `scripts/smoke_phase2.py` | exact |

---

## Pattern Assignments

### `src/intervals_mcp_server/tools/climbing.py` (tool, request-response)

This file gets THREE related changes: (1) refactor `enrich_activity_climbing` body into `_enrich_impl(activity_id, ..., _skip_conflict_scan=False)`, (2) add `create_climbing_activity` tool, (3) add `complete_climbing_session` tool. Each draws from a different analog.

#### A. Refactor: `enrich_activity_climbing` → `_enrich_impl` (D-11)

**Analog:** `src/intervals_mcp_server/tools/climbing.py::enrich_activity_climbing` (the function being refactored — self-analog).

**Public-tool thin-wrapper shape** (existing signature at lines 155–169 stays as `@mcp.tool()`; body becomes a forwarder to `_enrich_impl`):

```python
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
    """[docstring preserved verbatim]"""
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
```

**`_enrich_impl` body** = the existing 240-line block at `tools/climbing.py:233–472` moved verbatim into a private async helper. Add a single internal kwarg `_skip_conflict_scan: bool = False` (D-12) that, when True, **skips section 7 (GET conflict scan), section 9 (conflict detection), and section 10 (audit on override)**. Sections 1–6 (validation, custom-field guard) and 8, 11–15 (build pairs, PUT writes, readback, success) all run unchanged. Note: `_` prefix is intra-file only — not exported, not imported by sibling tool modules (D-22 satisfied).

**Pattern: at-least-one-supplied (carry-forward D-12 from Phase 2)** — verbatim from lines 233–248:

```python
# --- 1. At-least-one-supplied (D-12) ------------------------------------
climbing_fields = (
    discipline, indoor, session_focus,
    top_grade_sent, top_grade_attempted, sends, attempts, rpe,
)
if all(v is None for v in climbing_fields):
    return (
        "Error: nothing to write — at least one climbing field or rpe "
        "must be supplied."
    )
```

**For the new tools' fresh-POST path:** `_skip_conflict_scan=True` short-circuits past lines 315–333 (pre-GET) and lines 355–381 (conflict scan + audit). The freshly-POSTed activity has no prior values, so conflict detection is a wasted GET (D-12 rationale).

---

#### B. New tool: `create_climbing_activity` (D-13, D-14, D-15, D-16, D-17)

**Analog:** `tools/climbing.py::enrich_activity_climbing` (signature shape, decorator, pylint disables, error-string returns) + `tools/events.py::_prepare_event_data` (Pitfall #4 `start_date_local` format).

**Decorator + signature pattern** (mirrors lines 155–169 of the existing `enrich_activity_climbing`):

```python
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
    """[Google-style docstring; document hardcoded type='WeightTraining',
    duration_minutes→moving_time conversion, optional name template]"""
```

**`resolve_athlete_id` pattern** (verbatim from `enrich_activity_climbing` lines 250–253 / `events.py::add_or_update_event` lines 358–360):

```python
athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
if error_msg:
    return error_msg
```

**Pitfall #4 `start_date_local` format** — copy from `tools/events.py::_prepare_event_data` line 56:

```python
# events.py:56 — the established model
"start_date_local": start_date + "T00:00:00",
```

In Phase 3 form (string from user input only — never `datetime.utcnow()`):

```python
start_date_local = f"{date}T00:00:00"  # Pitfall #4 / D-17
```

**Duplicate-guard GET pattern** (D-01, D-02, D-03) — adapt from `tools/activities.py::get_activities` lines 132–144 (calls the underlying API directly, **not** the public `get_activities` tool — per CONTEXT canonical_refs):

```python
# Duplicate guard (CLIMB-09 / Pitfall #1) — GET activities for the target date.
dup_params = {"oldest": date, "newest": date}
dup_result = await make_intervals_request(
    url=f"/athlete/{athlete_id_to_use}/activities",
    api_key=api_key,
    params=dup_params,
)
if isinstance(dup_result, dict) and "error" in dup_result:
    return f"Error checking for duplicate activities: {dup_result.get('message', 'Unknown error')}"

# Filter to (date, type=='WeightTraining') matches per D-01.
matches: list[dict[str, Any]] = []
if isinstance(dup_result, list):
    for activity in dup_result:
        if not isinstance(activity, dict):
            continue
        if activity.get("type") != "WeightTraining":
            continue
        # start_date_local on a same-day match starts with the YYYY-MM-DD.
        sdl = activity.get("start_date_local") or ""
        if isinstance(sdl, str) and sdl.startswith(date):
            matches.append(activity)

if matches:
    # D-02 / D-04 — list ALL matches with id, name, start_date_local; suggest enrich.
    lines = [
        f"Error: a WeightTraining activity already exists on {date}; refusing to create a duplicate.",
        "Matching activities:",
    ]
    for a in matches:
        lines.append(
            f'  {a.get("id")} — "{a.get("name", "Unnamed")}" ({a.get("start_date_local")})'
        )
    lines.append(
        "Call enrich_activity_climbing(activity_id=..., ...) to add climbing metadata to an existing activity."
    )
    return "\n".join(lines)
```

**Title template (D-16)** — small in-file helper (or imported from `utils/climbing.py`; see Section D below):

```python
_DISCIPLINE_HUMAN = {
    "bouldering": "Bouldering",
    "sport_lead": "Sport lead",
    "top_rope": "Top rope",
    "trad": "Trad",
}

def _build_default_name(date: str, discipline: str | None) -> str:
    if discipline and discipline in _DISCIPLINE_HUMAN:
        return f"Climbing — {_DISCIPLINE_HUMAN[discipline]} — {date}"
    return f"Climbing — {date}"

# In tool body:
activity_name = name if name is not None else _build_default_name(date, discipline)
```

**POST body + endpoint** (Phase 1 spike confirmed shape; mirror `scripts/smoke_phase2.py` lines 111–121):

```python
create_body = {
    "start_date_local": f"{date}T00:00:00",
    "type": "WeightTraining",                # D-15 — hardcoded
    "name": activity_name,
    "moving_time": duration_minutes * 60,    # D-14 — minutes → seconds
}
create_resp = await make_intervals_request(
    url=f"/athlete/{athlete_id_to_use}/activities/manual",
    api_key=api_key,
    data=create_body,
    method="POST",
)
if isinstance(create_resp, dict) and "error" in create_resp:
    return f"Error creating activity: {create_resp.get('message', 'Unknown error')}"
if not isinstance(create_resp, dict) or not create_resp.get("id"):
    return f"Error: unexpected response from activity create: {create_resp!r}"
new_activity_id = str(create_resp["id"])
```

**Single-shot enrich after POST (D-08, D-09, D-12)** — call `_enrich_impl` only when at least one climbing field or rpe is supplied; otherwise return success directly:

```python
any_enrich_field = any(
    v is not None
    for v in (discipline, indoor, session_focus, top_grade_sent,
              top_grade_attempted, sends, attempts, rpe)
)
if not any_enrich_field:
    # No metadata to add — return the create-only success.
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
    override=False,
    athlete_id=athlete_id_to_use,
    api_key=api_key,
    _skip_conflict_scan=True,  # D-12 — fresh activity has no prior values
)
if not enrich_result.startswith("Successfully"):
    # D-09 — POST landed but enrichment failed; do NOT delete.
    return (
        f"Created activity {new_activity_id} but enrichment failed:\n{enrich_result}\n\n"
        f"Call enrich_activity_climbing(activity_id={new_activity_id}, override=True, ...) "
        f"to retry adding climbing metadata."
    )
return enrich_result
```

---

#### C. New tool: `complete_climbing_session` (D-05, D-06, D-07, D-08)

**Analog:** `create_climbing_activity` (above, mirror duplicate-guard + POST + enrich) + `tools/events.py::get_event_by_id` lines 165–199 (event GET pattern).

**Signature** (mirrors `enrich_activity_climbing` parameter shape, with `event_id` replacing `activity_id`, no `date`/`duration_minutes` since they come from the event):

```python
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
    """[docstring; document that event provides date/type/name verbatim,
    paired_event_id is set explicitly, planned event stays on calendar]"""
```

**Event GET (D-05)** — adapt from `tools/events.py::get_event_by_id` lines 184–199. Note URL: existing get-by-id uses `/athlete/{id}/event/{event_id}` (singular `event`) at line 185. Confirm during planning whether singular or plural is correct for v1; events.py uses both (`/events/{id}` for DELETE at line 220, `/event/{id}` for GET at line 185). Test fakes can match either; live behavior must be confirmed.

```python
event_get = await make_intervals_request(
    url=f"/athlete/{athlete_id_to_use}/events/{event_id}",  # confirm singular vs plural
    api_key=api_key,
)
if isinstance(event_get, dict) and "error" in event_get:
    return f"Error fetching planned event: {event_get.get('message', 'Unknown error')}"
if not isinstance(event_get, dict) or not event_get:
    return f"Error: planned event {event_id} not found."

# D-07 — event is source of truth for date/type/name.
event_start_date_local = event_get.get("start_date_local")  # e.g. "2026-04-27T00:00:00"
event_type = event_get.get("type") or "WeightTraining"
event_name = event_get.get("name") or f"Climbing — {event_id}"
if not isinstance(event_start_date_local, str):
    return f"Error: planned event {event_id} has no start_date_local."
event_date = event_start_date_local.split("T", 1)[0]  # "2026-04-27"

# Already-paired check (Claude's Discretion in CONTEXT.md — recommended yes).
existing_pair = event_get.get("paired_event_id")
if existing_pair:
    return (
        f"Event {event_id} is already paired to activity {existing_pair}. "
        f"Call enrich_activity_climbing(activity_id={existing_pair}, ...) "
        f"to add climbing metadata."
    )
```

**Duplicate guard** — same pattern as `create_climbing_activity` Section B above (D-03 — both tools enforce it). Use `event_date` as the `oldest`/`newest` filter.

**POST body with explicit `paired_event_id` (D-06, D-07)**:

```python
post_body = {
    "start_date_local": event_start_date_local,  # verbatim from event (already T00:00:00)
    "type": event_type,
    "name": event_name,
    "moving_time": event_get.get("moving_time") or 0,  # event-supplied or 0
    "paired_event_id": event_id,                       # D-06 — explicit
}
create_resp = await make_intervals_request(
    url=f"/athlete/{athlete_id_to_use}/activities/manual",
    api_key=api_key,
    data=post_body,
    method="POST",
)
# (Same error handling as create_climbing_activity Section B)
new_activity_id = str(create_resp["id"])
```

**Readback-verify `paired_event_id == event_id`** (specifics: "Readback verification of `paired_event_id`"):

```python
verify_get = await make_intervals_request(
    url=f"/activity/{new_activity_id}",
    api_key=api_key,
)
verify_dict = verify_get[0] if isinstance(verify_get, list) and verify_get else verify_get
if not isinstance(verify_dict, dict):
    return f"Error reading back created activity {new_activity_id} for paired_event_id verification."
got_pair = verify_dict.get("paired_event_id")
if got_pair != event_id:
    return (
        f"Error: paired_event_id mismatch on activity {new_activity_id}: "
        f"sent {event_id!r}, got {got_pair!r}. "
        f"The link from event to activity may not have taken."
    )
```

**Then enrich** — same `_enrich_impl(... _skip_conflict_scan=True)` call as Section B.

---

#### D. POSSIBLE: `discipline_human` map placement (Claude's Discretion)

**Two options, planner picks one:**

- **Option 1 (recommended):** in `src/intervals_mcp_server/utils/climbing.py`, sibling to `Discipline` enum (line 28–34). Keeps climbing taxonomy together; importable from `tools/climbing.py`:
  ```python
  # utils/climbing.py — append after Discipline enum
  DISCIPLINE_HUMAN: MappingProxyType[str, str] = MappingProxyType({
      Discipline.BOULDERING.value: "Bouldering",
      Discipline.SPORT_LEAD.value: "Sport lead",
      Discipline.TOP_ROPE.value: "Top rope",
      Discipline.TRAD.value: "Trad",
  })
  ```
- **Option 2:** in `tools/climbing.py` next to the title-builder helper. Slightly tighter locality; no cross-module dependency.

Either keeps D-22 satisfied (utility import is public, allowed; in-file constant is trivially in-scope).

---

### `tests/test_climbing_create.py` (test, request-response mocked)

**Analog:** `tests/test_climbing_write.py` (verbatim mocking pattern).

**Imports + bootstrap** (verbatim from lines 1–20 of `test_climbing_write.py`):

```python
"""Unit tests for tools/climbing.py::create_climbing_activity and complete_climbing_session — CLIMB-01, CLIMB-02, CLIMB-09."""

import asyncio
import inspect
import os
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

import pytest  # pylint: disable=wrong-import-position

from intervals_mcp_server.utils.climbing import (  # pylint: disable=wrong-import-position
    CUSTOM_FIELD_KEYS,
    Discipline,
    SessionFocus,
)
```

**Fake-response helpers** (mirror `_make_fake_all_present` / `_make_fake_clean_activity` from `test_climbing_write.py:28–54` — copy-paste; consider moving to a shared `tests/_climbing_fakes.py` only if the duplication becomes painful — Phase 2 chose to duplicate, so Phase 3 should match):

```python
def _make_fake_all_present() -> list[dict[str, object]]:
    activity: dict[str, object] = {
        "id": "i1",
        "name": "Session with all climbing fields",
        "type": "WeightTraining",
    }
    for key in CUSTOM_FIELD_KEYS:
        activity[key] = None
    return [activity]


def _make_fake_clean_activity(activity_id: str = "i1") -> dict[str, object]:
    activity: dict[str, object] = {
        "id": activity_id,
        "name": "Sample",
        "type": "WeightTraining",
        "start_date_local": "2026-04-27T00:00:00",
    }
    for key in CUSTOM_FIELD_KEYS:
        activity[key] = None
    activity["icu_rpe"] = None
    return activity
```

**Mocking pattern (the established seam)** — verbatim shape from `test_climbing_write.py:91–118`:

```python
async def fake_request(
    url: str,
    api_key: str | None = None,
    params: dict[str, Any] | None = None,
    method: str = "GET",
    data: dict[str, Any] | None = None,
) -> Any:
    # Branch on (method, url, params) — return shape per Intervals.icu API.
    ...

monkeypatch.setattr(
    "intervals_mcp_server.api.client.make_intervals_request", fake_request
)
monkeypatch.setattr(
    "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
)
```

**Both seams MUST be patched** (the module-level re-import in `tools/climbing.py:14` means the callsite reference is `intervals_mcp_server.tools.climbing.make_intervals_request`, not the original in `api.client`). This is exactly how `test_climbing_write.py` does it.

**Async invocation pattern**:

```python
result = asyncio.run(
    create_climbing_activity(date="2026-04-27", duration_minutes=90, athlete_id="i1")
)
assert result.startswith("Successfully"), result
```

**Required test cases** (per CONTEXT integration_points + specifics):

| # | Test | Pattern source |
|---|------|----------------|
| 1 | `test_create_tool_registered` — `inspect.iscoroutinefunction` + signature param count | `test_enrich_tool_registered` lines 62–69 |
| 2 | `test_complete_tool_registered` — same shape | same |
| 3 | `test_create_duplicate_guard_fires` — fake activities-list returns one matching activity → tool refuses with id+name+date | `test_default_deny_re_enrichment` lines 227–271 (refuses-with-list pattern) + `get_activities` URL filter |
| 4 | `test_create_no_duplicate_proceeds_to_post` — empty activities-list → POST runs, enrich runs, success | `test_enrich_writes_custom_fields` lines 77–133 (multi-step counter pattern) |
| 5 | `test_create_pitfall4_timezone` — `date="2026-04-27"` → POST body has `start_date_local == "2026-04-27T00:00:00"` exactly | `test_enrich_uses_locked_put_body_shape` lines 662–722 (capture POST body, assert keys) |
| 6 | `test_create_pitfall4_never_uses_utcnow` — monkeypatch `datetime.utcnow()` to next-day UTC; POST body still uses user input verbatim | extension of #5 |
| 7 | `test_create_name_template_default` — no `name`, `discipline="bouldering"` → POST body name `== "Climbing — Bouldering — 2026-04-27"` | extension of #5 |
| 8 | `test_create_name_template_no_discipline` — no `name`, no `discipline` → name `== "Climbing — 2026-04-27"` | extension of #5 |
| 9 | `test_create_user_supplied_name_used_verbatim` — `name="Whatever"` → POST body name `== "Whatever"` | extension of #5 |
| 10 | `test_create_post_error_returns_error` — fake POST returns `{"error": True, ...}` → tool returns "Error creating activity" | `test_split_put_partial_failure_named` lines 730–785 (error-dict shape) |
| 11 | `test_create_enrichment_fails_after_post_keeps_activity` — POST OK, enrichment PUT fails → error names new activity_id, hints retry, NO delete call | `test_split_put_partial_failure_named` (same pattern, transposed) |
| 12 | `test_complete_event_provides_date_type_name` — fake event GET returns event dict; POST body matches event verbatim AND has `paired_event_id == event_id` | extension of #5 |
| 13 | `test_complete_already_paired_refuses` — event GET returns `paired_event_id` non-null → tool refuses, suggests enrich on paired activity | `test_default_deny_re_enrichment` (refusal pattern) |
| 14 | `test_complete_paired_event_id_readback_verifies` — POST OK, readback returns activity with matching `paired_event_id` → success | extension of #4 |
| 15 | `test_complete_paired_event_id_readback_mismatch_errors` — readback returns different `paired_event_id` → tool returns mismatch error | `test_icu_rpe_readback_mismatch_errors` lines 394–438 |
| 16 | `test_skip_conflict_scan_path_no_pre_get` — when `_enrich_impl` is called from `create_climbing_activity` post-POST, NO conflict-scan GET fires (counter == 0) | counter-driven assertion: `test_missing_custom_fields_short_circuits` lines 174–219 |
| 17 | `test_create_no_climbing_fields_skips_enrich` — `date` + `duration_minutes` only → POST runs, no PUT, no enrich-impl call | extension of #4 |

**Pylint disable header** (mirror the file-level convention in `test_climbing_write.py`): use `pytest.MonkeyPatch` typed parameter; add `# pylint: disable=wrong-import-position` on the `pytest` and `intervals_mcp_server` imports per the existing test file convention (lines 14, 16).

---

### `src/intervals_mcp_server/utils/formatting.py` (formatter, data transform — POSSIBLE additive modify)

**Analog:** `utils/formatting.py::format_climbing_activity` lines 552–599 (the function being potentially extended).

**Pattern: additive field-render line** (only if test #14 needs `paired_event_id` rendered for a clearer assertion — otherwise skip). Insert before the closing `)` of the f-string at line 598 OR as a separate conditional line so a missing key still produces N/A:

```python
# Existing renderer body lines 575–599 — extend ONLY if useful.
# Add somewhere between Date and Discipline (or at end before RPE):
paired = activity.get("paired_event_id")
paired_str = paired if paired else "N/A"

return (
    f"Climbing Activity\n"
    f"  ID: {activity.get('id', 'N/A')}\n"
    f"  Name: {activity.get('name', 'Unnamed')}\n"
    f"  Date: {activity.get('start_date_local', 'Unknown')}\n"
    f"  Paired event: {paired_str}\n"           # <-- new line, additive only
    f"  Discipline: {activity.get('discipline', 'N/A')}\n"
    # ... rest unchanged
)
```

**Regression risk:** Phase 2's `test_format_climbing_activity_renders_existing_fields_unchanged` (`tests/test_climbing.py:293–332`) is a **byte-equal snapshot** test. Adding a line to the renderer **will fail that test** unless the snapshot string at lines 314–326 is updated in the same commit. Plan accordingly: either skip this extension (Claude's Discretion in CONTEXT — `format_climbing_activity` is **not required** for Phase 3) OR update the snapshot.

**Recommendation:** Skip this modification. Tests in `test_climbing_create.py` can read `paired_event_id` directly from the captured fake response without needing it in the renderer. Less diff, less regression risk.

---

### `src/intervals_mcp_server/utils/climbing.py` (utility, static data — POSSIBLE additive modify)

**Analog:** `utils/climbing.py::Discipline` (lines 28–34) and `CUSTOM_FIELD_KEYS` (lines 60–98).

**Pattern: `MappingProxyType` for read-only dicts** (mirrors `CUSTOM_FIELD_KEYS` line 60):

```python
# Append after Discipline enum (line 35), before SessionFocus (line 37) — or
# at the bottom of the module, after CUSTOM_FIELD_KEYS. Either is fine.

DISCIPLINE_HUMAN: MappingProxyType[str, str] = MappingProxyType({
    Discipline.BOULDERING.value: "Bouldering",
    Discipline.SPORT_LEAD.value: "Sport lead",
    Discipline.TOP_ROPE.value: "Top rope",
    Discipline.TRAD.value: "Trad",
})
```

If added, also append `"DISCIPLINE_HUMAN"` to `__all__` at line 20–25:

```python
__all__ = [
    "Discipline",
    "SessionFocus",
    "FieldSpec",
    "CUSTOM_FIELD_KEYS",
    "DISCIPLINE_HUMAN",  # new
]
```

**Note:** alternative is to keep this constant local to `tools/climbing.py` — see Section D under `tools/climbing.py` above. Planner picks one location.

---

### `scripts/smoke_phase3.py` (script, live smoke — OPTIONAL)

**Analog:** `scripts/smoke_phase2.py` (the entire 197-line file).

**Module header + imports + setup** — verbatim from lines 1–55 of `smoke_phase2.py`, with module name + comment block updated for Phase 3. Add the new tool imports:

```python
from intervals_mcp_server.tools.climbing import (  # noqa: E402
    complete_climbing_session,
    create_climbing_activity,
    enrich_activity_climbing,
)
```

**Main body — mirror `smoke_phase2.py:69–192` step pattern**:

1. `create_climbing_activity(date="2099-01-01", duration_minutes=90, discipline="bouldering", ...)` → capture activity_id
2. DELETE that activity (cleanup)
3. Create a planned event for 2099-01-02 via `add_or_update_event` → capture event_id
4. `complete_climbing_session(event_id=event_id, ...)` → capture activity_id, assert `paired_event_id == event_id` from the readback
5. DELETE the activity AND DELETE the event in `finally`

**Cleanup pattern** (verbatim from lines 160–186):

```python
finally:
    if activity_id:
        await make_intervals_request(
            url=f"/activity/{activity_id}",
            method="DELETE",
        )
    if event_id:
        await make_intervals_request(
            url=f"/athlete/{athlete_id}/events/{event_id}",
            method="DELETE",
        )
```

**Logger + redact pattern** — verbatim from lines 48–66 (no changes needed).

**Recommendation per CONTEXT:** SKIP unless the readback of `paired_event_id` fails in unit tests against the working hypothesis. Phase 1 spike confirmed `paired_event_id` is in the response shape — readback verification in unit tests should suffice.

---

## Shared Patterns

### Pattern S-1: `make_intervals_request` is the only HTTP boundary

**Source:** `src/intervals_mcp_server/api/client.py:152–158` (signature). Used in every tool.

**Apply to:** `create_climbing_activity`, `complete_climbing_session`, `_enrich_impl` (already does this), and every fake in tests.

**Signature (call site):**

```python
result = await make_intervals_request(
    url="/path",                      # required
    api_key=api_key,                  # optional
    params={"oldest": ...},           # optional GET query params
    method="POST",                    # default "GET"
    data={"key": "value"},            # POST/PUT body
)
```

**Error-shape check (used after every call):**

```python
if isinstance(result, dict) and "error" in result:
    return f"Error <action>: {result.get('message', 'Unknown error')}"
```

This pattern appears in `tools/climbing.py:70`, `tools/climbing.py:320`, `tools/climbing.py:425`, `tools/events.py:73`, `tools/events.py:141`, `tools/activities.py:139` — universal across the codebase.

---

### Pattern S-2: `resolve_athlete_id` resolution

**Source:** `src/intervals_mcp_server/utils/validation.py:50–70` and used in every tool.

**Apply to:** Both new tools (immediately after the at-least-one-supplied check, before any HTTP call).

**Verbatim usage** (from `enrich_activity_climbing` lines 251–253):

```python
athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
if error_msg:
    return error_msg
```

---

### Pattern S-3: Pylint suppressions on many-arg tool functions

**Source:** `tools/climbing.py:156` (the canonical many-arg climbing tool) and `tools/activities.py:104`.

**Apply to:** `create_climbing_activity`, `complete_climbing_session`, and the new `_enrich_impl` private helper.

**Verbatim header:**

```python
@mcp.tool()
async def <name>(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-return-statements,too-many-branches,too-many-locals,too-many-statements
```

For `_enrich_impl` (no `@mcp.tool()` because it's private):

```python
async def _enrich_impl(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-return-statements,too-many-branches,too-many-locals,too-many-statements
    activity_id: str,
    *,
    discipline: str | None = None,
    # ... all of enrich_activity_climbing's named params ...
    _skip_conflict_scan: bool = False,
) -> str:
```

---

### Pattern S-4: Error-string return contract (MCP protocol)

**Source:** universal across `tools/*.py`. Tools return `str` always; success path is a formatted summary, error path starts with `"Error"`.

**Apply to:** Both new tools.

**Examples in repo:**
- Success: `"Successfully enriched activity i1.\n\n<format_climbing_activity output>"` (`tools/climbing.py:469–472`)
- Error: `"Error: <description>"` (`tools/climbing.py:246`, `:262`, `:291`, etc.)
- Error w/ named entity: `"Error fetching activity for conflict scan: <message>"` (`tools/climbing.py:321–324`)

---

### Pattern S-5: Validation runs BEFORE any HTTP call

**Source:** `tools/climbing.py:233–311` (the entire pre-HTTP block in `enrich_activity_climbing`).

**Apply to:** Both new tools (before duplicate-guard GET, before POST). For `create_climbing_activity`: validate enum values and grade-discipline coupling first; for `complete_climbing_session`: same, before fetching the event. (`_enrich_impl` itself runs the validation again — that's the idempotent design; the new tools also pre-validate to fail fast and avoid wasted GETs.)

**Note:** since `_enrich_impl` runs the same validations (and for the fresh-POST path the new tools just forward the user's params verbatim), the new tools **do not need to duplicate** the validation block. The single source of truth is `_enrich_impl`. The new tools' only pre-HTTP validation is the `date` and `duration_minutes` shape (basic type/format).

---

### Pattern S-6: Test bootstrap — sys.path + env defaults

**Source:** `tests/test_climbing_write.py:1–20`, `tests/test_climbing.py:1–19`.

**Apply to:** `tests/test_climbing_create.py` verbatim header.

```python
import asyncio
import inspect
import os
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

import pytest  # pylint: disable=wrong-import-position
```

This is required so the tests pass `pytest --collect-only` (Pitfall #14 / D-20).

---

### Pattern S-7: Two-seam `monkeypatch` of `make_intervals_request`

**Source:** every async test in `tests/test_climbing_write.py` (e.g. lines 113–118).

**Apply to:** every test in `tests/test_climbing_create.py` that exercises an async tool.

**Why both seams:** `tools/climbing.py:14` does `from intervals_mcp_server.api.client import make_intervals_request`, so the callsite reference is `intervals_mcp_server.tools.climbing.make_intervals_request`. Patching only `api.client.make_intervals_request` after the import has already happened leaves the cached callsite reference pointing to the original.

```python
monkeypatch.setattr(
    "intervals_mcp_server.api.client.make_intervals_request", fake_request
)
monkeypatch.setattr(
    "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
)
```

If a test exercises `add_activity_message` (used inside `_enrich_impl` for the override audit path — though `_skip_conflict_scan=True` skips that for fresh-POST), also patch `tools.activities.make_intervals_request` (see `test_climbing_write.py:317–319`).

---

## No Analog Found

None — every Phase 3 file has at least one in-repo analog.

---

## Metadata

**Analog search scope:**
- `src/intervals_mcp_server/tools/` (all 5 files)
- `src/intervals_mcp_server/utils/` (all 6 files)
- `src/intervals_mcp_server/api/client.py`
- `tests/test_climbing*.py` (2 files)
- `scripts/smoke_phase2.py`
- `.planning/codebase/` (read for conventions and concerns)

**Files scanned:** 13

**Pattern extraction date:** 2026-04-28

**Key analog files (read in full or in targeted ranges):**
- `src/intervals_mcp_server/tools/climbing.py` (472 lines, full read — the file being modified)
- `src/intervals_mcp_server/tools/events.py` (405 lines, full read — `_prepare_event_data` Pitfall #4 model + `get_event_by_id` for D-05)
- `src/intervals_mcp_server/tools/activities.py` (382 lines, full read — `get_activities` for duplicate-guard URL/params + `add_activity_message` shape)
- `tests/test_climbing_write.py` (785 lines, full read — the test analog)
- `tests/test_climbing.py` (332 lines, full read — secondary test analog + formatter snapshot test that constrains `format_climbing_activity` extension)
- `src/intervals_mcp_server/utils/climbing.py` (98 lines, full)
- `src/intervals_mcp_server/utils/formatting.py` (lines 552–599 targeted — `format_climbing_activity`)
- `src/intervals_mcp_server/utils/validation.py` (88 lines, full — `resolve_athlete_id`)
- `src/intervals_mcp_server/utils/grades.py` (63 lines, full — `validate_grade` signature)
- `src/intervals_mcp_server/api/client.py` (lines 152–200 targeted — `make_intervals_request` signature)
- `scripts/smoke_phase2.py` (197 lines, full)
