---
phase: 03-activity-creation-and-session-completion
plan: 01
subsystem: tools/climbing
tags: [refactor, climbing, intervals-icu, mcp, internal-helper]
dependency_graph:
  requires: []
  provides: [_enrich_impl private helper with _skip_conflict_scan kwarg]
  affects: [plans/03-02, plans/03-03]
tech_stack:
  added: []
  patterns: [thin-wrapper public tool, private-helper code reuse, keyword-only internal flag]
key_files:
  modified:
    - src/intervals_mcp_server/tools/climbing.py
decisions:
  - "_enrich_impl placed between _verify_custom_fields_setup_impl and verify_custom_fields_setup for natural private-before-public reading order"
  - "pre: dict[str, Any] = {} initialized before if not _skip_conflict_scan: block so section 8 onward always has a valid binding"
  - "Section 9 conflict-list construction runs unconditionally (safe when pre={}); only the refusal return is guarded by _skip_conflict_scan"
metrics:
  duration: "~3 minutes"
  completed: "2026-04-28"
  tasks_completed: 1
  files_modified: 1
---

# Phase 03 Plan 01: Enrich-impl Refactor Summary

**One-liner:** Extracted `enrich_activity_climbing` body into private `_enrich_impl(activity_id, *, ..., _skip_conflict_scan=False)` helper; public tool reduced to 15-line thin forwarder with zero behavior change.

## What Was Built

Refactored `src/intervals_mcp_server/tools/climbing.py` to enable code reuse between the existing enrichment tool and the two new Phase 3 tools (`create_climbing_activity`, `complete_climbing_session`) without duplicating the 240-line validation/write/readback block or changing any public behavior.

### Structural Changes

**Before:** `enrich_activity_climbing` contained all 15 sections (lines 233-472, 240 lines of body logic).

**After:**
- `_enrich_impl(activity_id, *, discipline, indoor, session_focus, top_grade_sent, top_grade_attempted, sends, attempts, rpe, override, athlete_id, api_key, _skip_conflict_scan=False) -> str` — new private async helper at module line 111, between `_verify_custom_fields_setup_impl` and `verify_custom_fields_setup`. Contains all 15 sections.
- `enrich_activity_climbing` — signature, decorator, pylint disables, and full docstring preserved verbatim. Body reduced to `return await _enrich_impl(activity_id, discipline=discipline, ..., # _skip_conflict_scan defaults False)`.

### The Three Guarded Sections (D-12)

| Section | Guard applied | Rationale |
|---------|---------------|-----------|
| 7 — GET activity for conflict scan | `pre: dict[str, Any] = {}` initialized before block; entire GET wrapped in `if not _skip_conflict_scan:` | Brand-new activity has no prior values; GET is wasted round-trip |
| 9 — Conflict refusal return | Conflict-list construction runs always (safe with `pre={}`); only `if conflicts and not override: return ...` becomes `if not _skip_conflict_scan and conflicts and not override:` | Defensive guard even though fresh-POST `pre={}` means conflicts is always empty |
| 10 — Audit on override | `if conflicts and override:` becomes `if not _skip_conflict_scan and conflicts and override:` | Fresh activity has nothing to audit; same defensive rationale |

Sections 1-6 and 8, 11-15 moved byte-identical — no rewording, no restructuring.

## Test Results

```
tests/test_climbing_write.py: 17 passed in 0.56s
Full suite: 128 passed in 0.69s
```

All 17 tests in `tests/test_climbing_write.py` pass unchanged, including:
- `test_missing_custom_fields_short_circuits` — confirms section 6 fires BEFORE section 7 (verify-fields guard still runs before the now-conditional conflict-scan GET)
- `test_default_deny_re_enrichment` — conflict scan still refuses via public tool (`_skip_conflict_scan=False` default)
- `test_override_writes_audit_message` — section 10 audit still fires via public tool
- `test_split_put_partial_failure_named` — D-16 split-PUT error messaging preserved verbatim

## Structural Verification (grep checks)

```
grep -nE '^async def _enrich_impl\('   → line 111  ✓
grep -nE '^async def enrich_activity_climbing\(' → line 420  ✓
grep -c '_skip_conflict_scan'           → 6 (≥4 threshold)  ✓
grep -nE 'return await _enrich_impl'   → line 497  ✓
```

Importability check: `from intervals_mcp_server.tools.climbing import enrich_activity_climbing, _enrich_impl, verify_custom_fields_setup` → OK; `_enrich_impl` is async, `_skip_conflict_scan` is in `inspect.signature(_enrich_impl).parameters`.

## Lint and Type Checks

- `ruff check src/intervals_mcp_server/tools/climbing.py` — All checks passed
- `mypy src/intervals_mcp_server/tools/climbing.py` — Success: no issues found in 1 source file

## Carry-Forward Note

Plans 02 (`create_climbing_activity`) and 03 (`complete_climbing_session`) are now unblocked. Both will call:

```python
await _enrich_impl(
    new_activity_id,
    discipline=discipline,
    ...
    _skip_conflict_scan=True,  # D-12 — fresh activity has no prior values
)
```

The `_skip_conflict_scan` flag is `_`-prefixed and keyword-only — not exposed to MCP. D-22 is satisfied because `_enrich_impl` lives in the same file as its callers (no sibling-module `_`-prefix import).

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — this is a pure refactor. No new data paths, no new UI surface, no placeholder values.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced. All `make_intervals_request` calls in `_enrich_impl` are byte-identical moves from the pre-refactor `enrich_activity_climbing` body.

## Self-Check: PASSED

- `src/intervals_mcp_server/tools/climbing.py` — exists and modified ✓
- Commit `4833e9f` exists in git log ✓
- 17 tests pass in `test_climbing_write.py` ✓
- 128 tests pass in full suite ✓
- ruff + mypy clean ✓
