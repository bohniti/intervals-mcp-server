# Phase 5: Server Wiring and Acceptance - Context

**Gathered:** 2026-04-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Wrap up the climbing-training-loop milestone: tighten the `server.py` wiring so every Phase 1–4 tool is named and re-exported (not just side-effect-registered), refresh the README so a fresh user understands the new tool surface, prove no regressions structurally (registration assertion test) and behaviorally (existing pytest suite), and exercise each new tool live against Intervals.icu via both an automated script and a Claude Desktop checklist. No new tool surface, no new HTTP, no new behavior.

**In scope for this phase:**
- `server.py` — add 4 named imports (`write_wellness_entry`, `enrich_activity_climbing`, `create_climbing_activity`, `complete_climbing_session`) and 4 `__all__` entries; refresh the module docstring "MCP tools provided" list to include all 6 climbing/wellness/status tools.
- `README.md` — refresh the introduction paragraph to mention climbing session completion, wellness writes, and the status report; add a "Climbing tools" section under the existing "Climbing setup" with one short (~5 line) subsection per new tool: what it does + example invocation. Five subsections (verify is already documented in Phase 1).
- `tests/test_server_registration.py` — new test file: import `server`, query the FastMCP instance for registered tools, assert the full expected name set is present.
- `scripts/smoke_phase5.py` — new automated live-API smoke script exercising every new tool via `make_intervals_request()`. Far-future date (2099-01-01); DELETE cleanup for created activities; far-future wellness entry left in place (zero training impact); status is read-only.
- `.planning/phases/05-server-wiring-and-acceptance/05-LIVE-SMOKE.md` — manual checklist for Claude Desktop side: one row per new tool, "asked Claude to run X, got non-error response" — proves the tools/list visibility independently of the registration test.
- `.planning/phases/05-server-wiring-and-acceptance/05-SMOKE-FINDINGS.md` (or equivalent in the smoke script's output) — captures any surprises from the live run.

**Out of scope (belongs elsewhere):**
- Any new tool, parameter, or behavior — milestone is locked at the Phase 1–4 surface.
- v2 work (`GEN-v2-01`, `COACH-v2-01`, `CLIMB-v2-01..03`) — explicitly deferred per `PROJECT.md` Out of Scope.
- Milestone-completion ceremony (`/gsd-complete-milestone`, archive, version bump) — that's the next workflow step after Phase 5 verifies, not this phase's responsibility.
- Re-running Phase 2/3 spikes — Phase 5 trusts what those spikes confirmed.
- Test rewrites or refactors of existing test files — Phase 5 is additive only (Pitfall #12 carry-forward).

</domain>

<decisions>
## Implementation Decisions

### Server.py wiring
- **D-01:** **Explicit named imports + `__all__` entries for every new tool.** Add `write_wellness_entry` to the `from intervals_mcp_server.tools.wellness import ...` line (currently imports only `get_wellness_data`). Add `enrich_activity_climbing`, `create_climbing_activity`, `complete_climbing_session` to the `from intervals_mcp_server.tools.climbing import ...` line (currently imports only `verify_custom_fields_setup`). Add all four names to the `__all__` list. Mirrors the existing pattern (activities, events, custom_items all have full named imports and full `__all__` entries) and turns "tool quietly disappears from `tools/list` because someone deleted an import line" into a loud import error at server startup.
- **D-02:** **Refresh the `server.py` module docstring "MCP tools provided" bullet list** to include all six new tools: `verify_custom_fields_setup`, `write_wellness_entry`, `enrich_activity_climbing`, `create_climbing_activity`, `complete_climbing_session`, `get_training_status`. The list is currently stale — adding the milestone's tools keeps it truthful; existing stale entries (if any) are out of scope to fix here.

### README documentation
- **D-03:** **One short subsection per new tool under the existing "Climbing setup" section.** Five subsections (verify is already documented in Phase 1):
  - `write_wellness_entry`
  - `enrich_activity_climbing`
  - `create_climbing_activity`
  - `complete_climbing_session`
  - `get_training_status`
  Each subsection is roughly five lines: tool name as a sub-heading, one sentence on what it does, one sentence on when Claude should use it, one paste-ready example invocation showing the most common parameter shape. Keep the prose minimal — the canonical usage detail lives in tool docstrings (Pitfall #6 carry-forward); the README is the discovery surface.
- **D-04:** **Refresh the README introduction paragraph** so it mentions climbing session completion, wellness writes, and the training status report. Currently it says "tools for authentication and data retrieval for activities, events, and wellness data" — that pitch undersells what the milestone shipped. New phrasing should name the new domains without enumerating every tool.
- **D-05:** **No `docs/CLIMBING-WORKFLOW.md` or narrative tutorial in v1.** The per-tool subsections (D-03) plus the existing "Climbing setup" section are enough for a fresh user to discover the surface. A narrative walkthrough is a v1.x consideration if Timo's actual use surfaces a need.

### Regression validation
- **D-06:** **New `tests/test_server_registration.py` asserts the full expected tool name set is registered with FastMCP.** Test imports `intervals_mcp_server.server` (triggering decorator registration), then queries the `mcp` instance for its registered tool list and asserts every expected name is present. Expected name set is a constant at the top of the test file — single source of truth for "what tools this milestone ships". Catches the silent-removal failure mode (someone deletes a `from .tools.X import Y` line and the tool quietly drops off `tools/list`) at unit-test speed.
- **D-07:** **Existing test suite must pass unchanged (success criterion 3).** No edits to existing `tests/test_*.py` files. If the named-imports change in D-01 surfaces a circular-import or test-fixture issue, fix at the import site, not by modifying tests. Pitfall #12 (no shared-utility regression) and Phase 1 D-19/D-20 carry-forward.
- **D-08:** **Run `pytest --collect-only` as part of the Phase 5 verification** to confirm `tests/test_server_registration.py` is discovered (Pitfall #14 carry-forward — Phase 1 D-19 / Phase 2 D-23 / Phase 3 D-20 / Phase 4 D-18).

### Live smoke testing
- **D-09:** **`scripts/smoke_phase5.py` exercises every new tool via `make_intervals_request()` against the live account.** Goes through the full new surface in one run:
  1. `verify_custom_fields_setup` — confirms athlete account has all 7 fields (carry-over sanity check).
  2. `write_wellness_entry` — PUT a minimal entry on `2099-01-01` (sleep_hours + soreness), readback verifies.
  3. `create_climbing_activity` — POST a minimal climbing activity on `2099-01-01` with discipline + indoor + RPE; capture activity_id; readback via `format_climbing_activity` verifies.
  4. `enrich_activity_climbing` — call against the activity_id from step 3 with additional fields (e.g., `top_grade_sent`, `sends`); readback verifies.
  5. `complete_climbing_session` — create a planned event on `2099-01-02` first, then call the tool against `event_id`; readback verifies `paired_event_id` linkage.
  6. `get_training_status` — read-only call against `as_of_date="2099-01-01"`; renders the report; verifies it's in 400-600 token range.
  7. Cleanup pass: `DELETE /activity/{id}` for activities created in steps 3 and 5; `DELETE` the planned event from step 5.
  Logs each step's request body / response status / readback verdict to a findings artifact (canonical name: `.planning/phases/05-server-wiring-and-acceptance/05-SMOKE-FINDINGS.md`). Uses `make_intervals_request()` exclusively (PROJECT.md constraint).
- **D-10:** **Far-future date strategy: `2099-01-01` for wellness/activity, `2099-01-02` for the planned event.** Same pattern as Phase 1 D-03, Phase 2 D-03, Phase 3 (carry-forward). Wellness PUT for `2099-01-01` is left in place after the run — zero training-load impact, never surfaces in any UI date range Timo cares about. Activities and the planned event are DELETE'd in the cleanup pass (Phase 1 spike confirmed `DELETE /activity/{id}` works; events have an existing `delete_event` tool surface). The script exits non-zero if any cleanup fails so the user knows manual intervention is needed.
- **D-11:** **`05-LIVE-SMOKE.md` manual checklist for the Claude Desktop side.** One row per new tool with a checkbox: "asked Claude to run X with parameters Y, observed non-error response Z". Proves the success-criterion-1 visibility (`tools/list` in Claude Desktop shows the new tools) and success-criterion-4 acceptance (each tool produces a non-error response in Claude Desktop, not just via the script). Lives in the phase directory; ticked off by Timo before the phase is marked complete.
- **D-12:** **Smoke script and registration test are independent.** The unit-test registration assertion (D-06) catches structural drift; the live script (D-09) catches API contract drift; the manual checklist (D-11) catches the Claude Desktop tool-list rendering. All three are cheap, all three answer different failure questions, all three run in Phase 5.

### Cross-cutting / Pitfall guards (carry-forward)
- **D-13:** **All HTTP through `make_intervals_request()`** (PROJECT.md constraint). The smoke script must not introduce a direct `httpx` call even for cleanup — `make_intervals_request(method="DELETE", ...)` is the path.
- **D-14:** **No `_`-prefix imports across sibling tool modules.** Phase 1 D-18 / Phase 2 D-22 / Phase 3 D-22 / Phase 4 D-14 carry-forward. Phase 5 doesn't add cross-module imports — the registration test reads `mcp.list_tools()` (or whatever the FastMCP query API is), it doesn't reach into private state.
- **D-15:** **No regressions to existing tools or formatters.** `format_climbing_activity`, `format_status_report`, `format_wellness_entry` all stay untouched. `tools/wellness.py`, `tools/climbing.py`, `tools/status.py`, `tools/activities.py`, `tools/events.py`, `tools/custom_items.py` are read-only in this phase except for the import-site changes covered by D-01 (which are in `server.py`, not in the tool modules themselves). Existing tests must pass with zero changes.
- **D-16:** **MCP statelessness preserved** (PROJECT.md constraint). Phase 5 adds no state, no caching, no shadow store.

### Folded Todos

None — `gsd-sdk query todo.match-phase 5` returned 0 matches.

### Claude's Discretion

- Exact prose for the README "Climbing tools" subsections — keep them ~5 lines each but planner picks the example invocation and framing.
- Whether the registration test queries FastMCP via `mcp.list_tools()` (async), inspects an internal registry attribute, or imports each name from `server.__all__` and asserts callability — whichever is most idiomatic against the FastMCP version pinned in `uv.lock`.
- Smoke-script CLI ergonomics — whether it accepts a `--no-cleanup` flag for debugging, whether it prints a summary table at the end, whether it writes findings as Markdown or JSON. Implementation detail.
- Whether `05-SMOKE-FINDINGS.md` is auto-written by the script or hand-curated from the script's stdout. Either is acceptable; the canonical file lives in the phase directory.
- Bullet ordering of the refreshed `server.py` "MCP tools provided" docstring list — alphabetical, grouped by domain, or insertion order. Cosmetic.
- Whether the manual `05-LIVE-SMOKE.md` checklist captures Claude Desktop's exact text response or just a thumbs-up checkbox. Planner picks; thumbs-up is enough for the success criterion, capturing the response is nicer for future debugging.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project-level contracts
- `.planning/PROJECT.md` — vision, Key Decisions table, Constraints (single HTTP boundary, MCP statelessness, no shadow store, single-athlete), Out of Scope (no v2 work in this phase).
- `.planning/REQUIREMENTS.md` — Phase 5 requirements: **SETUP-01** (README documents required custom fields — already shipped Phase 1; Phase 5 verifies still accurate), **SETUP-02** (verification path exists — `verify_custom_fields_setup`, already shipped Phase 1; Phase 5 confirms still working).
- `.planning/ROADMAP.md` §"Phase 5: Server Wiring and Acceptance" — Goal and four Success Criteria.
- `CLAUDE.md` — project working-style and key constraints.
- `AGENTS.md` — contributor + tooling guide (uv, pytest, ruff, mypy).

### Prior phase carry-forward (mandatory)
- `.planning/phases/01-foundation-and-write-path-spike/01-CONTEXT.md` — D-13 (README is the canonical setup-doc location, no separate `docs/SETUP-CLIMBING.md`), D-17 (`tools/climbing.py` already imported into `server.py`), D-18 (no `_`-prefix sibling imports), D-19/D-20 (test discovery, no regression).
- `.planning/phases/01-foundation-and-write-path-spike/01-SPIKE-FINDINGS.md` — confirmed `DELETE /activity/{id}` works (D-10 cleanup relies on this), confirmed `POST /athlete/{id}/activities/manual` returns activity id, confirmed wellness PUT shape.
- `.planning/phases/02-wellness-write-and-activity-enrichment/02-CONTEXT.md` — D-22 (no `_`-prefix sibling imports), D-23 (separate test files), D-24 (no formatter regression), D-25 (smoke-test gating: standalone scripts, never in CI). D-09 wellness drop-None upsert is the surface the smoke script exercises.
- `.planning/phases/02-wellness-write-and-activity-enrichment/02-SPIKE-FINDINGS.md` — wellness scale ranges, activity custom-field PUT body shape, `icu_rpe` write path. The smoke script trusts these.
- `.planning/phases/03-activity-creation-and-session-completion/03-CONTEXT.md` — D-01..D-04 (duplicate guard semantics — smoke script must not trip it on a fresh `2099-01-01`), D-06 (`paired_event_id` explicitly set; smoke step 5 verifies), D-17 (`start_date_local = "{date}T00:00:00"` — smoke script honors).
- `.planning/phases/04-training-status-report/04-CONTEXT.md` — D-12 (token budget verified by tests, smoke step 6 confirms 400-600 range still holds against far-future fabricated data).

### Research
- `.planning/research/PITFALLS.md` — **#12** (no shared-utility regression — applies to the `server.py` wiring change), **#14** (test discovery — `tests/test_server_registration.py` must collect). The smoke script honors **#1** (idempotency — runs cleanup so re-running the script doesn't snowball state) and **#5** (MCP single-shot — every script step is a single tool call's worth of work).
- `.planning/research/SUMMARY.md` — overall domain context.

### Codebase context
- `.planning/codebase/STRUCTURE.md` — module layout; `server.py` is where tool imports register the MCP surface.
- `.planning/codebase/CONVENTIONS.md` — naming, import ordering, docstring style. The new README subsections follow Google-style tone consistent with existing tool docstrings.
- `.planning/codebase/TESTING.md` — `pytest --collect-only` discovery rule; the registration test must comply.
- `.planning/codebase/INTEGRATIONS.md` — Intervals.icu endpoint patterns and auth (the smoke script uses these).
- `.planning/codebase/CONCERNS.md` — `server.py` is small (132 lines); the wiring change adds ~6 lines net. No file-size concern triggered.

### Source files (read before modifying)
- `src/intervals_mcp_server/server.py` — the main file Phase 5 modifies. Currently 132 lines. Wiring change is on lines 25–44 (docstring tools list), 87 (wellness imports), 95 (climbing imports), 100–122 (`__all__`).
- `src/intervals_mcp_server/mcp_instance.py` — the `mcp` singleton; the registration test queries it.
- `src/intervals_mcp_server/tools/wellness.py` — already has `write_wellness_entry` registered via `@mcp.tool()`; just needs to be in the named-import line in `server.py`.
- `src/intervals_mcp_server/tools/climbing.py` — already has `enrich_activity_climbing`, `create_climbing_activity`, `complete_climbing_session` registered via `@mcp.tool()`; just needs them added to the named-import line in `server.py`.
- `src/intervals_mcp_server/tools/status.py` — `get_training_status` is already named-imported (line 96).
- `src/intervals_mcp_server/api/client.py` — `make_intervals_request()`; the smoke script's only HTTP path.
- `scripts/spike_write_endpoints.py`, `scripts/smoke_phase2.py` — reference structure for `scripts/smoke_phase5.py` (logging, redaction, findings-write pattern, cleanup discipline).
- `README.md` — currently 296 lines. Intro paragraph (line 3), "Climbing setup" section (lines 75–117), then "Updating" (line 119+). New "Climbing tools" section lands between the existing "Verifying the setup" subsection (line 106) and "Updating" (line 119), or appended after "Verifying the setup" — planner picks placement.
- `tests/` directory — model the registration test on existing test patterns (monkeypatch, asyncio.run); the new file is purely additive.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `make_intervals_request()` (`src/intervals_mcp_server/api/client.py`) — sole HTTP boundary; smoke script uses it for every step including DELETE cleanup.
- `mcp` singleton (`src/intervals_mcp_server/mcp_instance.py`) — the FastMCP instance; the registration test queries its tool list.
- Existing `__all__` block (`src/intervals_mcp_server/server.py` lines 100–122) — the established pattern for re-exports; D-01 extends it additively.
- Existing tool docstrings — already Google-style (Pitfall #6 carry-forward); the README subsections quote/summarize them rather than duplicating.
- `format_climbing_activity()` (`src/intervals_mcp_server/utils/formatting.py`) — readback rendering; the smoke script uses it to verify each create/enrich step.
- `format_status_report()` (`src/intervals_mcp_server/utils/status.py`) — same role for the status-tool smoke step.
- `delete_event` (`src/intervals_mcp_server/tools/events.py`) — already public; smoke script uses it for the planned-event cleanup.
- Existing test patterns in `tests/test_server.py` — `from intervals_mcp_server import server` import sets up the registration; the new registration test follows this pattern.
- `scripts/spike_write_endpoints.py` (Phase 1) and `scripts/smoke_phase2.py` (Phase 2) — proven shape for live-API scripts: redacted logging, far-future dates, structured findings file, idempotent cleanup.

### Established Patterns
- **Re-export shape:** `from .tools.X import name1, name2, ...` followed by inclusion in `__all__`. Activities, events, custom_items are the templates; D-01 extends climbing and wellness to match.
- **Module docstring tool list:** A bulleted list at the top of `server.py` enumerates registered tools. D-02 keeps it truthful for the milestone's surface.
- **Smoke scripts:** Standalone async scripts under `scripts/`, run via `uv run`, never imported into `tests/` (so they never run in CI per Phase 2 D-25). Far-future date for write paths; cleanup at end.
- **Test naming:** `tests/test_<domain>.py`. The new file is `tests/test_server_registration.py` — domain is "server", concern is "registration".
- **README structure:** `## Header` for top-level sections (Setup, Climbing setup, Updating); `### Subheader` for sub-content. The new "Climbing tools" lands as a top-level `## Climbing tools` section after the existing "Climbing setup" so it reads as a parallel sibling.

### Integration Points
- `server.py` lines 25–44 — module docstring "MCP tools provided" list (D-02 refresh target).
- `server.py` line 87 — wellness named-import line (add `write_wellness_entry`).
- `server.py` line 95 — climbing named-import line (add three tools).
- `server.py` lines 100–122 — `__all__` (add four entries).
- `README.md` line 3 — intro paragraph (D-04 refresh target).
- `README.md` after line 117 — landing for the new "Climbing tools" section (D-03).
- `tests/test_server_registration.py` — new file (D-06).
- `scripts/smoke_phase5.py` — new file (D-09).
- `.planning/phases/05-server-wiring-and-acceptance/05-LIVE-SMOKE.md` — new file (D-11).
- `.planning/phases/05-server-wiring-and-acceptance/05-SMOKE-FINDINGS.md` — new file written by the smoke script run (D-09).

</code_context>

<specifics>
## Specific Ideas

- **`__all__` ordering** — keep the existing top-down order (existing tools first, climbing/status appended). The four new names sit alphabetically within the climbing block, with `write_wellness_entry` joining the wellness block. Don't re-sort the whole list — minimizes diff and preserves git blame.
- **Smoke script step ordering matters.** Run `verify_custom_fields_setup` first — if the athlete account is missing fields, the climbing-write steps will hard-block (Phase 1 D-12 by design) and the script can fail early with a clear pointer to the README. Then wellness (no custom-field dependency, isolated). Then create → enrich (creates state the next step depends on). Then complete_session against a freshly-created planned event. Then status (read-only — bottom because it gives the broadest signal once the rest has run). Cleanup last.
- **Live smoke script must not contaminate real training data.** Far-future date is the primary guard (carry-forward from Phase 1/2/3); cleanup is the secondary. If both fail, the result lives in 2099 and is invisible to any reasonable query.
- **Manual checklist captures the human-in-the-loop test.** The registration test proves "the FastMCP instance has these tools registered". The smoke script proves "the API contract still works". Only Claude Desktop running against the actual MCP server proves "Claude can see and call them". That last leg is the manual checklist's reason to exist — it's not redundant with either automated check.
- **`server.py` docstring fix is cosmetic but cheap.** While editing the file for D-01 anyway, refresh the docstring (D-02). Don't make a separate task for it.
- **No CHANGELOG / release-notes file in v1.** Single-user project. The Key Decisions table in `PROJECT.md` and the per-phase artifacts already capture every meaningful change.

</specifics>

<deferred>
## Deferred Ideas

- **Narrative `docs/CLIMBING-WORKFLOW.md`** — could be useful for v1.x onboarding but not for the single-user shipping today; the per-tool README subsections cover the surface.
- **CHANGELOG.md** — single-user project, no need until external consumers exist.
- **Automated end-to-end Claude Desktop test harness** — would require a Claude Desktop test client; manual checklist is enough for v1.
- **CI integration of `scripts/smoke_phase5.py`** — out of scope; smoke scripts intentionally run only on demand against the live account (Phase 2 D-25 carry-forward).
- **Property-based or fuzz tests for the registration test** — overkill; the expected-name-set assertion is enough.
- **Bumping the package version / tagging a release** — milestone-completion ceremony, not Phase 5 work. Lives in `/gsd-complete-milestone`.
- **Adding tool-count assertions in addition to name assertions** — count is implicit in the name set; redundant.
- **Refreshing `tools/__init__.py` `__all__` if it exists** — out of scope unless it's stale and breaking re-exports somewhere; planner checks once, defers if not needed.

### Reviewed Todos (not folded)

None — no pending todos in STATE.md to review; `gsd-sdk query todo.match-phase 5` returned 0 matches.

</deferred>

---

*Phase: 05-server-wiring-and-acceptance*
*Context gathered: 2026-04-29*
