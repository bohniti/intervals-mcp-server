---
status: partial
phase: 02-wellness-write-and-activity-enrichment
source: [02-VERIFICATION.md]
started: 2026-04-27T00:00:00Z
updated: 2026-04-27T00:00:00Z
---

## Current Test

[awaiting human testing — gated on SETUP-01: define the seven climbing custom-field schemas in the Intervals.icu athlete UI]

## Tests

### 1. Run `uv run python scripts/smoke_phase2.py` against live Intervals.icu after SETUP-01
expected: Exit code 0; logs show "Successfully wrote wellness entry", activity create, "Successfully enriched activity", DELETE cleanup, wellness PUT -1 cleanup. No leftover spike data on 2099-01-01 in the web UI.
result: [pending]

### 2. Confirm Phase 2 ROADMAP success criterion #2 against live API
expected: After running smoke_phase2.py, the enrich step returns "Successfully enriched..." AND the readback in the script log shows icu_rpe=6, discipline=bouldering, top_grade_sent=6A+, etc., on the throwaway activity.
result: [pending]

### 3. (Optional) Re-run `uv run python scripts/spike_write_endpoints_phase2.py` after SETUP-01
expected: Spike exits 0; findings file rewrites the "Activity custom-field PUT shape" section from UNRESOLVED-SETUP-01 to LOCKED with paste-ready body. Informational only — the working hypothesis already implemented in `enrich_activity_climbing` matches the expected LOCKED shape.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
