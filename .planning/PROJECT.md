# Intervals.icu MCP Server — Climbing Training Loop

## What This Is

An MCP (Model Context Protocol) server that exposes the Intervals.icu API as tools Claude and other LLMs can call. Current scope reads activities, wellness, events, and custom items, and creates/updates/deletes planned calendar events. This milestone extends it into a **climbing-aware training loop**: Timo (a climber who tracks workouts manually) can close the loop on planned sessions, create or enrich climbing activities with discipline/grades/RPE, log subjective wellness conversationally, and get a single status report that tells him how hard to train next.

## Core Value

Finish a climbing session → tell Claude → in one short conversation a complete activity (metadata + RPE) lands on Intervals.icu, and you can ask "how should I train tomorrow?" and get a data-backed answer that blends training load with wellness.

## Requirements

### Validated

<!-- Existing capabilities inferred from the codebase (pre-GSD baseline). -->

- ✓ Read activities, activity details, intervals, streams, and messages from Intervals.icu — existing (`src/intervals_mcp_server/tools/activities.py`)
- ✓ Post messages / comments on activities — existing (`add_activity_message`)
- ✓ Read calendar events (single, by range) — existing (`src/intervals_mcp_server/tools/events.py`)
- ✓ Create / update / delete planned calendar events (workouts on the calendar) — existing (`add_or_update_event`, `delete_event`, `delete_events_by_date_range`)
- ✓ Read wellness entries (sleep, soreness, HRV, fatigue, etc.) — existing (`src/intervals_mcp_server/tools/wellness.py`)
- ✓ Read custom items — existing (`src/intervals_mcp_server/tools/custom_items.py`)
- ✓ FastMCP server with stdio / SSE / streamable-http transports — existing (`src/intervals_mcp_server/server.py`, `server_setup.py`)
- ✓ Single HTTP boundary through `make_intervals_request()` with auth, retry, error mapping — existing (`src/intervals_mcp_server/api/client.py`)
- ✓ Mark a planned event as done — creates a **linked activity**; the planned event stays on the calendar — v1.0 (`complete_climbing_session` in `src/intervals_mcp_server/tools/climbing.py`)
- ✓ Create a climbing activity from scratch (fully manual entry, no watch) — v1.0 (`create_climbing_activity` in `src/intervals_mcp_server/tools/climbing.py`)
- ✓ Status tool — one report covering **today's readiness**, **weekly load review**, and **long-term trend**, fed by CTL/ATL/TSB + sleep + subjective soreness/fatigue + HRV/RHR — v1.0 (`get_training_status` in `src/intervals_mcp_server/tools/status.py`; renders ~250 tokens, well under the 600 budget)
- ✓ Enrich an existing activity (e.g., Garmin-synced) with climbing metadata + RPE — v1.0 (`enrich_activity_climbing` in `src/intervals_mcp_server/tools/climbing.py`)
- ✓ Capture structured climbing fields on completion: **discipline** (bouldering / sport lead / top-rope / trad, gym vs outdoor), **volume & grades** (sends + attempts in Font for boulders, French sport for routes), **session focus** (power / endurance / technique / projecting / mileage) — v1.0 (`utils/climbing.py` `CUSTOM_FIELD_KEYS` + `Discipline`/`SessionFocus` StrEnums; consumed by every climbing tool)
- ✓ Write RPE (1–10) to the native `icu_rpe` field on the activity — v1.0 (split-PUT pattern in `enrich_activity_climbing`; readback-verified)
- ✓ Write wellness entries conversationally (sleep, soreness, HRV, RHR, subjective metrics) — v1.0 (`write_wellness_entry` in `src/intervals_mcp_server/tools/wellness.py`; drop-None upsert, readback-verified)
- ✓ Diagnostic tool to verify required Intervals.icu custom-field schemas are defined in the athlete account — v1.0 (`verify_custom_fields_setup` in `src/intervals_mcp_server/tools/climbing.py`; readback-heuristic since no definitions endpoint exists)

### Active

<!-- v1.x hypotheses for the next milestone. Defined during /gsd-new-milestone. -->

(none yet — define during `/gsd-new-milestone`)

### Out of Scope

<!-- Explicit boundaries. Reasons included so they don't get re-added without discussion. -->

