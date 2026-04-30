# Phase 3: Activity Creation and Session Completion - Context

**Gathered:** 2026-04-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver two write tools that produce climbing activities on Intervals.icu, both duplicate-safe, on top of the Phase 1 utility layer and the Phase 2 enrichment foundation:

1. **`create_climbing_activity`** — POST a manual climbing activity from scratch (no prior event, no Garmin sync). Date + duration are user-supplied; climbing fields enrich on top in the same call.
2. **`complete_climbing_session`** — Complete a planned calendar event by reading the event server-side, POSTing a linked activity (`paired_event_id` set explicitly), then enriching with climbing metadata + RPE in the same single-shot call. The planned event stays on the calendar (PROJECT.md Key Decision).

Both tools route through `make_intervals_request()`, perform a GET-before-POST duplicate guard (CLIMB-09), and reuse the Phase 2 enrichment logic (validation, custom-field guard, split-PUT, readback) via a refactored private `_enrich_impl` in `tools/climbing.py`.

**In scope for this phase:**
- Duplicate guard on every POST: GET activities for `(date, type)` and refuse with the existing activity_id if a match exists.
- `create_climbing_activity` in `tools/climbing.py` — explicit named-param tool; required: `date`, `duration_minutes`. Climbing fields and `name` optional.
- `complete_climbing_session` in `tools/climbing.py` — explicit named-param tool; required: `event_id`. Tool fetches the planned event server-side, derives date/type/name from it, sets `paired_event_id` explicitly in the POST body, then enriches.
- Refactor of the existing `enrich_activity_climbing` body into a private `_enrich_impl(activity_id, ...)` helper; the public tool keeps its signature and behavior.
- Tests in new `tests/test_climbing_create.py` covering both tools, duplicate-guard fires, paired_event_id verification, and the Pitfall #4 timezone case.
- Smoke-test extension or new script under `scripts/` if `paired_event_id` behavior needs a live probe (Claude's Discretion — defer if response shape from Phase 1 spike is sufficient).

**Out of scope (belongs to later phases):**
- Status / readiness reporting — Phase 4.
- Server.py wiring of new tools — `tools/climbing.py` is already imported (Phase 1); new tools ride that decorator registration with zero `server.py` edits.
- Generic non-climbing manual-activity creation — v2 (`GEN-v2-01`).
- `force_create=True` / override flag for duplicate guard — deferred (legitimate same-day duplicates are rare; revisit only if real demand).
- Free-text `description` / `notes` parameter on create_climbing_activity — deferred.
- Improving the verify-fields readback heuristic — Phase 1 known limitation (carry-forward).

</domain>

<decisions>
## Implementation Decisions

### Duplicate guard (CLIMB-09 / Pitfall #1)

- **D-01:** **Match criteria — `(date, type)`.** Duplicate guard runs before any POST: GET `/athlete/{id}/activities?oldest={date}&newest={date}` and check whether any returned activity has `start_date_local` matching the target date AND `type == "WeightTraining"`. No name match, no date-only fan-out. Catches Garmin-synced records and prior MCP retries equally.
- **D-02:** **Hit behavior — refuse with existing id.** If one or more matches found, return a clear error naming each matching activity (id, name, start_date_local) and suggesting `enrich_activity_climbing` as the follow-up. Stateless, non-destructive, lets Claude (the LLM) drive the next step.
- **D-03:** **Both tools enforce the guard.** `create_climbing_activity` AND `complete_climbing_session` perform the same duplicate check. Pitfall #1's retry/reconnect risk applies symmetrically.
- **D-04:** **Single undifferentiated match list.** The error lists all matches uniformly; no special climbing-vs-non-climbing detection. Keeps the guard's logic narrow and the tool output simple. Claude reads the list and decides.

### `complete_climbing_session` event linking (CLIMB-01 / Pitfall #4)

- **D-05:** **`event_id` is required; tool fetches the event server-side.** Signature accepts `event_id: str` (required), and the tool calls GET `/athlete/{id}/events/{event_id}` to read `start_date_local`, `type`, and `name`. The event is the source of truth — there is no user-supplied `date` or `type` parameter to drift from it.
- **D-06:** **Set `paired_event_id` explicitly in the POST body.** Include `paired_event_id: event_id` in the POST to `/athlete/{id}/activities/manual`. Field is present in the activity response shape (Phase 1 spike confirmed). Readback verifies `paired_event_id == event_id`. Do not rely on Intervals.icu's date+type auto-match (LOW-MEDIUM confidence per STATE.md "Blockers/Concerns").
- **D-07:** **Event values verbatim; climbing fields enrich on top.** `start_date_local`, `type`, and `name` in the POST body come from the planned event. User-supplied climbing fields (discipline, indoor, session_focus, grades, sends, attempts, rpe) are passed to the post-POST enrichment step. No reconciliation between user params and event metadata — the event wins on all fact-of-the-session fields.
- **D-08:** **Single-shot complete + enrich.** `complete_climbing_session` accepts the same climbing-field params as `enrich_activity_climbing` (per D-08 carries the climbing-field params: discipline, indoor, session_focus, top_grade_sent, top_grade_attempted, sends, attempts, rpe). After POST returns the new activity_id, the tool internally calls `_enrich_impl(activity_id, ...)`. One tool call closes the loop (matches Pitfall #5 single-shot principle).

### POST + enrichment atomicity & code reuse

- **D-09:** **Enrichment failure after successful POST → leave the activity, return clear error.** If the POST succeeds (activity_id returned) but the subsequent `_enrich_impl` call fails, the tool does NOT delete the activity. It returns an error naming the activity_id and what landed/didn't, plus a hint to call `enrich_activity_climbing(activity_id=..., override=True, ...)` to retry. Matches D-16's "no silent partial state" principle from Phase 2; preserves any RPE that already wrote.
- **D-10:** **POST is treated as atomic.** If the POST itself returns an error, the tool returns the error verbatim. No defensive GET-after-POST-error to hunt for orphaned activities — Intervals.icu's `/activities/manual` is all-or-nothing per Phase 1 spike.
- **D-11:** **Refactor: `enrich_activity_climbing` body → private `_enrich_impl`.** Move the enrichment logic (validation, conflict scan, verify-fields guard, split-PUT, readback) into a private helper `_enrich_impl(activity_id, *, discipline=None, ...) -> str` in `tools/climbing.py`. The public `enrich_activity_climbing` tool keeps its signature and forwards to `_enrich_impl`. The new tools call `_enrich_impl` after their POST. D-22 carry-forward (no `_`-prefix imports across sibling tool modules) is satisfied — the helper is in the SAME file as both consumers, so no sibling-import rule is invoked. Per the rule's spirit (Pitfall #11), this is the correct shape: shared logic is named, in one place, in the file that owns it.
- **D-12:** **Skip the override conflict-scan on freshly-POSTed activities.** When `_enrich_impl` is called from `create_climbing_activity` or `complete_climbing_session` immediately after POST, pass an internal flag (e.g., `_skip_conflict_scan=True`) so the conflict-scan GET is skipped — a brand-new activity has no prior climbing values, conflict detection would always pass, and the extra GET is wasted. The public `enrich_activity_climbing` tool always runs the conflict-scan as before. The flag is `_`-prefixed and not exposed to MCP — it's an internal-only optimization.

### Parameter shape & defaults

- **D-13:** **`create_climbing_activity` required params: `date`, `duration_minutes`. Title and climbing fields all optional.** Signature:
  ```python
  async def create_climbing_activity(
      date: str,                            # required, YYYY-MM-DD
      duration_minutes: int,                # required
      name: str | None = None,              # optional, template default
      discipline: str | None = None,
      indoor: bool | None = None,
      session_focus: str | None = None,
      top_grade_sent: str | None = None,
      top_grade_attempted: str | None = None,
      sends: int | None = None,
      attempts: int | None = None,
      rpe: int | None = None,
      athlete_id: str | None = None,
      api_key: str | None = None,
  ) -> str:
  ```
- **D-14:** **Public param is `duration_minutes` (int); tool converts to `moving_time` seconds internally.** `moving_time = duration_minutes * 60`. Same user-friendly-units pattern as P2 D-08 (`sleep_hours` → `sleepSecs`). Document the conversion in the docstring so Claude knows to gather "how many minutes did you climb for". HRV and resting_hr have no analog here; this is climbing-specific.
- **D-15:** **Activity `type` is hardcoded as `"WeightTraining"`.** Phase 1 spike confirmed this works. v1 is climbing-only by scope (PROJECT.md Out of Scope: generic activities). Adding a `type` parameter would surface generic-activity scope creep that GEN-v2-01 owns. Document the hardcode in the docstring.
- **D-16:** **`name` is optional with a template default.** If user passes `name`, use it verbatim. Otherwise build the title from supplied climbing fields:
  - If `discipline` is supplied: `"Climbing — {discipline_human} — {date}"` where `discipline_human` is a small map (`bouldering` → "Bouldering", `sport_lead` → "Sport lead", `top_rope` → "Top rope", `trad` → "Trad"). Do not expose enum values verbatim in titles — they appear in the Intervals.icu UI.
  - Otherwise fall back to `"Climbing — {date}"`.
  - Encourages Claude to call with minimal args while still producing scannable activity titles.

### Cross-cutting / Pitfall guards (carry-forward)

- **D-17:** **`start_date_local` format = `"{date}T00:00:00"` (Pitfall #4).** Both new tools construct `start_date_local` from the user-supplied (or event-derived) `YYYY-MM-DD` date string. **Never derive from `datetime.utcnow()`.** Matches `events.py::_prepare_event_data` — that function is the established model for this format in the codebase. Tests must include a date-near-midnight case asserting the format.
- **D-18:** **Discipline-aware grade validation runs BEFORE any HTTP call.** Carries P2 D-13 forward. Use `validate_grade(grade, discipline)` from `utils/grades.py`. If `top_grade_sent` or `top_grade_attempted` is supplied, `discipline` must also be supplied (`_enrich_impl` enforces this).
- **D-19:** **Conditional verify-fields guard runs BEFORE POST when any custom-field param supplied.** `_enrich_impl` already runs `_verify_custom_fields_setup_impl` if any custom-field key is present (P2 D-20). For the new tools, this means: if user passes any climbing field on `create_climbing_activity` / `complete_climbing_session`, the verify-fields guard fires before the POST. RPE-only or no-climbing-field calls skip the guard (RPE is native).
- **D-20:** **Tests live in new `tests/test_climbing_create.py`.** Separate from `tests/test_climbing_write.py` (Phase 2's `enrich_activity_climbing` tests) and `tests/test_climbing.py` (Phase 1's verify-tool tests). Must be discovered by `pytest --collect-only` per Pitfall #14.
- **D-21:** **No regression to existing tools.** `tools/climbing.py` is extended additively. The `enrich_activity_climbing` refactor (D-11) preserves the public signature and behavior; existing Phase 2 tests must pass unchanged. `format_climbing_activity` is extended only if a new field needs rendering (e.g., `paired_event_id`); not rewritten.
- **D-22:** **No `_`-prefix imports across sibling tool modules.** Phase 1 D-22 carries forward. The `_enrich_impl` helper sits in the same file as its callers — no sibling-import rule is invoked. If `tools/activities.py` ever needs to share something with `tools/climbing.py`, promote to `utils/`.

### Folded Todos

None — STATE.md "Pending Todos" is empty; `gsd-sdk query todo.match-phase 3` returned 0 matches.

### Claude's Discretion

- Exact mechanics of the `_enrich_impl` extraction — whether it's a single function or a small set of internal helpers (conflict-scan, write, readback). Refactor mechanics; planner picks the shape that minimizes diff to the existing tool.
- Whether to add a Phase 3 spike for `paired_event_id` behavior. Phase 1 spike confirmed `paired_event_id` is in the activity response shape, but never exercised setting it explicitly via POST. Recommendation: skip the spike — readback verification of `paired_event_id == event_id` after POST is sufficient. Add a probe only if the readback fails.
- Whether `complete_climbing_session` should error if the planned event already has a `paired_event_id` set (i.e., already completed). Recommendation: yes, fail with a hint to call `enrich_activity_climbing` on the paired activity instead. Implementation detail.
- Whether the duplicate-guard error message lists ALL matches or just the first. Recommendation: list all (typically 0 or 1; >1 means Garmin sync + manual create on same day, which is itself worth surfacing).
- Whether `_skip_conflict_scan` is implemented as an explicit kwarg on `_enrich_impl` or by inverting the call order (e.g., a `_enrich_fresh` thin wrapper). Implementation detail.
- Optional `Phase 3` smoke-test script at `scripts/smoke_phase3.py` (mirrors Phase 2's `scripts/smoke_phase2.py`) that creates a planned event, calls `complete_climbing_session`, and asserts the linkage. Defer if Phase 2's smoke-test infrastructure is reusable.
- Whether the `discipline_human` mapping lives in `utils/climbing.py` (next to the `Discipline` enum) or in `tools/climbing.py` (next to the title-building helper). Planner picks; either is fine.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project-level contracts
- `.planning/PROJECT.md` — vision; Key Decisions: "Completion creates a linked activity, planned event stays on calendar", "Climbing fields collected as optional tool parameters, not two-phase tools", "Single-athlete"; Constraints (single HTTP boundary, MCP statelessness, no shadow store); Out of Scope (generic activities, multi-athlete).
- `.planning/REQUIREMENTS.md` — Phase 3 requirements: **CLIMB-01** (complete_climbing_session linked activity), **CLIMB-02** (create_climbing_activity from scratch), **CLIMB-09** (duplicate guard).
- `.planning/ROADMAP.md` §"Phase 3: Activity Creation and Session Completion" — Goal and three Success Criteria.

### Phase 1 + Phase 2 carry-forward (mandatory)
- `.planning/phases/01-foundation-and-write-path-spike/01-CONTEXT.md` — D-15 (extend format_climbing_activity), D-17 (climbing tools live in `tools/climbing.py`), D-18 (no `_`-prefix sibling imports), D-19/D-20 (test discovery, no regression).
- `.planning/phases/01-foundation-and-write-path-spike/01-SPIKE-FINDINGS.md` — confirmed `POST /athlete/{id}/activities/manual` returns activity id with body `{start_date_local, type, name, moving_time}`; `type="WeightTraining"` works; `start_date_local="YYYY-MM-DDT00:00:00"` (local midnight); `paired_event_id` field present in response shape (never null after pairing); `DELETE /activity/{id}` available.
- `.planning/phases/02-wellness-write-and-activity-enrichment/02-CONTEXT.md` — D-12 (at-least-one-supplied), D-13 (grade validation pre-HTTP), D-14 (default-deny override + audit), D-15 (readback verifies supplied fields only), D-16 (split-PUT: RPE first, custom fields second), D-20 (conditional verify-fields guard), D-22 (no `_`-prefix sibling imports), D-23 (separate test files), D-24 (no formatter regression).
- `.planning/phases/02-wellness-write-and-activity-enrichment/02-SPIKE-FINDINGS.md` — split-PUT pattern paste-ready; activity custom-field PUT shape working hypothesis (top-level keys via `PUT /activity/{id}`); SETUP-01 prerequisite still pending in production (custom-field schemas).

### Research
- `.planning/research/PITFALLS.md` — especially **#1** (idempotency / duplicate guard mandatory; D-01..D-04), **#2** (silent custom-field write failure → readback verify; carried via `_enrich_impl`), **#3** (grade-discipline coupling; D-18), **#4** (start_date_local timezone — `YYYY-MM-DDT00:00:00`, never `utcnow()`; D-17), **#5** (MCP single-shot statelessness; D-08), **#10** (override audit on existing activities; carried via `_enrich_impl`), **#11** (no `_`-prefix sibling imports; D-22), **#14** (test discovery; D-20).
- `.planning/research/SUMMARY.md` — domain context.

### Codebase context
- `.planning/codebase/STRUCTURE.md` — "Where To Add New Code" table; `tools/climbing.py` is the destination (D-15/D-17 carry-forward).
- `.planning/codebase/CONVENTIONS.md` — naming, error patterns (return error string from tools), Google-style docstrings, import ordering, `# pylint: disable=too-many-arguments` pattern.
- `.planning/codebase/CONCERNS.md` — module-size warning (`tools/climbing.py` already 472 lines; the `_enrich_impl` refactor doesn't grow the file meaningfully, and the two new tools add ~80 lines each — modest extension is OK; revisit only if file crosses ~700 lines).
- `.planning/codebase/INTEGRATIONS.md` — Intervals.icu endpoint patterns and auth.
- `.planning/codebase/TESTING.md` — test layout, pytest discovery rules, mocking pattern (`monkeypatch` `make_intervals_request` + `asyncio.run`).
- `AGENTS.md` — uv, pytest, ruff, mypy tooling.

### Source files (read before modifying)
- `src/intervals_mcp_server/api/client.py` — the single HTTP boundary; `make_intervals_request(url, data, method, params, api_key)` (D-22 PROJECT.md constraint).
- `src/intervals_mcp_server/mcp_instance.py` — `mcp` import for `@mcp.tool()` registration.
- `src/intervals_mcp_server/tools/climbing.py` — Phase 2 module; the `_enrich_impl` extraction lands here, plus the two new public tools. Existing `_verify_custom_fields_setup_impl`, `_README_POINTER`, and `enrich_activity_climbing` body all relevant.
- `src/intervals_mcp_server/tools/activities.py` — `get_activities` is the duplicate-check helper (D-01 calls the underlying API directly, not the public tool); reference for activity GET patterns; `add_activity_message` already imported in `tools/climbing.py` (D-22 — public, allowed).
- `src/intervals_mcp_server/tools/events.py` — `_prepare_event_data` is the established model for `start_date_local = "{date}T00:00:00"` (Pitfall #4 / D-17). Read before constructing the activity POST body.
- `src/intervals_mcp_server/utils/climbing.py` — `Discipline`, `SessionFocus`, `CUSTOM_FIELD_KEYS` (read-only); the `discipline_human` map (D-16) may live here.
- `src/intervals_mcp_server/utils/grades.py` — `validate_grade(grade, discipline)`; `_enrich_impl` calls it.
- `src/intervals_mcp_server/utils/validation.py` — `resolve_athlete_id` pattern; both new tools use it.
- `src/intervals_mcp_server/utils/formatting.py` — `format_climbing_activity` (Phase 1, extended in Phase 2); `format_activity_summary` is the read-side model. May need additive extension to render `paired_event_id` if its readback surfaces in tests.
- `tests/test_climbing.py`, `tests/test_climbing_write.py` — existing test files for the verify tool and `enrich_activity_climbing`. Read for the established mocking pattern; do NOT modify.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `make_intervals_request(url, data, method, params, api_key)` — the single HTTP boundary; supports POST/PUT/GET/DELETE; both new tools use it directly.
- `enrich_activity_climbing` body in `tools/climbing.py` (currently lines 232–472) — about to be extracted into `_enrich_impl(activity_id, *, ..., _skip_conflict_scan=False) -> str`. The public tool then becomes a thin wrapper.
- `_verify_custom_fields_setup_impl(athlete_id, api_key) -> tuple[bool, list[str], str]` in `tools/climbing.py` — the pre-write guard `_enrich_impl` consumes; runs unchanged after the refactor.
- `_README_POINTER` in `tools/climbing.py` — readback-failure error tail; reused via `_enrich_impl`.
- `validate_grade(grade, discipline)` in `utils/grades.py` — same call site as Phase 2.
- `Discipline`, `SessionFocus`, `CUSTOM_FIELD_KEYS` in `utils/climbing.py` — frozen spec; Phase 3 reads only.
- `resolve_athlete_id(athlete_id, config.athlete_id)` in `utils/validation.py` — both new tools use this.
- `format_climbing_activity(activity)` in `utils/formatting.py` — already renders the climbing fields and `icu_rpe`. Possibly extended to render `paired_event_id` if useful in test output.
- `add_activity_message` (public) imported from `tools/activities.py` into `tools/climbing.py` — used inside `_enrich_impl` for override audit; not invoked from the new tools' direct path (fresh-POST never has conflicts).
- `_prepare_event_data` (private but same-file pattern) in `tools/events.py` — the model for `start_date_local = "{date}T00:00:00"`. Read for the Pitfall #4 format pattern; do not import.
- Test patterns in `tests/test_climbing_write.py` and `tests/test_server.py` — `monkeypatch` `make_intervals_request`, run via `asyncio.run`. Mirror for the new tests.

### Established Patterns
- **start_date_local format:** `"{date}T00:00:00"` exactly. Constructed from a `YYYY-MM-DD` user input by string concatenation. Never `datetime.utcnow().isoformat()` or any timezone-aware datetime — `events.py::_prepare_event_data` is the model.
- **POST endpoint for manual activities:** `POST /athlete/{athlete_id}/activities/manual` with body `{start_date_local, type, name, moving_time, ...}`. Returns the full activity dict including `id`. Phase 1 spike confirmed.
- **Activity `type`:** hardcoded `"WeightTraining"` for v1 climbing.
- **Single-shot tool:** all params on one call (Pitfall #5). The LLM gathers conversationally before calling.
- **Default-deny on existing values:** `_enrich_impl` runs the conflict-scan + override-audit when called from the public `enrich_activity_climbing` tool. Skipped via internal kwarg when called immediately post-POST.
- **Error returns:** tools return strings on error (MCP protocol); `make_intervals_request` returns `{"error": True, "status_code": ..., "message": ...}` on HTTP failure; `_enrich_impl` and the new tools check `isinstance(result, dict) and "error" in result`.
- **Naming:** tool functions are `verb_noun_qualifier`: `create_climbing_activity`, `complete_climbing_session` follow the `enrich_activity_climbing` / `verify_custom_fields_setup` model.
- **Many-arg tools:** `# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-return-statements,too-many-branches,too-many-locals,too-many-statements` — already on `enrich_activity_climbing`; new tools will need similar.

### Integration Points
- `tools/climbing.py` — gains `create_climbing_activity` and `complete_climbing_session` as new public `@mcp.tool()`-decorated functions. The existing `enrich_activity_climbing` body is refactored into `_enrich_impl`; the public tool keeps its signature and is rewritten as a thin wrapper. `verify_custom_fields_setup`, `_verify_custom_fields_setup_impl`, `_README_POINTER`, and the imports are unchanged.
- `tests/test_climbing_create.py` — **new test file** (D-20). Covers: duplicate-guard hit/miss for both tools, paired_event_id readback verification, Pitfall #4 timezone case, name template generation, `_skip_conflict_scan` path, integration of `_enrich_impl` from the new tools, error paths (POST fail, enrichment fail-after-POST-success).
- `tests/test_climbing_write.py` — **untouched** (Phase 2 tests; the `enrich_activity_climbing` refactor preserves public behavior, so its tests must still pass). Run `pytest tests/test_climbing_write.py -q` after the refactor as a regression check.
- `utils/formatting.py` — possibly extended to render `paired_event_id` in `format_climbing_activity` if the readback display benefits from it. Additive-only extension; existing fields untouched.
- `scripts/` — optional `scripts/smoke_phase3.py` mirroring `scripts/smoke_phase2.py` (Claude's Discretion). Not required if Phase 2's smoke-test infrastructure is reusable.
- `server.py` — **no changes**. `tools/climbing.py` is already imported (Phase 1).
- `README.md` — **no changes**. SETUP-01 docs already cover the seven custom fields; Phase 3 adds no new user prerequisites.

</code_context>

<specifics>
## Specific Ideas

- **Duplicate-guard error message format.** List each matching activity on its own line: `i142495224 — "Sport gym session" (2026-04-27)` so Claude can read it back as an actionable list and offer to enrich a specific id rather than guessing. The error string ends with a hint: `"Call enrich_activity_climbing(activity_id=..., ...) to add climbing metadata to an existing activity."`
- **Title template human-readable.** `discipline_human` map: `bouldering` → "Bouldering", `sport_lead` → "Sport lead", `top_rope` → "Top rope", `trad` → "Trad". Auto-generated titles look like `"Climbing — Bouldering — 2026-04-27"`. Never expose enum values verbatim in titles — they appear in the Intervals.icu UI.
- **`complete_climbing_session` already-paired check.** If the GET on the planned event returns an event whose `paired_event_id` is already non-null (or whose `completed`-style flag is set, depending on the response shape — confirm during planning), the tool fails with: `"Event {event_id} is already paired to activity {paired_id}. Call enrich_activity_climbing(activity_id={paired_id}, ...) to add climbing metadata."`
- **Pitfall #4 test case.** Add a unit test with input `date="2026-04-27"` and assert `start_date_local == "2026-04-27T00:00:00"` exactly. Add a second test that monkeypatches `datetime.utcnow()` to return `2026-04-28T00:30:00Z` (next-day UTC) and confirms the activity body still uses `"2026-04-27T00:00:00"` from the user input — proves the tool never derives the date from system clock.
- **Readback verification of `paired_event_id`.** After POST in `complete_climbing_session`, the tool reads the activity back and confirms `paired_event_id == event_id`. If absent or different, return an error naming the activity_id and the mismatch — strong signal that explicit-set didn't take.
- **Refactor diff discipline.** The `enrich_activity_climbing` → `_enrich_impl` extraction should preserve all 14 P2 decisions (D-12 through D-25 carry-forward). Run `pytest tests/test_climbing_write.py -q` as the first checkpoint after the refactor; the entire Phase 2 test suite must pass unchanged before any new tool code is written.

</specifics>

<deferred>
## Deferred Ideas

- **`force_create=True` flag** on either new tool to bypass the duplicate guard for legitimate same-day duplicates (e.g., AM gym + PM outdoor). Defer to v2 unless real demand surfaces during use.
- **Free-text `description` / `notes` parameter** on `create_climbing_activity` for free-form session notes. Defer; users can edit the description in the Intervals.icu UI post-create. Add only if a real need appears.
- **`type="Other"` alternative** for climbing activities. Defer — `WeightTraining` works and feeds rpeTSS (Intervals.icu's load math). Revisit only if Intervals.icu introduces a native climbing type.
- **`duration_minutes` bounds (min/max)** — defer; trust the user. Adding bounds is a footgun (5h boulder day on a road trip is real).
- **Generic non-climbing manual-activity creation** (`write_activity` / `create_activity`) — v2 (`GEN-v2-01`).
- **Phase 4 status-tool side: how a duplicate-guarded but still-uncompleted planned event flows into CTL/ATL** — Phase 4 concern; out of scope here.
- **Auto-generating the title from session_focus or grades** (e.g., `"Bouldering V5 project session"`) — clever but premature; the current template is enough.
- **Improving the verify-fields readback heuristic** (false-positive on never-populated fields) — Phase 1 known limitation; carried forward, no change here.

### Reviewed Todos (not folded)

None — no pending todos in STATE.md to review; `gsd-sdk query todo.match-phase 3` returned 0 matches.

</deferred>

---

*Phase: 03-activity-creation-and-session-completion*
*Context gathered: 2026-04-27*
