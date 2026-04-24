# Phase 1: Foundation and Write-Path Spike - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Eliminate the two open API uncertainties by performing live writes (PUT `/athlete/{id}/wellness/{date}` and POST `/athlete/{id}/activities`) and build the shared utility layer — grade validation, climbing-domain enums, custom-field key constants, minimal formatter — that every Phase 2–4 tool will depend on.

**In scope for this phase:**
- Standalone spike script that exercises the two unverified write endpoints against Timo's real account using a far-future test date, with cleanup
- `utils/grades.py` — Font + French sport regex + `validate_grade(grade, discipline)`
- `utils/climbing.py` — `Discipline` and `SessionFocus` StrEnums + `CUSTOM_FIELD_KEYS` `FieldSpec` table
- `utils/formatting.py` — minimal `format_climbing_activity()` that renders the fields Phase 1 establishes
- `verify_custom_fields_setup` — Claude-callable MCP tool **and** reusable internal helper
- README section documenting the 7 required Intervals.icu custom fields; verify-tool docstring mirrors it
- `01-SPIKE-FINDINGS.md` capturing confirmed body shapes, upsert semantics, and any field-schema surprises

**Out of scope (belongs to later phases):**
- The actual `write_wellness_entry` and `enrich_activity_climbing` tools (Phase 2)
- `create_climbing_activity` and `complete_climbing_session` (Phase 3)
- Duplicate-guard logic (Phase 3)
- Any status/readiness reporting (Phase 4)
- Server wiring of new tools into `server.py` beyond what the verify-tool requires (Phase 5)

</domain>

<decisions>
## Implementation Decisions

### Spike Execution
- **D-01:** The spike runs as a **standalone async script** at `scripts/spike_write_endpoints.py`, executed via `uv run`. Not a pytest test (spike ≠ test; it writes to live data and must not run in CI).
- **D-02:** The script uses `make_intervals_request()` — no direct `httpx` — so that the same auth/retry/error paths the real tools use are exercised.
- **D-03:** Spike target date is **far-future** (use `2099-01-01` or similar). Script writes, reads back, and attempts to delete/blank the entries. If an activity `DELETE` endpoint is not confirmed available, the script leaves a manual cleanup checklist at the bottom of `01-SPIKE-FINDINGS.md` (delete via Intervals.icu web UI).
- **D-04:** Confirmed findings — request body shape, response shape, upsert vs replace semantics for wellness PUT, required vs optional fields for activities POST, native `icu_rpe` write behaviour, the viable `type` value for climbing activities (`"WeightTraining"` vs `"Other"`) — are written to `.planning/phases/01-foundation-and-write-path-spike/01-SPIKE-FINDINGS.md` as the canonical reference for Phase 2 and Phase 3 planners.

### Grade / Discipline Validation
- **D-05:** `utils/grades.py` provides **regex + typed helpers** — `FONT_RE`, `FRENCH_SPORT_RE`, and `validate_grade(grade: str, discipline: Discipline) -> str` that raises `ValueError` with a message naming the expected scale. No parser, no enum-of-all-grades.
- **D-06:** **Strict case + bare modifiers:**
  - Font must be uppercase (`6A`, `6A+`) — `FONT_RE = r'^[3-9][A-C](\+)?$|^[1-2]$'` (tune range for top-end if needed; the base pattern is the canonical commit)
  - French sport must be lowercase (`6a`, `6a+`) — `FRENCH_SPORT_RE = r'^[3-9][abc](\+)?$'`
  - `+` allowed. Slashes (`6A/6A+`), descriptors (`hard 6A`), and cross-case input are rejected. Case **is** the cross-scale guard — do not normalize.
- **D-07:** `Discipline` is a `StrEnum` in `utils/climbing.py` with members `BOULDERING = "bouldering"`, `SPORT_LEAD = "sport_lead"`, `TOP_ROPE = "top_rope"`, `TRAD = "trad"`. `indoor: bool` is a **separate** tool parameter — not encoded into discipline.
- **D-08:** `SessionFocus` is a `StrEnum` in `utils/climbing.py`: `POWER`, `ENDURANCE`, `TECHNIQUE`, `PROJECTING`, `MILEAGE` (values lowercase to match the `CUSTOM_FIELD_KEYS` option list).

