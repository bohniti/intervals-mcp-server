---
phase: 05-server-wiring-and-acceptance
plan: 03
subsystem: testing
tags: [fastmcp, pytest, registration, structural-drift, mcp-tools]

# Dependency graph
requires:
  - phase: 01-foundation-and-write-path-spike
    provides: verify_custom_fields_setup tool registration pattern
  - phase: 02-wellness-write-and-activity-enrichment
    provides: write_wellness_entry, enrich_activity_climbing tool registrations
  - phase: 03-activity-creation-and-session-completion
    provides: create_climbing_activity, complete_climbing_session tool registrations
  - phase: 04-training-status-report
    provides: get_training_status tool registration
provides:
  - "tests/test_server_registration.py: structural drift gate for all 23 milestone tools"
  - "EXPECTED_TOOLS frozenset: single source of truth for milestone tool surface"
  - "Two-assertion split catching both missing and unexpected tool registrations"
affects: [05-server-wiring-and-acceptance, CI, code-review]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "asyncio.run(mcp.list_tools()) for sync-test-friendly FastMCP introspection"
    - "frozenset EXPECTED_TOOLS as single source of truth for milestone surface"
    - "Two-assertion split (missing vs extra) for actionable failure messages"

key-files:
  created:
    - tests/test_server_registration.py
  modified: []

key-decisions:
  - "Used asyncio.run(mcp.list_tools()) public API (not private _tool_manager) per D-14"
  - "Two-assertion split (test_all_expected + test_no_unexpected) for clear drift direction per D-06"
  - "EXPECTED_TOOLS frozenset as literal constant at top of file — single source of truth"
  - "Sync test functions wrapping asyncio.run() per project convention (no pytest-asyncio)"

patterns-established:
  - "Registration test pattern: import server module (side-effect registration) + query mcp.list_tools()"
  - "EXPECTED_TOOLS frozenset as milestone surface declaration"

requirements-completed: [SETUP-02]

# Metrics
duration: 8min
completed: 2026-04-29
---

# Phase 5 Plan 03: Server Registration Assertion Test Summary

**Structural drift gate via asyncio.run(mcp.list_tools()) asserting all 23 milestone tools registered — catches silent tool removal at unit-test speed without HTTP**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-29T11:55:00Z
- **Completed:** 2026-04-29T12:03:32Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created `tests/test_server_registration.py` with EXPECTED_TOOLS frozenset naming all 23 milestone tools
- `test_all_expected_tools_registered`: asserts EXPECTED_TOOLS is a subset of FastMCP's registered tools — fails if a tool import is removed from server.py
- `test_no_unexpected_tools_registered`: asserts registered is a subset of EXPECTED_TOOLS — fails if a new @mcp.tool() is added without updating the expected set
- Both tests pass (2 passed in 0.62s), ruff and mypy clean, pytest --collect-only discovers both functions

## Task Commits

1. **Task 1: Create tests/test_server_registration.py** - `2613436` (test)

**Plan metadata:** (included in task commit for single-task plan)

## Files Created/Modified
- `tests/test_server_registration.py` - Registration drift gate: imports server module, queries mcp.list_tools(), asserts EXPECTED_TOOLS frozenset (23 names) in both directions

## Decisions Made
- Confirmed all 23 tools register via @mcp.tool() decorators even without the explicit __all__ wiring from plan 05-01 — decorator registration happens at module import time, so the test passes regardless of server.py's __all__ state
- Used public asyncio.run(mcp.list_tools()) API per D-14 (no private state introspection)
- Two-assertion split per D-06 (clearer failure messages than single equality assertion)
- Sync test wrapping asyncio.run() per existing project convention (test_server.py, test_climbing_write.py)

## Deviations from Plan

None - plan executed exactly as written. The exact file content from the plan was written verbatim.

## Issues Encountered

None. Pre-flight check confirmed all 23 expected tools were already registered via @mcp.tool() decorators in their respective tool modules (decorator registration is import-time, not dependent on server.py __all__ entries), so EXPECTED_TOOLS frozenset as specified in the plan matched the current registry exactly.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Registration drift gate is in place: any tool removed from server.py's imports or any @mcp.tool() decorator removed will now fail loudly in CI
- The two-direction assertions catch both "missing tool" (deleted import) and "surprise tool" (added @mcp.tool() without updating EXPECTED_TOOLS)
- EXPECTED_TOOLS is the single source of truth for the milestone surface — plan 05-01's server.py wiring will make the __all__ consistent with it
- No blockers for phase completion

---
*Phase: 05-server-wiring-and-acceptance*
*Completed: 2026-04-29*
