---
phase: 01-foundation-and-write-path-spike
verified: 2026-04-24T12:33:08Z
status: passed
score: 8/8 must-haves verified (programmatic) — human confirmation approved 2026-04-24
overrides_applied: 0
human_verification:
  - test: "Live Intervals.icu write paths confirmed by inspecting committed spike findings"
    expected: "01-SPIKE-FINDINGS.md documents a real 200 OK on PUT /wellness/{date} (write_1_response has {id: '2099-01-01', sleepSecs: 28800, soreness: 3}), a real activity id returned from POST /activities/manual (primary_response.id='i142495224'), and upsert_semantics_confirmed=true. User should confirm that no orphan data remains at 2099-01-01 in the Intervals.icu web UI and that the committed findings match what was observed during the live run."
    why_human: "Live-API execution is a one-shot human-gated checkpoint — the verifier cannot re-execute against the real account, and cannot visually confirm that no orphan activity or wellness row remains at 2099-01-01 in the Intervals.icu web UI. Findings file content is present and well-formed, but ground-truth cleanup is only visible to the account owner."
---

# Phase 1: Foundation and Write-Path Spike Verification Report

**Phase Goal:** The two unverified write endpoints are confirmed working and the shared utility layer is in place so every subsequent tool can be built against real API contracts and real formatter output