- Multi-athlete support — Timo is the only athlete; designing for coach-multi-athlete would force authz and data-scoping work for zero user benefit
- Generic manual activities (logging any sport, not just climbing) — deferred to v2 milestone; climbing-first keeps v1 scope tight and lets the tool shape settle against real use before generalizing
- Coaching / plan generation (auto-suggesting workouts, prescribing training) — deferred to v2 milestone; v1 status tool reports state only, Claude (the LLM) does any coaching-style reasoning on top
- Inventing a non-Intervals.icu data store — all structured climbing data lives in Intervals.icu (custom fields + native fields), nothing shadow-stored locally

## Current State

**Shipped:** v1.0 Climbing Training Loop on 2026-04-30 — closed the climbing loop with 5 phases / 22 plans / 19/19 v1 requirements.

**Codebase now:** 5,030 LOC source + 4,399 LOC tests (197 passing, 7 xfail snake_case-shape locks documented as test-debt). New modules: `tools/climbing.py`, `tools/status.py`, `utils/climbing.py`, `utils/grades.py`, `utils/wellness.py`, `utils/status.py`. New tools registered with FastMCP: `verify_custom_fields_setup`, `enrich_activity_climbing`, `create_climbing_activity`, `complete_climbing_session`, `write_wellness_entry`, `get_training_status`.

**Operator setup:** README "Climbing setup" section documents the 7 required custom fields; `verify_custom_fields_setup` reports any missing fields by name; live smoke at `scripts/smoke_phase5.py`.

**Next milestone goals:** TBD — define via `/gsd-new-milestone`. Candidates from the v2 backlog in the archived requirements: finger/skin condition wellness field, venue context, grade-band volume aggregation in status report, generic non-climbing manual activities, lightweight coaching suggestions.

## Context

**Product:** A single-user MCP server bridging Claude and Intervals.icu. v1.0 closed the loop: completion, climbing-aware activity creation/enrichment, wellness writes, and the single-call training-status report.

**User:** Timo — climber. Primary sport is climbing (bouldering + sport). Tracks sessions manually most of the time; occasionally via Garmin. Uses Font grading for boulders and French sport grading for routes.

**Technical environment (from codebase map):**
- Python 3.12+, FastMCP, httpx async client, python-dotenv
- Existing layering is clean: `mcp_instance.py` holds the singleton FastMCP; tools decorate against it; all HTTP goes through `make_intervals_request()`; utilities are leaf deps
- Tools are grouped by domain (`activities.py`, `events.py`, `wellness.py`, `custom_items.py`) — new climbing tools should follow the same pattern
- See `.planning/codebase/` for full tech / architecture / structure / conventions / testing / integrations / concerns maps

**Known concerns (from `.planning/codebase/CONCERNS.md`) to weigh during planning:**
- Module size: `activities.py` and `wellness.py` are already large; new tools should not pile on — consider a dedicated climbing module
- Output formatting is prose-heavy; any new tool should follow the existing formatter conventions in `utils/formatting.py`
- Test coverage is concentrated on the HTTP client + formatters; new tool behavior needs corresponding tests

**Intervals.icu API constraints:**
- Activities and calendar events are distinct resources. Planned workouts live as events; completed work lives as activities. Intervals.icu auto-matches them by date + workout type when both exist.
- Custom fields must be **defined in the Intervals.icu account** (web UI, athlete settings) before the API can write them. The tool cannot create field schemas — it can only populate defined fields. This is a **user prerequisite**, documented up front.
- Native `icu_rpe` (1–10) is the canonical RPE field. Using it feeds intervals.icu's own load math (rpeTSS).

## Constraints

