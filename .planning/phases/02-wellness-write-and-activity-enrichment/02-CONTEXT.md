# Phase 2: Wellness Write and Activity Enrichment - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver two write tools for the climbing training loop on top of the Phase 1 utility layer:

1. **`write_wellness_entry`** — Conversationally log wellness data with upsert semantics. Subjective + objective metrics for a single date.
2. **`enrich_activity_climbing`** — Add climbing metadata (discipline, indoor, session focus, grades, sends/attempts) and the native `icu_rpe` field to an existing Intervals.icu activity by ID.

Both tools must route through `make_intervals_request()` (PROJECT.md constraint), respect MCP statelessness (single-shot, all fields as parameters — Pitfall #5), and leave a paste-ready smoke-test trail Phase 3 will inherit.

**In scope for this phase:**
- Targeted second probe (extending the Phase 1 spike approach) to resolve three open API unknowns the Phase 1 spike couldn't close: activity custom-field PUT body shape, wellness subjective-field valid scales, and `icu_rpe` write path.
- `utils/wellness.py` — wellness-specific constants (range tables) and helpers (unit conversions, drop-None body builder), with tests.
- `write_wellness_entry` in `tools/wellness.py` — explicit named-param tool with hard scale validation, user-friendly units, upsert-by-omission, no custom-field guard.
- `enrich_activity_climbing` in `tools/climbing.py` — explicit named-param tool with discipline-aware grade validation, default-deny re-enrichment guard with override flag + audit message, supplied-fields-only readback verification, conditional verify-fields guard.
- Extension of `format_climbing_activity` to render readback after enrichment.
- `02-SPIKE-FINDINGS.md` capturing the second-probe results.
- An integration smoke-test path Phase 3 can build on.

**Out of scope (belongs to later phases):**
- `create_climbing_activity` — Phase 3 (CLIMB-02).
- `complete_climbing_session` (planned-event-to-activity linking) — Phase 3 (CLIMB-01).
- Duplicate-activity guard — Phase 3 (CLIMB-09).
- Status / readiness reporting — Phase 4.
- Server.py wiring is already done (Phase 1 added `tools/climbing.py` import) — Phase 2 only adds tools to the existing module; `tools/wellness.py` is already imported.
- `verify_custom_fields_setup` itself — already shipped in Phase 1; Phase 2 only consumes `_verify_custom_fields_setup_impl` as a guard.
- Improving the verify-fields readback heuristic (false-positive on never-populated fields) — known limitation, document workaround if it surfaces during smoke-test.

</domain>

<decisions>
## Implementation Decisions

### API uncertainty resolution (open from Phase 1 spike)

- **D-01:** Plan 02-01 is a targeted second-probe script that resolves all three open unknowns before any tool implementation begins:
  - **(a) Activity custom-field PUT shape** — try variations of the failing `PUT /activity/{id}` body (top-level keys, nested envelopes, alternate URLs like `PUT /athlete/{id}/activity/{id}` and `POST /activity/{id}`) until a body roundtrips through readback.
  - **(b) Wellness subjective-field valid scales** — probe `fatigue`, `stress`, `motivation`, `mood`, `soreness`, `sleep_quality` with values across 1-4 and 1-10; record which range each accepts.
  - **(c) `icu_rpe` write path** — try `icu_rpe: 6` in the same PUT as custom fields; if the call fails, isolate `icu_rpe` to its own PUT to confirm write semantics.
- **D-02:** Findings land in `.planning/phases/02-wellness-write-and-activity-enrichment/02-SPIKE-FINDINGS.md` (new file). Phase 1's spike findings stay closed; Phase 2 owns its own discovery artifacts.
- **D-03:** The probe script uses `make_intervals_request()` against `SPIKE_DATE = "2099-01-01"`, follows the Phase 1 spike script structure (`scripts/spike_write_endpoints_phase2.py` or extend `scripts/spike_write_endpoints.py` — planner picks; either is acceptable as long as the new findings file is the canonical reference).
- **D-04:** Plan 02-04 (`enrich_activity_climbing`) cannot start until D-01's findings are reviewed. Plan 02-02 / 02-03 (wellness side) can start in parallel as soon as D-01's wellness scale results land — they don't depend on the activity-write probe.
- **D-05:** **Hard-stop fallback.** If the second probe still cannot land custom fields on an activity via any reasonable body shape, **stop Phase 2 and re-discuss**. Do not ship a half-broken `enrich_activity_climbing`. The Key Decision "Structured climbing data → Intervals.icu custom fields" in PROJECT.md may need revisiting (description-as-structured-text fallback or scope-cut to RPE-only) — that decision is explicitly out of scope for this phase to make unilaterally.

### `write_wellness_entry` API surface

- **D-06:** **Parameter shape — explicit named params, no escape hatch.** One Optional param per supported field: `date` (required, `YYYY-MM-DD`), `sleep_hours`, `sleep_quality`, `soreness`, `fatigue`, `motivation`, `stress`, `mood`, `hrv`, `resting_hr`, plus the standard `athlete_id` / `api_key`. New wellness fields require a deliberate signature change — matches v1 climbing-first scope.
- **D-07:** **Hard scale validation, ranges locked from D-01(b) probe results.** A `WELLNESS_RANGES` constant in `utils/wellness.py` maps each numeric param to its `(min, max)` tuple based on what the probe confirms. Out-of-range values raise `ValueError` with a clear message naming the expected range — same pattern as `validate_grade()`. No "warn and pass through" — silent contamination is the failure mode we explicitly reject.
- **D-08:** **User-friendly units in, API units inside.** `sleep_hours: float` (e.g. `8.0`) is the public param; the tool converts to `sleepSecs = int(round(sleep_hours * 3600))` before the PUT. Document the conversion in the docstring so Claude knows to gather "hours of sleep". The same pattern applies to any other unit-mismatched field surfaced by the probe (none expected today). HRV (ms) and resting_hr (bpm) pass through unchanged.
- **D-09:** **Upsert via drop-None.** Build the PUT body as `{api_key: value for param, value in candidates.items() if value is not None}`. Mapping from public param name to API field name (`sleep_hours → sleepSecs`, `resting_hr → restingHR`, `mood → mood`, etc.) lives in a small `_PARAM_TO_API_FIELD` dict in `tools/wellness.py` next to the tool. No explicit clear-field mechanism in v1 — out of scope.
- **D-10:** **Reject empty calls.** If every wellness param is None (only `date` was supplied), the tool returns an error instead of issuing a no-op PUT.
- **D-11:** **Readback after wellness PUT.** GET `/athlete/{id}/wellness?oldest={date}&newest={date}` after the PUT and confirm each supplied field roundtrips. If any supplied field is missing or different, return an error. Cheap and prevents silent loss (mirrors Pitfall #2 thinking, applied to wellness).

### `enrich_activity_climbing` API surface

- **D-12:** **Parameter contract — activity_id required, climbing fields all optional.** Signature:
  ```python
  async def enrich_activity_climbing(
      activity_id: str,                      # required
      discipline: str | None = None,         # required if any grade is set
      indoor: bool | None = None,
      session_focus: str | None = None,
      top_grade_sent: str | None = None,
      top_grade_attempted: str | None = None,
      sends: int | None = None,
      attempts: int | None = None,
      rpe: int | None = None,                # 1-10 → icu_rpe (native)
      override: bool = False,                # Pitfall #10 guard bypass
      athlete_id: str | None = None,
      api_key: str | None = None,
  ) -> str:
  ```
  At-least-one-supplied check: if every climbing field (everything except `activity_id`, `override`, `athlete_id`, `api_key`) is None, refuse with "nothing to write". If any of `top_grade_sent` / `top_grade_attempted` is supplied, `discipline` must also be supplied — grade validation depends on it.
- **D-13:** **Discipline-aware grade validation runs before any API call.** Use the existing `validate_grade(grade, discipline)` from `utils/grades.py` (Phase 1, D-05). Font-on-route or French-on-boulder → `ValueError` with named expected scale.
- **D-14:** **Re-enrichment: default-deny + explicit `override=True`.** Before PUT, GET the activity. For each supplied climbing field, check the activity's current value:
  - If any supplied field already has a non-null value AND `override` is False → refuse with a list of conflicting fields and their current values, and a hint to pass `override=True` if intentional.
  - If `override=True` → proceed with the write AND immediately call `add_activity_message(activity_id, ...)` recording the override and the prior values that are being overwritten. Audit trail lives in Intervals.icu's own message log (matches Pitfall #10 mitigation, no shadow store).
  - `icu_rpe` is included in the conflict check the same way as custom fields (overwriting prior RPE is also history-mutation).
- **D-15:** **Readback verifies only supplied fields.** After PUT, GET `/activity/{id}` and confirm each supplied field appears in the readback with the exact value sent. If any supplied field is missing (silent ignore — Pitfall #2) or has a different value, return a clear error: list which fields didn't land, and add the README pointer (`_README_POINTER` from `tools/climbing.py`) when custom fields are involved. Do not check non-supplied fields.
- **D-16:** **`icu_rpe` write co-located with custom fields, contingent on probe.** If D-01(c) confirms a single PUT body can carry both `icu_rpe` and custom-field keys, do that — single PUT, single readback. If the probe finds `icu_rpe` requires a separate endpoint, fall back to two writes in fixed sequence (RPE first, then custom fields). On partial failure (RPE landed, custom fields didn't), return an explicit error naming what landed and what didn't — no silent partial state. Planner records the chosen path in 02-SPIKE-FINDINGS.md and the tool docstring.

### Module placement & guard pattern

- **D-17:** **`write_wellness_entry` lives in `tools/wellness.py`.** Wellness writes are not climbing-specific (WELL-01/02/03 cover general wellness logging — sleep, HRV, RHR, mood, etc.). The existing `tools/wellness.py` is small (71 lines, only `get_wellness_data`) — adding `write_wellness_entry` there keeps the wellness domain together. `tools/climbing.py` stays focused on climbing-specific tools.
- **D-18:** **`enrich_activity_climbing` lives in `tools/climbing.py`.** Climbing-specific by design; sits next to `verify_custom_fields_setup` (the guard it consumes) and the future Phase 3 climbing tools.
- **D-19:** **New `utils/wellness.py` module.** Houses `WELLNESS_RANGES` (the locked range table), unit converters (`sleep_hours_to_secs`), and `build_wellness_put_body(params: dict) -> dict` (the drop-None + name-translation helper). `tools/wellness.py` imports from it. Mirrors the Phase 1 split (`utils/grades.py` + `utils/climbing.py`) — keeps `utils/climbing.py` climbing-only per D-16's spirit.
- **D-20:** **Verify-fields guard fires conditionally on `enrich_activity_climbing`.** If the call writes only `rpe` (no custom-field params supplied), skip the guard — `icu_rpe` is a native field and doesn't depend on user-defined custom fields. If any of (`discipline`, `indoor`, `session_focus`, `top_grade_sent`, `top_grade_attempted`, `sends`, `attempts`) is supplied, run `_verify_custom_fields_setup_impl(...)` before PUT and hard-block on missing fields with the named-field error format (D-12 from Phase 1).
- **D-21:** **No verify-fields guard on `write_wellness_entry`.** Wellness fields are all native to Intervals.icu's wellness model — they don't require user-defined custom fields. The verify gate exists to protect climbing custom-field writes from silent failure (Pitfall #2). One short code comment at the call site explains why so future-Claude doesn't add it back "for consistency".

### Cross-cutting / Pitfall guards

- **D-22:** **No `_`-prefix imports from sibling tool modules.** Phase 1 D-18 carried forward. If `tools/wellness.py` and `tools/climbing.py` need to share something (e.g., the readback-verification helper pattern), promote it to `utils/`.
- **D-23:** **Tests live in `tests/test_wellness_write.py` and `tests/test_climbing_write.py`** (separate from the existing `test_climbing.py` which covers the verify tool from Phase 1) and must be discovered by `pytest --collect-only` per Pitfall #14. The existing wellness read tool's test already lives in `test_server.py`; the new write tool gets its own file because the test surface is bigger.
- **D-24:** **No regression to existing tools.** `tools/wellness.py` gains `write_wellness_entry` additively; `get_wellness_data` signature and behavior are untouched. `format_climbing_activity` is *extended* to handle the new readback scenarios, not rewritten (Phase 1 D-15 carried forward).
- **D-25:** **Smoke-test gating.** The integration smoke-test (live API call from Plan 02-05) is a standalone script (similar in spirit to the Phase 1 spike), not a pytest test, so it never runs in CI. The script writes to a far-future date and uses DELETE for cleanup (confirmed available by Phase 1 spike).

### Folded Todos

None — STATE.md "Pending Todos" is empty.

### Claude's Discretion

- Exact wellness API field-name mapping (`mood` vs `feel`, etc.) — confirm field names from the Phase 1 spike's wellness response and lock in `_PARAM_TO_API_FIELD` accordingly.
- Whether the second probe extends `scripts/spike_write_endpoints.py` or creates `scripts/spike_write_endpoints_phase2.py` — both fine, planner picks; the canonical findings file is what matters.
- Exact mechanics of `add_activity_message` for the override audit trail (call format, message text template) — implementation detail.
- Order of arguments in `enrich_activity_climbing` after `activity_id` — rough grouping (discipline → grade-related → counts → rpe → override → ids) is fine; planner can adjust.
- Pre-existing test file `tests/test_climbing.py` may grow new sections OR a new file `test_climbing_write.py` may be created for the enrich tool — planner's call based on file size after D-23 lands.
- Whether to wire any user-friendly `feel` parameter (1-5 emoji-style) — currently not in scope; defer unless probe surfaces an Intervals.icu equivalent worth supporting.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project-level contracts
- `.planning/PROJECT.md` — vision, Key Decisions table (especially "Structured climbing data → Intervals.icu custom fields", "RPE → native `icu_rpe` field", "Climbing fields collected as optional tool parameters"), Constraints, Out of Scope. Phase 2 must not invalidate any Key Decision; D-05 explicitly defers any such invalidation to a re-discuss step.
- `.planning/REQUIREMENTS.md` — Phase 2 requirements: **WELL-01, WELL-02, WELL-03, CLIMB-03, CLIMB-04, CLIMB-05, CLIMB-06, CLIMB-07, CLIMB-10**.
- `.planning/ROADMAP.md` §"Phase 2: Wellness Write and Activity Enrichment" — Goal and four Success Criteria.

### Phase 1 carry-forward (mandatory)
- `.planning/phases/01-foundation-and-write-path-spike/01-CONTEXT.md` — Decisions D-09 (CUSTOM_FIELD_KEYS spec), D-11 (verify is also internal helper), D-12 (hard-block on missing fields), D-15 (extend format_climbing_activity), D-17 (climbing tools live in tools/climbing.py), D-18 (no `_`-prefix sibling imports), D-19/D-20 (test discovery, no regression).
- `.planning/phases/01-foundation-and-write-path-spike/01-SPIKE-FINDINGS.md` — confirmed wellness PUT body shape (sleepSecs, soreness), confirmed POST /athlete/{id}/activities/manual returns id, confirmed DELETE /activity/{id} works, **the unresolved 422 on activity custom-field PUT and the 422 on wellness `fatigue: 5`** (these are exactly what Plan 02-01 must close), full activity readback shape including the native `icu_rpe` field.
- `scripts/spike_write_endpoints.py` — reference structure for the Plan 02-01 second probe (logging, redaction, findings-write pattern).

### Research
- `.planning/research/PITFALLS.md` — especially **#2** (silent custom-field write failure → readback verification mandatory; D-15), **#3** (grade-discipline coupling; D-13), **#5** (MCP statelessness — single tool, all params), **#6** (docstrings instruct the LLM what to ask), **#10** (retroactive grade overwrite; D-14 override flag + audit message), **#11** (no `_`-prefix sibling imports; D-22), **#12** (no shared-utility regression; D-24), **#14** (test discovery; D-23). Integration gotcha: "Omit absent keys from PUT body; null clears the field" → D-09.
- `.planning/research/SUMMARY.md` — domain context.

### Codebase context
- `.planning/codebase/STRUCTURE.md` — "Where To Add New Code" table validates D-17 (`tools/wellness.py`), D-18 (`tools/climbing.py`), D-19 (`utils/wellness.py`).
- `.planning/codebase/CONVENTIONS.md` — naming, error patterns (return error dict / string for tools), Google-style docstrings, import ordering, `# pylint: disable=too-many-arguments` pattern (write tools have many params).
- `.planning/codebase/CONCERNS.md` — module-size warning (don't pile onto activities.py / wellness.py is now in scope to extend modestly), formatter-churn warning (extend, don't mutate).
- `.planning/codebase/INTEGRATIONS.md` — Intervals.icu endpoint patterns and auth.
- `.planning/codebase/TESTING.md` — test layout, pytest discovery rules, mocking pattern (`monkeypatch` + `asyncio.run`).
- `AGENTS.md` — uv, pytest, ruff, mypy tooling.

### Source files (read before modifying)
- `src/intervals_mcp_server/api/client.py` — the single HTTP boundary; `make_intervals_request(url, data, method, params, api_key)`.
- `src/intervals_mcp_server/mcp_instance.py` — `mcp` import for `@mcp.tool()` registration.
- `src/intervals_mcp_server/tools/wellness.py` — current 71-line module; `write_wellness_entry` joins it.
- `src/intervals_mcp_server/tools/climbing.py` — Phase 1 module; hosts `_verify_custom_fields_setup_impl` (the guard D-20 uses) and `_README_POINTER` (the error-message tail D-15 uses); `enrich_activity_climbing` joins it.
- `src/intervals_mcp_server/tools/activities.py` — reference for `add_activity_message` usage (D-14 audit trail) and activity GET patterns (D-15 readback).
- `src/intervals_mcp_server/utils/climbing.py` — `Discipline`, `SessionFocus`, `CUSTOM_FIELD_KEYS`, `FieldSpec`. Phase 2 reads only; does not modify (per D-19, wellness ranges live in new `utils/wellness.py`).
- `src/intervals_mcp_server/utils/grades.py` — `validate_grade(grade, discipline)`; D-13 calls it directly.
- `src/intervals_mcp_server/utils/validation.py` — `resolve_athlete_id` pattern; both new tools use it.
- `src/intervals_mcp_server/utils/formatting.py` — `format_climbing_activity` (Phase 1) is extended in Plan 02-05; the existing `format_wellness_entry` is the model for any new wellness rendering.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `make_intervals_request(url, data, method, params, api_key)` — supports PUT/POST/DELETE/GET via `method` param; both Phase 2 tools use it directly.
- `_verify_custom_fields_setup_impl(athlete_id, api_key) -> tuple[bool, list[str], str]` in `tools/climbing.py` — the pre-write guard for `enrich_activity_climbing` (D-20). Already returns the structured tuple; the tool calls it and short-circuits on `not ok`.
- `_README_POINTER` in `tools/climbing.py` — the tail string for missing-field errors. Reuse in D-15's readback-failure message when custom fields are involved.
- `validate_grade(grade, discipline)` in `utils/grades.py` — drop-in for D-13.
- `Discipline`, `SessionFocus`, `CUSTOM_FIELD_KEYS` in `utils/climbing.py` — frozen spec; `enrich_activity_climbing` references these directly.
- `resolve_athlete_id(athlete_id, config.athlete_id)` in `utils/validation.py` — both new tools use this pattern (matches existing `get_wellness_data` and `verify_custom_fields_setup`).
- `format_wellness_entry(entry, include_all_fields)` in `utils/formatting.py` — model for any new wellness-write rendering.
- `format_climbing_activity(activity)` in `utils/formatting.py` — already exists from Phase 1 (currently renders 11 fields). Plan 02-05 extends to handle `icu_rpe` post-enrichment readback rendering.
- Existing test patterns in `tests/test_server.py` and `tests/test_make_intervals_request.py` — `monkeypatch` `make_intervals_request`, run via `asyncio.run`. Mirror these for the new write tools.

### Established Patterns
- **Naming:** snake_case modules and functions; `PascalCase` dataclasses/enums; `UPPER_SNAKE_CASE` module constants; tool functions are present-tense verbs (`get_*`, `write_*`, `enrich_*`, `verify_*`, `add_or_update_*`).
- **Error handling:** `make_intervals_request()` returns `{"error": True, "status_code": ..., "message": "..."}` on failure; tools check `isinstance(result, dict) and "error" in result` and return a user-facing error string. Validators raise `ValueError` with names of expected formats. Tools always return `str` (MCP protocol contract).
- **Docstrings:** Google-style (Args, Returns, Raises). For write tools: the docstring is the LLM's instruction sheet — explicitly enumerate which params Claude should gather conversationally before calling (Pitfall #6). The Phase 1 `verify_custom_fields_setup` docstring is the established template.
- **Tool registration:** `@mcp.tool()` decorator; module imports `mcp` from `mcp_instance`; module is imported by `server.py`. `tools/climbing.py` and `tools/wellness.py` are both already imported — Phase 2 needs zero `server.py` edits.
- **Many-arg tools:** `# pylint: disable=too-many-arguments` is the established pattern for tools that exceed the 8-arg ruff/pylint limit (`get_activities` already does this).
- **Import order:** stdlib → third-party → local; line length 100; ruff-formatted.

### Integration Points
- `tools/wellness.py` — gains `write_wellness_entry`. No changes to `get_wellness_data` signature or behavior.
- `tools/climbing.py` — gains `enrich_activity_climbing`. `_verify_custom_fields_setup_impl` and `_README_POINTER` get a second consumer (the new tool); both are currently used only by the public `verify_custom_fields_setup`.
- `utils/wellness.py` — **new file**. Mirrors the `utils/grades.py` shape (a small focused module: range constants + 2-3 helpers + module docstring).
- `utils/climbing.py` — read-only; no changes (per D-19).
- `utils/formatting.py` — `format_climbing_activity` extended (additive only); `format_wellness_entry` untouched.
- `scripts/` — gains either an extension to `spike_write_endpoints.py` or a new `spike_write_endpoints_phase2.py` (D-03; planner picks).
- `tests/test_wellness_write.py` and `tests/test_climbing_write.py` — new test files (D-23). Existing test files unchanged.
- README — no required changes in Phase 2 unless the second probe surfaces a new user prerequisite (e.g., a wellness setup step). Setup docs already cover the 7 climbing custom fields.

</code_context>

<specifics>
## Specific Ideas

- The second-probe script must produce paste-ready code blocks in `02-SPIKE-FINDINGS.md` showing the *exact body shape that worked* for activity custom-field PUT — Plan 02-04 will copy that body shape verbatim into `enrich_activity_climbing`.
- The wellness range table is a single source of truth; tests must assert that every numeric param in `write_wellness_entry`'s signature has a corresponding entry in `WELLNESS_RANGES` (changing one without the other fails the test). Mirrors the Phase 1 alignment test for `Discipline.value` ↔ `CUSTOM_FIELD_KEYS["discipline"].options`.
- The `enrich_activity_climbing` re-enrichment refusal message should list each conflicting field on its own line with its current value (e.g., `discipline: bouldering (already set)`), so Claude can read it back to the user as an actionable list rather than a generic error.
- The `add_activity_message` audit message for an override should be a single line in a recognizable format: `[enrich override] discipline: bouldering→sport_lead, top_grade_sent: 6A→6A+ (prior values preserved here)`. Searchable, parsable, doesn't require schema.
- For the readback-verification error: when a wellness field is missing post-PUT, do not include the README pointer (it's a wellness API issue, not a custom-field setup issue). When a custom field is missing post-PUT, include the README pointer because that's almost always a setup problem.

</specifics>

<deferred>
## Deferred Ideas

- **Explicit wellness clear-field mechanism** — passing `clear_fields=["sleepSecs", "fatigue"]` to send `null` and clear values. v1 user has no need; would add a footgun. Deferred, no v2 ticket yet.
- **`extra_fields` escape hatch for wellness writes** — opening the door to `weight`, `comments`, `hydration`, etc. without a signature change. Deferred until a real use case appears (climbing-first scope holds).
- **Improving the verify-fields readback heuristic** (false-positive on never-populated fields) — Phase 1 known limitation; Phase 2 documents the workaround if it bites during smoke-test, doesn't fix it.
- **Auto-generating the docstring or wellness range table from a single source** — keep manual sync in v1, with tests asserting alignment. Premature DRY otherwise.
- **Status-tool-side data-quality flag for missing wellness fields** — Phase 4 concern; out of scope here.
- **Generic non-climbing manual-activity creation tool (`write_activity`)** — v2 (`GEN-v2-01`).
- **Finger / skin condition wellness field** — v2 (`CLIMB-v2-01`); not in `WELLNESS_RANGES`.
- **Dedicated `set_activity_rpe` tool** — single-purpose tool considered and rejected; `icu_rpe` rides inside `enrich_activity_climbing` (D-16) per the project's "single tool, all fields" decision.

### Reviewed Todos (not folded)

None — no pending todos in STATE.md to review.

</deferred>

---

*Phase: 02-wellness-write-and-activity-enrichment*
*Context gathered: 2026-04-25*
