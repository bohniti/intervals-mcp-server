# Roadmap: Intervals.icu MCP — Climbing Training Loop

## Overview

Five phases take an existing read-heavy MCP server to a closed-loop climbing training tool. Phase 1 eliminates API uncertainty and builds the utility layer everything else depends on. Phases 2–3 deliver the write tools in dependency order (wellness write and enrichment before activity creation, which requires a duplicate guard built on top). Phase 4 adds the status report that aggregates what the write tools produce. Phase 5 wires everything into the live server, validates no regressions, and ships the user-prerequisite documentation.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation and Write-Path Spike** - Confirm unverified API endpoints and build the utility layer (grading, types, validation, formatting stubs) that all tools depend on
- [ ] **Phase 2: Wellness Write and Activity Enrichment** - Deliver the wellness write tool and the activity enrichment tool; smoke-test the full write path through make_intervals_request()
- [ ] **Phase 3: Activity Creation and Session Completion** - Deliver create-from-scratch and complete-planned-session tools with duplicate guard and event-linking logic
- [ ] **Phase 4: Training Status Report** - Deliver the single-call status tool that blends CTL/ATL/TSB, wellness signals, and RPE data quality into a ~400-600 token report
- [ ] **Phase 5: Server Wiring and Acceptance** - Wire all new tools into server.py, ship prerequisite documentation, run regression suite against existing tools

## Phase Details

### Phase 1: Foundation and Write-Path Spike
**Goal**: The two unverified write endpoints are confirmed working and the shared utility layer is in place so every subsequent tool can be built against real API contracts and real formatter output
**Depends on**: Nothing (first phase)
**Requirements**: SETUP-01, SETUP-02, CLIMB-08
**Success Criteria** (what must be TRUE):
  1. A real PUT to `/athlete/{id}/wellness/{date}` succeeds with a minimal body; upsert vs replace semantics are documented from the live response
  2. A real POST to `/athlete/{id}/activities` returns an activity id; the minimum required body fields are documented from the live response
  3. `utils/grades.py` rejects a Font grade on a sport-route discipline and a French-sport grade on a boulder discipline with an error message naming the expected scale
  4. The required custom-field definitions are documented (field names, types, options) in README and a `verify_custom_fields_setup` helper can report whether they exist in the athlete account
**Plans**: 6 plans
**Plan list**:
- [x] 01-01-PLAN.md — Climbing utilities (Discipline/SessionFocus enums, FieldSpec, CUSTOM_FIELD_KEYS, validate_grade, utility tests)
- [x] 01-02-PLAN.md — Formatter extension (format_climbing_activity appended to utils/formatting.py)
- [x] 01-03-PLAN.md — Spike script creation (scripts/spike_write_endpoints.py — live API probe)
- [x] 01-04-PLAN.md — Run spike against live API + capture findings (checkpoint, manual cleanup)
- [x] 01-05-PLAN.md — verify_custom_fields_setup tool + server wiring + tool-layer tests
- [x] 01-06-PLAN.md — README "Climbing setup" section (SETUP-01 docs)
**UI hint**: no

### Phase 2: Wellness Write and Activity Enrichment
**Goal**: Users can log wellness data conversationally and enrich a Garmin-synced activity with climbing metadata and RPE
**Depends on**: Phase 1
**Requirements**: WELL-01, WELL-02, WELL-03, CLIMB-03, CLIMB-04, CLIMB-05, CLIMB-06, CLIMB-07, CLIMB-10
**Success Criteria** (what must be TRUE):
  1. User can call `write_wellness_entry` with any subset of sleep, soreness, HRV, RHR, fatigue, motivation, stress fields; fields not supplied do not overwrite values already present for that day
  2. User can call `enrich_activity_climbing` with an existing activity ID and climbing fields (discipline, grade, session focus, RPE); the native `icu_rpe` field is confirmed written by reading the activity back
  3. If the required custom field schemas are absent from the athlete account, the enrichment tool returns a named error listing the missing fields rather than silently succeeding
  4. A Font grade is rejected on a sport-route activity and a French-sport grade is rejected on a boulder activity with a clear error before any API call is made
**Plans**: 5 plans
**Plan list**:
- [x] 02-01-PLAN.md — Phase 2 second-probe spike (resolves D-01a/b/c, locks PUT body shape, wellness ranges, icu_rpe path) — non-autonomous (D-05 review gate)
- [x] 02-02-PLAN.md — utils/wellness.py module (WELLNESS_RANGES, build_wellness_put_body, sleep_hours_to_secs) + test_wellness_write.py scaffolding
- [x] 02-03-PLAN.md — write_wellness_entry MCP tool (additive in tools/wellness.py) + WELL-01/02/03 unit tests
- [x] 02-04-PLAN.md — enrich_activity_climbing MCP tool (additive in tools/climbing.py) + CLIMB-03..07 / CLIMB-10 unit tests
- [x] 02-05-PLAN.md — format_climbing_activity post-enrichment regression tests + scripts/smoke_phase2.py end-to-end live test (D-25)
**UI hint**: no

