# Phase 4: Training Status Report - Context

**Gathered:** 2026-04-29
**Status:** Ready for planning

<domain>
## Phase Boundary

A single read-only MCP tool — `get_training_status` — that reads training-load metrics (CTL/ATL/TSB) from Intervals.icu wellness daily entries, recent wellness signals (sleep, soreness, fatigue, HRV, RHR), and recent activity records, then returns ONE plain-text report of 400–600 tokens covering today's readiness, weekly load review, and long-term trend, with an explicit data-quality flag when recent climbing activities have noisy RPE coverage.

Read-only by design — no writes, no state, no shadow store. All HTTP through `make_intervals_request()`. Stateless / single-shot — Claude (the LLM) gathers any optional parameter (e.g., `as_of_date`) before calling the tool.

</domain>

<decisions>
## Implementation Decisions

### Report shape & framing
- **D-01:** **`get_training_status` returns a single plain-text string with minimal markdown.** Structure: three labeled sections in fixed order — `## Today` → `## This Week` → `## Long-Term Trend` — each with bullet lists. No tables, no code blocks. Markdown overhead is acceptable in the 400–600 token budget and significantly improves both human readability of raw output and Claude's ability to re-render the data.
- **D-02:** **Today's readiness shows TSB number AND a verbal band.** Format: `- Readiness: Balanced (TSB +3.4)`. The number lets Claude reason about magnitude; the band gives the user a quick verdict. Both are surfaced because we don't know whether the consumer is the user reading raw output or Claude paraphrasing — both audiences are first-class.
- **D-03:** **TSB band thresholds (standard).** `TSB > 25` → "Burnt out / Detraining"; `5 < TSB ≤ 25` → "Fresh"; `-10 ≤ TSB ≤ 5` → "Balanced"; `-25 ≤ TSB < -10` → "Fatigued (productive load)"; `TSB < -25` → "Risk". These widely-cited bands are explicit constants in `utils/status.py` (single source of truth, grep-discoverable). Tunability is a v2 question after real use.

### Data sources & TSB computation
- **D-04:** **CTL and ATL come from the wellness daily-entry training metrics.** Single API call: `GET /athlete/{id}/wellness?oldest={start}&newest={end}` covers the entire 42-day window for every section of the report — no per-activity reads of `icu_ctl`/`icu_atl`. Reuses the established read pattern from `tools/wellness.py::get_wellness_data`.
- **D-05:** **TSB is computed as `CTL - ATL` per entry.** Wellness API does not expose a `tsb` field directly (Phase 1 spike scope). Math is explicit and grep-able; no fallback to a possibly-future API field. Implementation note: per Intervals.icu's data model, CTL and ATL on the wellness entry are already the smoothed exponentially-weighted values, so a straight subtraction is correct.
- **D-06:** **Time windows (hardcoded for v1):**
  - Weekly load review: **7 days**
  - Long-term trend: **42 days** (covers a typical 6-week training block)
  - RPE coverage check: **14 days**
  - Wellness blend (recent sleep/soreness/fatigue/HRV/RHR): **7 days** (matches success criterion 2)
  All four windows are constants in `utils/status.py`. No tool params expose them in v1 — Claude (the LLM) does not need to control window length to deliver the report described in ROADMAP.md.
- **D-07:** **Walk-back fallback when today's wellness entry is missing.** If `entries[as_of_date]` has no CTL/ATL, scan back day-by-day up to **7 days** and use the most recent entry that has both. The Today section adds a one-line note: `Latest fitness data: {N} days ago.` If no entry within 7 days has both CTL and ATL, the Today section degrades to D-12 (graceful empty-section text).

