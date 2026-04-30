---
phase: 02-wellness-write-and-activity-enrichment
verified: 2026-04-25T00:00:00Z
status: human_needed
score: 4/4 must-haves verified (build-side); 1 ROADMAP success criterion deferred to live-API verification (SETUP-01)
overrides_applied: 0
human_verification:
  - test: "Run `uv run python scripts/smoke_phase2.py` against live Intervals.icu after SETUP-01 (define seven custom-field schemas in athlete UI)"
    expected: "Exit code 0; logs show 'Successfully wrote wellness entry', activity create, 'Successfully enriched activity', DELETE cleanup, wellness PUT -1 cleanup. No leftover spike data on 2099-01-01 in the web UI."
    why_human: "Live API call; not safe in CI (per D-25); requires user to have defined seven custom-field schemas in their athlete account first (SETUP-01 / spike findings disposition was UNRESOLVED-SETUP-01)"
  - test: "Confirm Phase 2 ROADMAP success criterion #2 (`enrich_activity_climbing` ... 'the native icu_rpe field is confirmed written by reading the activity back') against live API"
    expected: "After running smoke_phase2.py, the enrich step returns 'Successfully enriched...' AND the readback in the script log shows icu_rpe=6, discipline=bouldering, top_grade_sent=6A+, etc., on the throwaway activity"
    why_human: "Live API roundtrip cannot be verified in unit tests; the implementation against the working hypothesis (top-level keys via PUT /activity/{id}, split-PUT for icu_rpe) was locked from the spike but never roundtripped on a real activity because the spike returned 422 due to the SETUP-01 prerequisite, not D-05"
  - test: "After SETUP-01, optionally re-run `uv run python scripts/spike_write_endpoints_phase2.py` to upgrade `02-SPIKE-FINDINGS.md`'s 'Activity custom-field PUT shape' section from UNRESOLVED-SETUP-01 to LOCKED"
    expected: "Spike exits 0; findings file rewrites the section to LOCKED with paste-ready body; this is informational, not blocking — the working hypothesis already implemented in `enrich_activity_climbing` matches the expected LOCKED shape."
    why_human: "Live API; one-shot human-driven probe step (D-04 review gate originally blocked Plan 02-04, the user explicitly approved proceeding via working hypothesis)"
---

# Phase 02: Wellness Write and Activity Enrichment — Verification Report

**Phase Goal:** Users can log wellness data conversationally and enrich a Garmin-synced activity with climbing metadata and RPE
**Verified:** 2026-04-25
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| T1 | User can call `write_wellness_entry` with any subset of fields; unsupplied fields do not overwrite existing values (ROADMAP SC1; WELL-01/02/03 build-side) | VERIFIED | `tools/wellness.py:87-246` — 12-param tool with drop-None upsert via `build_wellness_put_body`; `tests/test_wellness_write.py` 20/20 pass; named tests for WELL-01/02/03 all green |
| T2 | User can call `enrich_activity_climbing` with activity_id + climbing fields; the tool writes them and reads them back (ROADMAP SC2 — build-side delivered; live-API roundtrip GATED on SETUP-01) | VERIFIED-WITH-CAVEAT | `tools/climbing.py:155-472` — 12-param tool with split-PUT (icu_rpe first, custom fields second), conflict-scan, override-audit, readback equality check; `tests/test_climbing_write.py` 17/17 pass against mocked HTTP. Live-API roundtrip awaits SETUP-01 (see human_verification[0]). |
| T3 | If custom-field schemas are absent, the tool returns a named error listing the missing fields (ROADMAP SC3; CLIMB-10 — readback flavour) | VERIFIED | `tools/climbing.py:306-311` calls `_verify_custom_fields_setup_impl`, returns `human_message` (which already includes `_README_POINTER`) on `not ok`; `tests/test_climbing_write.py::test_missing_custom_fields_short_circuits` and `::test_readback_custom_field_failure_includes_readme_pointer` pass |
| T4 | A Font grade on a sport route or French-sport on a boulder is rejected with a clear pre-API error naming the expected scale (ROADMAP SC4; CLIMB-04 / CLIMB-08 carry-forward) | VERIFIED | `tools/climbing.py:266-277` calls `validate_grade(grade, disc_enum)` BEFORE any HTTP; `tests/test_climbing_write.py::test_grade_discipline_mismatch_rejects_pre_api` asserts `AssertionError("HTTP must not be called")` was not triggered and error contains "French sport"; passes |

