---
phase: 05-server-wiring-and-acceptance
plan: "04"
subsystem: scripts/smoke
tags: [smoke-testing, live-api, acceptance, climbing, wellness, status]
dependency_graph:
  requires:
    - 05-01 (server.py wiring — smoke script calls the registered tools)
    - 05-02 (README — setup docs required before smoke step 1 can succeed)
    - 05-03 (registration test — structural check; smoke script is behavioral check)
  provides:
    - Live-API end-to-end smoke for every milestone tool (D-09)
    - 05-LIVE-SMOKE.md manual checklist skeleton (D-11)
    - 05-SMOKE-FINDINGS.md canonical record skeleton (D-09)
  affects:
    - 05-05 (acceptance gate — runs smoke_phase5.py against live account)
tech_stack:
  added: []
  patterns:
    - Async smoke script with try/finally cleanup (mirrors smoke_phase2.py)
    - _redact() helper for athlete-id redaction in all log output
    - Far-future date constants (SMOKE_DATE / SMOKE_EVENT_DATE) per D-10
    - Single HTTP boundary via make_intervals_request() per D-13
key_files:
  created:
    - scripts/smoke_phase5.py
    - .planning/phases/05-server-wiring-and-acceptance/05-LIVE-SMOKE.md
    - .planning/phases/05-server-wiring-and-acceptance/05-SMOKE-FINDINGS.md
  modified: []
decisions:
  - "Wellness entry at SMOKE_DATE intentionally left in place per D-10 (far-future date, zero training-load impact)"
  - "Two distinct smoke dates (2099-01-01 and 2099-01-02) to avoid the date+type duplicate-guard collision between create and complete-session"
  - "Script does not auto-write 05-SMOKE-FINDINGS.md — hand-curation from stdout is sufficient per CONTEXT line 80"
  - "No --no-cleanup flag added — script is simple enough; debugging can set breakpoints"
metrics:
  duration: "~15 minutes"
  completed: "2026-04-29"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 0
---

# Phase 05 Plan 04: Smoke Script and Acceptance Skeletons Summary

## One-liner

Live-API smoke script (`scripts/smoke_phase5.py`) covering all seven D-09 steps (verify → wellness → create → enrich → complete-session → status → cleanup) with redacted logging, far-future dates, single HTTP boundary, and idempotent try/finally cleanup, plus two planning artifact skeletons for the acceptance gate.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create scripts/smoke_phase5.py | e12729b | scripts/smoke_phase5.py |
| 2 | Create 05-LIVE-SMOKE.md and 05-SMOKE-FINDINGS.md | 8ddc446 | .planning/phases/05-server-wiring-and-acceptance/05-LIVE-SMOKE.md, .planning/phases/05-server-wiring-and-acceptance/05-SMOKE-FINDINGS.md |

## Verification Results

- `uvx ruff check scripts/smoke_phase5.py`: clean (0 errors)
- `uv run mypy scripts/smoke_phase5.py`: clean (0 errors)
- AST parse: OK (async main() function present)
- `uv run pytest --collect-only -q | grep smoke_phase5`: 0 matches (not discoverable by pytest per D-25)
- `grep -c "import httpx" scripts/smoke_phase5.py`: 0 (no direct HTTP per D-13)
- `grep -c "_redact" scripts/smoke_phase5.py`: 16 (>= 8 required)
- All 7 step labels present: Step 1-6 + Cleanup
- `grep -c 'method="DELETE"'`: exactly 2 (activity + event cleanup)
- `grep -c "await make_intervals_request"`: 2 (cleanup DELETEs only; tool calls use make_intervals_request internally)
- Script line count: 261 (>= 200 required)
- SMOKE_DATE constant: "2099-01-01" ✓
- SMOKE_EVENT_DATE constant: "2099-01-02" ✓
- 05-LIVE-SMOKE.md: 5 test rows, YAML front-matter, ## Tests, ## Summary, ## Gaps ✓
- 05-SMOKE-FINDINGS.md: canonical header, redaction note, 7 step section headers ✓

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] ruff/mypy not in venv initially**
- **Found during:** Task 1 verification
- **Issue:** `uv run ruff` and `uv run mypy` failed with "No such file or directory". Dev extras not installed.
- **Fix:** Ran `uv sync --all-extras` to install dev dependencies including ruff and mypy. Accidentally also ran `uv add ruff --dev` which modified pyproject.toml and uv.lock; reverted those changes via `git checkout -- pyproject.toml uv.lock` before committing.
- **Files modified:** None (revert preserved original state)
- **Commit:** N/A (no files committed for this deviation)

## Known Stubs

None. The smoke script is fully implemented. The markdown files (05-LIVE-SMOKE.md, 05-SMOKE-FINDINGS.md) intentionally contain `[pending]` placeholders — these are acceptance-gate placeholders to be filled by Plan 05-05 when the script runs against the live account. This is the documented design, not unintended stubs.

## Threat Flags

No new network endpoints, auth paths, or file access patterns introduced beyond what was already in the threat model. The `scripts/smoke_phase5.py` file is covered by T-05-09 through T-05-14 in the plan's threat register, all mitigated by construction (redaction, far-future dates, single HTTP boundary, pytest non-discoverability).

## Self-Check: PASSED

All three files confirmed present on disk. Both task commits confirmed in git log (e12729b, 8ddc446).
