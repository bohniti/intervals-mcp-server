# Project Research Summary

**Project:** Intervals.icu MCP Server — Climbing Training Loop Extension
**Domain:** Fitness API write layer + climbing-domain session logging and load management
**Researched:** 2026-04-24
**Confidence:** MEDIUM-HIGH

## Executive Summary

This milestone extends an existing, well-structured Python/FastMCP MCP server into a closed-loop climbing training tool. The server already handles reads (activities, wellness, events) and calendar writes; the gap is the write layer for session completion, climbing metadata enrichment, wellness logging, and a unified readiness status report. Expert practice in this domain is clear: use rpeTSS (session RPE x duration) as the load unit, store structured climbing context (discipline, grade, session focus) in Intervals.icu custom fields, and keep all data in Intervals.icu as the single source of truth. The implementation is additive — no existing tool is replaced or restructured, and zero new package dependencies are required.

The recommended approach is a clean new `tools/climbing.py` module (four MCP tools) alongside a single `write_wellness_entry` addition to the existing `tools/wellness.py`. A new `utils/grading.py` (~30 LOC) handles Font and French sport grade validation inline. The status tool aggregates CTL/ATL/TSB + wellness + recent sessions into a single structured report that Claude then interprets — the LLM provides the coaching reasoning that no static algorithm can match. This separation of data retrieval (tool job) from interpretive reasoning (Claude job) is the architectural differentiator.

The two critical risks are both addressable with small, mandatory guards: (1) activity creation is not idempotent — a check-before-POST duplicate guard is required from day one; (2) Intervals.icu custom fields silently ignore writes if the field schemas are not pre-defined in the athlete account — readback verification and a clear user-prerequisite checklist are mandatory. Both risks are fully preventable with patterns already established in the codebase.

## Key Findings

### Recommended Stack

The entire extension builds on the existing stack with no new `pyproject.toml` entries. Python 3.12+, FastMCP, httpx async, and python-dotenv are already present and sufficient. The only new code artifact is `utils/grading.py` — a ~30 LOC stdlib-only module implementing Font and French sport grade validation and ordinal ranking.

The write API surface confidence is MEDIUM for the two unexercised endpoints: `POST /athlete/{id}/activities` (create activity) and `PUT /athlete/{id}/wellness/{YYYY-MM-DD}` (wellness upsert). Both are inferred from codebase patterns and Intervals.icu API conventions; a Phase 1 spike to confirm exact required body fields is mandatory before building the full tool suite.

**Core technologies:**
- Python 3.12+ / FastMCP / httpx: entire server — already locked in by project constraints
- `make_intervals_request()`: single HTTP boundary for all new writes — existing, no changes needed
- `utils/grading.py` (NEW, no dependency): Font + French sport grade validation and ordinal ranking — no maintained PyPI library exists for these scales
- `utils/types.py` extension: `ClimbingSession` and `GradeRange` dataclasses — domain model that produces the activity PUT body
- `tools/climbing.py` (NEW): four MCP tools — dedicated module per STRUCTURE.md convention, avoids piling onto the already-complex `activities.py`

### Expected Features

The training loop is only closed when all six P1 features are present; any subset leaves an identifiable gap.

**Must have (table stakes):**
- Write RPE (`icu_rpe`, 1-10) to an existing activity — enables rpeTSS and therefore all load metrics
- Create a climbing activity from scratch — covers Timo's primary manual-entry path
- Enrich an existing Garmin-synced activity with discipline, grade, session focus — turns HR blob into meaningful record
- Mark a planned calendar event as done via linked activity creation — closes the calendar planning loop
- Write wellness entries (sleep, soreness, HRV, RHR, fatigue) — feeds readiness calculation
- Status report (CTL/ATL/TSB + last 7d wellness + recent sessions) — the single "how should I train today?" answer

**Should have (competitive differentiators):**
- Venue context (gym vs outdoor) as custom field — low-effort, aids grade calibration
- Finger condition / skin as explicit field — biggest climbing-specific readiness signal; add to v1.x after validation
- Grade-band volume aggregation in status report — enables pyramid analysis; defer until status tool proves useful

