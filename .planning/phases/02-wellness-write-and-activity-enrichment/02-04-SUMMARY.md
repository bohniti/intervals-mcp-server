---
phase: 02
plan: 04
subsystem: tools.climbing
tags: [enrichment, custom-fields, icu_rpe, readback, override-audit, split-put]
requires:
  - "Phase 1 D-09: CUSTOM_FIELD_KEYS spec (utils/climbing.py)"
  - "Phase 1 D-11: _verify_custom_fields_setup_impl helper (tools/climbing.py)"
  - "Phase 1 D-15: format_climbing_activity (utils/formatting.py)"
  - "Phase 1 D-13: validate_grade (utils/grades.py)"
  - "Plan 02-01: 02-SPIKE-FINDINGS.md (icu_rpe SPLIT-PUT lock; custom-field PUT body working hypothesis)"
provides:
  - "tools.climbing::enrich_activity_climbing — write tool for climbing metadata + RPE"
  - "Override audit format `[enrich override] field: old→new`"
affects:
  - "tools/climbing.py (additive — enrich_activity_climbing appended; existing helpers byte-identical)"
  - "tests/test_climbing_write.py (new — 17 tests covering CLIMB-03..07, CLIMB-10 readback)"
tech-stack:
  added: []
  patterns:
    - "Split-PUT D-16: icu_rpe via PUT /activity/{id} first, then custom fields via PUT /activity/{id}"
    - "Default-deny conflict scan (Pitfall #10) with override audit via add_activity_message"
    - "Value-equality readback verification on supplied fields only (Pitfall #2)"
    - "_README_POINTER appended on custom-field readback failure; omitted on icu_rpe-only failure"
key-files:
  created:
    - tests/test_climbing_write.py
  modified:
    - src/intervals_mcp_server/tools/climbing.py
    - .planning/phases/02-wellness-write-and-activity-enrichment/02-04-PLAN.md
decisions:
  - "D-16 path locked to SPLIT-PUT per 02-SPIKE-FINDINGS.md (icu_rpe write path LOCKED; isolated PUT /activity/{id} body {icu_rpe: N})"
  - "Custom-field PUT body shape: top-level keys via PUT /activity/{id} (working hypothesis from spike; runtime guard via verify_custom_fields_setup catches missing schemas)"
  - "Audit on override is fire-and-forget via add_activity_message (the public tool — D-22 allows this import)"
metrics:
  duration_minutes: 18
  tasks_completed: 3
  tests_added: 17
  tests_total_after: 123
  completed: 2026-04-25
---

# Phase 02 Plan 04: enrich_activity_climbing Summary

**One-liner:** Climbing-enrichment write tool (`enrich_activity_climbing`) with discipline-aware
grade validation, conditional verify-fields guard, default-deny re-enrichment with override audit,
SPLIT-PUT path (icu_rpe first, custom fields second per D-16), and value-equality readback
verification on supplied fields only.

## What Was Built

### Source: `src/intervals_mcp_server/tools/climbing.py`

Added `enrich_activity_climbing` as the second `@mcp.tool()` in the module. Existing
`verify_custom_fields_setup`, `_verify_custom_fields_setup_impl`, and `_README_POINTER` are
byte-identical (D-24 no-regression). Imports were extended additively with public-name imports
only (D-22).