**Verified:** 2026-04-24T12:33:08Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                                               | Status     | Evidence                                                                                                                                                                                                                              |
| --- | ----------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Real PUT to `/athlete/{id}/wellness/{date}` succeeds; upsert vs replace semantics documented from live response (SC-1, SETUP-02)    | VERIFIED (human confirmation recommended) | `01-SPIKE-FINDINGS.md` contains live `write_1_response` (200 OK) with `{"id":"2099-01-01","sleepSecs":28800,"soreness":3,...}`. `upsert_semantics_confirmed: true` (sleepSecs from write_1 survived write_2). Cleanup response confirms `-1` clears numeric fields. |
| 2   | Real POST to `/athlete/{id}/activities` returns an activity id; minimum body fields documented from live response (SC-2, SETUP-02)  | VERIFIED (human confirmation recommended) | `01-SPIKE-FINDINGS.md` contains `primary_response.id = "i142495224"` from `POST /athlete/{athlete_id}/activities/manual` with body `{start_date_local, type:"WeightTraining", name, moving_time}`. `delete_available: true` cleanup executed. |
| 3   | `utils/grades.py` rejects Font grade on sport-route discipline and French-sport grade on boulder discipline with scale-naming error (SC-3, CLIMB-08) | VERIFIED | `validate_grade("6A", Discipline.SPORT_LEAD)` raises `ValueError` containing "French sport"; `validate_grade("6a", Discipline.BOULDERING)` raises `ValueError` containing "Font"; confirmed by pytest and programmatic smoke test. |
| 4   | Required custom-field definitions documented in README + `verify_custom_fields_setup` helper reports presence/absence (SC-4, SETUP-01, SETUP-02) | VERIFIED | README.md §"Climbing setup — required Intervals.icu custom fields" lists all 7 field rows with types and options. `verify_custom_fields_setup` tool exists in `tools/climbing.py`, wired into `server.py`, asserts missing fields by name with README pointer. |
| 5   | Utility layer in place for subsequent tools (Discipline/SessionFocus enums, CUSTOM_FIELD_KEYS spec, format_climbing_activity)        | VERIFIED | `src/intervals_mcp_server/utils/climbing.py` exposes Discipline (4 members), SessionFocus (5 members), FieldSpec dataclass, CUSTOM_FIELD_KEYS MappingProxyType (7 keys, read-only). `src/intervals_mcp_server/utils/formatting.py` defines `format_climbing_activity` at line 552. |
| 6   | Tool layer (`tools/climbing.py`) exists and is wired into `server.py` via import + `__all__` (D-17)                                  | VERIFIED | `server.py:95` imports `verify_custom_fields_setup`; `server.py:119` adds it to `__all__`. `from intervals_mcp_server.server import verify_custom_fields_setup` succeeds; identity equals `tools.climbing.verify_custom_fields_setup`. |
| 7   | Existing test suite passes; no regressions (D-20 / Pitfall #12)                                                                      | VERIFIED | `uv run pytest tests/` → 86 passed, 0 failed (baseline was 34; phase added 52 new tests). ruff + mypy green across new files. |
| 8   | Secret-leak gates pass — spike findings redact athlete_id (SETUP-02, security)                                                       | VERIFIED | `grep -c "i507957" 01-SPIKE-FINDINGS.md` → 0; `grep -c "{athlete_id}" 01-SPIKE-FINDINGS.md` → 19 (placeholder used). Only `i142495224`-style ids appearing are the throwaway activity id (response body, not credential). |

**Score:** 8/8 truths verified programmatically. Truths #1 and #2 (live-API outcomes) have full evidence in the committed findings file; human confirmation of real-world cleanup is recommended but the automated evidence is authoritative for the plan's Success Criteria.

### Required Artifacts

| Artifact                                                | Expected                                                                                          | Status      | Details |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ----------- | ------- |
| `src/intervals_mcp_server/utils/climbing.py`            | Discipline, SessionFocus StrEnums; FieldSpec; CUSTOM_FIELD_KEYS (99 lines)                        | VERIFIED    | All four exports present; 4+5 enum members; 7 CUSTOM_FIELD_KEYS entries wrapped in MappingProxyType; `__all__` matches declared exports. |
| `src/intervals_mcp_server/utils/grades.py`              | FONT_RE (`^[3-9][A-C]\+?$|^[12]$`), FRENCH_SPORT_RE (`^[3-9][abc]\+?$`), validate_grade           | VERIFIED    | Both compiled regexes and validate_grade present; strict case guard; no `re.IGNORECASE` or `.lower()`/`.upper()`; imports Discipline from sibling module. |
| `src/intervals_mcp_server/utils/formatting.py` (format_climbing_activity) | Appended formatter; byte-identical to existing functions                                   | VERIFIED    | `format_climbing_activity` at line 552. `format_activity_summary` + `format_wellness_entry` still present (greps return 1 each). |
| `src/intervals_mcp_server/tools/climbing.py`            | verify_custom_fields_setup @mcp.tool + _verify_custom_fields_setup_impl helper                    | VERIFIED    | Tool decorator present; helper async, returns `tuple[bool, list[str], str]`; docstring contains all 7 field keys; no warn-and-proceed phrasing. |
| `src/intervals_mcp_server/server.py` (wiring)           | Single import + `__all__` entry for `verify_custom_fields_setup`                                  | VERIFIED    | Line 95 import; line 119 `__all__` entry; full existing imports preserved. |
| `scripts/spike_write_endpoints.py`                      | Standalone async probe (SPIKE_DATE=2099-01-01, make_intervals_request only, redaction helper)    | VERIFIED    | 311 lines; `SPIKE_DATE = "2099-01-01"`; no `import httpx`; `_redact` helper used; all 3 definitions-endpoint candidates probed; not discovered by pytest (0 matches). |
| `.planning/phases/01-foundation-and-write-path-spike/01-SPIKE-FINDINGS.md` | Non-empty findings from live run; 3 required H2 sections; no raw athlete id    | VERIFIED    | ~1900 lines, contains `## Wellness PUT`, `## Activity POST + custom-field PUT`, `## Custom-field definitions endpoint discovery`; no raw athlete id; `winning_endpoint: "/athlete/{athlete_id}/sport-settings"`. |
| `tests/test_climbing.py`                                | Utility-layer tests (7) + tool-layer tests (6)                                                   | VERIFIED    | 13 tests total; all pass. Covers Discipline/SessionFocus alignment, MappingProxyType read-only, tool registration, happy path, all-missing, some-missing, API error, helper tuple shape. |
| `tests/test_grades.py`                                  | Regex matrix + dispatch outcomes                                                                 | VERIFIED    | 31 tests (parametrized Font / French sport regex matrix + 4 dispatch outcomes + gibberish). |
| `tests/test_format_climbing_activity.py`                | Formatter coverage                                                                                | VERIFIED    | 8 tests covering empty dict, full dict, indoor boolean handling, icu_rpe formatting, regression guard. |
| `README.md` §"Climbing setup — required Intervals.icu custom fields" | 7-row table matching CUSTOM_FIELD_KEYS + case-sensitive warning + verify-tool pointer  | VERIFIED    | Heading at line 75; 7 table rows (one per field key); discipline + session_focus select options inline; case-sensitive called out; verify_custom_fields_setup referenced. |

### Key Link Verification

| From                                                         | To                                                                | Via                                                                       | Status  | Details                                                                                                                                                              |
| ------------------------------------------------------------ | ----------------------------------------------------------------- | ------------------------------------------------------------------------- | ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `utils/grades.py`                                            | `utils/climbing.py:Discipline`                                   | `from intervals_mcp_server.utils.climbing import Discipline`             | WIRED   | Import present at line 13. validate_grade dispatches on Discipline enum.                                                                                             |
| `CUSTOM_FIELD_KEYS["discipline"].options`                    | `Discipline` enum values                                         | `tuple(d.value for d in Discipline)`                                     | WIRED   | Programmatic assertion: `CUSTOM_FIELD_KEYS["discipline"].options == ('bouldering','sport_lead','top_rope','trad')` — test in tests/test_climbing.py confirms.         |
| `CUSTOM_FIELD_KEYS["session_focus"].options`                 | `SessionFocus` enum values                                       | `tuple(f.value for f in SessionFocus)`                                   | WIRED   | Same pattern; test_session_focus_options_match_custom_field_spec passes.                                                                                             |
| `scripts/spike_write_endpoints.py`                           | `api.client.make_intervals_request`                              | `from intervals_mcp_server.api.client import make_intervals_request`    | WIRED   | Import present; used 14 times throughout script. No direct httpx.                                                                                                     |
| `scripts/spike_write_endpoints.py`                           | `utils.formatting.format_climbing_activity`                      | `from intervals_mcp_server.utils.formatting import format_climbing_activity` | WIRED   | Import present; called on the readback-after-custom-field-put to produce `rendered_readback` in findings.                                                           |
| `tools/climbing.py:verify_custom_fields_setup`               | `tools/climbing.py:_verify_custom_fields_setup_impl`             | `await _verify_custom_fields_setup_impl(...)`                             | WIRED   | Line 141 in tools/climbing.py: `_ok, _missing, human_message = await _verify_custom_fields_setup_impl(...)`.                                                          |
| `server.py`                                                  | `tools/climbing.py:verify_custom_fields_setup`                   | `from intervals_mcp_server.tools.climbing import verify_custom_fields_setup` | WIRED   | Line 95 import; `__all__` entry at line 119; test_verify_tool_registered confirms identity equals the tool module function.                                          |
| `verify_custom_fields_setup` error path                      | README §"Climbing setup — required Intervals.icu custom fields" | error message contains the section name verbatim                          | WIRED   | `_README_POINTER` constant in tools/climbing.py:20-23 uses the exact heading; README.md line 75 defines the matching section. Test `test_verify_custom_fields_setup_all_missing` asserts both strings appear in error output. |

### Data-Flow Trace (Level 4)

| Artifact                                                           | Data Variable         | Source                                                                                   | Produces Real Data                          | Status      |
| ------------------------------------------------------------------ | --------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------- | ----------- |
| `tools/climbing.py:verify_custom_fields_setup`                     | `human_message` (str) | `_verify_custom_fields_setup_impl` → `make_intervals_request("/athlete/{id}/activities?limit=50")` → presence-check against CUSTOM_FIELD_KEYS | Yes (live HTTP via make_intervals_request); unit tests monkeypatch both paths | FLOWING     |
| `utils/formatting.py:format_climbing_activity`                     | return string         | pure fn over `activity` dict param (no state)                                           | Yes — `dict.get(key, fallback)` produces real output for every rendered field | FLOWING     |
| `utils/grades.py:validate_grade`                                   | return string / raise | pure fn over `grade` + `discipline` params                                              | Yes — regex match is the decision                                              | FLOWING     |
| `scripts/spike_write_endpoints.py:main`                            | findings dicts        | `make_intervals_request` live calls → `_redact` → `write_findings` → `01-SPIKE-FINDINGS.md` | Yes — findings file populated with real 2xx + error responses captured in situ | FLOWING     |

### Behavioral Spot-Checks

| Behavior                                                                    | Command                                                                                           | Result                                      | Status  |
| --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------- | ------- |
| Discipline + SessionFocus enums shaped correctly                            | `uv run python -c "..."` comprehensive smoke test                                                | `All truth checks PASSED`                   | PASS    |
| validate_grade dispatches correctly (Font on route → ValueError "French sport"; French on boulder → ValueError "Font") | inline raise checks                                                          | Both raise with correct message tokens      | PASS    |
| CUSTOM_FIELD_KEYS is immutable MappingProxyType                             | attempted mutation                                                                                | TypeError raised                            | PASS    |
| format_climbing_activity handles empty dict, full dict, indoor bool variants, icu_rpe numeric | inline property checks                                                    | All assertions pass (`Yes`/`No`/`N/A`, `7.5/10`, all tokens present) | PASS    |
| Server re-exports tool function identity                                    | `from intervals_mcp_server.server import verify_custom_fields_setup` + `is` check                | `OK: server re-exports tool function identity` | PASS |
| Spike script invisible to pytest                                            | `uv run pytest --collect-only -q \| grep -c spike_write_endpoints`                                | `0`                                          | PASS    |
| Phase 01 test modules pass                                                  | `uv run pytest tests/test_climbing.py tests/test_grades.py tests/test_format_climbing_activity.py -v` | 52 passed                                | PASS    |
| Full test suite (regression guard)                                          | `uv run pytest tests/`                                                                            | 86 passed                                   | PASS    |
| ruff across new files                                                       | `uv run ruff check src/...climbing.py src/...grades.py src/...tools/climbing.py src/...server.py scripts/spike_write_endpoints.py` | `All checks passed!` | PASS |
| mypy across new files                                                       | `uv run mypy <same list>`                                                                         | `Success: no issues found in 5 source files` | PASS |
| No direct httpx usage in spike script or tools/climbing                     | `grep -E "^import httpx\|^from httpx" scripts/spike_write_endpoints.py src/intervals_mcp_server/tools/climbing.py` | empty (exit 1)                       | PASS |
| No warn-and-proceed in tools/climbing.py (D-12)                             | `grep -iE "warn and proceed\|warning.*proceed\|continuing anyway" src/intervals_mcp_server/tools/climbing.py` | empty (exit 1)                       | PASS |

### Requirements Coverage

| Requirement | Source Plan(s)             | Description                                                                                                                                                      | Status      | Evidence |
| ----------- | -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | -------- |
| CLIMB-08    | 01-01, 01-02               | Grade values are validated against the declared discipline — Font grades rejected on a sport route, French sport grades rejected on a boulder, clear error      | SATISFIED   | `utils/grades.py:validate_grade` dispatches on Discipline, raises ValueError naming "Font" or "French sport"; 31 tests in tests/test_grades.py cover the matrix. `format_climbing_activity` renders the validated fields downstream. |
| SETUP-01    | 01-01, 01-06               | README documents required custom fields (keys, types, options) before tools can write them                                                                       | SATISFIED   | README.md §"Climbing setup — required Intervals.icu custom fields" (line 75) has a 7-row table matching CUSTOM_FIELD_KEYS. Case-sensitivity and grade-scale guidance included. Referenced by `verify_custom_fields_setup` error message. |
| SETUP-02    | 01-03, 01-04, 01-05        | Verification path (diagnostic tool or self-check) reports missing custom fields by name                                                                          | SATISFIED   | `verify_custom_fields_setup` MCP tool + `_verify_custom_fields_setup_impl` helper in `tools/climbing.py`; hard-blocks with named-field errors; readback-heuristic strategy chosen per spike findings (no definitions endpoint exists). Tool-layer tests assert all-missing, some-missing, and error paths. |

Note: REQUIREMENTS.md traceability table maps SETUP-01 to Phase 5, but ROADMAP.md Phase 1 explicitly lists `Requirements: SETUP-01, SETUP-02, CLIMB-08` and Success Criterion 4 requires SETUP-01 documentation in this phase. The plans correctly implement per the ROADMAP (Phase 5 will presumably re-verify/polish). This is a pre-existing REQUIREMENTS.md inconsistency, not a phase gap; flagging for project-bookkeeping attention but not blocking goal achievement.

### Anti-Patterns Found

| File                                              | Line    | Pattern                                                                   | Severity | Impact |
| ------------------------------------------------- | ------- | ------------------------------------------------------------------------- | -------- | ------ |
| `scripts/spike_write_endpoints.py`                | ~228    | Non-error responses hard-coded to `status_code: 200` (from Review WR-01)  | Info     | Findings file conflates "non-error" with "HTTP 200"; doesn't affect goal — the `winning_endpoint` choice is based on error-vs-success, not the specific code. Documented in `01-REVIEW.md` WR-01 for future polish. |
| `src/intervals_mcp_server/tools/climbing.py`      | 84-98   | Readback-heuristic can false-positive "missing" for defined-but-unpopulated fields (Review WR-02) | Info     | Phase-accepted trade-off (acknowledged in helper docstring). Phase 2 write tools still surface ground-truth 422 errors from the live API. Documented in `01-REVIEW.md` WR-02 + plan 01-05 SUMMARY decision log. |
| `scripts/spike_write_endpoints.py`                | ~122    | Unconditional cleanup PUT even after errored writes (Review WR-03)        | Info     | Minimal blast radius (SPIKE_DATE is far-future, script is one-shot). Documented in `01-REVIEW.md` WR-03. |
| `src/intervals_mcp_server/utils/grades.py`        | 24      | FONT_RE accepts bare "1" / "2" (Review IN-01)                             | Info     | Defensive grade-scale completeness; documented in 01-01-SUMMARY.md rationale. Edge case, low impact. |
| `src/intervals_mcp_server/utils/formatting.py`    | 576-577 | `isinstance(rpe, (int, float))` matches `bool` (Review IN-02)             | Info     | Harmless against real Intervals.icu responses (API never returns bool for icu_rpe). |

All findings above are classified "Info" — none block the Phase 1 goal. The existing `01-REVIEW.md` (committed `a2cfe6f`) catalogs these with suggested fixes for future polish.

### Human Verification Required

1. **Confirm live-API evidence matches real-world state (Success Criteria 1 + 2)**

   **Test:** Open `.planning/phases/01-foundation-and-write-path-spike/01-SPIKE-FINDINGS.md` and cross-check against what you observed when running the spike:
   - `write_1_response` showed a 200 OK with `sleepSecs: 28800, soreness: 3`?
   - `primary_response.id` was a real activity id (`i142495224` in findings) returned from `POST /athlete/{id}/activities/manual`?
   - `upsert_semantics_confirmed: true`?
   - `delete_response` showed successful DELETE (no orphan activity remaining)?

   Additionally, log in to https://intervals.icu → Activities → date range including 2099-01-01 → confirm no orphan activity or wellness data remains at that date.

   **Expected:** Findings file matches your recollection of the spike run and the Intervals.icu web UI shows no leftover artifacts at 2099-01-01.

   **Why human:** The verifier cannot re-execute the spike (destructive against live account), cannot access the Intervals.icu web UI to confirm cleanup state, and cannot independently authenticate the findings JSON as the actual response body vs. a fabricated file. The committed artifact is well-formed and redacted, and all structural checks pass; real-world fidelity is a trust-but-verify step for the account owner.

### Gaps Summary

None. All four ROADMAP Success Criteria have concrete evidence in the codebase + committed findings. The single "human_needed" item is a recommended real-world confirmation check for the live-API evidence — it is not a code or artifact gap. If the user confirms the live run matches the committed findings and no orphan data remains at 2099-01-01, the phase is complete.

---

_Verified: 2026-04-24T12:33:08Z_
_Verifier: Claude (gsd-verifier)_