**Defer (v2+):**
- Per-problem / per-route structured tick list — requires a list-type data model; flat Intervals.icu custom fields cannot represent it cleanly
- Fingerboard / hangboard protocol tool — v1: log as bouldering + session_focus=fingerboard with notes
- Historical PR tracking — requires efficient indexing of historical custom fields; performance work needed
- Generic manual activity creation for non-climbing sports

### Architecture Approach

The new code slots into the existing layered architecture without changing any layer's contract. A new `tools/climbing.py` module registers four `@mcp.tool()` functions against the existing FastMCP singleton; `tools/wellness.py` gets one additional tool. All HTTP traffic continues through `make_intervals_request()`. The only new utils are `grading.py` (new module) and extensions to `types.py`, `validation.py`, and `formatting.py`. Build order follows the dependency graph — leaf utils first (grading, types, validation, formatting), then write tools (wellness first as simplest write-path smoke test, then climbing tools), then status tool (most complex orchestration) last.

**Major components:**
1. `tools/climbing.py` — four MCP tools: `complete_climbing_session`, `create_climbing_activity`, `enrich_activity_climbing`, `get_training_status`
2. `tools/wellness.py` + `write_wellness_entry` — one new tool extending the existing module; simple PUT write path
3. `utils/grading.py` — Font + French sport grade lists, normalisation functions, ordinal rank for comparison
4. `utils/types.py` + `ClimbingSession` / `GradeRange` — domain dataclasses; `ClimbingSession.to_dict()` produces the Intervals.icu activity PUT body
5. `utils/formatting.py` + `format_climbing_session()` / `format_training_status()` — renderers only; synthesis logic stays in the tool layer

### Critical Pitfalls

1. **Duplicate activities on retry** — `POST /athlete/{id}/activities` is not idempotent; timeout or MCP reconnect causes a second POST creating a duplicate. Prevention: mandatory GET-for-existing-activity before every POST; tool accepts `existing_activity_id` to skip creation. This guard must be in the first implementation, not added later.

2. **Custom field writes silently succeed but store nothing** — Intervals.icu returns HTTP 200 and ignores unknown field keys when custom field schemas are not defined in the athlete account. Prevention: readback verification after every custom field PUT; explicit warning in the response if fields are absent post-write; user-prerequisite checklist in README and tool docstrings.

3. **Grade system cross-contamination** — Font 6A (boulder) and French sport 6a (route) look identical in free text; writing the wrong scale makes historical trend analysis meaningless. Prevention: validate grade against declared discipline in `validate_climbing_fields()` before any API call; reject mismatches with a clear error naming the expected format.

4. **Event-to-activity timezone mismatch breaks auto-linking** — Intervals.icu matches planned events to activities by `start_date_local` and type; UTC datetime offsets can shift the date across midnight. Prevention: always write `start_date_local` as `YYYY-MM-DDT00:00:00` (no offset, user-supplied date as ground truth), matching the format used in existing `events.py`.

5. **Status report token budget blown** — naive status report returning raw API payloads for 30 days of activities consumes 10,000+ tokens, degrading LLM reasoning quality. Prevention: aggregate in the tool layer before returning; target 400-600 token output; fetch only what is needed (7-14 day wellness window, 10 recent activities, current fitness values).

## Implications for Roadmap

### Phase 1: Foundation and Write-Path Spike

**Rationale:** Two write endpoints (`POST /athlete/{id}/activities`, `PUT /athlete/{id}/wellness/{date}`) have only MEDIUM confidence — exact required fields are unverified. Validating them early eliminates the biggest technical risk before any tool is fully built. Simultaneously, the utility layer (grading, types, validation, formatting) must exist before tools can be written and tested.

**Delivers:** Confirmed API write-path knowledge; `utils/grading.py` with full Font + French sport validation; `ClimbingSession` and `GradeRange` dataclasses; `validate_climbing_fields()`; formatter stubs; test infrastructure (`test_grading.py`) in place.

**Addresses:** Grade validation (Pitfall 3), utility layer for all tools, API endpoint confidence gap.

**Avoids:** Pitfall 3 (grade ambiguity), Pitfall 12 (regressing shared utilities by extending without snapshots), Pitfall 14 (test discovery wiring).