### Custom-Field Prerequisite System
- **D-09:** **Field key convention:** lowercase underscore, unprefixed. Pinned keys for v1:

  | Key | Intervals.icu type | Options |
  |-----|-------------------|---------|
  | `discipline` | select | `bouldering`, `sport_lead`, `top_rope`, `trad` |
  | `indoor` | bool | — |
  | `session_focus` | select | `power`, `endurance`, `technique`, `projecting`, `mileage` |
  | `top_grade_sent` | text | — (validated against discipline by write tools) |
  | `top_grade_attempted` | text | — |
  | `sends` | integer | — |
  | `attempts` | integer | — |

  **Alignment requirement:** the `select` option strings must match the `Discipline` and `SessionFocus` StrEnum `.value`s exactly. Tests must assert this alignment so a future rename of one side fails loudly.

- **D-10:** `CUSTOM_FIELD_KEYS` is a **frozen dict of `FieldSpec` dataclasses** in `utils/climbing.py`. Single source of truth for: (a) the verify tool's expected-fields list, (b) Phase 2 write tools' payload keys, (c) the README setup section. No duplicated string constants elsewhere.
- **D-11:** `verify_custom_fields_setup` is **both** a Claude-callable MCP tool **and** an internal helper function used by every climbing-write tool as a pre-write guard. One implementation, two call sites.
- **D-12:** On missing fields: **hard block with named-field error.** Refuse to POST/PUT. Error message lists every missing field and points to the README section. No "warn and proceed" — Pitfall #2 says silent success on undefined custom fields is a class-A data-loss failure, and we do not accept it.
- **D-13:** Setup docs live in **README + verify-tool docstring**. The docstring mirrors the README table so Claude has the setup checklist in-context when the verify tool reports missing fields. No separate `docs/SETUP-CLIMBING.md` file in v1.

### Utility Layout
- **D-14:** Phase 1 creates **two new files**:
  - `src/intervals_mcp_server/utils/grades.py` — regex constants + `validate_grade`
  - `src/intervals_mcp_server/utils/climbing.py` — `Discipline`, `SessionFocus`, `FieldSpec`, `CUSTOM_FIELD_KEYS`
- **D-15:** `src/intervals_mcp_server/utils/formatting.py` is **extended** (not replaced) with a minimal `format_climbing_activity(activity: dict) -> str` that renders the fields Phase 1 establishes (discipline, indoor, session_focus, top_grade_sent/attempted, sends, attempts, `icu_rpe`). Phase 2 extends it further as new scenarios surface. This enables the spike to render its own readback.
- **D-16:** `utils/types.py` and `utils/validation.py` are **not modified** in Phase 1. Climbing types and validation do not mix into the general-purpose modules — this protects the existing workout-step types from unrelated churn and keeps grep discoverability tight ("climbing" → one file).
- **D-17:** The new climbing **MCP tool module** `src/intervals_mcp_server/tools/climbing.py` is created in Phase 1 **solely to register the `verify_custom_fields_setup` tool**. This establishes the file and the `server.py` import in Phase 1, so Phase 2 adds `write_wellness_entry` / `enrich_activity_climbing` to an already-wired module instead of touching `server.py` again.

