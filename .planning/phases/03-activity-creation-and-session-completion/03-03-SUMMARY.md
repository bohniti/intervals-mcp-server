---
phase: 03-activity-creation-and-session-completion
plan: 03
subsystem: tools/climbing
tags: [feature, climbing, intervals-icu, mcp, session-complete, paired-event-id, duplicate-guard]
dependency_graph:
  requires: [03-01 (_enrich_impl with _skip_conflict_scan), 03-02 (create_climbing_activity, _DISCIPLINE_HUMAN, _build_default_name)]
  provides: [complete_climbing_session @mcp.tool()]
  affects: [phase-04 status-tool (activities produced by complete_climbing_session feed CTL/ATL/TSB)]
tech_stack:
  added: []
  patterns: [event-GET-before-POST, paired_event_id explicit-set + readback-verify, two-layer duplicate guard, D-09 atomicity on enrichment failure]
key_files:
  modified:
    - src/intervals_mcp_server/tools/climbing.py
    - tests/test_climbing_create.py
decisions:
  - "complete_climbing_session uses singular /event/{id} URL for event GET (mirrors tools/events.py:185 get_event_by_id pattern)"
  - "Already-paired guard fires before duplicate-guard GET — most specific guard runs first (already-paired → no GET, no POST)"
  - "moving_time from event if int > 0, else 0 — explicit int check avoids accepting string '5400' from event response"
  - "verify_dict handles both list-of-one and plain dict readback shapes (consistent with _enrich_impl readback)"
  - "test count: plan specified 18 (12+6) but test_climbing_create.py already had 13 from Plan 02 (documented deviation in 03-02-SUMMARY); final count is 19 (13+6)"
metrics:
  duration: "~5 minutes"
  completed: "2026-04-28"
  tasks_completed: 2
  files_modified: 2
---

# Phase 03 Plan 03: Complete Climbing Session Summary

**One-liner:** Added `complete_climbing_session` MCP tool — GET event → already-paired guard → duplicate guard → POST with explicit `paired_event_id` → readback-verify link → optional single-shot enrich via `_enrich_impl(_skip_conflict_scan=True)` — backed by 6 new unit tests.

## What Was Built

### Task 1: `complete_climbing_session` tool appended to `tools/climbing.py`

Appended the new `@mcp.tool()`-decorated async function `complete_climbing_session` after `create_climbing_activity` in `src/intervals_mcp_server/tools/climbing.py`.

**11-param signature** (no `date`/`type`/`duration_minutes`/`name` — those come from the planned event verbatim):
```
event_id, discipline, indoor, session_focus, top_grade_sent, top_grade_attempted,
sends, attempts, rpe, athlete_id, api_key
```

**HTTP call sequence (ordered):**

| Step | URL | Method | Purpose |
|------|-----|--------|---------|
| 1 | `/athlete/{id}/event/{event_id}` | GET | Fetch planned event (D-05) |
| 2 | (guard check) | — | Already-paired refusal if `event.paired_event_id` non-null |
| 3 | `/athlete/{id}/activities?oldest={date}&newest={date}` | GET | Duplicate guard (CLIMB-09/D-03) |
| 4 | `/athlete/{id}/activities/manual` | POST | Create linked activity with `paired_event_id` explicit (D-06) |
| 5 | `/activity/{new_id}` | GET | Readback verifies `paired_event_id == event_id` (D-06 proof) |
| 6 | `_enrich_impl(... _skip_conflict_scan=True)` | (internal) | Optional single-shot enrich (D-08, D-12) |

**Guard behaviors:**
- **Already-paired:** `"Event {event_id} is already paired to activity {paired_id}. Call enrich_activity_climbing(activity_id={paired_id}, ...) to add climbing metadata."` — no dup-guard GET, no POST
- **Duplicate guard:** same multi-line `(date, WeightTraining)` refusal format as `create_climbing_activity` — enforces D-03 (both tools guard)
- **Readback mismatch:** `"Error: paired_event_id mismatch on activity {id}: sent {event_id!r}, got {got!r}. ..."` — activity preserved (D-09), no DELETE
- **Enrichment failure after POST:** activity preserved, retry hint via `enrich_activity_climbing(activity_id={id}, override=True, ...)` (D-09)