Final 12-param signature:

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
```

Order of operations executed by the tool:

1. At-least-one-supplied (D-12).
2. `resolve_athlete_id`.
3. Grade-discipline coupling + `validate_grade` per discipline (D-12 / D-13).
4. `session_focus` enum check.
5. `rpe` range check 1..10 (D-12 / CLIMB-07).
6. Conditional `_verify_custom_fields_setup_impl` guard (D-20 / CLIMB-10) — skipped on RPE-only writes.
7. GET `/activity/{id}` (conflict scan).
8. Build `supplied_pairs` (API field name → sent value; `rpe` maps to `icu_rpe`).
9. Conflict scan; refuse with conflicts list when override=False (D-14).
10. Audit on override via `add_activity_message` (`[enrich override] field: old→new` format; D-14).
11. **D-16 SPLIT-PUT writes**: icu_rpe first (separate PUT /activity/{id} with `{"icu_rpe": rpe}`),
    then custom fields (PUT /activity/{id} with top-level keys). Partial-failure error names what
    landed (`icu_rpe={rpe}`) and what didn't.
12. Readback GET `/activity/{id}`.
13. Per-field equality on supplied fields only.
14. On readback failure, `_README_POINTER` appended only if any custom field is in the mismatch
    list (D-15 + `<specifics>`); not for icu_rpe-only failure.
15. Success: render via `format_climbing_activity(post)`.

### Tests: `tests/test_climbing_write.py`

17 tests (15 unconditional + 2 additional supporting tests including the conditional split-PUT
partial-failure test). All pass.

| Test | Requirement |
|------|-------------|
| `test_enrich_tool_registered` | sanity |
| `test_enrich_writes_custom_fields` | **CLIMB-03** |
| `test_grade_discipline_mismatch_rejects_pre_api` | **CLIMB-04** |
| `test_missing_custom_fields_short_circuits` | **CLIMB-05** |
| `test_default_deny_re_enrichment` | **CLIMB-06** (default-deny) |
| `test_override_writes_audit_message` | **CLIMB-06** (override audit) |
| `test_icu_rpe_writes_and_reads_back` | **CLIMB-07** (write+roundtrip) |
| `test_icu_rpe_readback_mismatch_errors` | **CLIMB-07** (mismatch) |
| `test_enrich_rejects_empty_call` | D-12 |
| `test_enrich_rejects_grade_without_discipline` | D-12 |
| `test_enrich_rejects_unknown_discipline` | D-12 |
| `test_enrich_rejects_unknown_session_focus` | D-12 (session_focus enum) |
| `test_enrich_rejects_rpe_out_of_range` | D-12 / CLIMB-07 range |
| `test_readback_custom_field_failure_includes_readme_pointer` | **CLIMB-10** (readback flavour) |
| `test_type_coercion_drift_int_vs_float_passes` | RESEARCH.md Pattern 3 |
| `test_enrich_uses_locked_put_body_shape` | D-16 body shape (top-level keys) |
| `test_split_put_partial_failure_named` | D-16 split-PUT (I-03 fix) |

## D-16 Branch Lock

Per 02-SPIKE-FINDINGS.md `## icu_rpe write path (LOCKED)`, the chosen branch is **SPLIT-PUT**.

Marker comment in **plan file** (`02-04-PLAN.md`):
```
    # D-16 path: SPLIT-PUT (per 02-SPIKE-FINDINGS.md)
```

Marker comment in **source** (`src/intervals_mcp_server/tools/climbing.py`):
```
    # D-16 path: SPLIT-PUT (per 02-SPIKE-FINDINGS.md)
```

