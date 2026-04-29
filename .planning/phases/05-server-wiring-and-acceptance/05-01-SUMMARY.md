---
phase: 05-server-wiring-and-acceptance
plan: "01"
subsystem: server-wiring
tags: [server, imports, re-export, docstring, wiring]
dependency_graph:
  requires:
    - src/intervals_mcp_server/tools/wellness.py (write_wellness_entry already @mcp.tool()-decorated)
    - src/intervals_mcp_server/tools/climbing.py (complete_climbing_session, create_climbing_activity, enrich_activity_climbing already decorated)
  provides:
    - src/intervals_mcp_server/server.py (explicit named imports + __all__ re-export of every milestone tool)
  affects:
    - Any consumer that imports from intervals_mcp_server.server (all six milestone tools now importable by name)
tech_stack:
  added: []
  patterns:
    - Parenthesized multi-name import block (already used for activities/events/custom_items; extended to wellness and climbing)
    - __all__ re-export list extension (additive, insertion-order preserved)
key_files:
  created: []
  modified:
    - src/intervals_mcp_server/server.py
decisions:
  - D-01: explicit named imports for every new tool (wellness + climbing) so silent tool removal becomes loud ImportError
  - D-02: module docstring "MCP tools provided" list refreshed to include all 6 milestone tools
  - D-15: tool modules are read-only; only server.py touched
metrics:
  duration: "2 minutes"
  completed: "2026-04-29T12:03:13Z"
  tasks_completed: 4
  tasks_total: 4
  files_modified: 1
---

# Phase 5 Plan 01: Server Wiring Summary

**One-liner:** Explicit named imports + `__all__` re-export of all four new milestone tools (`write_wellness_entry`, `enrich_activity_climbing`, `create_climbing_activity`, `complete_climbing_session`) in `server.py`, with refreshed module docstring listing all six milestone tools.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Convert wellness import to multi-name parenthesized form (D-01) | 5563711 | src/intervals_mcp_server/server.py |
| 2 | Extend climbing import to 4 names + add 4 entries to `__all__` (D-01) | 5d7118a | src/intervals_mcp_server/server.py |
| 3 | Refresh module docstring "MCP tools provided" list (D-02) | 139074f | src/intervals_mcp_server/server.py |
| 4 | Run pytest + ruff + mypy regression gate (D-07/D-15) | (no commit — verification only) | — |

## What Was Done

**Task 1** replaced the single-name wellness import with a parenthesized multi-name block listing `get_wellness_data` and `write_wellness_entry` alphabetically, preserving the `# pylint: disable=wrong-import-position  # noqa: E402` comment on the opening line.

**Task 2** replaced the single-name climbing import (`verify_custom_fields_setup` only) with a parenthesized four-name block (alphabetical: `complete_climbing_session`, `create_climbing_activity`, `enrich_activity_climbing`, `verify_custom_fields_setup`). Extended `__all__` by inserting four new entries after the existing `verify_custom_fields_setup` anchor and before `get_training_status`, in the prescribed order: `enrich_activity_climbing`, `create_climbing_activity`, `complete_climbing_session`, `write_wellness_entry`.

**Task 3** appended six new bullets to the module docstring's "MCP tools provided" list: `verify_custom_fields_setup`, `write_wellness_entry`, `enrich_activity_climbing`, `create_climbing_activity`, `complete_climbing_session`, `get_training_status`. All existing 17 bullets and the closing `See the README` sentence were preserved verbatim.

**Task 4** confirmed: `ruff check` clean, `mypy` clean, 195/195 pytest tests pass, `git diff` scope confined to `src/intervals_mcp_server/server.py` only (zero changes to tests/, tools/, or utils/).

## Verification Results

- `uv run python -c "from intervals_mcp_server.server import write_wellness_entry, enrich_activity_climbing, create_climbing_activity, complete_climbing_session, verify_custom_fields_setup, get_training_status; print('OK')"` — OK
- `__all__` insertion order assertion passes: `verify_custom_fields_setup` < `enrich_activity_climbing` < `create_climbing_activity` < `complete_climbing_session` < `write_wellness_entry` < `get_training_status`
- 195 pytest tests pass (no regressions)
- ruff check: clean
- mypy: clean
- `git diff --name-only HEAD~3 HEAD` shows only `src/intervals_mcp_server/server.py`

## Deviations from Plan

None — plan executed exactly as written. All three code tasks and the verification gate completed without deviation.

## Known Stubs

None. This plan adds no data-rendering logic; it is import/re-export wiring and docstring only.

## Threat Flags

None. The change is additive import-time organization with no new network, file I/O, auth, or user-input surface (consistent with the plan's threat model: no new trust boundaries).

## Self-Check: PASSED

- `src/intervals_mcp_server/server.py` exists and is modified as described.
- Commits 5563711, 5d7118a, 139074f are present in git log.
- 195 tests pass with the wiring change in place.
- No tool module (tools/wellness.py, tools/climbing.py, tools/status.py) was modified.