**Score:** 4/4 build-side truths verified. ROADMAP SC2's live-API portion is deferred to manual smoke verification (human_verification list above) — gated on SETUP-01.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/intervals_mcp_server/utils/wellness.py` | `WELLNESS_RANGES` (MappingProxyType, 6 entries × (1,4)), `PARAM_TO_API_FIELD` (9 entries), `sleep_hours_to_secs`, `build_wellness_put_body` | VERIFIED | All four exports present; mypy clean; ruff clean; module imports without HTTP/tool deps (leaf module) |
| `src/intervals_mcp_server/tools/wellness.py` | `write_wellness_entry @mcp.tool()` with explicit Optional params, range validation, drop-None upsert, readback verification, empty-call rejection | VERIFIED | 12-param signature; `inspect.iscoroutinefunction == True`; tool registered in MCP runtime list (verified via `mcp.list_tools()`); `get_wellness_data` body byte-identical (D-24 carry-forward) |
| `src/intervals_mcp_server/tools/climbing.py` | `enrich_activity_climbing @mcp.tool()` 12-param, conflict-scan + readback + audit + D-16 SPLIT-PUT path | VERIFIED | Marker comment `# D-16 path: SPLIT-PUT (per 02-SPIKE-FINDINGS.md)` present exactly once; `_verify_custom_fields_setup_impl`, `verify_custom_fields_setup`, `_README_POINTER` byte-identical to Phase 1 (D-24); tool registered in MCP runtime list |
| `src/intervals_mcp_server/utils/formatting.py` | `format_climbing_activity` extended docstring (Phase 2 role); body unchanged | VERIFIED | Snapshot test `test_format_climbing_activity_renders_existing_fields_unchanged` passes (byte-equal to captured baseline); 4 additional formatter tests for icu_rpe/empty/indoor=False/RPE-float all pass |
| `tests/test_wellness_write.py` | 20 tests — 9 helper full-bodied + 11 tool-layer tests | VERIFIED | 20/20 pass, 0 skipped. WELL-01 (`test_sleep_hours_converts_to_secs_and_upserts`), WELL-02 (`test_subset_upsert_does_not_overwrite_unrelated_fields`), WELL-03 (`test_out_of_range_rejects_pre_api`) all green |
| `tests/test_climbing_write.py` | 17 tests covering CLIMB-03..07, CLIMB-10 readback, override audit, type-coercion, split-PUT partial failure | VERIFIED | 17/17 pass; all named falsifiable assertions pass; `test_split_put_partial_failure_named` present (split-branch was retained per spike) |
| `tests/test_climbing.py` | 5 new formatter tests appended (CLIMB-10 formatting flavour + snapshot guard) | VERIFIED | 18/18 tests pass (13 from Phase 1 + 5 new); `test_format_climbing_activity_renders_icu_rpe` passes |
| `scripts/smoke_phase2.py` | Standalone E2E live-API smoke; writes wellness, creates activity, enriches, DELETE cleanup, wellness PUT -1 cleanup; no `def test_*`; SPIKE_DATE=2099-01-01; try/finally; redaction | VERIFIED-STATIC | File exists (196 lines); AST parses cleanly; imports `write_wellness_entry` and `enrich_activity_climbing`; SPIKE_DATE locked; `_redact()` used; try/finally cleanup wired; not collected by `pytest --collect-only` (zero `def test_*`); never executed against live API yet — that is the deferred human-verification step |
| `scripts/spike_write_endpoints_phase2.py` | Three async probes + findings writer; D-05 hard-stop wired | VERIFIED | File exists; defines all three probe functions; SETUP-01 detection refined during live run; produced canonical `02-SPIKE-FINDINGS.md` |
| `.planning/phases/02-wellness-write-and-activity-enrichment/02-SPIKE-FINDINGS.md` | Four LOCKED/UNRESOLVED sections | VERIFIED-WITH-CAVEAT | All four required sections present: wellness ranges LOCKED (1,4 × 6 fields); icu_rpe write path LOCKED (split_put_rpe_first); activity custom-field PUT shape UNRESOLVED-SETUP-01 (NOT D-05; user-acknowledged as prerequisite); manual cleanup section present |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `tools/wellness.py::write_wellness_entry` | `utils/wellness.py` | `from intervals_mcp_server.utils.wellness import WELLNESS_RANGES, build_wellness_put_body` | WIRED | Import + `body = build_wellness_put_body(candidates)` at line 197; `WELLNESS_RANGES[name]` lookup at line 174 |
| `tools/wellness.py::write_wellness_entry` | `make_intervals_request` (single HTTP boundary) | `await make_intervals_request(...)` for PUT (line 203) and GET readback (line 213) | WIRED | Two HTTP calls per successful invocation; both returns checked for `"error"` dict |
| `tools/climbing.py::enrich_activity_climbing` | `_verify_custom_fields_setup_impl` (same module) | `await _verify_custom_fields_setup_impl(athlete_id_to_use, api_key)` at line 307 | WIRED | Conditional on `custom_field_supplied` (RPE-only writes skip — D-20) |
| `tools/climbing.py::enrich_activity_climbing` | `tools/activities.py::add_activity_message` | `from intervals_mcp_server.tools.activities import add_activity_message` (line 16); `await add_activity_message(...)` at line 376 | WIRED | Audit POST fired only when `conflicts and override`; test `test_override_writes_audit_message` asserts call count == 1 with `[enrich override] field: old→new` content |
| `tools/climbing.py::enrich_activity_climbing` | `utils/grades.py::validate_grade` | `from intervals_mcp_server.utils.grades import validate_grade` (line 19); call at line 275 | WIRED | Discipline-aware grade validation pre-API |
| `tools/climbing.py::enrich_activity_climbing` | `make_intervals_request` (split PUT) | Three HTTP calls: pre-GET (conflict scan, line 316), PUT icu_rpe (line 392), PUT custom fields (line 405), post-GET readback (line 421) | WIRED | All gated on appropriate conditions; partial-failure error path covered by test |
| `scripts/smoke_phase2.py` | `tools/wellness.py::write_wellness_entry` | `from intervals_mcp_server.tools.wellness import write_wellness_entry` (line 46); call at line 100 | WIRED | Direct function call exercises full code path |
| `scripts/smoke_phase2.py` | `tools/climbing.py::enrich_activity_climbing` | `from intervals_mcp_server.tools.climbing import enrich_activity_climbing` (line 45); call at line 145 | WIRED | Direct function call after activity create |
| `server.py` (existing, untouched) | `tools/wellness` and `tools/climbing` modules | `from intervals_mcp_server.tools.wellness import get_wellness_data` (line 87); `from intervals_mcp_server.tools.climbing import verify_custom_fields_setup` (line 95) | WIRED | Module imports trigger ALL `@mcp.tool()` decorations — verified via runtime `mcp.list_tools()` shows both `write_wellness_entry` and `enrich_activity_climbing` registered. Phase 2 deliberately does not edit `server.py` (D-23) — Phase 5 owns explicit re-export work if Claude Desktop discovery requires it |

