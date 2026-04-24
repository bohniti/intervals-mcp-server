---
phase: 01-foundation-and-write-path-spike
plan: 02
subsystem: utils/formatting
tags:
  - climbing
  - formatter
  - presentation
  - tdd
requires:
  - "Intervals.icu activity JSON dict shape"
provides:
  - "format_climbing_activity(activity: dict[str, Any]) -> str"
affects:
  - "scripts/spike_write_endpoints.py (Plan 01-03 — imports this formatter for readback)"
  - "Phase 2 enrichment tool return path"
tech_stack_added: []
patterns_added:
  - "Compact f-string formatter with explicit boolean→Yes/No/N/A mapping"
key_files_created:
  - tests/test_format_climbing_activity.py
  - .planning/phases/01-foundation-and-write-path-spike/deferred-items.md
key_files_modified:
  - src/intervals_mcp_server/utils/formatting.py
decisions:
  - "Followed D-15 (append, not replace) and D-20 (Pitfall #12 byte-identical guard) literally: 0 deletions in the `formatting.py` diff."
  - "Followed the plan's exact f-string return shape rather than the alternative `lines.append` idiom — 8 fixed fields make a single return expression more readable."
  - "Logged 2 pre-existing mypy errors in `_KeyTracker` / `format_wellness_entry` to deferred-items.md rather than auto-fixing (D-16 / scope-boundary rule)."
metrics:
  duration_min: 3
  tasks_completed: 1
  files_touched: 3
  tests_before: 34
  tests_after: 42
  completed_date: "2026-04-24"
---

# Phase 01 Plan 02: Extend utils/formatting.py with format_climbing_activity Summary