### RPE data-quality flag
- **D-08:** **Threshold locked at >30% missing RPE** — matches ROADMAP success criterion 3 verbatim. No tuning until real-world use shows the warning fires too often or never.
- **D-09:** **Denominator is climbing activities only — `type == "WeightTraining"` (Phase 3 D-15 carry-forward).** v1 is climbing-first; non-climbing activities aren't part of v1's load story. Filter is applied to the activities returned for the 14-day window before computing the missing-RPE percentage.
- **D-10:** **"Lacks RPE" means the activity dict has no `icu_rpe` value or its value is `None` / absent.** A literal `0` is treated as logged data (some climbers may use 0 for no perceived effort). Explicit field-level check, not truthy/falsy.
- **D-11:** **Suppress the warning on small samples (`< 3` climbing activities in the 14-day window).** Replace it with a one-line note: `RPE coverage: low activity volume (< 3 sessions in last 14 days).` This prevents the threshold from firing on noisy denominators (1 of 2 missing = 50%) while still cueing the user that the readiness signal is light, not flagged.

### Token budget enforcement
- **D-12:** **Token budget verified by tests, not enforced at runtime.** Add `tiktoken` (cl100k_base encoding — Claude/GPT-compatible) to project deps. A unit test in `tests/test_status.py` asserts a representative full-data sample renders in 400–600 tokens. The tool itself does NOT count tokens at runtime or truncate sections — the budget is a design constraint, not a guard rail. Keeps the tool fast and the failure mode loud (test fails when the report drifts out of band, not silently truncated output at runtime).
- **D-13:** **Empty / sparse data → graceful per-section degradation.** Each section independently renders an explicit one-line explanation when its data is empty: `## Today\n- No wellness data in last 7 days.` / `## This Week\n- No CTL/ATL trend data in last 7 days.` / `## Long-Term Trend\n- No CTL/ATL trend data in last 42 days.` The tool always returns SOME report — never errors, never silently omits a section. Empty-section paths are also covered by the token-budget test (the empty-data variant must still land in 400–600 tokens).

### Module placement & code shape
- **D-14:** **New module: `src/intervals_mcp_server/tools/status.py` registers `get_training_status` as the only public tool.** Follows the Phase 1 climbing precedent (separate `tools/climbing.py` rather than piling onto the already-large `activities.py` / `wellness.py`). `status.py` imports from `tools/wellness.py` for the wellness-read helper if extracted, otherwise reuses `make_intervals_request()` directly per the project-level rule. No `_`-prefixed cross-tool imports (D-22 carry-forward across all prior phases).
- **D-15:** **New module: `src/intervals_mcp_server/utils/status.py` houses constants + helpers.** Members: `TSB_BANDS` (the D-03 thresholds), `WINDOW_DAYS_WEEKLY = 7`, `WINDOW_DAYS_LONG_TERM = 42`, `WINDOW_DAYS_RPE = 14`, `RPE_MISSING_THRESHOLD = 0.30`, `MIN_RPE_SAMPLE = 3`, `tsb_band(tsb: float) -> str`, `compute_rpe_coverage(activities: list[dict]) -> tuple[int, int]`, `format_today_section(...)`, `format_weekly_section(...)`, `format_longterm_section(...)`, `format_status_report(...)`. Mirrors the Phase 1/2 split of `tools/climbing.py` + `utils/climbing.py` and `tools/wellness.py` + `utils/wellness.py`.
- **D-16:** **Public signature:**
  ```python
  @mcp.tool()
  async def get_training_status(
      athlete_id: str | None = None,
      api_key: str | None = None,
      as_of_date: str | None = None,
  ) -> str:
  ```
  `as_of_date` defaults to today (UTC date in `YYYY-MM-DD`); lets Claude ask "what was my readiness on 2026-04-21". Standard `athlete_id` / `api_key` resolution pattern (carries forward from every prior tool). No window-override params (D-06).

### Cross-cutting / Pitfall guards (carry-forward)
- **D-17:** **All HTTP through `make_intervals_request()`** (project-level rule). No direct `httpx`. The tool issues two GETs in v1: one to `/athlete/{id}/wellness` (covers the 42-day window across all sections) and one to `/athlete/{id}/activities?oldest=...&newest=...` (14-day window for the RPE coverage check). Both share the standard auth/retry/error path.
- **D-18:** **Tests live in new `tests/test_status.py`.** Discovered by `pytest --collect-only` per Pitfall #14. No regression to existing tools.
- **D-19:** **Date format `YYYY-MM-DD` is the public contract for `as_of_date`.** Validate format up front and raise `ValueError` with a clear message — same pattern as climbing-tools' grade validation. Construct query-string `oldest`/`newest` as `YYYY-MM-DD` strings; never derive from `datetime.now()` for any user-facing date (Pitfall #4 carry-forward, even though the report is read-only).
- **D-20:** **No regression to existing tools.** `tools/wellness.py` and `tools/activities.py` are not modified. `format_climbing_activity` is not touched. The new code is purely additive.

