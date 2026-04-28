---
phase: 03-activity-creation-and-session-completion
plan: 02
subsystem: tools/climbing
tags: [feature, climbing, intervals-icu, mcp, activity-create, duplicate-guard, tdd]
dependency_graph:
  requires: [03-01 (_enrich_impl private helper with _skip_conflict_scan kwarg)]
  provides: [create_climbing_activity @mcp.tool(), _DISCIPLINE_HUMAN map, _build_default_name helper]
  affects: [plans/03-03 (complete_climbing_session appends to same files without line overlap)]
tech_stack:
  added: []
  patterns: [duplicate-guard GET before POST, Pitfall-4-safe start_date_local, D-09 atomicity on enrichment failure, D-16 name template]
key_files:
  modified:
    - src/intervals_mcp_server/tools/climbing.py
  created:
    - tests/test_climbing_create.py
decisions:
  - "_DISCIPLINE_HUMAN map and _build_default_name helper placed in tools/climbing.py (Option 2) next to their only consumer — no cross-module dependency needed"
  - "13 test functions created (plan listed 12 numbered; test_create_duplicate_guard_ignores_non_weight_training from plan code block is additional coverage — correct to include)"
  - "Enrichment failure path (D-09) returns error naming activity_id without DELETE — preserves any icu_rpe that may have written in split-PUT"
metrics:
  duration: "~6 minutes"
  completed: "2026-04-28"
  tasks_completed: 2
  files_modified: 1
  files_created: 1
---

# Phase 03 Plan 02: Create Climbing Activity Summary

**One-liner:** Added `create_climbing_activity` MCP tool with duplicate-guard POST, Pitfall-4-safe date handling, D-16 name template, and optional single-shot enrichment via `_enrich_impl(_skip_conflict_scan=True)` — backed by 13 unit tests.

## What Was Built

### Task 1: `create_climbing_activity` tool in `tools/climbing.py`

Appended the new `@mcp.tool()`-decorated async function `create_climbing_activity` to `src/intervals_mcp_server/tools/climbing.py`, plus two supporting pieces:

**`_DISCIPLINE_HUMAN` map** — maps `Discipline` enum values to human-readable names for the D-16 name template (e.g., `"sport_lead"` → `"Sport lead"`).

**`_build_default_name(date, discipline)` helper** — produces `"Climbing — {Discipline} — {date}"` when discipline is supplied, `"Climbing — {date}"` otherwise. Unknown discipline values fall back gracefully.

**`create_climbing_activity` function** — 13-param signature (`date`, `duration_minutes`, `name`, `discipline`, `indoor`, `session_focus`, `top_grade_sent`, `top_grade_attempted`, `sends`, `attempts`, `rpe`, `athlete_id`, `api_key`). Full flow:

1. `resolve_athlete_id` (D-22 pattern)
2. Duplicate-guard GET (`/athlete/{id}/activities?oldest={date}&newest={date}`) filters for `(date, type=WeightTraining)` matches — refuses with listing + `enrich_activity_climbing(...)` hint if any found (CLIMB-09/Pitfall #1)
3. POST body: `start_date_local=f"{date}T00:00:00"` (never from system clock — Pitfall #4/D-17), `type="WeightTraining"` (hardcoded D-15), `moving_time=duration_minutes*60` (D-14)
4. POST to `/athlete/{id}/activities/manual`
5. If any climbing field supplied: call `_enrich_impl(new_id, ..., _skip_conflict_scan=True)` (D-08/D-12); on enrichment failure return activity_id + retry hint without DELETE (D-09)
6. If no climbing fields: return `"Successfully created activity {id} on {date}."`

### Task 2: `tests/test_climbing_create.py` (13 unit tests)

Created new test file mirroring `tests/test_climbing_write.py` structure:

| Test | What it covers |
|------|----------------|
| `test_create_tool_registered` | Async coroutine, 13 params, required params have no defaults |
| `test_create_no_duplicate_proceeds_to_post` | CLIMB-02 happy path: empty list → POST → success, no enrich |
| `test_create_duplicate_guard_fires` | CLIMB-09: WeightTraining activity on date → refuse with id/name/date + hint, NO POST |
| `test_create_duplicate_guard_ignores_non_weight_training` | Ride on same date does NOT block the POST |
| `test_create_pitfall4_timezone_format` | POST body `start_date_local == "2026-04-27T00:00:00"` exactly (string equality) |
| `test_create_pitfall4_never_uses_utcnow` | Clock patched to 2099 — POST body still uses user-supplied date verbatim |
| `test_create_name_template_with_discipline` | D-16: no name + discipline=bouldering → `"Climbing — Bouldering — 2026-04-27"` |
| `test_create_name_template_without_discipline` | D-16: no name, no discipline → `"Climbing — 2026-04-27"` |
| `test_create_user_name_used_verbatim` | User-supplied name used verbatim; template not invoked |
| `test_create_post_error_returns_error_no_activity_id` | D-10: POST error dict → `"Error creating activity: boom"`, no PUT |
| `test_create_enrichment_fails_after_post_keeps_activity` | D-09: POST OK, verify-fields empty → enrich fails → error names id + retry hint, no DELETE |
| `test_create_no_climbing_fields_skips_enrich_call` | Only date+duration → success after POST; no PUT, no readback GET |
| `test_create_with_climbing_fields_calls_enrich_with_skip_flag` | D-12: pre-PUT conflict-scan GET on new activity_id count == 0 with _skip_conflict_scan=True |

Two-seam monkeypatch applied in all 12 tests that exercise the tool (both `api.client.make_intervals_request` and `tools.climbing.make_intervals_request`).

## Test Results

```
tests/test_climbing_create.py: 13 passed
tests/test_climbing_write.py:  17 passed (no regression)
Full suite: 141 passed in 0.67s
```

## Structural Verification (grep checks)

```
grep -nE '^async def create_climbing_activity\('  → line 542  ✓
grep -nE '@mcp\.tool\(\)' | wc -l               → 3 (≥3 threshold)  ✓
grep -nE 'WeightTraining'                         → 5 matches (≥2)  ✓
grep -nE 'T00:00:00'                             → 2 matches  ✓
grep -nE '_skip_conflict_scan=True'              → 1 match (exactly 1)  ✓
grep -nE 'duration_minutes \* 60'               → 1 match  ✓
grep -nE 'datetime\.(utcnow|now)\('             → 0 matches (only comment line)  ✓
grep -nE 'activities/manual'                     → 1 match  ✓
grep -nE '_DISCIPLINE_HUMAN|_build_default_name' → 6 matches (≥4)  ✓
```

## Lint and Type Checks

- `ruff check src/intervals_mcp_server/tools/climbing.py` — All checks passed
- `mypy src/intervals_mcp_server/tools/climbing.py` — Success: no issues found in 1 source file
- `ruff check tests/test_climbing_create.py` — All checks passed

## Deviations from Plan

### Auto-resolved Plan Inconsistency (Documentation only)

**Found during:** Task 2 acceptance criteria check
**Issue:** Plan's numbered `<behavior>` list shows 12 tests (Test 1-12), but the plan's code block includes a 13th test `test_create_duplicate_guard_ignores_non_weight_training` between Test 3 and Test 4. The acceptance criteria says `wc -l` returns 12.
**Resolution:** Included all 13 tests from the plan's code block — the code block is the authoritative specification. The 13th test covers the non-WeightTraining filter case (a Ride on the same date should not block the climbing POST), which is explicit in the duplicate-guard logic and provides meaningful additional coverage.
**Impact:** 13 tests instead of 12; all 13 pass; additional coverage is positive.

## Known Stubs

None — all data flows through to the real `_enrich_impl` for enrichment cases; create-only path returns a concrete success string with the actual activity ID.

## Threat Flags

None — no new network endpoints beyond those documented in the plan's threat model. The `create_climbing_activity` tool makes GET + POST calls through the established `make_intervals_request` boundary. All threat model mitigations from the plan (T-03-02-01 through T-03-02-09) are implemented.

## Self-Check: PASSED

- `src/intervals_mcp_server/tools/climbing.py` exists and modified ✓
- `tests/test_climbing_create.py` exists and created ✓
- Commit `37398db` (Task 1) exists in git log ✓
- Commit `c1ed6d6` (Task 2) exists in git log ✓
- 13 tests pass in `test_climbing_create.py` ✓
- 141 tests pass in full suite ✓
- ruff + mypy clean on climbing.py ✓
- ruff clean on test_climbing_create.py ✓
