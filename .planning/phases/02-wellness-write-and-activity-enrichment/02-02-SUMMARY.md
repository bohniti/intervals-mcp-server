---
phase: 02-wellness-write-and-activity-enrichment
plan: 02
subsystem: api
tags: [wellness, validation, intervals-icu, mappingproxytype, leaf-utility]

# Dependency graph
requires:
  - phase: 02-wellness-write-and-activity-enrichment
    provides: "Plan 02-01 02-SPIKE-FINDINGS.md `## Wellness subjective-field ranges (LOCKED)` paste-ready dict literal"
  - phase: 01-foundation-and-write-path-spike
    provides: "01-SPIKE-FINDINGS.md confirmed wellness API field names (sleepSecs, sleepQuality, soreness, fatigue, stress, mood, motivation, hrv, restingHR)"
provides:
  - "src/intervals_mcp_server/utils/wellness.py — leaf module with WELLNESS_RANGES (MappingProxyType, 6 entries), PARAM_TO_API_FIELD (9 entries), sleep_hours_to_secs, build_wellness_put_body"
  - "tests/test_wellness_write.py — 9 helper-layer unit tests (full bodies) plus 11 Wave-0 stubs (skipped) for Plan 02-03 to fill"
  - "Named validation-map test stubs ready for Plan 02-03: test_sleep_hours_converts_to_secs_and_upserts (WELL-01), test_subset_upsert_does_not_overwrite_unrelated_fields (WELL-02), test_out_of_range_rejects_pre_api (WELL-03)"
affects: [02-03, plan-02-03, write_wellness_entry, wellness-write]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "MappingProxyType-as-SSOT: read-only constant table mirrors utils/climbing.py CUSTOM_FIELD_KEYS — alignment test (Plan 02-03) catches signature drift"
    - "Drop-None body builder: PUT upsert semantics (sending null clears) handled in helper, not in tool — keeps tool layer thin"
    - "Public-name → API-name translation map (PARAM_TO_API_FIELD) with sleep_hours special case (float hours → int sleepSecs via sleep_hours_to_secs)"
    - "Wave-0 stub pattern: pytest.skip() body with explicit `filled in plan 02-03` reason; pytest --collect-only discovers them so future plan can fill bodies without renaming"

key-files:
  created:
    - "src/intervals_mcp_server/utils/wellness.py"
    - "tests/test_wellness_write.py"
  modified: []

key-decisions:
  - "WELLNESS_RANGES omits sleep_hours, hrv, resting_hr — sleep_hours converts before validation; hrv/resting_hr are pass-through floats/ints with no enum-style range to lock (per plan behavior spec)"
  - "All 6 subjective fields locked from spike at (1, 4) — fatigue, stress, motivation, mood, soreness, sleep_quality — none unresolved"
  - "build_wellness_put_body raises KeyError on unknown public param keys (defensive — Plan 02-03 only passes known keys, this catches future drift)"

patterns-established:
  - "Leaf-module shape mirrors utils/grades.py: docstring + __all__ + UPPER_SNAKE_CASE constant + small pure helpers, no api/ or tools/ imports"
  - "Wave-0 stub naming aligned with 02-VALIDATION.md falsifiable-assertion table so Plan 02-03 fills bodies without renaming"

requirements-completed: [WELL-01, WELL-02, WELL-03]

# Metrics
duration: ~10min
completed: 2026-04-27
---

# Phase 02 Plan 02: Wellness helpers + Wave-0 test scaffolding Summary

**Leaf utility module utils/wellness.py with locked WELLNESS_RANGES (6 fields × (1,4)), drop-None PUT body builder, and 20-test collection (9 helper full-bodied + 11 Wave-0 stubs) ready for Plan 02-03 to consume.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-27T09:09:00Z (approx — orchestrator-spawned)
- **Completed:** 2026-04-27T09:19:51Z
- **Tasks:** 2
- **Files modified:** 0
- **Files created:** 2

## Accomplishments