### Phase 3: Activity Creation and Session Completion
**Goal**: Users can create a climbing activity from scratch and mark a planned calendar event as done, both with duplicate protection
**Depends on**: Phase 2
**Requirements**: CLIMB-01, CLIMB-02, CLIMB-09
**Success Criteria** (what must be TRUE):
  1. User can call `create_climbing_activity` with date, duration, title, and optional climbing fields; the tool first checks for an existing activity on that date/type and returns a warning instead of creating a duplicate
  2. User can call `complete_climbing_session` referencing a planned calendar event; the tool creates a linked activity with `start_date_local` matching the event date, leaving the planned event intact on the calendar
  3. Calling `create_climbing_activity` a second time for the same date (simulating MCP reconnect or LLM retry) surfaces the existing activity and does not create a second record in Intervals.icu
**Plans**: 3 plans
**Plan list**:
- [x] 03-01-PLAN.md — Refactor enrich_activity_climbing body into private _enrich_impl(_skip_conflict_scan=False) helper; preserve Phase 2 public behavior verbatim (Wave 1)
- [x] 03-02-PLAN.md — create_climbing_activity MCP tool (additive in tools/climbing.py) + tests/test_climbing_create.py with CLIMB-02 / CLIMB-09 / Pitfall #4 coverage (Wave 2)
- [x] 03-03-PLAN.md — complete_climbing_session MCP tool (event GET → POST with explicit paired_event_id → readback verifies link) + 6 added tests covering CLIMB-01 / CLIMB-09 (Wave 3 — depends on Plan 02 to avoid same-wave file overlap)
**UI hint**: no

### Phase 4: Training Status Report
**Goal**: Users can ask "how should I train today?" and receive a single sub-600-token report blending CTL/ATL/TSB, recent wellness signals, and an RPE data-quality flag
**Depends on**: Phase 3
**Requirements**: STAT-01, STAT-02, STAT-03, STAT-04
**Success Criteria** (what must be TRUE):
  1. `get_training_status` returns a single string report covering today's readiness (TSB), weekly load review (CTL/ATL trend), and a long-term trend summary in one tool call
  2. The report incorporates recent sleep, soreness, fatigue, HRV/RHR from the last 7 days of wellness entries alongside the fitness metrics
  3. When more than 30% of activities in the recent window lack `icu_rpe`, the report includes an explicit data-quality warning naming it as a reason the readiness signal may be noisy
  4. The formatted report is 400–600 tokens (verified by token count) so the LLM retains headroom to reason on top of the data
**Plans**: 3 plans
**Plan list**:
- [x] 04-01-PLAN.md — utils/status.py: TSB_BANDS constants + window/RPE constants + tsb_band + compute_rpe_coverage + format_today_section / format_weekly_section / format_longterm_section / format_status_report (pure leaf module)
- [x] 04-02-PLAN.md — tools/status.py: get_training_status MCP tool (two GETs, walk-back, RPE flag) + server.py wiring
- [x] 04-03-PLAN.md — tests/test_status.py: utils unit tests + tool integration tests + tiktoken token-budget tests (STAT-04) + pyproject.toml dev-extras update
**UI hint**: no

### Phase 5: Server Wiring and Acceptance
**Goal**: All new tools are reachable from Claude Desktop, the user can set up required custom fields without guessing, and existing tools have not regressed
**Depends on**: Phase 4
**Requirements**: SETUP-01, SETUP-02
**Success Criteria** (what must be TRUE):
  1. After `server.py` is updated and the MCP server is restarted, `tools/list` in Claude Desktop shows all new tool names (`write_wellness_entry`, `enrich_activity_climbing`, `create_climbing_activity`, `complete_climbing_session`, `get_training_status`)
  2. The README or dedicated setup doc lists every required Intervals.icu custom field by `fieldName`, type, and valid options so the user can create them in the athlete settings UI without opening source code
  3. The full existing test suite passes without modification, confirming no regressions in activity, event, wellness (read), and custom-items tools
  4. A smoke test of each new tool via Claude Desktop produces a non-error response against the live Intervals.icu account
**Plans**: 5 plans
**Plan list**:
- [ ] 05-01-PLAN.md — server.py wiring: explicit named imports + __all__ entries for the four new tools + docstring refresh (D-01/D-02)
- [ ] 05-02-PLAN.md — README refresh: intro paragraph (D-04) + new `## Climbing tools` section with five subsections (D-03)
- [ ] 05-03-PLAN.md — tests/test_server_registration.py: structural drift gate asserting every milestone tool is registered with FastMCP (D-06/D-08)
- [ ] 05-04-PLAN.md — scripts/smoke_phase5.py + 05-LIVE-SMOKE.md checklist + 05-SMOKE-FINDINGS.md skeleton (D-09/D-10/D-11)
- [ ] 05-05-PLAN.md — Acceptance gate (Wave 2, non-autonomous): pytest + live smoke run + Claude Desktop checklist drive — confirms SC-1..SC-4
**UI hint**: no

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation and Write-Path Spike | 0/TBD | Not started | - |
| 2. Wellness Write and Activity Enrichment | 0/TBD | Not started | - |
| 3. Activity Creation and Session Completion | 0/TBD | Not started | - |
| 4. Training Status Report | 0/TBD | Not started | - |
| 5. Server Wiring and Acceptance | 0/TBD | Not started | - |
