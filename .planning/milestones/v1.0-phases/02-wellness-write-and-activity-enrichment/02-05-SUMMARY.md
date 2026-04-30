---
phase: 02-wellness-write-and-activity-enrichment
plan: 05
subsystem: testing
tags: [smoke-test, formatter, regression-test, climbing, wellness, pytest, intervals-icu]

# Dependency graph
requires:
  - phase: 01-foundation-and-write-path-spike
    provides: format_climbing_activity (Phase 1 11-field renderer)
  - phase: 02-wellness-write-and-activity-enrichment
    provides: write_wellness_entry (Plan 02-03), enrich_activity_climbing (Plan 02-04, parallel)
provides:
  - Snapshot regression test locking format_climbing_activity output for Phase-1-shaped input (I-07 fix)
  - Four CLIMB-10 formatter assertions (icu_rpe rendering, empty activity, indoor=False, RPE float)
  - scripts/smoke_phase2.py end-to-end live-API smoke test (D-25)
  - Additive docstring extension on format_climbing_activity noting post-enrichment readback role
affects:
  - phase 03 (climbing-tools), phase 04 (status-report) — both depend on the renderer staying byte-stable
  - SETUP-01 verification flow — the smoke script is the canonical "did SETUP-01 land + did Phase 2 tools work end-to-end?" check

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Snapshot regression test for formatter byte-stability"
    - "Standalone live-API smoke script under scripts/ with try/finally cleanup, _redact() helper, no def test_* (D-25 / Pitfall #14)"

key-files:
  created:
    - scripts/smoke_phase2.py
  modified:
    - src/intervals_mcp_server/utils/formatting.py (docstring only — body unchanged per D-24)
    - tests/test_climbing.py (5 new formatter tests appended)

key-decisions:
  - "Renderer body left unchanged. Phase 1 already covered all 11 fields (id, name, start_date_local, discipline, indoor, session_focus, top_grade_sent, top_grade_attempted, sends, attempts, icu_rpe). 02-SPIKE-FINDINGS.md surfaced no new field that Plan 02-04 would have added to the tool surface, so the conditional 'add Comments line' branch in the plan's behavior section did NOT fire. Docstring was the only source change."
  - "Captured snapshot expected-string was verified by running format_climbing_activity({'id': 'phase1-snapshot', 'name': 'Phase 1 baseline', 'start_date_local': '2025-01-01T00:00:00'}) BEFORE writing the test, so the snapshot locks current behaviour rather than guessing it."
  - "Smoke script imports both write_wellness_entry and enrich_activity_climbing. The latter is being implemented by the parallel Plan 02-04 worktree — in this worktree the import target does not yet exist. The script is intended for hand-run AFTER the worktrees merge, so the missing-import is expected and harmless: pytest does not collect scripts/, the AST parses cleanly, and the user runs the script after SETUP-01 + merge."

patterns-established:
  - "Snapshot regression pattern: capture renderer output for a fixed input vector once, paste it as a triple-quoted expected constant, byte-equality assertion. Replaces fragile 'function body unchanged' regex checks (I-07)."
  - "Live-API smoke script structure: SPIKE_DATE=2099-01-01, _redact() helper, try/finally activity DELETE + wellness PUT -1 cleanup, no def test_*, file under scripts/ not tests/."

requirements-completed: [CLIMB-10]

# Metrics
duration: ~15min
completed: 2026-04-27
---

# Phase 02 Plan 05: Formatter regression + end-to-end smoke script Summary

**Snapshot-locked the Phase 1 climbing renderer for post-enrichment readback and added scripts/smoke_phase2.py — a standalone live-API smoke test exercising the full Phase 2 write path with try/finally cleanup, never collected by pytest.**

## Performance

- **Duration:** ~15 minutes
- **Started:** 2026-04-27T09:22:00Z (approx — worktree base reset)
- **Completed:** 2026-04-27T09:37:00Z
- **Tasks:** 2/2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- Five formatter regression tests added covering CLIMB-10's formatting flavour: icu_rpe rendering, empty-activity defensive behaviour, `indoor: False → "No"` mapping, RPE float rendering, and a snapshot byte-equality test (I-07 fix replacing the previous regex-based check).
- `format_climbing_activity` docstring extended additively (body byte-unchanged) to document its Phase 2 role as the post-enrichment readback renderer for `enrich_activity_climbing`.
- `scripts/smoke_phase2.py` created — exercises `write_wellness_entry` → `POST /athlete/{id}/activities/manual` → `enrich_activity_climbing` → `DELETE /activity/{id}` → wellness PUT -1 cleanup, with athlete-id redaction on every log line and try/finally guarantees that DELETE runs even mid-failure.
- All five formatter tests + the existing 13 tests in `tests/test_climbing.py` pass; full repo suite holds at 111 passed (was 106; +5 new tests). `pytest --collect-only` does not pick up `scripts/smoke_phase2.py`.