### Claude's Discretion

The planner / executor have flexibility on:
- Whether `format_today_section` etc. each take dicts or unpack to typed kwargs (style choice; either is fine).
- Whether the wellness-blend bullet lists "sleep / soreness / fatigue / HRV / RHR" show 7-day mean, latest value, latest + delta-from-7d-mean, or another reasonable summary — pick what reads well in the 400–600 token budget. The success criterion only requires "incorporates" recent wellness signals; specific aggregation shape is implementation detail.
- Whether the test suite uses recorded JSON fixtures or hand-crafted dict literals — both are acceptable; project convention so far has been mostly hand-crafted dicts (see `tests/test_climbing_create.py`).

### Folded Todos

None — no pending todos matched Phase 4 scope.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project-level
- `.planning/PROJECT.md` — Core value, key decisions (especially "Status tool = single tool returning one combined report"), v1 / v2 split, out-of-scope guardrails
- `.planning/REQUIREMENTS.md` — STAT-01 / STAT-02 / STAT-03 / STAT-04 acceptance criteria, requirements traceability table
- `.planning/ROADMAP.md` — Phase 4 goal, success criteria, requirements list
- `CLAUDE.md` — Project working-style and key constraints (HTTP through `make_intervals_request()`, no shadow store, stateless tools)
- `AGENTS.md` — Contributor + tooling guide (uv, pytest, ruff, mypy)

### Codebase maps
- `.planning/codebase/STRUCTURE.md` — Module layout, where new code goes
- `.planning/codebase/CONVENTIONS.md` — Coding conventions; specifically the rule that new tools shouldn't bloat `activities.py` / `wellness.py`
- `.planning/codebase/CONCERNS.md` — Module-size concern that motivated the climbing-module precedent in Phase 1

### Prior phase decisions (carry-forward)
- `.planning/phases/01-foundation-and-write-path-spike/01-CONTEXT.md` — D-02 (HTTP via `make_intervals_request()`), D-14 (utils-vs-tools split pattern), D-22 (no `_`-prefix imports across sibling tool modules)
- `.planning/phases/02-wellness-write-and-activity-enrichment/02-CONTEXT.md` — D-08 (user-friendly units in / API units inside pattern; relevant if any aggregation needs unit conversion), wellness API path (`/athlete/{id}/wellness?oldest=...&newest=...`) confirmed
- `.planning/phases/03-activity-creation-and-session-completion/03-CONTEXT.md` — D-15 (`type == "WeightTraining"` is the climbing activity type — directly used by the RPE-coverage filter)
- `.planning/phases/01-foundation-and-write-path-spike/01-SPIKE-FINDINGS.md` — Wellness API response shape, confirmed presence of `ctl` / `atl` fields per daily entry, absence of `tsb` field

### External / domain references
- The Intervals.icu wellness API endpoint shape and field names — confirmed by Phase 1 spike findings; no external doc beyond what the spike captured.
- TSB band thresholds — derived from standard training-stress-balance literature (TrainingPeaks / Friel 2007); no specific external doc cited, the constants in D-03 ARE the project's source of truth.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`make_intervals_request()` (`src/intervals_mcp_server/api/client.py`)** — Sole HTTP boundary; handles auth header, retry, error mapping. New tool calls it twice (wellness range + activities range).
- **`get_wellness_data` (`src/intervals_mcp_server/tools/wellness.py`)** — Established pattern for `oldest`/`newest` window queries against `/athlete/{id}/wellness`. The new status tool's wellness fetch can mirror its query construction.
- **`format_*` helpers in `src/intervals_mcp_server/utils/formatting.py`** — Existing rendering pattern (bullet lists, section headings) for `format_activity_summary`, `format_wellness_entry`, `format_workout`. The new `utils/status.py` formatters follow the same shape — pure functions, take a dict / list, return a string.
- **`Discipline` and `SessionFocus` (`src/intervals_mcp_server/utils/climbing.py`)** — Not directly used by status, but the file is the reference for how project-specific enums + constants live in a `utils/` module. `utils/status.py` mirrors that layout: constants at top, dataclasses next, functions below.
- **Wellness range constants (`src/intervals_mcp_server/utils/wellness.py::WELLNESS_RANGES`)** — Reference pattern for "single source of truth dict at module top".