- **Tech stack:** Must stay on Python 3.12+, FastMCP, httpx async. No new frameworks. — Existing architecture is clean and the MCP/FastMCP stack is the product.
- **Single HTTP boundary:** All new Intervals.icu calls must go through `make_intervals_request()` in `src/intervals_mcp_server/api/client.py`. — Centralized auth, retry, error mapping; established pattern.
- **MCP statelessness:** Tools are single-shot request/response. No hidden conversational state in tools. The LLM gathers climbing fields and passes them as parameters. — MCP architecture fundamental; violating it would break the protocol contract.
- **No local shadow store:** Structured climbing data lives in Intervals.icu (custom fields + native fields), not in a side database. — One source of truth; keeps the server stateless and portable across machines.
- **User prerequisite:** Intervals.icu custom fields (discipline, grade-sent, grade-attempted, session-focus, etc.) must exist in the athlete's account before the tools that write them will work. — Intervals.icu API does not allow custom-field schema creation; we document the required fields.
- **Grade systems:** Font (bouldering) + French sport (routes). — Matches the user's practice; keeps the input validators tight.
- **Single-athlete:** `ATHLETE_ID` from config; no multi-tenant handling. — Out of scope per user decision.
- **Compatibility:** Existing tool signatures and behavior must not regress. New capability is additive. — Backward compatibility is cheap here (no external consumers beyond the user's Claude client) but regressions would silently break planned-event workflows already in use.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Completion creates a linked activity, planned event stays on calendar | Keeps planned-vs-actual history intact; relies on Intervals.icu's native event↔activity matching; simpler than flipping event flags | ✓ Good — v1.0 (`complete_climbing_session` sets explicit `paired_event_id` + readback-verifies link) |
| Structured climbing data → Intervals.icu custom fields (not local storage, not activity description) | Queryable, single source of truth, survives the MCP server being re-installed; trade-off is the user-setup prerequisite | ✓ Good — v1.0 (7-field `CUSTOM_FIELD_KEYS` spec; readback-verified writes) |
| RPE → native `icu_rpe` field | Feeds intervals.icu's own load math (rpeTSS); universally recognized; no redundant custom field | ✓ Good — v1.0 (split-PUT pattern: RPE first, custom fields second) |
| Climbing fields collected as optional tool parameters, not two-phase tools | Keeps MCP tools stateless; Claude conversationally gathers inputs before the single tool call | ✓ Good — v1.0 |
| Grade systems limited to Font + French sport in v1 | Matches user's actual practice; validation stays tight; V-scale/YDS can be added later without breaking anything | ✓ Good — v1.0 (strict-case regex in `utils/grades.py`) |
| Status tool = single tool returning one combined report (readiness + weekly + trend) | User asked for "all three in one report"; one tool call is simpler for the LLM than orchestrating three | ✓ Good — v1.0 (~250-token report; well under 600-token budget) |
| Wellness writes in v1, generic manual activities + coaching in v2 | User confirmed v1 interest in wellness writes; deferring generic + coaching keeps scope tractable and lets climbing patterns settle first | ✓ Good — v1.0 |
| Live API spike before Phase 2 build (Phase 1) | `POST /activities` and `PUT /wellness/{date}` body shapes were MEDIUM-confidence only; cheap probe before locking tool design | ✓ Good — v1.0 (locked endpoint to `/activities/manual`, confirmed wellness upsert, surfaced no-definitions-endpoint reality forcing readback-heuristic) |
| Custom-field verification = readback heuristic, not definitions-endpoint introspection | Phase 1 spike found no working definitions endpoint (`/custom-fields`, `/activity-fields` both 404; `/sport-settings` doesn't expose user-defined activity fields) | ✓ Good — v1.0 (`verify_custom_fields_setup` writes a probe activity, reads it back, names missing fields) |
| Drop-None upsert in wellness writes (omitted ≠ cleared) | Intervals.icu treats `null` as "clear"; supplying every field every call would clobber wearable-synced HRV. Drop-None at body-build time, not at tool layer | ✓ Good — v1.0 (`build_wellness_put_body` in `utils/wellness.py`) |
| Default-deny conflict scan in enrichment with explicit override audit | Silent overwrite of existing custom-field values is the high-blast-radius failure mode; required override flag + audit message provides paper trail | ✓ Good — v1.0 (`[enrich override] field: old→new` via `add_activity_message`) |
| Structural drift gate via FastMCP `mcp.list_tools()` introspection | Catches silent tool removal at unit-test speed without needing HTTP or live registration; `EXPECTED_TOOLS` frozenset is single source of truth | ✓ Good — v1.0 (`tests/test_server_registration.py`; 23 tools enforced) |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-30 after v1.0 milestone — climbing training loop shipped end-to-end. All 19 v1 requirements validated. Active section cleared; next milestone goals to be set via `/gsd-new-milestone`.*