### Cross-Cutting / Pitfall Guards
- **D-18:** **No `_`-prefixed imports from sibling tool modules** (Pitfall #11). If something in `activities.py` or `wellness.py` is worth sharing, it is promoted to `utils/` with a public name in the phase that needs it.
- **D-19:** Tests for `utils/grades.py` and `utils/climbing.py` are added in Phase 1 (`tests/test_grades.py`, `tests/test_climbing.py`) and must be discovered by `pytest --collect-only` — the test-drift check (Pitfall #14) is enforced per phase.
- **D-20:** Phase 1 makes **no changes to existing formatters or shared utilities that could regress existing tools** (Pitfall #12). All new code is purely additive; existing tests must still pass unchanged.

### Folded Todos
None — no pending todos match Phase 1 scope.

### Claude's Discretion
- Exact regex bounds for top-end grades (e.g., whether Font `9A+` is worth including given Timo's actual grade range). Planner picks a sensible range and documents it.
- Exact readback retry / timing for verify-on-write after Intervals.icu PUT — treat as implementation detail, not a discussion decision.
- Log level for the spike script (info vs debug).
- Whether `FieldSpec` is a `@dataclass(frozen=True)` or a `NamedTuple` — pick whichever reads best given how `utils/types.py` currently does dataclasses.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project-level contracts
- `.planning/PROJECT.md` — vision, Key Decisions table, Constraints, Out of Scope. Phase 1 must not invalidate any Key Decision.
- `.planning/REQUIREMENTS.md` — Phase 1 requirements: **SETUP-01** (README documents required custom fields), **SETUP-02** (verification path exists), **CLIMB-08** (grade validation against discipline).
- `.planning/ROADMAP.md` §"Phase 1: Foundation and Write-Path Spike" — Goal and Success Criteria.

### Research
- `.planning/research/PITFALLS.md` — especially Pitfall #2 (silent custom-field write failure), #3 (grade system ambiguity), #5 (MCP statelessness), #11 (private-helper coupling), #12 (shared-utility regression), #14 (test drift).
- `.planning/research/SUMMARY.md` — overview of the domain and why the existing codebase is shaped the way it is.
- `.planning/research/FEATURES.md` — what "closing the loop" means end-to-end; Phase 1 is the foundation, not the feature.

### Codebase context
- `.planning/codebase/STRUCTURE.md` — "Where To Add New Code" table. `utils/grades.py`, `utils/climbing.py`, `tools/climbing.py` land here per that table.
- `.planning/codebase/CONVENTIONS.md` — naming, error patterns, import ordering, docstring style (Google-style).
- `.planning/codebase/CONCERNS.md` — known issues in the existing code that Phase 1 must not worsen (module-size, formatter churn, test-coverage concentration).
- `.planning/codebase/INTEGRATIONS.md` — current Intervals.icu endpoint use and auth patterns.
- `.planning/codebase/TESTING.md` — test layout and pytest discovery rules.
- `AGENTS.md` — tooling guide (uv, pytest, ruff, mypy).

### Source files (read before modifying)
- `src/intervals_mcp_server/api/client.py` — the single HTTP boundary the spike and verify tool must use.
- `src/intervals_mcp_server/mcp_instance.py` — the one place `FastMCP` is constructed; new tool modules import `mcp` from here.
- `src/intervals_mcp_server/tools/wellness.py` — existing read-side wellness tool, reference for shape of PUT payload we're spiking.
- `src/intervals_mcp_server/tools/activities.py` — existing activities read tool; reference for `type` handling.
- `src/intervals_mcp_server/utils/validation.py` — pattern for how ValueErrors are raised with user-facing messages.
- `src/intervals_mcp_server/utils/types.py` — pattern for how existing enums / dataclasses are shaped.
- `src/intervals_mcp_server/utils/formatting.py` — pattern for existing `format_*` functions; `format_climbing_activity` mirrors that style.
- `src/intervals_mcp_server/server.py` — where `tools/climbing.py` will be imported to trigger decorator registration.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `make_intervals_request()` in `api/client.py` — the single HTTP boundary the spike must use; already handles auth, retry on closed-client, and error mapping.
- `resolve_athlete_id()` in `utils/validation.py` — pattern for how tool parameters fall back to env config; the verify tool uses it.
- `@mcp.tool()` decorator pattern (via `mcp_instance.mcp`) — `tools/climbing.py` registers `verify_custom_fields_setup` the same way existing tools do.
- Existing `format_wellness_entry()` and `format_activity_summary()` in `utils/formatting.py` — `format_climbing_activity()` follows the same shape (dict in → str out, `_KeyTracker` optional depending on how many fields are rendered).
- Existing tests in `tests/test_server.py` and `tests/test_make_intervals_request.py` — template for tool-registration assertions and `make_intervals_request` mocking pattern (monkeypatch + asyncio.run).

### Established Patterns
- **Naming:** snake_case modules, snake_case functions, PascalCase dataclasses/enums, UPPER_SNAKE_CASE constants. StrEnum values are lowercase strings (matches `WorkoutTarget` etc. in `utils/types.py`, adjusted to lowercase per our custom-field option alignment).
- **Error handling:** API errors return `{"error": True, "status_code": ..., "message": "..."}` from `make_intervals_request()`. Tools return error messages as strings for MCP protocol compatibility. Validators raise `ValueError` with user-facing messages.
- **Docstrings:** Google-style (Args, Returns, Raises). For write tools the docstring doubles as the LLM's instruction on what to gather conversationally (Pitfall #6) — `verify_custom_fields_setup`'s docstring is the first of those and sets the tone.
- **Import ordering:** stdlib, third-party, local (per `CONVENTIONS.md`).
- **Line length:** 100 chars, ruff-formatted.

### Integration Points
- `src/intervals_mcp_server/server.py` gains one new import: the `tools/climbing.py` module, placed alongside existing `from intervals_mcp_server.tools import activities, events, wellness, custom_items` lines. That single line is the only `server.py` edit Phase 1 requires.
- README gains one new section (after whichever existing setup section fits best — planner decides placement) titled "Climbing setup — required Intervals.icu custom fields" with the 7-field table.
- `scripts/` directory may not exist yet — planner creates it if needed for `spike_write_endpoints.py`.

</code_context>

<specifics>
## Specific Ideas

- Discipline and SessionFocus StrEnum values must be lowercase snake_case strings matching `CUSTOM_FIELD_KEYS` option tuples exactly. A unit test asserts this alignment — changing one side without the other fails the test.
- The spike script's output should contain paste-ready "confirmed body shapes" code blocks so Phase 2's planner can copy them into tool implementations verbatim.
- The verify tool's error message, when fields are missing, lists each missing field key on its own line and links to the README section anchor — Claude reads this and can relay it to the user as an actionable checklist.
- Font regex is the primary cross-scale guard (uppercase letters). Keep the French sport regex strictly lowercase. Do not add a "case-insensitive" flag anywhere.
- `start_date_local` format concerns (Pitfall #4) do not apply in Phase 1 because Phase 1 does not create a real activity beyond the spike — but the spike script must already use `YYYY-MM-DDT00:00:00` format so Phase 3 inherits a correct pattern from the start.

</specifics>

<deferred>
## Deferred Ideas

- **V-scale (V0–V17) and YDS (5.x) grade support** — out of scope per `PROJECT.md` Out of Scope. The `grades.py` module is structured so adding these later means adding two more regex + dispatch arms to `validate_grade`, not rewriting.
- **Grade-rank comparison / arithmetic** (`is_harder_than(a, b)`) — not needed until a feature that compares grades ships (e.g., grade-band aggregation in v2 status report). Keep grade validation string-in / string-out for v1.
- **Finger / skin condition field** (`CLIMB-v2-01`) — v2 requirement; not in `CUSTOM_FIELD_KEYS`.
- **Venue / crag field** (`CLIMB-v2-02`) — v2 requirement; not in `CUSTOM_FIELD_KEYS`.
- **Auto-generating the README field table from `CUSTOM_FIELD_KEYS`** — tempting single-source trick. Deferred because it adds a doc-generation step before it's worth it; for now the README table and `CUSTOM_FIELD_KEYS` are manually kept in sync with a test asserting the mapping matches what the README declares (optional; planner decides).
- **Delete endpoint for activities** — spike will confirm or deny. If denied, Phase 1 ships with a manual cleanup checklist and the spike runs to far-future date; Phase 3's duplicate guard absorbs this limitation.

### Reviewed Todos (not folded)
None — no pending todos in STATE.md.

</deferred>

---

*Phase: 01-foundation-and-write-path-spike*
*Context gathered: 2026-04-24*