### Phase 2: Wellness Write and Activity Enrichment

**Rationale:** `write_wellness_entry` is the simplest write tool — one PUT, existing validators, no domain-specific logic beyond field filtering. It smoke-tests the write path through `make_intervals_request()` before more complex climbing tools are built. Activity enrichment (`enrich_activity_climbing`) is the second simplest write — a single PUT on an existing activity ID using `ClimbingSession.to_dict()`.

**Delivers:** `write_wellness_entry` tool in `wellness.py`; `enrich_activity_climbing` tool in `climbing.py`; readback verification logic; `override_grade` guard on second enrichment call; `verify_custom_fields_setup` helper.

**Addresses:** Write wellness entries (P1), enrich Garmin-synced activity (P1), RPE write (P1 via enrichment).

**Avoids:** Pitfall 2 (silent custom field write failure), Pitfall 10 (retroactive grade overwrite — override guard), Pitfall 4 (timezone format — validated here).

### Phase 3: Activity Creation and Session Completion

**Rationale:** Creating activities from scratch introduces the POST idempotency problem and the two-call pattern (POST + PUT). Building on the working enrichment code from Phase 2 means the PUT half is already tested; only the creation + duplicate-guard logic is new. `complete_climbing_session` adds the event-linking dimension on top.

**Delivers:** `create_climbing_activity` tool (POST + PUT, duplicate guard); `complete_climbing_session` tool (POST + PUT with event auto-linking); integration tests covering duplicate creation scenario and `start_date_local` format matching event format.

**Addresses:** Create climbing activity from scratch (P1), mark planned event as done (P1).

**Avoids:** Pitfall 1 (duplicate activity — mandatory pre-POST GET guard), Pitfall 4 (timezone mismatch test), Pitfall 5 (MCP stateless contract), Pitfall 6 (terse docstrings — enumerate fields Claude must gather before calling).

### Phase 4: Training Status Report

**Rationale:** The status tool is the most complex orchestration — three sequential API reads, synthesis logic, and a strict token budget. It depends on all prior phases being stable (wellness data written, activities with RPE, formatting utilities complete). Deferring it last ensures the data it reads is actually populated by the completed tools.

**Delivers:** `get_training_status` tool; three-endpoint sequential fetch (fitness, wellness, activities); synthesis logic in tool layer (not formatter); RPE data-quality flag (warns if >30% of recent activities lack RPE); rolling-window averaging for subjective wellness scores; `format_training_status()` rendering to ~400-600 token output.

**Addresses:** Status report (P1), CTL/ATL/TSB + wellness + session summary in one call.

**Avoids:** Pitfall 7 (huge JSON — token budget enforcement), Pitfall 8 (CTL/ATL without load context — RPE data-quality warning), Pitfall 9 (over-interpreting single wellness score — rolling average required).

### Phase 5: Server Wiring and Acceptance

**Rationale:** Separating wiring and end-to-end acceptance from implementation prevents tools that pass unit tests but fail to register in the live MCP server, or regressions in existing tools discovered only at ship time.

**Delivers:** `server.py` import for `tools/climbing`; updated README with custom field setup checklist; MCP server restart + tool-list verification; full regression test pass on existing tools; smoke test of all new tools via Claude Desktop.

**Addresses:** User-prerequisite documentation, Pitfall 13 (MCP restart assumption), Pitfall 12 (regression in existing tool signatures).

### Phase Ordering Rationale

- Utility layer precedes all tools because every tool depends on `grading.py`, `types.py`, and `validation.py`; building them first means tools can be written against real formatter output from the start
- Wellness write before activity creation because it validates the PUT path with minimal complexity — if `make_intervals_request()` has a write issue, it surfaces on a 1-call tool before a 2-call tool
- Enrichment before creation because enrichment is a pure PUT on a known ID; creation adds POST + duplicate guard on top; shared `ClimbingSession.to_dict()` logic is exercised by enrichment first
- Status tool last because it reads the data the other tools write; running it earlier would test against empty or stale data
- API spike is Phase 1 because any undiscovered incompatibility in the create-activity or write-wellness endpoint shapes would invalidate the tool designs if discovered later