### Data-Flow Trace (Level 4)

The Phase 2 deliverables are not data-rendering UI components — they are MCP tools that transform inputs to API calls and back. Data flow at runtime is exercised by:

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `write_wellness_entry` | `body` (PUT payload) | `build_wellness_put_body(candidates)` — drop-None + name translation | Yes — only non-None supplied params reach the API; verified by `test_write_wellness_entry_unsupplied_field_dropped` and `test_subset_upsert_does_not_overwrite_unrelated_fields` | FLOWING |
| `write_wellness_entry` | `entry` (readback dict) | `make_intervals_request(...wellness, params=...)` GET response normalized from list | Yes — equality check iterates `body.items()` against `entry.get(api_name)`; mismatches surface as multi-line error (no README pointer for native fields) | FLOWING |
| `enrich_activity_climbing` | `pre` (conflict-scan dict) | GET `/activity/{id}` normalized from list/dict | Yes — used to detect conflicts before any PUT | FLOWING |
| `enrich_activity_climbing` | `supplied_pairs` (PUT bodies) | Built from non-None supplied params, mapping `rpe → icu_rpe` | Yes — split into `{"icu_rpe": rpe}` and `cf_body` (top-level keys); both reach `make_intervals_request` | FLOWING |
| `enrich_activity_climbing` | `post` (readback dict) | GET `/activity/{id}` after both PUTs | Yes — per-field equality with `_README_POINTER` appended on any custom-field mismatch | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Module import + tool symbols available | `uv run python -c "from intervals_mcp_server.tools.wellness import write_wellness_entry; from intervals_mcp_server.tools.climbing import enrich_activity_climbing; print(type(write_wellness_entry).__name__, type(enrich_activity_climbing).__name__)"` | Both import cleanly; both are coroutine functions | PASS |
| Both tools register in MCP runtime via existing server.py imports | `python -c "import intervals_mcp_server.tools.wellness, intervals_mcp_server.tools.climbing; from intervals_mcp_server.mcp_instance import mcp; import asyncio; print('write_wellness_entry' in [t.name for t in asyncio.run(mcp.list_tools())]); print('enrich_activity_climbing' in [t.name for t in asyncio.run(mcp.list_tools())])"` | Both `True` — registered tools count went from 13 (post-Phase-1) to 15 | PASS |
| Full pytest suite green (mocked HTTP) | `uv run --extra dev pytest tests/` | 128 passed, 0 failed, 0 skipped | PASS |
| All WELL-01/02/03 + alignment + tool-registered named tests pass | `uv run --extra dev pytest tests/test_wellness_write.py::test_sleep_hours_converts_to_secs_and_upserts tests/test_wellness_write.py::test_subset_upsert_does_not_overwrite_unrelated_fields tests/test_wellness_write.py::test_out_of_range_rejects_pre_api tests/test_wellness_write.py::test_signature_aligns_with_wellness_ranges tests/test_wellness_write.py::test_wellness_tool_registered -x` | 5 passed in 0.55s | PASS |
| All CLIMB-03..07 + CLIMB-10 readback named tests pass | `uv run --extra dev pytest tests/test_climbing_write.py::test_enrich_writes_custom_fields ::test_grade_discipline_mismatch_rejects_pre_api ::test_missing_custom_fields_short_circuits ::test_default_deny_re_enrichment ::test_override_writes_audit_message ::test_icu_rpe_writes_and_reads_back ::test_icu_rpe_readback_mismatch_errors ::test_readback_custom_field_failure_includes_readme_pointer -x` | 8 passed in 0.54s | PASS |
| CLIMB-10 formatting-flavour test passes | `uv run --extra dev pytest tests/test_climbing.py::test_format_climbing_activity_renders_icu_rpe -x` | 1 passed in 0.02s | PASS |
| Smoke script not collected as pytest test (D-25 / Pitfall #14) | `uv run --extra dev pytest --collect-only scripts/smoke_phase2.py` and `uv run --extra dev pytest --collect-only` (count) | scripts/smoke_phase2.py: "no tests collected"; full repo: "128 tests collected" — all from `tests/` dir | PASS |
| Ruff and mypy clean on all Phase 2 files | `uv run --extra dev ruff check src/.../wellness.py src/.../climbing.py utils/wellness.py tests/test_wellness_write.py tests/test_climbing_write.py scripts/smoke_phase2.py && uv run --extra dev mypy src/.../wellness.py src/.../climbing.py utils/wellness.py` | "All checks passed!" + "Success: no issues found in 3 source files" | PASS |
| Smoke script runs against live API (E2E SC2 verification) | `uv run python scripts/smoke_phase2.py` | NOT RUN — requires SETUP-01 prerequisite; deferred to human verification | SKIP |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| WELL-01 | 02-02, 02-03 | Log subjective wellness fields (sleep hours, sleep quality, soreness, fatigue, motivation, stress) in one tool call | SATISFIED | `write_wellness_entry` 12-param signature; named test `test_sleep_hours_converts_to_secs_and_upserts` passes |
| WELL-02 | 02-02, 02-03 | Log objective wellness (HRV, resting HR) in same tool call | SATISFIED | `hrv` and `resting_hr` params present; subset-upsert test `test_subset_upsert_does_not_overwrite_unrelated_fields` passes |
| WELL-03 | 02-02, 02-03 | Upsert semantics — unsupplied fields do not clobber existing values | SATISFIED | `build_wellness_put_body` drops None entries; named test `test_out_of_range_rejects_pre_api` passes; `test_write_wellness_entry_unsupplied_field_dropped` passes |
| CLIMB-03 | 02-04 | Enrich existing activity by activity_id with climbing metadata + RPE | SATISFIED (build-side) / NEEDS HUMAN (live-API roundtrip) | `enrich_activity_climbing` exists; `test_enrich_writes_custom_fields` passes; live-API confirmation requires SETUP-01 + smoke script |
| CLIMB-04 | 02-04 | Discipline parameter accepted (bouldering / sport_lead / top_rope / trad + indoor) | SATISFIED | `discipline` and `indoor` params present; `test_grade_discipline_mismatch_rejects_pre_api` passes (uses `validate_grade`) |
| CLIMB-05 | 02-04 | Volume + grades — sends and attempts; Font for boulders, French sport for routes | SATISFIED | `top_grade_sent`, `top_grade_attempted`, `sends`, `attempts` params present; `validate_grade` enforces scale-discipline coupling |
| CLIMB-06 | 02-04 | Session focus parameter accepted | SATISFIED | `session_focus` param present; `SessionFocus` enum check at line 280-287; `test_enrich_rejects_unknown_session_focus` passes |
| CLIMB-07 | 02-04 | RPE 1-10 written to native `icu_rpe` | SATISFIED (build-side) / NEEDS HUMAN (live roundtrip) | `rpe` param + `1 <= rpe <= 10` check; split-PUT writes `{"icu_rpe": rpe}` to `/activity/{id}`; `test_icu_rpe_writes_and_reads_back` and `test_icu_rpe_readback_mismatch_errors` pass against mocked HTTP. Live-API confirmation per ROADMAP SC2 awaits SETUP-01. |
| CLIMB-10 | 02-04 (readback), 02-05 (formatting) | Custom-field writes are read-back-verified — clear error if schema missing | SATISFIED (build-side) / NEEDS HUMAN (live silent-ignore detection) | `_verify_custom_fields_setup_impl` runs pre-PUT when custom fields supplied; readback-failure path appends `_README_POINTER`; `test_missing_custom_fields_short_circuits`, `test_readback_custom_field_failure_includes_readme_pointer`, and `test_format_climbing_activity_renders_icu_rpe` all pass |

**Orphaned requirements check:** REQUIREMENTS.md maps WELL-01, WELL-02, WELL-03, CLIMB-03, CLIMB-04, CLIMB-05, CLIMB-06, CLIMB-07, CLIMB-10 to Phase 2. All nine appear in plan frontmatter (`requirements: [...]`) for plans 02-02, 02-03, 02-04, 02-05. No orphans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/intervals_mcp_server/tools/climbing.py` | 175 | "(Phase 3, not yet implemented)" — docstring mentions `create_climbing_activity` is a future tool | Info | Benign — this is LLM guidance text inside `enrich_activity_climbing`'s docstring, not a stub. The implementation itself is complete. |
| `scripts/smoke_phase2.py` | 59 | "placeholder for logged output" — comment in `_redact()` helper docstring | Info | Benign — describes the redaction-placeholder string `{athlete_id}`, not an unimplemented stub. |

No blocker-level anti-patterns. No `pytest.skip()` calls in tool tests (all Wave-0 stubs filled in 02-03 / 02-04). No `raise NotImplementedError`. No `return None` placeholders. No `httpx` imports outside `api/client.py` (single-HTTP-boundary constraint upheld).

### Human Verification Required

Three items deferred to live-API verification (acknowledged context: SETUP-01 prerequisite was not met when the spike ran; the user explicitly approved proceeding with the working hypothesis for the activity custom-field PUT body shape):

1. **Run `uv run python scripts/smoke_phase2.py` after SETUP-01.** This is the canonical E2E test for ROADMAP SC2 ("the native `icu_rpe` field is confirmed written by reading the activity back"). Expected: exit 0, all three steps log "Successfully", DELETE cleanup runs, wellness PUT -1 cleanup runs. The runtime guard `verify_custom_fields_setup` (Phase 1) protects production users from this same prerequisite.

2. **Confirm icu_rpe + custom-field roundtrip on a real activity.** Same smoke run as #1 — expected to surface the readback dict in logs containing `icu_rpe=6, discipline="bouldering", top_grade_sent="6A+", top_grade_attempted="7A", sends=4, attempts=7, indoor=True, session_focus="power"`. If any of these fail to roundtrip, the tool returns a `did not roundtrip` error (with `_README_POINTER` for custom fields) — that is also acceptable evidence that the readback-failure path works as designed.

3. **(Optional, informational) Re-run `uv run python scripts/spike_write_endpoints_phase2.py` after SETUP-01.** Upgrades `02-SPIKE-FINDINGS.md`'s "Activity custom-field PUT shape" section from UNRESOLVED-SETUP-01 to LOCKED. The working hypothesis already implemented in `enrich_activity_climbing` (top-level keys via `PUT /activity/{id}`) should match the LOCKED shape. This is not a blocker for the build-side verification; it just closes the documentation loop.

### Gaps Summary

There are NO build-side gaps. All four ROADMAP success criteria for Phase 2 have their build-side implementation complete and tested with mocked HTTP:

- SC1 (`write_wellness_entry` upsert with subset of fields): VERIFIED — 20/20 tests pass, including the named WELL-01/02/03 falsifiable assertions.
- SC2 (`enrich_activity_climbing` + readback): build-side VERIFIED — 17/17 tests pass; live-API roundtrip portion is the human-verification item, deferred to SETUP-01.
- SC3 (missing custom-field schemas → named error): VERIFIED — guard fires pre-PUT, error includes README pointer; `test_missing_custom_fields_short_circuits` passes.
- SC4 (Font-on-route / French-on-boulder rejected pre-API): VERIFIED — `validate_grade` runs before any HTTP; `test_grade_discipline_mismatch_rejects_pre_api` enforces no HTTP call.

The single open item is the live-API smoke confirmation, gated on a documented user prerequisite (SETUP-01 — define the seven custom-field schemas in the Intervals.icu UI). Per the user-supplied verification context, this gating is BY DESIGN: the spike correctly diagnosed the 422 as SETUP-01 (not D-05), the user approved proceeding via working hypothesis, and the runtime guard `verify_custom_fields_setup` protects production users from the same prerequisite. Status is `human_needed` because Step 8 of the verification protocol explicitly classifies "external service integration" / "real-time behavior" as always requiring human verification — even though all programmatic checks pass.

Code review (`02-REVIEW.md`) flagged 4 warnings (correctness/quality concerns around override-audit-vs-partial-failure timing, TOCTOU window between conflict-scan and PUT, etc.) and 5 info items. None are blockers and none invalidate the goal achievement; the orchestrator is free to surface them as Phase 3+ refinements.

---

*Verified: 2026-04-25*
*Verifier: Claude (gsd-verifier)*
