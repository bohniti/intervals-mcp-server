---
status: pending
phase: 05-server-wiring-and-acceptance
source: [05-CONTEXT.md, 05-PATTERNS.md]
started: 2026-04-29T00:00:00Z
updated: 2026-04-29T00:00:00Z
---

## Purpose

Manual checklist for the Claude Desktop side of Phase 5 acceptance.
Proves success-criterion-1 (`tools/list` in Claude Desktop shows the new
tools) and success-criterion-4 (each tool produces a non-error response
in Claude Desktop, not just via `scripts/smoke_phase5.py`). The unit
registration test (`tests/test_server_registration.py`) catches
structural drift; the smoke script catches API contract drift; this
checklist catches Claude Desktop tool-list rendering — three independent
checks (CONTEXT D-12).

Tick each row off in Claude Desktop running against the locally-installed
MCP server. Use far-future dates (2099-01-01 / 2099-01-02) to avoid
contaminating real training data; cleanup runs via `scripts/smoke_phase5.py`
or by hand from the Intervals.icu web UI. The wellness PUT at 2099-01-01
is intentionally left in place (D-10 — zero training-load impact).

## Current Test

[awaiting Plan 05 acceptance gate]

## Tests

### 1. write_wellness_entry — visible in tools/list AND callable
expected: Claude Desktop's tool list shows `write_wellness_entry`. Asking Claude to "log a wellness entry for 2099-01-01 with 8 hours sleep and soreness 2" results in a non-error response from the tool (i.e. starts with "Successfully").
result: [pending]
claude_response_excerpt: [optional]

### 2. enrich_activity_climbing — visible AND callable
expected: tool visible in list. Asking Claude to "enrich activity {ACTIVITY_ID} with bouldering, indoor, top grade sent 6A+, RPE 6" returns a non-error response. Use the activity id from the smoke-script run if available (`scripts/smoke_phase5.py` step 3 output).
result: [pending]
claude_response_excerpt: [optional]

### 3. create_climbing_activity — visible AND callable
expected: tool visible. Asking Claude to "log a 90-minute bouldering session indoors on 2099-01-01 with RPE 6 and a 6A+ send" returns a non-error response. The duplicate-guard may fire if the smoke script already ran on the same date — that is also a valid, non-error tool-callable result (it returns a warning string, not an error).
result: [pending]
claude_response_excerpt: [optional]

### 4. complete_climbing_session — visible AND callable
expected: tool visible. Asking Claude to "complete planned event {EVENT_ID} as a sport_lead session, RPE 7" returns a non-error response. Create the planned event for `2099-01-02` first via the smoke script step 5 or by hand in the Intervals.icu calendar.
result: [pending]
claude_response_excerpt: [optional]

### 5. get_training_status — visible AND callable
expected: tool visible. Asking Claude "how should I train tomorrow?" results in Claude calling get_training_status (or asking it directly returns the report). The response is non-empty text with three labeled sections present (## Today, ## This Week, ## Long-Term Trend).
result: [pending]
claude_response_excerpt: [optional]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps

[populate during the manual run]