### Research Flags

Phases needing deeper research during planning:
- **Phase 1 (API spike):** `POST /athlete/{id}/activities` required fields and exact response shape; `PUT /athlete/{id}/wellness/{date}` upsert vs replace semantics — MEDIUM confidence only, must be confirmed before tool implementation. The spike itself is the research.
- **Phase 3:** Intervals.icu event-to-activity auto-matching exact criteria (date + type only, or additional fields?) — LOW-MEDIUM confidence. If matching requires more than date and `WeightTraining` type, `complete_climbing_session` design is affected.

Phases with standard patterns (skip research-phase):
- **Phase 2:** Activity enrichment via `PUT /activity/{id}` — HIGH confidence from existing `add_or_update_event` pattern
- **Phase 4:** Status report fetch patterns — GET endpoints are already HIGH confidence (existing tools); synthesis and formatting are internal logic
- **Phase 5:** Server wiring — established pattern, zero uncertainty

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technology decisions locked by project constraints; no new packages; grade library research is the only soft point but the inline decision is clearly correct |
| Features | MEDIUM | Domain knowledge is well-grounded (rpeTSS math, coaching readiness model, grade systems); competitor app feature tables not live-verified — treat as directionally correct, not authoritative |
| Architecture | HIGH | Based on direct codebase analysis; module boundaries follow documented patterns; all decisions traceable to STRUCTURE.md, CONVENTIONS.md, CONCERNS.md |
| Pitfalls | HIGH | Sourced from direct codebase read + documented constraints; most pitfalls confirmed by existing code evidence (idempotency, silent custom field failure, timezone format) not speculation |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Activity create endpoint body shape:** `POST /athlete/{id}/activities` required fields (particularly whether `type`, `moving_time`, and `elapsed_time` are all required or just `type` + `start_date_local`) must be confirmed in a Phase 1 spike before building `create_climbing_activity`. Incorrect assumptions here will cause 422 errors at runtime.
- **Wellness PUT upsert semantics:** Does the wellness PUT merge with existing fields, or replace the whole entry? If replace, sending only the fields the user mentioned will silently clear fields already logged for the day (e.g., HRV logged by a wearable). Null-value handling (Pitfall integration table) must be confirmed: omit absent keys vs send null.
- **Event-to-activity auto-match criteria:** Exact matching logic (date only? date + sport type? distance threshold?) is inferred, not confirmed. If matching requires more than date + `WeightTraining` type, `complete_climbing_session` may need a different activity type or additional fields.
- **`WeightTraining` as climbing activity type:** The closest available type for climbing is inferred as `"WeightTraining"` or `"Other"` — there is no native `"Climbing"` type. Whether `"WeightTraining"` activities receive rpeTSS treatment identically to other types needs confirmation.

## Sources

### Primary (HIGH confidence)
- `src/intervals_mcp_server/` — full codebase direct read; confirmed write patterns, field names, error handling conventions
- `.planning/codebase/ARCHITECTURE.md`, `STRUCTURE.md`, `CONVENTIONS.md`, `CONCERNS.md` — confirmed module boundaries, complexity waivers, shared utility patterns
- `.planning/PROJECT.md` — confirmed constraints, key decisions, stated user prerequisites
- `tests/ressources/wellness_entry.json` — confirmed wellness field names, scale units, nullable fields

### Secondary (MEDIUM confidence)
- Intervals.icu REST API conventions inferred from existing tool patterns (POST/PUT shapes, partial update semantics)
- Lattice Training methodology, Steve Bechtel "Logical Progression", Eva Lopez finger research — climbing load model and readiness coach frameworks
- Crimpd / 8a.nu / Lattice app feature sets — training knowledge, not live-verified

### Tertiary (LOW confidence)
- Intervals.icu activity type string for climbing (`"WeightTraining"` vs `"Other"`) — inferred, needs Phase 1 spike confirmation
- `POST /athlete/{id}/activities` required body fields — inferred from API conventions, not confirmed
- Event-to-activity auto-match criteria — inferred from Intervals.icu documentation patterns, not directly tested

---
*Research completed: 2026-04-24*
*Ready for roadmap: yes*
