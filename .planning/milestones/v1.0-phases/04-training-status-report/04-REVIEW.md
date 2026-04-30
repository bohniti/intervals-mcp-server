---
phase: 04-training-status-report
reviewed: 2026-04-29T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - src/intervals_mcp_server/utils/status.py
  - src/intervals_mcp_server/tools/status.py
  - src/intervals_mcp_server/server.py
  - tests/test_status.py
  - pyproject.toml
findings:
  critical: 0
  warning: 1
  info: 6
  total: 7
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-04-29
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Phase 4 introduces a single new MCP tool (`get_training_status`) plus its
pure-rendering helpers and a comprehensive test suite. Overall code quality is
high: the `utils/status.py` / `tools/status.py` split mirrors the established
brownfield pattern, all I/O goes through `make_intervals_request()`, and the
graceful-degradation contract from CONTEXT D-13 is honored on every code path.
Tests exercise boundary conditions, walk-back, RPE warning suppression, HTTP
errors, and pathological API shapes — and verify the STAT-04 token budget with
`tiktoken`.

No critical bugs, no security issues, and no behavioral defects. Findings
below are documentation/robustness concerns:

- **One Warning**: An internal-doc inconsistency in `TSB_BANDS` between the
  written boundary comment and the actual `tsb_band()` semantics. Could
  mislead a future maintainer who reads the constants table to understand
  band boundaries.
- **Six Info-level items**: minor robustness / clarity improvements
  (overloaded constant for walk-back, narrowed activities-response handling,
  truthy `or` fallback for date resolution, hardcoded "42 days" string,
  data-mutation note, and a redundant `validate_date` on the
  system-generated default).

The implementation matches Phase 4 plans (04-01, 04-02, 04-03) and locked
context decisions D-02, D-03, D-04, D-06, D-07, D-08, D-09, D-10, D-11, D-12,
D-13, D-19.

## Warnings

### WR-01: TSB_BANDS comment describes boundary semantics that don't match `tsb_band()`

**File:** `src/intervals_mcp_server/utils/status.py:36-44`

**Issue:** The comment block above `TSB_BANDS` claims:

```
# Order matters: tsb_band() walks them in order and returns the first match where
# lower < tsb <= upper (with float('-inf') / float('inf') as open ends).
```

That walking semantics does not match `tsb_band()` (which uses a chained-if,
not a walk over `TSB_BANDS`) at the lower boundary of the "Balanced" band.

Concretely, applying the documented `lower < tsb <= upper` rule to
`(-10.0, 5.0, "Balanced")` and then `(-25.0, -10.0, "Fatigued ...")`:

- TSB = -10.0: `-10 < -10` is false -> skip "Balanced". `-25 < -10 <= -10` is
  true -> "Fatigued (productive load)".

But `tsb_band(-10.0)` returns `"Balanced"` (asserted in
`test_tsb_band_every_boundary` line 113), because the actual implementation
on line 77 uses `if tsb >= -10.0: return "Balanced"` (inclusive lower).

The same mismatch applies to the upper edge of "Fresh" vs "Burnt out": the
docstring on `tsb_band()` lines 73-81 (the function-level docstring) is the
correct contract; the table-level comment is wrong.

A future maintainer adding a sixth band, or refactoring `tsb_band()` to walk
`TSB_BANDS` (which the current comment explicitly invites), would silently
flip the inclusivity of the boundaries and break the test suite.

**Fix:** Either (a) make the comment match the chained-if behavior, or (b)
delete the misleading semantics description since `tsb_band()` does not
actually use this table. Option (a) is preferable so the constants stay
self-documenting:

```python
# TSB bands locked from CONTEXT D-03. Tuple = (lower, upper, label).
# These describe the closed/open intervals enforced by tsb_band():
#   ( 25.0,  +inf,  "Burnt out / Detraining")  ->  tsb >  25
#   (  5.0,  25.0,  "Fresh")                   ->  5 <  tsb <= 25
#   (-10.0,   5.0,  "Balanced")                -> -10 <= tsb <= 5
#   (-25.0, -10.0,  "Fatigued (productive load)") -> -25 <= tsb < -10
#   (-inf,  -25.0,  "Risk")                    ->        tsb < -25
# tsb_band() implements these via chained-if (see lines 73-81); the table
# is a grep-discoverable spec, not a lookup target.
TSB_BANDS: tuple[tuple[float, float, str], ...] = (
    ...
)
```

## Info

### IN-01: Walk-back loop reuses `WINDOW_DAYS_WEEKLY` for an unrelated cap

**File:** `src/intervals_mcp_server/tools/status.py:146`

**Issue:** The walk-back search (CONTEXT D-07, "scan back day-by-day up to 7
days") is bounded by `WINDOW_DAYS_WEEKLY`:

```python
for offset in range(WINDOW_DAYS_WEEKLY):  # 0..6 (max walk-back = 7 days, D-07)
```

`WINDOW_DAYS_WEEKLY` is defined for the weekly-trend window. The two
constants happen to coincide at 7 today, but they are conceptually
independent — D-06 sets the weekly window, D-07 sets the walk-back cap. If
someone later tunes the weekly window to 5 or 10 days (a foreseeable v2
change, since window-override params are deferred per D-06), walk-back
silently changes too.

**Fix:** Add a dedicated constant in `utils/status.py`:

```python
WALK_BACK_MAX_DAYS: int = 7  # D-07 — independent of WINDOW_DAYS_WEEKLY
```

then use it in the loop and inline-comment the coincidence:

```python
for offset in range(WALK_BACK_MAX_DAYS):  # 0..6, D-07
```

### IN-02: Activities response shape narrowed to `list` only

**File:** `src/intervals_mcp_server/tools/status.py:127-133`

**Issue:** Climbing-activity extraction handles only the `list` case:

```python
if isinstance(activities_result, list):
    for activity in activities_result:
        ...
```

If the activities endpoint ever returns a dict (the wellness endpoint can,
and lines 102-113 explicitly handle both shapes for wellness), the silent
fall-through here treats the response as zero climbing activities. The
small-sample suppression text fires, masking the underlying shape mismatch.

The current Intervals.icu API does return a list for `/activities`, so this
is not a live bug. But the asymmetry with the wellness handler a few lines
above looks unintentional — the test
`test_pathological_activities_response_does_not_crash` only exercises the
list path.

**Fix:** Either mirror the dict-or-list pattern from wellness, or add a
short explicit comment justifying the asymmetry, e.g.:

```python
# /activities always returns a JSON list per Intervals.icu API contract;
# unlike /wellness, dict shape is not observed.
climbing_activities: list[dict[str, Any]] = []
if isinstance(activities_result, list):
    ...
```

### IN-03: `e.get("date") or e.get("id")` falls through on empty strings

**File:** `src/intervals_mcp_server/tools/status.py:142`

**Issue:** Walk-back indexing uses an `or`-fallback for the date key:

```python
d = e.get("date") or e.get("id")
```

`or` treats falsy values (empty string, 0, etc.) as missing. If the API ever
returns `{"date": ""}`, the code falls through to `id`, which may not be a
date string (it is in current API responses, but that's coincidence — the id
field is documented as the wellness primary key and happens to be a date in
this endpoint).

This is defensive overkill given the current API contract, but the falsy-vs-None
distinction is a recurrent foot-gun. Prefer explicit None checks:

**Fix:**

```python
d = e.get("date")
if not isinstance(d, str):
    d = e.get("id") if isinstance(e.get("id"), str) else None
if d is None:
    continue
entries_by_date[d] = e
```

The existing `isinstance(d, str)` check on the next line already filters out
non-strings, so this is mostly cosmetic — but it makes the falsy-fallback
intent explicit instead of relying on Python truthiness.

### IN-04: `format_longterm_section` hardcodes "over 42 days" / "42d mean"

**File:** `src/intervals_mcp_server/utils/status.py:243-245`

**Issue:** The long-term bullets embed `42` as a literal string:

```python
f"- CTL: ... ({end['ctl'] - start['ctl']:+.1f}) over 42 days",
f"- ATL: ... ({end['atl'] - start['atl']:+.1f}) over 42 days",
f"- 42d mean CTL: {mean_ctl:.1f}, mean ATL: {mean_atl:.1f}",
```

`WINDOW_DAYS_LONG_TERM` is the canonical source of this value (line 48). The
graceful-empty branch already references it indirectly with the matching
literal `"in last 42 days"` (line 232). If the constant ever changes, three
literal strings drift out of sync silently — and the rendered output would
contradict the actual window.

**Fix:** Interpolate the constant:

```python
bullets = [
    f"- CTL: {start['ctl']:.1f} → {end['ctl']:.1f} "
    f"({end['ctl'] - start['ctl']:+.1f}) over {WINDOW_DAYS_LONG_TERM} days",
    f"- ATL: {start['atl']:.1f} → {end['atl']:.1f} "
    f"({end['atl'] - start['atl']:+.1f}) over {WINDOW_DAYS_LONG_TERM} days",
    f"- {WINDOW_DAYS_LONG_TERM}d mean CTL: {mean_ctl:.1f}, mean ATL: {mean_atl:.1f}",
]
```

Same minor concern in `format_weekly_section` for the "in last 7 days"
graceful path, and in `tools/status.py` lines 175-186 for the RPE warning
text. Single-window v1 makes this low-priority, but it's a cheap habit to
adopt now.

### IN-05: API response is mutated in place to backfill `date`

**File:** `src/intervals_mcp_server/tools/status.py:107-108`

**Issue:** When the wellness endpoint returns a dict-of-date-keys shape, the
tool mutates the response payload to backfill the missing `date` field:

```python
for date_str, data in wellness_result.items():
    if isinstance(data, dict):
        if "date" not in data:
            data["date"] = date_str
```

The comment on line 106 explicitly notes this mirrors `tools/wellness.py:74-78`,
so it's a deliberate convention copy. That makes it acceptable, but it does
mutate a value owned by `make_intervals_request()`. Since
`wellness_result` is local-scoped to this call and not cached upstream
(verified via `api/client.py`), there is no aliasing hazard today.

**Fix:** None required. Logging this as Info so future readers don't flag it
as a mistake. If `make_intervals_request()` ever introduces caching, this
mutation needs to be revisited (it would silently corrupt the cache for
subsequent callers). Consider a one-line comment:

```python
# Mirror tools/wellness.py:74-78. Safe today because make_intervals_request
# returns a fresh dict per call (no caching layer). If that changes, copy
# `data` before mutating.
```

### IN-06: `validate_date` runs on the system-generated default

**File:** `src/intervals_mcp_server/tools/status.py:75-80`

**Issue:** When `as_of_date is None`, the tool sets it to today UTC formatted
as `%Y-%m-%d` and *then* validates the format:

```python
if as_of_date is None:
    as_of_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
try:
    validate_date(as_of_date)
except ValueError as exc:
    return f"Error: {exc}"
```

Validation on a string the same module just produced via `strftime("%Y-%m-%d")`
can never fail — it's pure overhead. More importantly, a future refactor
that changes the default-construction path (e.g. moves it into a helper or
swaps `strftime` for ISO 8601) could silently start producing inputs that
*don't* validate, and the noise of a useless validation around it makes the
intent unclear.

**Fix:** Validate only on user-supplied input:

```python
if as_of_date is None:
    as_of_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
else:
    try:
        validate_date(as_of_date)
    except ValueError as exc:
        return f"Error: {exc}"
```

This keeps the D-19 "validate up front" rule intact for the user-facing
contract while removing the no-op validation pass.

---

_Reviewed: 2026-04-29_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
