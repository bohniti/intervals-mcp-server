---
phase: 02-wellness-write-and-activity-enrichment
plan: 03
subsystem: tools
tags: [wellness, mcp-tool, write-path, upsert, readback-verification, well-01, well-02, well-03]

# Dependency graph
requires:
  - phase: 02-wellness-write-and-activity-enrichment
    provides: "Plan 02-02 utils/wellness.py (WELLNESS_RANGES, PARAM_TO_API_FIELD, sleep_hours_to_secs, build_wellness_put_body) and the 11 reserved Wave-0 stubs in tests/test_wellness_write.py"
  - phase: 01-foundation-and-write-path-spike
    provides: "make_intervals_request single HTTP boundary; PUT /athlete/{id}/wellness/{date} URL shape confirmed; format_wellness_entry rendering"
provides:
  - "src/intervals_mcp_server/tools/wellness.py — write_wellness_entry @mcp.tool() (12-param, async, hard pre-API range validation, drop-None upsert, PUT then GET readback with per-field equality verification)"
  - "tests/test_wellness_write.py — 11 Wave-0 stubs replaced with full-bodied tests; 20 total tests (9 helper + 11 tool-layer); all 5 named falsifiable assertions for WELL-01/02/03 + alignment + tool-registered pass"
affects: [02-04, 02-05, write-tools, mcp-tool-discovery]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Validation-before-HTTP fail-fast: range check + empty-call check run before any make_intervals_request call (Pitfall #6 / D-07 / D-10)"
    - "Drop-None upsert via build_wellness_put_body: unsupplied (None) fields omitted from PUT body, not nulled (Intervals.icu treats null as 'clear' — D-09)"
    - "Per-field readback equality: PUT then GET, verify each supplied field roundtripped — wellness flavour of Pitfall #2 mitigation (D-11)"
    - "Dual-monkeypatch test pattern: patch make_intervals_request at BOTH api.client and tools.wellness import sites because tool re-imports the symbol"
    - "Wellness errors omit _README_POINTER: native fields, not user-defined custom fields (CONTEXT.md <specifics>)"
    - "Pre-API auth gate via resolve_athlete_id early-return — same shape as get_wellness_data and verify_custom_fields_setup"

key-files:
  created: []
  modified:
    - "src/intervals_mcp_server/tools/wellness.py — added write_wellness_entry tool (additive, get_wellness_data body untouched per D-24)"
    - "tests/test_wellness_write.py — replaced 11 Wave-0 stubs with full test bodies"

key-decisions:
  - "Date validation wrapped (try/except) returns user-string instead of letting ValueError propagate — matches tools/ convention (CONVENTIONS.md: tools always return str). Per plan task 1 behavior step 1."
  - "All 6 subjective fields are locked at (1,4) by Plan 02-02; the 'not yet supported' fallback path in the tool is therefore unreachable today but kept as a defensive guard (Pitfall #2-style belt-and-suspenders against future drift if a range entry is removed without removing the param)."
  - "Direct equality on readback values is sufficient for current wellness fields — sent and received types are int/int after sleep_hours conversion. No need for the type-coercion drift handling required by Plan 02-04 (where icu_rpe int↔float and indoor bool↔string drift can occur)."

patterns-established:
  - "Many-arg async tool with `# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-return-statements,too-many-branches` — extends the get_activities pattern with the two extra disables write tools need (early-return validators + range-check branches)"
  - "Validation-before-HTTP for write tools: validate_date → resolve_athlete_id → range check → empty-call check → build body → PUT → readback equality. This is the canonical write-tool order and Plan 02-04 reuses it for enrich_activity_climbing."

requirements-completed: [WELL-01, WELL-02, WELL-03]

# Metrics
duration: ~25min
completed: 2026-04-25
---

# Phase 02 Plan 03: write_wellness_entry MCP Tool Summary

**Single-shot MCP tool `write_wellness_entry` lets Claude log any subset of 9 wellness fields with hard pre-API range validation, drop-None upsert, and PUT-then-GET-readback per-field equality verification. All Wave-0 stubs filled; 20/20 tests green; 0 skipped.**

## Performance

- **Duration:** ~25 min
- **Started:** ~2026-04-25 (worktree spawn)
- **Tasks:** 2
- **Files modified:** 2 (no files created)
- **Tests:** 106 passed, 0 skipped, 0 failed (full suite)

## Tool Signature (copy-pasted from src/intervals_mcp_server/tools/wellness.py)

```python
@mcp.tool()
async def write_wellness_entry(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-return-statements,too-many-branches
    date: str,
    sleep_hours: float | None = None,
    sleep_quality: int | None = None,
    soreness: int | None = None,
    fatigue: int | None = None,
    motivation: int | None = None,
    stress: int | None = None,
    mood: int | None = None,
    hrv: float | None = None,
    resting_hr: int | None = None,
    athlete_id: str | None = None,
    api_key: str | None = None,
) -> str:
```

`inspect.signature(write_wellness_entry)` reports 12 parameters and `inspect.iscoroutinefunction(write_wellness_entry)` is `True`. The decorator order (`@mcp.tool()` first, `# pylint: disable=...` on the `async def` line) matches the `get_activities` analog.

## WELL-01 / WELL-02 / WELL-03 Named-Test Pass Confirmation

| Validation-map row | Named test | Status |
|---|---|---|
| WELL-01 | `tests/test_wellness_write.py::test_sleep_hours_converts_to_secs_and_upserts` | passed |
| WELL-02 | `tests/test_wellness_write.py::test_subset_upsert_does_not_overwrite_unrelated_fields` | passed |
| WELL-03 | `tests/test_wellness_write.py::test_out_of_range_rejects_pre_api` | passed |
| WELL-03 (specifics — no README pointer) | `tests/test_wellness_write.py::test_write_wellness_entry_readback_failure_no_readme_pointer` | passed |
| Cross-cutting (signature ↔ ranges alignment) | `tests/test_wellness_write.py::test_signature_aligns_with_wellness_ranges` | passed |
| Tool registration smoke | `tests/test_wellness_write.py::test_wellness_tool_registered` | passed |

Run command: `uv run pytest tests/test_wellness_write.py::test_sleep_hours_converts_to_secs_and_upserts tests/test_wellness_write.py::test_subset_upsert_does_not_overwrite_unrelated_fields tests/test_wellness_write.py::test_out_of_range_rejects_pre_api tests/test_wellness_write.py::test_signature_aligns_with_wellness_ranges tests/test_wellness_write.py::test_wellness_tool_registered -x` → `5 passed`.

Full file: `uv run pytest tests/test_wellness_write.py` → `20 passed in 0.58s`.

## Reference PUT Body — `write_wellness_entry(date="2099-01-01", sleep_hours=8.0, fatigue=2)`

For Plan 02-04's analogous activity readback verification pattern, here is the **exact** body shape Plan 02-03 produces and verifies on readback:

```python
# Inputs
candidates = {
    "sleep_hours": 8.0,
    "sleep_quality": None,
    "soreness": None,
    "fatigue": 2,
    "motivation": None,
    "stress": None,
    "mood": None,
    "hrv": None,
    "resting_hr": None,
}

# Output of build_wellness_put_body(candidates)
PUT_BODY = {"sleepSecs": 28800, "fatigue": 2}
```

**HTTP traffic:**

```text
PUT  /athlete/i1/wellness/2099-01-01    body={"sleepSecs": 28800, "fatigue": 2}
GET  /athlete/i1/wellness               params={"oldest": "2099-01-01", "newest": "2099-01-01"}
```

**Per-field equality check** iterates `body.items()` only (NOT all 9 candidate keys). For each `(api_key_name, sent_value)` pair, the readback entry must contain `entry.get(api_key_name) == sent_value`. Two checks here: `sleepSecs == 28800` and `fatigue == 2`. Mismatches collect into a multi-line error string; success path renders the entry via `format_wellness_entry`.

**Plan 02-04 takeaway:** the activity readback uses the same shape — iterate the supplied-keys body (not all custom-field keys), compare equality against the GET-readback dict, list each mismatching `api_name → sent vs got` pair. The one delta Plan 02-04 must add is README-pointer inclusion when any of the 7 climbing custom-field keys mismatches (per D-15 / Phase 1 D-12).

## Wellness Fields Omitted from WELLNESS_RANGES & "Not Yet Supported" Error Path

Per Plan 02-02 summary, **none** of the 6 subjective wellness fields are unresolved — the spike landed all 6 at `(1, 4)`:

| Field | Range | Marked unresolved? |
|---|---|---|
| fatigue | (1, 4) | no |
| stress | (1, 4) | no |
| motivation | (1, 4) | no |
| mood | (1, 4) | no |
| soreness | (1, 4) | no |
| sleep_quality | (1, 4) | no |

Therefore the "not yet supported" defensive code path in `write_wellness_entry`:

```python
elif name in {"sleep_quality", "soreness", "fatigue", "motivation", "stress", "mood"}:
    # Subjective field with no locked range — Plan 02-01 marked it unresolved.
    return (
        f"Error: {name} is not yet supported — its valid range was "
        f"not confirmed by the Phase 2 spike. Re-probe before re-enabling."
    )
```

is **unreachable in production** today. The path is intentionally retained as a Pitfall #2-style belt-and-suspenders guard against future drift (a future plan dropping a range entry without removing the param would otherwise silently send an unvalidated value to the API).

**Manual proof of reachability** (executed against the worktree):

```text
$ uv run python -c "<patch WELLNESS_RANGES to drop fatigue, call tool with fatigue=2>"
Error: fatigue is not yet supported — its valid range was not confirmed by the Phase 2 spike. Re-probe before re-enabling.
```

The pass-through fields (`sleep_hours`, `hrv`, `resting_hr`) have no enum-style range to lock — they intentionally do not appear in `WELLNESS_RANGES` and the alignment test only asserts coverage of the 6 subjective fields. Negative `sleep_hours` is caught later by `sleep_hours_to_secs` raising `ValueError`, which the tool surfaces as `Error building wellness body: sleep_hours must be non-negative, got <n>`.

## Task Commits

Each task committed atomically with `--no-verify` (parallel-executor worktree convention):

1. **Task 1: Add write_wellness_entry to tools/wellness.py** — `6cebe51` (feat)
2. **Task 2: Fill Wave-0 stubs in tests/test_wellness_write.py** — `ed788e5` (test)

Both commits ship to the executor worktree branch; orchestrator merges back to main after Wave 2 completes.

## Files Modified

- `src/intervals_mcp_server/tools/wellness.py` — module docstring extended (write tool mentioned alongside read tool); imports extended with `Any`, `validate_date`, `WELLNESS_RANGES`, `build_wellness_put_body`; appended ~150-line `write_wellness_entry` function. `get_wellness_data` body byte-identical (D-24 verified — only deleted lines in `git diff` are the old single-purpose docstring sentence and the old `validate.py` import line).
- `tests/test_wellness_write.py` — added `inspect` and `typing.Any` to module imports (replacing the `# noqa: F401` on `asyncio` since it's now actually used); replaced 11 `pytest.skip` stubs with full-bodied tests using the dual-monkeypatch + `asyncio.run` pattern from `tests/test_climbing.py:122-138`.

## Acceptance Criteria — Per Plan

### Task 1
- [x] Module imports cleanly (`uv run python -c "import intervals_mcp_server.tools.wellness"`).
- [x] `write_wellness_entry` is the second `@mcp.tool()` in the file (`grep -c '@mcp.tool()' = 2`).
- [x] `get_wellness_data` body unchanged — git diff minus-lines limited to module docstring and import-block expansion.
- [x] Signature has all 12 params (`len(inspect.signature(write_wellness_entry).parameters) == 12`).
- [x] D-21 explanatory comment present (`grep -q "No verify-fields guard here"`).
- [x] Empty-call error string present (`grep -q "at least one wellness field must be supplied"`).
- [x] Out-of-range error string present (`grep -q "out of range; expected"`).
- [x] Readback error string present (`grep -q "Error reading back wellness entry"`).
- [x] No `_README_POINTER` in wellness errors.
- [x] No direct `httpx` import.
- [x] No `_`-prefix sibling-module imports.
- [x] `server.py` not modified.
- [x] `format_climbing_activity` / `utils/formatting.py` not touched in this plan.
- [x] Ruff + mypy clean.

### Task 2
- [x] All tests pass — `20 passed, 0 skipped`.
- [x] WELL-01 / WELL-02 / WELL-03 named tests pass.
- [x] Alignment test (`test_signature_aligns_with_wellness_ranges`) passes.
- [x] Tool-registered smoke (`test_wellness_tool_registered`) passes.
- [x] Out-of-range test enforces no-HTTP via `AssertionError("HTTP must not be called")`.
- [x] Dual-monkeypatch present (18 `monkeypatch.setattr` calls across 8 tool-layer tests).
- [x] `server.py` not modified.
- [x] Existing `tests/test_climbing.py` still green (13 passed).
- [x] No `_`-prefix sibling imports in tests.

## Threat Mitigations Verified (per Plan threat_model)

| Threat ID | Mitigation | Test Evidence |
|---|---|---|
| T-02-03-01 (out-of-range silent write) | Hard pre-API range check; HTTP not invoked | `test_out_of_range_rejects_pre_api`: fake raises AssertionError on any HTTP, never reached |
| T-02-03-02 (None as null clears existing field) | `build_wellness_put_body` drops None entries | `test_write_wellness_entry_unsupplied_field_dropped`: PUT body has only `{sleepSecs, soreness}` keys when fatigue=None |
| T-02-03-03 (readback returns wrong value, tool reports success) | Per-field equality check post-PUT | `test_write_wellness_entry_readback_failure_no_readme_pointer`: mismatch surfaces "did not roundtrip" error |
| T-02-03-04 (irrelevant README pointer in wellness errors) | Wellness errors emit only API message; README pointer reserved for climbing custom-field setup | grep `! grep -q "_README_POINTER" tools/wellness.py`; mismatch error text omits "README" |
| T-02-03-05 (no-op call returns success) | Empty-call check before HTTP (D-10) | `test_write_wellness_entry_rejects_empty_call`: error string returned, calls counter == 0 |
| T-02-03-06 (httpx bypass of make_intervals_request) | grep guard; tool uses `make_intervals_request` only | `! grep -E "^import httpx" tools/wellness.py` |
| T-02-03-07 (`_`-prefix sibling import) | grep guard | `! grep -E "from intervals_mcp_server\\.tools\\.\\w+ import _" tools/wellness.py` |

## Deviations from Plan

None — plan executed exactly as written.

The plan provided paste-ready code in the `<action>` block; the only adjustments were:
- The `asyncio` import in the test file dropped its `# noqa: F401` comment (now that the stubs are filled, `asyncio.run` is actually used — the noqa was no longer needed).
- The reference PUT body for the SUMMARY's Plan 02-04 hand-off was confirmed by running the helper directly (`build_wellness_put_body(...)` returns `{"sleepSecs": 28800, "fatigue": 2}` — matches the plan's expected shape).

No bugs found, no missing critical functionality, no blocking issues, no architectural changes needed.

## Issues Encountered

- The worktree's `.venv` did not exist at start; `uv sync --all-extras` installed dependencies (one-time setup per worktree). All quality gates (ruff, mypy, pytest) green afterward.
- The plan's `<action>` block uses the unnecessary `# noqa: F401` on `asyncio` because the stubs were skipped; once the stubs were filled this comment was correctly removed (the import is now used). Recorded here as a documentation nuance, not a deviation.

## User Setup Required

None — additive tool + tests only; no external service configuration. The tool's prerequisite (`API_KEY` + `ATHLETE_ID` env vars) is unchanged from existing tools and already documented in README.

## Next Phase Readiness

- **Plan 02-04 (`enrich_activity_climbing`) can begin once Plan 02-01's spike findings land** (independent track — Plan 02-04 does not consume `tools/wellness.py`).
- **Plan 02-05 smoke test** can include `write_wellness_entry(date=SPIKE_DATE, sleep_hours=8.0, fatigue=2, ...)` as the wellness-side end-to-end exercise. The reference PUT body and GET URL above are paste-ready for that script.
- **No blockers.** STATE.md and ROADMAP.md updates are owned by the orchestrator post-wave per worktree-agent contract; this agent did not touch them.

## Self-Check: PASSED

- File `src/intervals_mcp_server/tools/wellness.py` modified additively: VERIFIED
- File `tests/test_wellness_write.py` modified additively: VERIFIED
- Commit `6cebe51` (Task 1): FOUND in git log
- Commit `ed788e5` (Task 2): FOUND in git log
- `write_wellness_entry` signature has 12 params: VERIFIED
- `inspect.iscoroutinefunction(write_wellness_entry) == True`: VERIFIED
- 20/20 tests in `test_wellness_write.py` pass with 0 skipped: VERIFIED
- WELL-01/02/03 named tests pass: VERIFIED (5/5 named tests, 0.54s)
- `tests/test_climbing.py` no regression (13 passed): VERIFIED
- Full pytest suite: 106 passed, 0 skipped, 0 failed: VERIFIED
- `ruff check` clean on modified files: VERIFIED
- `mypy` clean on modified files: VERIFIED
- `server.py` not modified: VERIFIED (`git diff --name-only HEAD~2 HEAD` shows only `tools/wellness.py` and `tests/test_wellness_write.py`)
- `utils/formatting.py` not modified: VERIFIED
- STATE.md not modified by this agent: VERIFIED
- ROADMAP.md not modified by this agent: VERIFIED

---
*Phase: 02-wellness-write-and-activity-enrichment*
*Completed: 2026-04-25*