**One-liner:** Additive `format_climbing_activity(activity) -> str` formatter for the 8 Phase 1 climbing fields (discipline, indoor, session_focus, top_grade_sent, top_grade_attempted, sends, attempts, icu_rpe) plus id/name/date headers, with explicit Yes/No/N/A boolean handling and `{rpe}/10` numeric RPE formatting — zero changes to any existing function in `formatting.py` (Pitfall #12 byte-identical guard).

## What Was Built

### Public API added

```python
def format_climbing_activity(activity: dict[str, Any]) -> str
```

Appended at the bottom of `src/intervals_mcp_server/utils/formatting.py` (after `format_intervals`, separated by two blank lines per PEP 8). No new imports — the function uses `dict[str, Any]` which was already available via the pre-existing `from typing import Any` at the top of the file.

### Rendered fields

Renders a single multi-line string with a `"Climbing Activity"` header followed by 11 indented lines, in order:

| Order | Line | Source key | Fallback |
|-------|------|-----------|----------|
| 1 | `ID` | `activity["id"]` | `"N/A"` |
| 2 | `Name` | `activity["name"]` | `"Unnamed"` |
| 3 | `Date` | `activity["start_date_local"]` | `"Unknown"` |
| 4 | `Discipline` | `activity["discipline"]` | `"N/A"` |
| 5 | `Indoor` | `activity["indoor"]` (bool) | `"Yes"` / `"No"` / `"N/A"` |
| 6 | `Session focus` | `activity["session_focus"]` | `"N/A"` |
| 7 | `Top grade sent` | `activity["top_grade_sent"]` | `"N/A"` |
| 8 | `Top grade attempted` | `activity["top_grade_attempted"]` | `"N/A"` |
| 9 | `Sends` | `activity["sends"]` | `"N/A"` |
| 10 | `Attempts` | `activity["attempts"]` | `"N/A"` |
| 11 | `RPE` | `activity["icu_rpe"]` | `"{rpe}/10"` if int/float, else `"N/A"` |

**Design rules applied:**
- `indoor` uses explicit `is True` / `is False` checks so that `True`/`False` render as `"Yes"`/`"No"` (not `"True"`/`"False"`) and `None` / missing both collapse to `"N/A"` (not `"None"`). This is the Yes/No/N/A contract the plan required.
- `icu_rpe` uses `isinstance(rpe, (int, float))` to mirror the existing `format_activity_summary` idiom (line 47 pre-change), keeping RPE rendering consistent across both formatters.
- No discipline / session_focus normalization — values arrive as either the `Discipline` / `SessionFocus` StrEnum `.value` (Phase 2 write tools) or raw-lowercase strings from the live API readback (Plan 01-03 spike). Both paths produce lowercase strings; the formatter renders whatever it's handed.

## Tests Added

`tests/test_format_climbing_activity.py` — 8 tests, all green:

| # | Test | Behavior guarded |
|---|------|------------------|
| 1 | `test_format_climbing_activity_empty_dict_renders_na` | Empty dict does not KeyError; every field falls back to `"N/A"`; header `"Climbing Activity"` is always present |
| 2 | `test_format_climbing_activity_full_dict_renders_all_fields` | All 11 rendered fields appear in output when fully specified |
| 3 | `test_format_climbing_activity_indoor_false_renders_no` | `indoor=False` → `"Indoor: No"`, not `"False"` |
| 4 | `test_format_climbing_activity_indoor_none_renders_na` | Explicit `indoor=None` → `"Indoor: N/A"` |
| 5 | `test_format_climbing_activity_rpe_float_renders_slash_10` | Float RPE (`7.5`) → `"7.5/10"` |
| 6 | `test_format_climbing_activity_rpe_int_renders_slash_10` | Int RPE (`8`) → `"8/10"` |
| 7 | `test_format_climbing_activity_rpe_missing_renders_na` | Missing RPE → `"RPE: N/A"` (not `"None/10"`) |
| 8 | `test_format_activity_summary_byte_identical_regression_guard` | D-20 / Pitfall #12: `format_activity_summary` output substrings are unchanged on a fixed sample dict |

## Verification Results

| Check | Command | Result |
|-------|---------|--------|
| Plan verify command | `uv run python -c "…"` (see plan) | `OK` |
| Full test suite | `uv run pytest tests/` | `42 passed` (was 34 pre-change — 8 new tests added) |
| Ruff | `uv run ruff check src/intervals_mcp_server/utils/formatting.py` | `All checks passed!` |
| Mypy (additive scope) | Mypy on the new function's lines | Clean — no errors on 552–592 |
| Pitfall #12 guard | `git diff src/intervals_mcp_server/utils/formatting.py \| grep -E "^-[^-]" \| grep -vE "^--- " \| wc -l` | `0` (no deletions) |
| D-16 untouched-utils guard | `git diff utils/types.py utils/validation.py utils/dates.py` | empty |
| `grep -c "^def format_climbing_activity"` | | `1` |
| `grep -c "^def format_activity_summary"` | | `1` (still present) |
| `grep -c "^def format_wellness_entry"` | | `1` (still present) |
| Field-read grep | `grep -cE "activity\.get\(['\"](discipline\|indoor\|session_focus\|top_grade_sent\|top_grade_attempted\|sends\|attempts\|icu_rpe)['\"]"` | `9` (≥ 7 required) |
| `grep -c "Climbing Activity"` | | `1` |
| `grep -c "Indoor: {indoor_str}"` | | `1` (Yes/No renderer used) |

## D-16 Respect Confirmation

`git diff src/intervals_mcp_server/utils/types.py src/intervals_mcp_server/utils/validation.py src/intervals_mcp_server/utils/dates.py` is empty — none of these general-purpose utility files were touched in Plan 01-02. Phase 1 keeps climbing-specific code out of the shared modules.

## Deviations from Plan

### Auto-fixed Issues

None. The plan was specific enough (exact function body, exact signatures, exact file location) that no Rule 1/2/3 deviations were needed.

### Deferred Issues (scope-boundary rule)

**Pre-existing mypy errors in `utils/formatting.py` (not in scope for Plan 01-02)**

Running `uv run mypy src/intervals_mcp_server/utils/formatting.py` surfaced two errors:

```
src/intervals_mcp_server/utils/formatting.py:28: error: Argument 1 to "add" of "set" has incompatible type "object"; expected "str"  [arg-type]
src/intervals_mcp_server/utils/formatting.py:358: error: "dict[str, Any]" has no attribute "accessed"  [attr-defined]
```

Both are in pre-existing code (`_KeyTracker.__contains__` at line 28 and `format_wellness_entry` at line 358). I verified they pre-existed by `git stash`-ing the new function and re-running mypy — both errors were already present on parent commit `8029fd5`, before any of my changes. Under D-16 / D-20 / Pitfall #12, Phase 1 must not modify existing shared utilities; auto-fixing these would violate the byte-identical regression guard. They are logged to `.planning/phases/01-foundation-and-write-path-spike/deferred-items.md` for a future dedicated typing-cleanup plan.

## Key Decisions Made During Execution

1. **Used the plan's exact f-string return block verbatim** rather than the alternative `lines = [...]; return "\n".join(lines)` idiom suggested by the pattern map. For 11 fixed fields with no conditional sections, the single-expression f-string is shorter, readable, and matches the style of `format_activity_summary` (the direct sibling function). This was one of the "planner's discretion" points.

2. **`indoor` handled with `is True` / `is False` explicit identity checks** (not `bool(indoor)`). This preserves the distinction between `False` (`"No"`) and `None`/missing (`"N/A"`), which `bool(None)` would collapse to `"No"` — wrong for a field where "absent" and "explicitly false" have different meanings.

3. **`icu_rpe` rendered via `isinstance(rpe, (int, float))`** to mirror `format_activity_summary`'s RPE handling at line 47 pre-change. Keeps the two formatters consistent.

4. **Logged pre-existing mypy errors rather than fixing** — D-20 and Pitfall #12 forbid touching shared utilities in Phase 1, and the scope-boundary rule forbids auto-fixing pre-existing unrelated issues. Deferred cleanly.

## Commits

| Hash | Type | Message |
|------|------|---------|
| `d1a0daf` | test | `test(01-02): add failing tests for format_climbing_activity` |
| `bc2ea02` | feat | `feat(01-02): add format_climbing_activity to utils/formatting.py` |
| `d97a044` | docs | `docs(01-02): log pre-existing mypy errors in formatting.py to deferred-items` |

TDD gate sequence (RED → GREEN) is clean:
- `d1a0daf` is `test(...)` — tests for `format_climbing_activity` fail (ImportError) before any implementation.
- `bc2ea02` is `feat(...)` — implementation added; all 8 new tests pass.
- No REFACTOR commit — code was minimal and clean on first pass, no cleanup needed.

## TDD Gate Compliance

- **RED gate:** Present — commit `d1a0daf` contains only `tests/test_format_climbing_activity.py` with tests that fail on the parent commit (ImportError for the not-yet-defined `format_climbing_activity`).
- **GREEN gate:** Present — commit `bc2ea02` contains only the `formatting.py` change; all 8 new tests pass.
- **REFACTOR gate:** Skipped — no post-GREEN cleanup needed.

## Known Stubs

None. The function is fully functional: given a dict it always produces a complete formatted string with defined fallbacks for every field.

## Threat Surface Scan

No new network endpoints, auth paths, file-access patterns, or schema changes introduced. The formatter is a pure function (dict in, string out). No threat flags.

## Self-Check: PASSED

- `src/intervals_mcp_server/utils/formatting.py` — present, `format_climbing_activity` at line 552.
- `tests/test_format_climbing_activity.py` — present, 8 tests collected.
- `.planning/phases/01-foundation-and-write-path-spike/deferred-items.md` — present.
- Commits `d1a0daf`, `bc2ea02`, `d97a044` — all present in `git log --oneline`.
- Full test suite: 42/42 passing.
- Plan verify command: `OK`.