- `src/intervals_mcp_server/utils/wellness.py` exports four symbols (`WELLNESS_RANGES`, `PARAM_TO_API_FIELD`, `sleep_hours_to_secs`, `build_wellness_put_body`) and is a true leaf module (no `api/` or `tools/` imports — verified by grep).
- `WELLNESS_RANGES` is a `MappingProxyType[str, tuple[int, int]]` populated verbatim from `02-SPIKE-FINDINGS.md` `## Wellness subjective-field ranges (LOCKED)`. Read-only — assignment raises `TypeError` (test confirms).
- `build_wellness_put_body` correctly drops None entries (D-09 / Pitfall #2 — null in Intervals.icu PUT body clears the field), translates public param names to API field names, and converts `sleep_hours` → `sleepSecs` along the way. Raises `KeyError` on unknown keys (defensive guard for Plan 02-03 drift).
- `sleep_hours_to_secs` rejects negative input with `ValueError`; rounds to nearest whole second.
- `tests/test_wellness_write.py` collects 20 tests; 9 helper-layer tests pass with full bodies; 11 Wave-0 stubs are discovered with `pytest.skip()` bodies and reserved names (including the three named in 02-VALIDATION.md falsifiable-assertion rows for WELL-01/02/03).
- `tests/test_climbing.py` still green (13 passed) — no regression.

## Task Commits

Each task was committed atomically (parallel-executor `--no-verify` per worktree convention):

1. **Task 1: Create src/intervals_mcp_server/utils/wellness.py** — `dda95cb` (feat)
2. **Task 2: Create tests/test_wellness_write.py** — `1f48810` (test)

_Note: Both tasks ship to a single feature branch in this worktree; the orchestrator merges back to main after Wave 2 completes._

## Files Created/Modified

- `src/intervals_mcp_server/utils/wellness.py` — leaf utility: `WELLNESS_RANGES` (read-only mapping, 6 entries from spike), `PARAM_TO_API_FIELD` (9 entries: 6 subjective + sleep_hours + hrv + resting_hr), `sleep_hours_to_secs(hours: float) -> int`, `build_wellness_put_body(params) -> dict`.
- `tests/test_wellness_write.py` — 9 full-bodied helper tests + 11 Wave-0 stubs (named per 02-VALIDATION.md so Plan 02-03 can fill bodies without renaming).

## Final WELLNESS_RANGES literal (pasted from 02-SPIKE-FINDINGS.md)

```python
WELLNESS_RANGES: MappingProxyType[str, tuple[int, int]] = MappingProxyType({
    "fatigue": (1, 4),
    "stress": (1, 4),
    "motivation": (1, 4),
    "mood": (1, 4),
    "soreness": (1, 4),
    "sleep_quality": (1, 4),
})
```

## Fields Omitted from WELLNESS_RANGES

- **`sleep_hours`** — float input, converted to `sleepSecs` BEFORE validation (per plan behavior spec); no enum-style range to lock at the (min, max) integer level.
- **`hrv`** — pass-through float (ms); no subjective scale.
- **`resting_hr`** — pass-through int (bpm); no subjective scale.
- **None of the 6 subjective fields are unresolved.** Plan 02-01 spike landed all 6 at `(1, 4)` — no Plan 02-03 "must not surface" notes are required.

## Test Collection from `pytest --collect-only`

20 tests collected (target was ≥16):

**Helper-layer full-bodied tests (9):**
- `test_sleep_hours_to_secs_basic`
- `test_sleep_hours_to_secs_rejects_negative`
- `test_build_wellness_put_body_drops_none`
- `test_build_wellness_put_body_translates_names`
- `test_build_wellness_put_body_converts_sleep_hours`
- `test_build_wellness_put_body_empty_input_returns_empty`
- `test_build_wellness_put_body_unknown_key_raises`
- `test_param_to_api_field_covers_all_public_params`
- `test_wellness_helpers` (suite-meta — 02-VALIDATION.md row 02-02 entry point)

**Wave-0 stubs (11) — Plan 02-03 fills bodies:**
- `test_signature_aligns_with_wellness_ranges`
- `test_wellness_tool_registered`
- `test_write_wellness_entry_happy_path`
- `test_write_wellness_entry_rejects_empty_call`
- `test_write_wellness_entry_rejects_out_of_range`
- `test_write_wellness_entry_readback_failure_no_readme_pointer`
- `test_write_wellness_entry_api_error_on_put`
- `test_write_wellness_entry_unsupplied_field_dropped`
- `test_subset_upsert_does_not_overwrite_unrelated_fields` (WELL-02 named)
- `test_sleep_hours_converts_to_secs_and_upserts` (WELL-01 named)
- `test_out_of_range_rejects_pre_api` (WELL-03 named)

## Plan 02-03 Readiness — Named-Stub Confirmation

Plan 02-03 can fill the following without renaming:

| Validation-map row | Stub function name | Status |
|---|---|---|
| WELL-01 | `test_sleep_hours_converts_to_secs_and_upserts` | reserved (skipped) |
| WELL-02 | `test_subset_upsert_does_not_overwrite_unrelated_fields` | reserved (skipped) |
| WELL-03 | `test_out_of_range_rejects_pre_api` | reserved (skipped) |
| WELL-03 (specifics) | `test_write_wellness_entry_readback_failure_no_readme_pointer` | reserved (skipped) |
| Cross-cutting | `test_signature_aligns_with_wellness_ranges` | reserved (skipped) |

All names verified via `grep -q "def test_..."` against `tests/test_wellness_write.py`.

## Decisions Made

- **WELLNESS_RANGES uses MappingProxyType (not plain dict)** — matches `utils/climbing.py::CUSTOM_FIELD_KEYS` shape and gives the test_wellness_helpers test a free read-only assertion (the assignment raises `TypeError`). This was the planner's discretion option in 02-PATTERNS.md lines 60-67; chosen for symmetry with the existing analog.
- **Leaf module discipline** — no `api/` or `tools/` imports (acceptance criterion enforced by grep). Future helpers shared between `tools/wellness.py` and `tools/climbing.py` must be promoted to `utils/` per Phase 1 D-22.
- **build_wellness_put_body raises KeyError on unknown keys** — defensive even though Plan 02-03 only passes known keys; catches future param-list drift.

## Deviations from Plan

None — plan executed exactly as written.

The plan provided a paste-ready module template with placeholder `WELLNESS_RANGES` content; the placeholder was replaced verbatim with the LOCKED dict literal from `02-SPIKE-FINDINGS.md`. No bugs found, no missing critical functionality, no blocking issues, no architectural changes needed.

## Issues Encountered

- The Task 1 acceptance-criteria block included a pytest invocation (`test_sleep_hours_to_secs_rejects_negative`) that depends on Task 2 having created the test file. The plan flags this in I-09 as a known cross-task dependency. Task 1 was committed first using the inline Python verify path, then the cross-task pytest assertion was retrocoursed in after Task 2 — confirmed passing.
- `uv sync --all-extras` was needed once to install `pytest`, `ruff`, and `mypy` into the worktree's `.venv` (first run in this worktree). All three pass clean on both new files.

## User Setup Required

None — utility module + tests only; no external service configuration.

## Next Phase Readiness

- **Plan 02-03 can begin immediately** with all wave-2 dependencies in place: WELLNESS_RANGES locked, name-translation map fixed, body-builder ready, and 11 reserved stub names matching the 02-VALIDATION.md falsifiable-assertion table.
- **No blockers.** Plan 02-04 (activity enrichment) does not consume `utils/wellness.py` so Wave 3 is unaffected by this plan.
- **Self-Check item:** STATE.md and ROADMAP.md updates are owned by the orchestrator post-wave per worktree-agent contract; this agent did not touch them.

## Self-Check: PASSED

- File `src/intervals_mcp_server/utils/wellness.py` exists: FOUND
- File `tests/test_wellness_write.py` exists: FOUND
- Commit `dda95cb` (Task 1): FOUND in git log
- Commit `1f48810` (Task 2): FOUND in git log
- `WELLNESS_RANGES` populated from spike findings (6 entries × (1,4)): VERIFIED
- 20 tests collected by `pytest --collect-only` (≥16 required): VERIFIED
- Helper tests pass (9 passed, 11 skipped): VERIFIED
- `tests/test_climbing.py` no regression (13 passed): VERIFIED
- `ruff check` clean on both new files: VERIFIED
- `mypy` clean on both new files: VERIFIED
- `server.py` not modified: VERIFIED
- STATE.md not modified by this agent: VERIFIED
- ROADMAP.md not modified by this agent: VERIFIED

---
*Phase: 02-wellness-write-and-activity-enrichment*
*Completed: 2026-04-27*