## Task Commits

1. **Task 1: Confirm + extend format_climbing_activity docstring + add formatter tests** — `4442577` (feat)
2. **Task 2: Create scripts/smoke_phase2.py end-to-end smoke test (D-25)** — `32e71f8` (feat)

## Files Created/Modified

- `scripts/smoke_phase2.py` (created, 196 lines) — Standalone async live-API smoke test for the Phase 2 tool surface. Imports `write_wellness_entry` from `tools/wellness.py` and `enrich_activity_climbing` from `tools/climbing.py`; uses `make_intervals_request` directly only for the throwaway-activity POST and the DELETE/PUT cleanup steps. `SPIKE_DATE = "2099-01-01"`. `try` / `finally` ensures cleanup runs on raise. Athlete-id redacted via `_redact()` before any `logger.info`. No `def test_*` inside; not under `tests/`.
- `src/intervals_mcp_server/utils/formatting.py` — Docstring on `format_climbing_activity` (lines 552–598) extended with a Phase 2 paragraph noting reuse for `enrich_activity_climbing` post-enrichment readback. Function body byte-unchanged (D-24 carry-forward).
- `tests/test_climbing.py` — Five new tests appended after `test_verify_internal_helper_returns_tuple`:
  - `test_format_climbing_activity_renders_icu_rpe` (CLIMB-10 falsifiable assertion per 02-VALIDATION.md)
  - `test_format_climbing_activity_handles_empty_activity` (defensive — N/A placeholders for missing keys)
  - `test_format_climbing_activity_indoor_false_renders_no` (`indoor=False` → `"No"`, never `"False"` or `"N/A"`)
  - `test_format_climbing_activity_rpe_float_renders` (icu_rpe accepts both int and float)
  - `test_format_climbing_activity_renders_existing_fields_unchanged` (I-07 fix — snapshot byte-equality)

## Decisions Made

- **Renderer body unchanged.** 02-SPIKE-FINDINGS.md `## Activity custom-field PUT shape` is currently UNRESOLVED (SETUP-01 PREREQUISITE NOT MET). No new fields were probed and confirmed for Plan 02-04's tool surface, so the conditional "add a `Comments` line" branch in Task 1's plan did not fire. The renderer continues to render exactly the 11 Phase 1 fields.
- **Snapshot expected-string was captured live before writing the test.** `python -c "from intervals_mcp_server.utils.formatting import format_climbing_activity; print(repr(format_climbing_activity({'id': 'phase1-snapshot', 'name': 'Phase 1 baseline', 'start_date_local': '2025-01-01T00:00:00'})))"` produced the exact string the test asserts against. The snapshot now locks current behaviour; any future renderer edit that alters this output will fail this test, making the regression intentional and reviewable.
- **Smoke script written despite Plan 02-04 not yet merged.** The smoke script imports `enrich_activity_climbing` from `tools/climbing.py`, which only exists on Plan 02-04's worktree (parallel wave 3 execution). The script is meant for hand-run by the user *after* SETUP-01 + after Plan 02-04 merges. AST parses cleanly, pytest does not collect it, and the user runs it manually — so the deferred import resolution is intentional and not a defect.

## Deviations from Plan

None — plan executed exactly as written.

The plan's Task 1 conditional ("if 02-SPIKE-FINDINGS.md surfaced a NEW field added to Plan 02-04's tool surface, append a `Comments` line") was evaluated and resolved to "no new field" by reading 02-SPIKE-FINDINGS.md `## Activity custom-field PUT shape` (UNRESOLVED — SETUP-01 prerequisite not met) and confirming that Plan 02-04 has not yet completed (no `02-04-SUMMARY.md`). Both inputs concur: no new field surfaced, body change skipped per the plan's explicit branch.

## Issues Encountered

- **Worktree base mismatch.** `git merge-base HEAD <expected>` returned `50bb125…` instead of the expected `3c07f2d…`. Resolved per the worktree-branch-check protocol with `git reset --hard 3c07f2d…` before any tooling calls. Post-reset, base matched and execution proceeded normally.
- **Pre-existing mypy errors in formatting.py** (lines 28 and 358 — `_KeyTracker.add(object)` and `dict[str, Any].accessed`) are unrelated to this plan's changes; verified by stashing local changes and re-running mypy. Out of scope per scope-boundary rule; no remediation taken.

## Smoke-script first-run outcome

