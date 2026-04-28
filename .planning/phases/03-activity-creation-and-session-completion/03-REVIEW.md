---
phase: 03-activity-creation-and-session-completion
reviewed: 2026-04-28T11:41:33Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - src/intervals_mcp_server/tools/climbing.py
  - tests/test_climbing_create.py
findings:
  critical: 0
  warning: 3
  info: 5
  total: 8
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-04-28T11:41:33Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Phase 3 implementation of `create_climbing_activity` and `complete_climbing_session` is solid: it honors the project's critical constraints (HTTP-through-`make_intervals_request`, duplicate-activity guard on every POST, readback verification, D-09 atomicity, D-12 single-shot enrichment, D-17 user-supplied date). Validation order matches `_enrich_impl`'s contract, and the test coverage exercises the listed decision points.

Three warnings are worth addressing before extending these tools further: a type-coercion gap on the `paired_event_id` readback compare (could fail when the API returns the id as an int), a silent fallback for `event.type` that lets a non-WeightTraining event slip past the duplicate-guard filter, and a discarded return from the audit-message write that loses a documented safety signal. The remaining items are info-level (duplicated duplicate-guard code, narrow event-shape type guard, dead `disable=` pylint hints, docstring drift, captured-but-unused test variable).

No critical issues were found. No project constraint is violated.

## Warnings

### WR-01: paired_event_id readback compare uses raw equality with no type coercion

**File:** `src/intervals_mcp_server/tools/climbing.py:929-935`
**Issue:** `complete_climbing_session` compares the readback `paired_event_id` to the `event_id` parameter with `!=`, but the readback value's type is whatever Intervals.icu returns (often an int for numeric ids). The same code defensively coerces `create_resp["id"]` via `str(...)` on line 906, but the paired-event compare does no coercion. If Intervals.icu returns `paired_event_id` as an int while `event_id` was passed as a string (or vice versa), the readback will report a spurious "paired_event_id mismatch" even though the link took correctly — and per D-09 the activity is preserved with a misleading error.

The unit tests at lines 727 and 731 use string `"ev123"` on both sides, so this gap is not exercised. Activity ids in this codebase are typically strings prefixed with `i` (e.g., `"i142495224"`), but event ids in the wild may be raw integers.

**Fix:**
```python
got_pair = verify_dict.get("paired_event_id")
if str(got_pair) != str(event_id):
    return (
        f"Error: paired_event_id mismatch on activity {new_activity_id}: "
        f"sent {event_id!r}, got {got_pair!r}. "
        f"The link from event {event_id} to activity may not have taken."
    )
```
Add a regression test that returns `paired_event_id` as an int from the fake (e.g., `123` while `event_id="123"`) and asserts success.

### WR-02: silent `type` fallback lets a non-WeightTraining event bypass the duplicate-guard filter

**File:** `src/intervals_mcp_server/tools/climbing.py:832, 857`
**Issue:** `event_type = event_get.get("type") or "WeightTraining"` (line 832) accepts whatever type the planned event declares but silently defaults to `"WeightTraining"` if missing. The duplicate guard at line 857 then filters strictly on `activity.get("type") != "WeightTraining"`. Two failure paths follow:

1. If the planned event is e.g. a `Ride` (a user mis-routes a non-climbing event through `complete_climbing_session`), the body POSTs `type="Ride"`, but the duplicate guard ignores `Ride` activities on the date — so the tool will happily create a duplicate ride next to an existing one.
2. The docstring claims "Activity type is hardcoded to `WeightTraining` — Phase 1 spike confirmed this works for climbing… Generic non-climbing manual activities are out of scope for v1." but the code does not enforce that on the `complete` path; only `create` hardcodes the type.

**Fix:** either enforce the climbing constraint at event-fetch time (refuse if `event_type` is anything other than `WeightTraining`), or align the duplicate-guard filter with `event_type` so it scans for the type that will actually be created:
```python
event_type = event_get.get("type") or "WeightTraining"
if event_type != "WeightTraining":
    return (
        f"Error: event {event_id} has type {event_type!r}; "
        f"complete_climbing_session only supports WeightTraining events for v1."
    )
```

### WR-03: audit-message write result is silently discarded; failure is invisible

**File:** `src/intervals_mcp_server/tools/climbing.py:276-281`
**Issue:** When `override=True` and conflicts exist, `_enrich_impl` writes an audit message via `add_activity_message(...)` and ignores its return value. `add_activity_message` returns a string starting with `"Error adding message to activity: ..."` on failure (see `tools/activities.py:372-374`). The comment on line 281 calls this "fire-and-forget" and notes that downstream readback still verifies the write — but the audit trail itself is the safety claim of D-14 / Pitfall #10. If the audit write silently fails, the override happens without an audit record, which defeats the point of writing one.

