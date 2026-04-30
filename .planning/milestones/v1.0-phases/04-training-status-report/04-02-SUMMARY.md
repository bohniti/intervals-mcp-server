---
phase: 04-training-status-report
plan: "02"
subsystem: tools/status
tags: [mcp-tool, training-status, read-only, wellness, activities]
dependency_graph:
  requires:
    - "04-01"  # utils/status.py exports (format helpers + constants)
  provides:
    - get_training_status  # public MCP tool
  affects:
    - src/intervals_mcp_server/server.py  # import side-effect registration
tech_stack:
  added: []
  patterns:
    - "two-GET orchestration (wellness 42d + activities 14d)"
    - "D-07 walk-back: day-by-day scan up to 7 days for CTL/ATL"
    - "D-11 small-sample RPE suppression"
    - "D-08/STAT-03 RPE data-quality warning naming noise source"
key_files:
  created:
    - src/intervals_mcp_server/tools/status.py
  modified:
    - src/intervals_mcp_server/server.py
decisions:
  - "wellness GET issued first (before activities GET) — single call covers all three report sections (D-04)"
  - "as_of_date validated before any HTTP call to satisfy T-04-01 injection guard"
  - "walk-back uses range(WINDOW_DAYS_WEEKLY) = 7 iterations max — O(1) dict lookup on indexed entries_by_date"
metrics:
  duration: "~10 minutes"
  completed: "2026-04-29T07:17:33Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 1
---

# Phase 04 Plan 02: MCP Tool (get_training_status) Summary

Created `src/intervals_mcp_server/tools/status.py` implementing the `get_training_status` MCP tool — a single read-only entry point issuing two GETs (wellness 42-day window, activities 14-day window) and rendering the blended CTL/ATL/TSB + wellness + RPE-flag report via the Plan 04-01 helpers.

## Shipped Signature

```python
@mcp.tool()
async def get_training_status(
    athlete_id: str | None = None,
    api_key: str | None = None,
    as_of_date: str | None = None,
) -> str:
```

All three parameters default to `None`. `as_of_date` defaults to today UTC when `None`. All parameters are optional — the tool works with zero arguments when env vars are set.

## HTTP Call Order

1. **Wellness GET first** — `GET /athlete/{id}/wellness?oldest={longterm_start}&newest={as_of_date}` (42-day window, covers Today + This Week + Long-Term Trend in one call per D-04)
2. **Activities GET second** — `GET /athlete/{id}/activities?oldest={rpe_start}&newest={as_of_date}` (14-day window, for RPE coverage check per D-09)

Plan 04-03 tests may assert this call order.

## Exact Warning Strings (pin-for-tests)

### Small-sample suppression (D-11) — total < MIN_RPE_SAMPLE (< 3 sessions)

```
> RPE coverage: low activity volume (< 3 sessions in last 14 days).
```

Note: The `< 3` is produced by f-string with the `MIN_RPE_SAMPLE` constant (= 3) and `WINDOW_DAYS_RPE` (= 14). If those constants change, the string changes.

### RPE data-quality warning (D-08/STAT-03) — more than 30% missing AND >= 3 sessions

```
> Data-quality: {missing} of {total} climbing activities in the last 14 days lack RPE ({pct}% missing). The readiness signal may be noisy because RPE feeds rpeTSS / icu_rpe.
```

Where `{missing}`, `{total}`, `{pct}` are integers computed at runtime. The literal suffix ` The readiness signal may be noisy because RPE feeds rpeTSS / icu_rpe.` is fixed. Plan 04-03 tests should match on the substrings `"RPE feeds rpeTSS / icu_rpe"` and `"readiness signal may be noisy"`.

Both warnings start with `> ` (markdown blockquote) with no trailing newline in the string itself — `format_status_report` appends `\n` if absent.

## Deviations from Plan

None — plan executed exactly as written. All code in `tools/status.py` mirrors the exact structures specified in the plan body (module header, step ordering, date-math formulas, response normalization shape from wellness.py:74-78, WeightTraining filter shape from climbing.py:638-647).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create tools/status.py with get_training_status | `0be2fda` | `src/intervals_mcp_server/tools/status.py` (created) |
| 2 | Wire get_training_status into server.py | `5b323e0` | `src/intervals_mcp_server/server.py` (2 lines added) |

## Verification Results

- ruff: clean on both files
- mypy: clean on both files
- pytest: 147/147 passed (no regressions)
- Signature introspection: `['athlete_id', 'api_key', 'as_of_date']` — matches D-16

## Requirements Addressed

- **STAT-01**: `get_training_status` registered as single MCP tool, returns one report with three labeled sections
- **STAT-02**: CTL/ATL/TSB + wellness blend (sleep/soreness/fatigue/HRV/RHR 7-day avg) in Today section
- **STAT-03**: RPE data-quality flag present with explicit "RPE feeds rpeTSS / icu_rpe" naming

## Self-Check: PASSED

- `src/intervals_mcp_server/tools/status.py` — FOUND
- `src/intervals_mcp_server/server.py` (modified) — FOUND
- Commit `0be2fda` — FOUND
- Commit `5b323e0` — FOUND
- 147 tests pass — CONFIRMED