Not executed during plan execution — the smoke script is the user-driven D-25 manual verification step. Per `<parallel_execution>` instructions: "The smoke script does NOT need to be runnable against the live API yet — the user will run it manually after SETUP-01 (custom-field schemas) is done." The script is verified static-only:

- AST parses cleanly: `uv run python -c "import ast; ast.parse(open('scripts/smoke_phase2.py').read())"` → OK
- `main` function present, no `def test_*` functions: AST inspection confirmed.
- Acceptance-criteria grep checks all pass (DELETE wired, try/finally present, `_redact` used, no httpx import, file name not `test_`-prefixed, server.py untouched).

## pytest discovery confirmation

```
$ uv run pytest --collect-only 2>&1 | tail -3

tests/test_wellness_write.py::test_subset_upsert_does_not_overwrite_unrelated_fields
tests/test_wellness_write.py::test_sleep_hours_converts_to_secs_and_upserts
tests/test_wellness_write.py::test_out_of_range_rejects_pre_api

111 tests collected in 0.48s
```

Total tests collected: **111** (was 106 pre-plan; +5 new formatter tests). `scripts/smoke_phase2.py` is NOT among the collected items — confirming D-25 / Pitfall #14 protection holds: the file lives under `scripts/`, file name does not start with `test_`, contains no `def test_*` functions.

When pytest is *forced* to collect from `scripts/smoke_phase2.py` directly:

```
$ uv run pytest --collect-only scripts/smoke_phase2.py 2>&1 | tail -3

!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
no tests collected, 1 error in 0.52s
```

The collection error is the missing-import for `enrich_activity_climbing` (Plan 02-04 not yet merged into this worktree). This is expected and harmless: pytest never reaches this file in normal usage.

## Pointer to all five Phase 2 plan summaries

For the verifier traversing the trail:

- `.planning/phases/02-wellness-write-and-activity-enrichment/02-01-SUMMARY.md` — second-probe spike + 02-SPIKE-FINDINGS.md
- `.planning/phases/02-wellness-write-and-activity-enrichment/02-02-SUMMARY.md` — `utils/wellness.py` (WELLNESS_RANGES, build_wellness_put_body)
- `.planning/phases/02-wellness-write-and-activity-enrichment/02-03-SUMMARY.md` — `write_wellness_entry` MCP tool
- `.planning/phases/02-wellness-write-and-activity-enrichment/02-04-SUMMARY.md` — `enrich_activity_climbing` MCP tool *(Plan 02-04, executing in parallel wave 3 — SUMMARY may not yet exist when this file is written)*
- `.planning/phases/02-wellness-write-and-activity-enrichment/02-05-SUMMARY.md` — this file (formatter regression + smoke script)

Plus the canonical references: `02-SPIKE-FINDINGS.md`, `02-VALIDATION.md`, `02-CONTEXT.md`, `02-RESEARCH.md`, `02-PATTERNS.md`.

## Threat Flags

None — no new security-relevant surface was introduced. The smoke script writes to a far-future date (`2099-01-01`) with try/finally DELETE cleanup; this is the threat model's mitigation, not a new threat.

## Next Phase Readiness

- Phase 2 ROADMAP success criterion #2 (icu_rpe written and confirmed by readback) is exercised both at unit-test layer (Plan 02-04's test_climbing_write.py) and at live-API layer (this plan's `scripts/smoke_phase2.py`).
- The formatter is now snapshot-locked — Phase 3 / Phase 4 plans that consume `format_climbing_activity` can rely on byte-stable output for the 11-field shape, or update the snapshot in the same commit if they intentionally change rendering.
- One outstanding user step remains before the smoke script can run: SETUP-01 (define the seven climbing custom-field schemas in the athlete's Intervals.icu account). This is documented in PROJECT.md as a user prerequisite, not a code blocker.

---

## Self-Check: PASSED

- File `scripts/smoke_phase2.py` exists: FOUND
- File `src/intervals_mcp_server/utils/formatting.py` modified: FOUND (docstring change present)
- File `tests/test_climbing.py` modified: FOUND (5 new tests appended)
- Commit `4442577` exists: FOUND
- Commit `32e71f8` exists: FOUND
- All five formatter tests pass: VERIFIED (`uv run pytest tests/test_climbing.py::test_format_climbing_activity_renders_icu_rpe ... -x` → 5 passed)
- Full pytest suite green: VERIFIED (111 passed)
- `pytest --collect-only` ignores smoke script: VERIFIED (111 tests collected, none from `scripts/`)

---
*Phase: 02-wellness-write-and-activity-enrichment*
*Completed: 2026-04-27*
