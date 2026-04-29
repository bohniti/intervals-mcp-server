---
phase: 04-training-status-report
plan: "01"
subsystem: utils
tags: [constants, formatters, tsb, rpe, pure-functions, leaf-module]
dependency_graph:
  requires: []
  provides:
    - src/intervals_mcp_server/utils/status.py
  affects:
    - src/intervals_mcp_server/tools/status.py   # Plan 04-02 consumes these exports
    - tests/test_status.py                        # Plan 04-03 tests these exports
tech_stack:
  added:
    - statistics.fmean (stdlib, Python 3.8+)
  patterns:
    - leaf-module (no intervals_mcp_server.* imports)
    - pure-formatter (dict/list in, str out)
    - tuple-constants (TSB_BANDS as ordered tuple not mapping)
key_files:
  created:
    - src/intervals_mcp_server/utils/status.py
  modified: []
decisions:
  - "tsb_band() uses chained-if form matching D-03 prose 1:1 rather than walking TSB_BANDS tuple — more readable and directly pinned to the spec"
  - "TSB_BANDS kept as a documented tuple constant for grep-discoverability and test pinning; tsb_band() does not walk it at runtime"
  - "format_today_section wellness blend uses 7-day mean over sleepSecs/soreness/fatigue/hrv/restingHR — picks fmean aggregation (Claude's Discretion shape)"
  - "Defensive isinstance check + explicit float() cast on numerics before fmean to satisfy mypy and guard against pathological API shapes (T-04-01)"
metrics:
  duration: "~10 minutes"
  completed: "2026-04-29"
  tasks_completed: 2
  files_created: 1
  files_modified: 0
requirements:
  - STAT-02
  - STAT-03
  - STAT-04
---

# Phase 4 Plan 01: Training Status Utils Summary

**One-liner:** Pure-helper leaf module `utils/status.py` providing TSB band constants, window/RPE thresholds, and six pure formatters consumed by the Phase 4 status tool.

## What Was Built

Created `src/intervals_mcp_server/utils/status.py` — a new leaf module (stdlib-only imports, no `intervals_mcp_server.*` deps) providing:

### Public Exports

| Symbol | Type | Source |
|--------|------|--------|
| `TSB_BANDS` | `tuple[tuple[float, float, str], ...]` | CONTEXT D-03 |
| `WINDOW_DAYS_WEEKLY` | `int = 7` | CONTEXT D-06 |
| `WINDOW_DAYS_LONG_TERM` | `int = 42` | CONTEXT D-06 |
| `WINDOW_DAYS_RPE` | `int = 14` | CONTEXT D-06 |
| `RPE_MISSING_THRESHOLD` | `float = 0.30` | CONTEXT D-08 |
| `MIN_RPE_SAMPLE` | `int = 3` | CONTEXT D-11 |
| `tsb_band(tsb: float) -> str` | pure function | CONTEXT D-03 |
| `compute_rpe_coverage(activities) -> tuple[int, int]` | pure function | CONTEXT D-10 |
| `format_today_section(today_entry, wellness_recent, walk_back_days) -> str` | pure formatter | CONTEXT D-02, D-07, D-13 |
| `format_weekly_section(weekly_entries) -> str` | pure formatter | CONTEXT D-13 |
| `format_longterm_section(longterm_entries) -> str` | pure formatter | CONTEXT D-13 |
| `format_status_report(today, weekly, longterm, rpe_warning) -> str` | thin orchestrator | CONTEXT D-01 |

### TSB Band Thresholds (LOCKED — D-03)

```
TSB > 25          → "Burnt out / Detraining"
5 < TSB <= 25     → "Fresh"
-10 <= TSB <= 5   → "Balanced"
-25 <= TSB < -10  → "Fatigued (productive load)"
TSB < -25         → "Risk"
```

### Exact Graceful-Empty Strings (LOCKED — D-13)

These exact strings are pinned for Plan 04-03 tests:

| Condition | String |
|-----------|--------|
| `today_entry is None` | `"## Today\n- No wellness data in last 7 days.\n"` |
| `ctl` or `atl` is None on today_entry | `"## Today\n- No CTL/ATL trend data in last 7 days.\n"` |
| `format_weekly_section([])` | `"## This Week\n- No CTL/ATL trend data in last 7 days.\n"` |
| `format_longterm_section([])` | `"## Long-Term Trend\n- No CTL/ATL trend data in last 42 days.\n"` |

### format_today_section — Wellness Blend Shape (Claude's Discretion)

Aggregation chosen: **7-day mean** (`statistics.fmean`) over these fields in order:
1. `sleepSecs` → rendered as `f"- Sleep (7d avg): {mean/3600:.1f} h"`
2. `soreness` → `f"- Soreness (7d avg): {mean:.1f}/4"`
3. `fatigue` → `f"- Fatigue (7d avg): {mean:.1f}/4"`
4. `hrv` → `f"- HRV (7d avg): {mean:.0f} ms"`
5. `restingHR` → `f"- Resting HR (7d avg): {mean:.0f} bpm"`

Fields with no numeric values in `wellness_recent` are silently skipped (no bullet emitted). This shape fits the 400–600 token budget — verified by Plan 04-03's tiktoken test.

### format_status_report — Section Concatenation

`today_section + "\n" + weekly_section + "\n" + longterm_section` — the `"\n"` between sections (each already ending in `"\n"`) produces blank-line separators. Optional `rpe_warning` appended at bottom with trailing newline.

## Verification Results

- ruff check: PASS
- mypy: PASS (no issues)
- Task 1 assertions (tsb_band boundaries, constants, compute_rpe_coverage): PASS
- Task 2 assertions (graceful-empty paths, happy-path readiness format, weekly delta, report concatenation): PASS
- Existing test suite: **147/147 passed** (purely additive change — no regressions)

## Commits

| Hash | Description |
|------|-------------|
| `f81e199` | feat(04-01): add utils/status.py — TSB constants, RPE helpers, section formatters |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] mypy type error on fmean with list[Any | None]**
- **Found during:** Task 1 verification (mypy)
- **Issue:** `fmean(values)` where `values` was typed as `list[Any | None]` — mypy rejects `Any | None` for `Iterable[SupportsFloat]`
- **Fix:** Changed list comprehension to explicitly type `values: list[float]` with `float(e[field_key])` cast inside, consistent with the isinstance guard that precedes it. Also applied `float()` cast in `format_longterm_section`'s `fmean` generator.
- **Files modified:** `src/intervals_mcp_server/utils/status.py`
- **Commit:** `f81e199` (included in same commit)

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes. This is a pure-function leaf module with no I/O. Nothing to flag beyond what the plan's `<threat_model>` already covers (T-04-01 defensive isinstance guards are implemented per spec).

## Self-Check

- [x] `src/intervals_mcp_server/utils/status.py` exists
- [x] Commit `f81e199` exists in git log
- [x] All 12 public symbols importable
- [x] Leaf module — no `intervals_mcp_server.*` imports
- [x] 147 tests pass

## Self-Check: PASSED