### Established Patterns
- **Single-tool-per-domain module:** `tools/climbing.py` was created in Phase 1 specifically to avoid bloating `tools/activities.py`. The same precedent applies here — `tools/status.py` is created for the same reason.
- **Hard validation up front, raise `ValueError` with a clear message:** Phase 1 D-06 / Phase 2 D-07 / Phase 3 D-19 / `validate_grade()` all follow this. `as_of_date` validation does the same.
- **`utils/<domain>.py` houses constants + helpers; `tools/<domain>.py` registers the MCP tool and orchestrates HTTP + formatting.** Phase 1 D-14, Phase 2 D-19. `utils/status.py` + `tools/status.py` follows directly.
- **Tests live in `tests/test_<domain>_*.py`** and are discovered by `pytest --collect-only` (Pitfall #14). `tests/test_status.py` mirrors `test_climbing_create.py`'s shape.

### Integration Points
- **Tool registration:** `src/intervals_mcp_server/server.py` imports each tool module to register MCP tools. Add `from intervals_mcp_server.tools import status  # noqa: F401` (or whatever the existing pattern is — planner confirms).
- **Wellness API path:** `/athlete/{id}/wellness?oldest={YYYY-MM-DD}&newest={YYYY-MM-DD}` — confirmed by Phase 1 spike + Phase 2 readback path.
- **Activities API path:** `/athlete/{id}/activities?oldest={YYYY-MM-DD}&newest={YYYY-MM-DD}` — same query-string shape as duplicate-guard scan in `tools/climbing.py::create_climbing_activity` (Phase 3).
- **Athlete ID + API key resolution:** Existing pattern reused — fall back to env vars `ATHLETE_ID` / `API_KEY` if not passed. The planner copies the existing 3-line resolution block from any P3 climbing tool.

</code_context>

<specifics>
## Specific Ideas

- **TSB bands are standard literature values** — the user picked the well-known set rather than custom climbing-tuned bands. Don't invent new thresholds in implementation; constants in D-03 are the contract.
- **The 42-day long-term window covers one typical training block** — this is the user's reason for picking 42 over 28 or 90. Don't shrink it for "smaller payload" reasons.
- **Climbing-activities-only RPE filter** — directly tied to the v1 climbing-first scope. Don't generalize to "all activities" even though it would be a one-line diff.
- **No runtime token-count guard** — the design intent is "the test fails loudly when the report drifts out of band", not "the tool quietly truncates". Don't add a runtime char-count check or section-drop branch.

</specifics>

<deferred>
## Deferred Ideas

- **Optional window-override params** (`weekly_window_days`, etc.) — deferred to v2 if real use shows the user (or Claude) needs to ask "what was my long-term trend over the past 90 days specifically".
- **TSB band tuning** — climbing-tuned bands or conservative/aggressive variants. Locked at standard values for v1; revisit only after the user reports the bands feel wrong in real use.
- **Wellness-signal aggregation method** — the planner picks an aggregation shape that fits the token budget; v2 could surface the choice as a tool param if Claude needs to ask for a different summary view.
- **Cross-validation between wellness CTL/ATL and per-activity icu_ctl/icu_atl** — would catch Intervals.icu API drift but doubles HTTP cost. v2 if drift is ever observed.
- **Reading TSB directly from a future API field** — defer until Intervals.icu publishes one; current behavior computes from CTL/ATL.
- **Generic / non-climbing readiness reporting** — covered by GEN-v2-01 in PROJECT.md Out of Scope.

</deferred>

---

*Phase: 04-training-status-report*
*Context gathered: 2026-04-29*