**Key correctness properties:**
- `start_date_local`, `type`, `name`, `moving_time` all verbatim from the event GET — no user-supplied date/type/name (D-07)
- `paired_event_id: event_id` explicitly in POST body — does NOT rely on Intervals.icu auto-match by date+type (D-06, LOW-MEDIUM confidence concern from STATE.md)
- No system clock — `start_date_local` comes from the planned event (Pitfall #4 / T-03-03-03)
- No DELETE on the planned event (PROJECT.md Key Decision: "completion creates a linked activity, planned event stays on calendar")
- No DELETE on the activity on any failure path (D-09)

### Task 2: 6 new tests in `tests/test_climbing_create.py`

Added `_make_fake_event` helper and 6 test functions in a `# === complete_climbing_session ===` section after Plan 02's 13 tests:

| Test | Coverage |
|------|----------|
| `test_complete_tool_registered` | 11 params, no forbidden params (date/type/duration_minutes/name), event_id required |
| `test_complete_event_provides_date_type_name_and_paired_event_id` | CLIMB-01 happy path; POST body verbatim from event; HTTP call order verified via counters |
| `test_complete_already_paired_refuses` | Already-paired guard; exact refusal string; asserts dup-guard GET and POST do NOT fire |
| `test_complete_duplicate_guard_on_event_date` | CLIMB-09 / D-03; WeightTraining on event date → refuse, no POST |
| `test_complete_paired_event_id_readback_mismatch_errors` | Readback null → mismatch error; asserts NO DELETE (T-03-03-06) |
| `test_complete_enrichment_fails_after_post_keeps_activity` | D-09 atomicity; POST OK + readback OK but enrich fails → error names activity_id, retry hint, NO DELETE |

Two-seam `monkeypatch` applied (both `api.client` and `tools.climbing` seams) in all 5 tests that exercise the tool. `asyncio.run(coroutine)` pattern throughout (no `pytest.mark.asyncio`).

## Test Results

```
tests/test_climbing_create.py: 19 passed (13 from Plan 02 + 6 from this plan)
tests/test_climbing_write.py:  17 passed (no regression — Phase 2 boundary)
Full suite: 147 passed in 0.71s
```

## Structural Verification (grep checks)

```
grep -nE '^async def complete_climbing_session\('  → line 732  ✓
grep -nE '@mcp\.tool\(\)' | wc -l                 → 4 (≥4 threshold)  ✓
grep -nE 'paired_event_id' | wc -l                → 11 (≥5 threshold)  ✓
grep -nE '"paired_event_id": event_id'            → line 885 (exactly 1)  ✓
grep -nE 'is already paired to activity'          → line 825 (exactly 1)  ✓
grep -nE 'paired_event_id mismatch'              → line 932 (exactly 1)  ✓
grep -nE '/event/'                               → lines 811, 813 (≥1)  ✓
grep -nE '_skip_conflict_scan=True' | wc -l       → 2 (Plan 02 + Plan 03)  ✓
grep -nE 'datetime\.(utcnow|now)\('              → 0 code matches (comment only)  ✓
grep -nE 'method="DELETE"'                       → 0 matches  ✓
```

## Lint and Type Checks

- `ruff check src/intervals_mcp_server/tools/climbing.py` — All checks passed
- `mypy src/intervals_mcp_server/tools/climbing.py` — Success: no issues found in 1 source file
- `ruff check tests/test_climbing_create.py` — All checks passed

## Deviations from Plan

### Plan-documented test count mismatch (documentation only)

**Found during:** Task 2 acceptance criteria check
**Issue:** Plan 03-03 specified 18 total tests (12 from Plan 02 + 6 from this plan). However, Plan 02 created 13 tests (documented in 03-02-SUMMARY.md as a deviation — the plan's code block included a 13th test `test_create_duplicate_guard_ignores_non_weight_training` not in the numbered list). As a result, the final count is 19 (13 + 6).
**Resolution:** Added all 6 tests specified in the 03-03 plan code block. All 19 tests pass.
**Impact:** One additional test; no missing coverage; positive deviation.

## Known Stubs

None — the tool makes real API calls through `make_intervals_request`. The `paired_event_id` explicit-set + readback-verify loop is fully wired. The LOW-MEDIUM confidence concern (whether Intervals.icu actually respects explicit `paired_event_id` in POST body) is exercised by the readback in the tool itself — if the live API ignores it, the mismatch error surfaces immediately.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes beyond those in the plan's threat model. The `complete_climbing_session` tool makes GET + POST + GET calls through the established `make_intervals_request` boundary. All threat model mitigations from the plan (T-03-03-01 through T-03-03-09) are implemented.

## Phase 3 Status

All three plans complete:

| Plan | Tool | Tests |
|------|------|-------|
| 03-01 | `_enrich_impl` refactor | 17 (test_climbing_write.py unchanged) |
| 03-02 | `create_climbing_activity` | 13 (test_climbing_create.py) |
| 03-03 | `complete_climbing_session` | +6 (test_climbing_create.py, total 19) |

The close-the-loop tools are in place. Phase 4 (status report) can build on top of the activities these tools produce.

## Carry-Forward

- **Phase 5 smoke-test:** The live test for `paired_event_id` readback (the LOW-MEDIUM-confidence item from STATE.md) will be exercised in Phase 5 when `complete_climbing_session` runs against the live Intervals.icu API. The unit tests prove the tool's logic; the smoke-test proves the API contract assumption.
- **Singular vs plural `/event/{id}` URL:** The tool uses singular `/event/{event_id}` (mirroring `tools/events.py:185`). Unit tests use a string-contains match (`"/event/" in url and "/events" not in url`) that matches the singular form. The Phase 5 smoke-test will surface any mismatch if Intervals.icu's GET-by-id path differs from the hypothesis.
- **`paired_event_id` on the event response:** The working hypothesis (that `event.paired_event_id` is non-null when the event has already been completed) is validated in unit tests via the mock. Phase 5 confirms against the live API.

## Self-Check: PASSED

- `src/intervals_mcp_server/tools/climbing.py` exists and modified ✓
- `tests/test_climbing_create.py` exists and modified ✓
- Commit `03f9f20` (Task 1) exists in git log ✓
- Commit `c621021` (Task 2) exists in git log ✓
- 19 tests pass in `test_climbing_create.py` ✓
- 147 tests pass in full suite ✓
- ruff + mypy clean on climbing.py ✓
- ruff clean on test_climbing_create.py ✓
