---
phase: 01-foundation-and-write-path-spike
plan: 05
subsystem: api
tags: [climbing, mcp-tool, custom-fields, verification, server-wiring]

# Dependency graph
requires:
  - phase: 01-foundation-and-write-path-spike
    provides: "CUSTOM_FIELD_KEYS + Discipline/SessionFocus enums (from 01-01)"
  - phase: 01-foundation-and-write-path-spike
    provides: "Live spike findings — confirmed no definitions endpoint (from 01-04)"
provides:
  - "verify_custom_fields_setup MCP tool (Claude-callable, SETUP-02)"
  - "_verify_custom_fields_setup_impl internal helper returning (ok, missing, message) tuple"
  - "tools/climbing.py module wired into server.py (Phase 2+ extends without server.py edits per D-17)"
affects: [phase-02, phase-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dual MCP-tool + internal-helper (D-11): one implementation, two call sites"
    - "Hard-block with named-field error on missing custom fields (D-12)"
    - "Readback-heuristic strategy for custom-field definition detection"

key-files:
  created:
    - "src/intervals_mcp_server/tools/climbing.py"
  modified:
    - "src/intervals_mcp_server/server.py"
    - "tests/test_climbing.py"

key-decisions:
  - "Implementation strategy: Case B readback heuristic (GET /athlete/{id}/activities, inspect top-level keys) — no definitions endpoint exists per 01-SPIKE-FINDINGS.md"
  - "Internal helper returns (bool, list[str], str) — Phase 2 write tools branch on the bool for hard-block enforcement"
  - "Activity probe window: 50 most recent activities (_READBACK_ACTIVITY_LIMIT)"

patterns-established:
  - "Readback heuristic: API responses with presence-checked top-level keys as definition-existence proxy"
  - "Dual-surface tool pattern: @mcp.tool() wrapper delegates to a plain-async helper; helper contract is the Phase 2 integration point"

requirements-completed: [SETUP-02]

# Metrics
duration: 5min
completed: 2026-04-24
---

# Phase 01 Plan 05: tools/climbing.py + verify_custom_fields_setup Summary

**verify_custom_fields_setup MCP tool shipped with an internal helper; tools/climbing.py wired into server.py; 6 new tool-layer tests (86 total) using Case B readback heuristic since no definitions endpoint exists.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-24T09:44:47Z
- **Completed:** 2026-04-24T09:49:46Z
- **Tasks:** 3
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- `src/intervals_mcp_server/tools/climbing.py` created with `verify_custom_fields_setup` (MCP tool) and `_verify_custom_fields_setup_impl` (internal helper returning `(ok, missing, human_message)`). Docstring mirrors the 7-field CUSTOM_FIELD_KEYS table (D-13).
- `server.py` gains one import line and one `__all__` entry. No other `server.py` edits — Phase 2+ tools extend `tools/climbing.py` directly (D-17).
- `tests/test_climbing.py` appended with 6 tool-layer tests (registration, all-present, all-missing, some-missing, API-error, internal-helper tuple shape). Full suite: 80 → 86 tests, all green. Ruff + mypy clean.
- SETUP-02 satisfied: verification path exists, reports missing fields by name, points to README setup section. D-12 hard-block enforced (no warn-and-proceed phrasing).

## Task Commits

Each task was committed atomically:

1. **Task 1: Create tools/climbing.py with verify_custom_fields_setup + internal helper** - `a5c77be` (feat)
2. **Task 2: Wire tools/climbing into server.py** - `3fa9cb5` (feat)
3. **Task 3: Append tool-layer tests to tests/test_climbing.py** - `f377ef7` (test)

## Files Created/Modified

- `src/intervals_mcp_server/tools/climbing.py` (created, 144 lines) — MCP tool module for climbing; currently exposes `verify_custom_fields_setup` and the `_verify_custom_fields_setup_impl` helper. Uses `make_intervals_request` exclusively for HTTP (per CLAUDE.md constraint).
- `src/intervals_mcp_server/server.py` (modified, +2 lines) — one import line for `verify_custom_fields_setup`; one new `__all__` entry.
- `tests/test_climbing.py` (modified, +150 lines appended; +1 line `import asyncio`) — 6 new tool-layer tests + 2 fake-builder helpers (`_make_fake_all_present`, `_make_fake_missing`) shaped for Case B readback heuristic.

## Decisions Made

### Implementation strategy: Case B (readback heuristic)

The spike findings (`01-SPIKE-FINDINGS.md`) show:
- `/athlete/{id}/custom-fields` → 404
- `/athlete/{id}/activity-fields` → 404
- `/athlete/{id}/sport-settings` → 200 OK, but the response exposes **sport-level config only** (FTP, HR zones, etc.). The `custom_field_ids: []` arrays are empty for all sports and don't enumerate field definitions by key/name.

There is therefore no definitions endpoint that reports the 7 required custom-field keys. The plan explicitly sanctioned falling back to the readback heuristic under this condition.

**Endpoint used:** `GET /athlete/{athlete_id}/activities?limit=50`

**Heuristic:** A key from `CUSTOM_FIELD_KEYS` that appears as a top-level field on ANY of the 50 most-recent activities is considered "defined" in the athlete account. A key absent from ALL 50 is reported missing.

**Trade-off acknowledged:** For a completely fresh athlete account with no climbing activities yet, even correctly-defined custom fields will not appear on historical activities, so the tool may report false positives for missing fields. This matches the intended SETUP-02 semantics — the user is guided to complete SETUP-01 (define fields) and to run the Phase 2 write tools, which surface the ground-truth `422 "Unknown custom field [X]"` error from the API when the fields are not defined. The helper's error-path also hard-blocks on API errors, so Phase 2 tools calling `_verify_custom_fields_setup_impl` will never proceed on a dubious result.

### Internal helper contract

Signature: `_verify_custom_fields_setup_impl(athlete_id_to_use: str, api_key: str | None) -> tuple[bool, list[str], str]`

Tuple contract Phase 2 consumes:
- `ok: bool` — True iff every `CUSTOM_FIELD_KEYS` key was observed on at least one recent activity
- `missing: list[str]` — ordered list (CUSTOM_FIELD_KEYS insertion order) of keys not observed; empty when `ok`
- `human_message: str` — rendered string the MCP-tool wrapper returns unchanged; contains the README pointer and per-key type/options when any key is missing

Phase 2 write tools (`write_wellness_entry`, `enrich_activity_climbing`) branch on `ok`: if False, they refuse to run and return `human_message` directly (hard-block per D-12).

## Deviations from Plan

None — plan executed exactly as written. The only judgment call was the documented Case A vs Case B choice, which the plan explicitly delegates to spike findings.

## Issues Encountered

- `uv run ruff` initially failed with "No such file or directory" because the fresh worktree had `.venv` but without dev extras. Resolved by running `uv sync --all-extras` — this is expected first-time setup per `AGENTS.md`.

## User Setup Required

None — no external service configuration required by this plan. SETUP-01 (the user defining the 7 climbing custom fields in Intervals.icu) remains a prerequisite for Phase 2 write tools, and is documented in PROJECT.md and will be in the Plan 06 README section.

## Confirmation points (per plan `<output>` section)

- **Strategy chosen:** Case B (readback heuristic) — rationale above.
- **Endpoint URL:** `GET /athlete/{athlete_id}/activities` with `params={"limit": 50}`.
- **Response key the implementation relies on:** presence of `CUSTOM_FIELD_KEYS` entries (`discipline`, `indoor`, `session_focus`, `top_grade_sent`, `top_grade_attempted`, `sends`, `attempts`) as top-level keys in each activity dict.
- **Internal helper return-tuple contract:** `(bool, list[str], str)` — Phase 2 consumes `bool` for the hard-block branch; `list[str]` for structured telemetry if needed; `str` for the human-readable message.
- **New total test count in tests/test_climbing.py:** 13 tests (7 utility-layer from Plan 01 + 6 tool-layer from this plan). Full suite: 86 tests, all passing.
- **Importability from server:** `from intervals_mcp_server.server import verify_custom_fields_setup` works; confirmed by `test_verify_tool_registered` and manual smoke-check.

## Next Phase Readiness

- `tools/climbing.py` is the single landing site for Phase 2 additions (`write_wellness_entry`, `enrich_activity_climbing`). No further `server.py` edits needed for those tools.
- Phase 2 write tools will call `_verify_custom_fields_setup_impl(...)` as a pre-write guard and branch on `ok`. The return-tuple contract is stable.
- Phase 2 planners should note: the helper's error path (`{"error": True, ...}` from `make_intervals_request`) returns `ok=False` with the full `CUSTOM_FIELD_KEYS.keys()` list as "missing" — write tools should treat API errors as hard-block, which is the behavior Phase 2 likely wants anyway (don't write if we can't verify).

## Self-Check: PASSED

Verification commands executed:

- `test -f src/intervals_mcp_server/tools/climbing.py` → FOUND
- `git log --oneline --all | grep a5c77be` → FOUND (Task 1)
- `git log --oneline --all | grep 3fa9cb5` → FOUND (Task 2)
- `git log --oneline --all | grep f377ef7` → FOUND (Task 3)
- `uv run pytest tests/` → 86 passed
- `uv run ruff check src/intervals_mcp_server/tools/climbing.py src/intervals_mcp_server/server.py tests/test_climbing.py` → All checks passed
- `uv run mypy src/intervals_mcp_server/tools/climbing.py src/intervals_mcp_server/server.py` → Success: no issues
- `uv run python -c "from intervals_mcp_server.server import verify_custom_fields_setup"` → exit 0

---
*Phase: 01-foundation-and-write-path-spike*
*Completed: 2026-04-24*