The two markers match (proof I-01's lock survived Task 0 → Task 1).

`test_split_put_partial_failure_named` is **PRESENT** (split-PUT branch was retained).

## PUT Body Shape

icu_rpe (separate PUT, sent first):

```python
await make_intervals_request(
    url=f"/activity/{activity_id}",
    api_key=api_key,
    data={"icu_rpe": rpe},
    method="PUT",
)
```

Custom fields (separate PUT, sent second; top-level keys per spike findings working hypothesis):

```python
cf_body = {k: v for k, v in supplied_pairs.items() if k != "icu_rpe"}
# Example cf_body for discipline + top_grade_sent:
# {"discipline": "bouldering", "top_grade_sent": "6A"}
await make_intervals_request(
    url=f"/activity/{activity_id}",
    api_key=api_key,
    data=cf_body,
    method="PUT",
)
```

Per 02-SPIKE-FINDINGS.md: live API roundtrip pending SETUP-01 (custom-field schemas defined in
the athlete account). The runtime `verify_custom_fields_setup` MCP tool from Phase 1 (D-11) is
the production safety net that catches missing schemas before any PUT in `enrich_activity_climbing`
(D-20).

## D-24 No-Regression Confirmation

`_verify_custom_fields_setup_impl`, `verify_custom_fields_setup`, and `_README_POINTER` are
byte-identical to pre-Plan-02-04. Confirmed via:

```bash
git diff HEAD~1 src/intervals_mcp_server/tools/climbing.py | grep "^- " | \
  grep -E "_verify_custom_fields_setup_impl|verify_custom_fields_setup|_README_POINTER" | wc -l
# 0
```

(I-02 fix: HEAD~1 from Task 2's perspective is Task 1's commit; the regression check resolves
correctly because Task 1 committed before Task 2 started.)

## Commit Trail

| Task | Commit | Message |
|------|--------|---------|
| 0 | `8c1b233` | docs(02): lock Plan 02-04 branches per spike findings (D-16 = SPLIT-PUT) |
| 1 | `3f0aab1` | feat(02-04): add enrich_activity_climbing tool (CLIMB-03..07, CLIMB-10) |
| 2 | `de878da` | test(02-04): cover enrich_activity_climbing CLIMB-* falsifiable assertions |

**I-02 anchor:** Task 1's commit SHA is `3f0aab1` — the regression-check anchor.

## Verification Results

- `uv run --extra dev pytest tests/test_climbing_write.py -x` → **17 passed**
- `uv run --extra dev pytest tests/test_climbing.py tests/test_wellness_write.py tests/test_make_intervals_request.py -x` → **34 passed** (no regression)
- `uv run --extra dev pytest` → **123 passed** (full suite green)
- `uv run --extra dev ruff check src tests` → All checks passed
- `uv run --extra dev mypy src/intervals_mcp_server/tools/climbing.py` → Success: no issues

All seven CLIMB-* falsifiable assertions in `02-VALIDATION.md` exercised by named tests:
CLIMB-03, CLIMB-04, CLIMB-05, CLIMB-06×2, CLIMB-07×2, CLIMB-10 (readback flavour). The other
CLIMB-10 row (formatting flavour) belongs to Plan 02-05 per I-04.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Self-referential verify command]**
- **Found during:** Task 0
- **Issue:** Task 0's `<automated>` verify command included `! grep -qE "KEEP ONE BRANCH" ...`,
  which causes the command to grep for its own argument string (the literal `"KEEP ONE BRANCH"`
  appears in the verify command text). This makes the check structurally unable to pass.
- **Fix:** Replaced the third clause with a regex that matches only the original 4-space-indented
  Python comment header (`! grep -qE "^    # Branch [AB] \(icu_rpe_path"`), which targets the
  *deleted scaffolding* and does not match the verify command itself.
- **Files modified:** `.planning/phases/02-wellness-write-and-activity-enrichment/02-04-PLAN.md`
  (Task 0's verify command line)
- **Commit:** `8c1b233` (rolled into Task 0 plan-revision commit)

No source-code changes were made beyond the plan instructions. No architectural deviations.

## Authentication Gates

None encountered (mocked HTTP throughout; no live API).

## Self-Check

- [x] `src/intervals_mcp_server/tools/climbing.py` exists and contains `enrich_activity_climbing`
- [x] `tests/test_climbing_write.py` exists with 17 tests
- [x] Commit `8c1b233` (Task 0) exists
- [x] Commit `3f0aab1` (Task 1) exists
- [x] Commit `de878da` (Task 2) exists
- [x] D-16 marker comment present in BOTH plan file AND source
- [x] All 17 tests in `test_climbing_write.py` pass
- [x] All 34 pre-existing related tests still pass
- [x] `_verify_custom_fields_setup_impl`, `verify_custom_fields_setup`, `_README_POINTER` byte-identical

## Self-Check: PASSED

All claimed files and commits verified to exist on disk and in git history. All 17 tests in
`tests/test_climbing_write.py` collected and pass. D-16 marker comment count: 1 in plan, 1 in
source (matched). No regressions: full pytest suite (123 tests) green.