**Fix:** capture the return and surface a warning prefix on the success path (or at minimum log it). Suggested:
```python
audit_result = await add_activity_message(
    activity_id=activity_id,
    content=content,
    api_key=api_key,
)
audit_failed = audit_result.startswith("Error")
# … later, on success path:
if audit_failed:
    return (
        f"Successfully enriched activity {activity_id} (NOTE: audit-message "
        f"write failed: {audit_result}; override was applied without an audit "
        f"trail).\n\n" + format_climbing_activity(post)
    )
```

## Info

### IN-01: duplicate-guard logic is copy-pasted between `create` and `complete`

**File:** `src/intervals_mcp_server/tools/climbing.py:625-664, 839-878`
**Issue:** The two duplicate-guard blocks are character-for-character identical except for the `date` variable name. Any future refinement (e.g., aligning `type` with `event_type` per WR-02, or adding pagination handling) has to be made in two places.
**Fix:** extract a private helper:
```python
async def _check_duplicate_weight_training(
    athlete_id_to_use: str,
    date: str,
    api_key: str | None,
) -> str | None:
    """Return None when no duplicates; the user-facing refusal string otherwise."""
    ...
```

### IN-02: event-GET shape guard rejects only the dict-empty case, not list responses

**File:** `src/intervals_mcp_server/tools/climbing.py:818`
**Issue:** `if not isinstance(event_get, dict) or not event_get:` returns "not found" if `make_intervals_request` returns anything that isn't a non-empty dict — but doesn't unwrap a list (the singular event endpoint is documented to return a dict, but other endpoints in this module unwrap lists defensively, e.g., lines 228-231 and 920-923). Inconsistent shape handling could surface as "event not found" when a future API change wraps the response.
**Fix:** mirror the unwrap pattern used in `_enrich_impl` step 7:
```python
event_obj: dict[str, Any] = {}
if isinstance(event_get, list) and event_get and isinstance(event_get[0], dict):
    event_obj = event_get[0]
elif isinstance(event_get, dict):
    event_obj = event_get
if not event_obj:
    return f"Error: planned event {event_id} not found."
# … then use event_obj instead of event_get
```

### IN-03: `pylint: disable=too-many-arguments,...` hints on `enrich_activity_climbing` are now redundant

**File:** `src/intervals_mcp_server/tools/climbing.py:420`
**Issue:** The public `enrich_activity_climbing` is now a thin pass-through to `_enrich_impl` — no branches, no locals, no return statements beyond the single `await`. The `# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-return-statements,too-many-branches,too-many-locals,too-many-statements` directive accurately describes the old in-place body, not the current shape. Only `too-many-arguments` and `too-many-positional-arguments` still apply.
**Fix:** trim the disable list to only the directives that still apply:
```python
@mcp.tool()
async def enrich_activity_climbing(  # pylint: disable=too-many-arguments,too-many-positional-arguments
```

### IN-04: docstring on `enrich_activity_climbing` still says `create_climbing_activity` is "Phase 3, not yet implemented"

**File:** `src/intervals_mcp_server/tools/climbing.py:438-439`
**Issue:** The docstring reads `for brand-new climbing sessions without a prior record, see create_climbing_activity (Phase 3, not yet implemented).` — but Phase 3 is the phase under review and `create_climbing_activity` is implemented in this same module a few lines below.
**Fix:** drop the parenthetical:
```
For brand-new climbing sessions without a prior record, see
`create_climbing_activity`. For completing a planned event from the
calendar, see `complete_climbing_session`.
```

### IN-05: `captured_post` is assigned in the create-happy-path test but never asserted on

**File:** `tests/test_climbing_create.py:80, 95`
**Issue:** `test_create_no_duplicate_proceeds_to_post` declares `captured_post: dict[str, Any] = {}` and updates it inside the fake POST handler, but never reads it. The body assertions are present in `test_create_pitfall4_timezone_format` and the name-template tests; this test only counts calls. The variable adds noise.
**Fix:** drop the `captured_post` declaration and the `captured_post.update(data or {})` line, OR add at least one assertion on `captured_post["start_date_local"]` / `["moving_time"]` to make the variable load-bearing.

---

_Reviewed: 2026-04-28T11:41:33Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
