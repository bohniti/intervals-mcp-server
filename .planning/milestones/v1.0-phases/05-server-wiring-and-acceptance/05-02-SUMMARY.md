---
phase: 05-server-wiring-and-acceptance
plan: 02
subsystem: documentation
tags: [readme, discovery, climbing-tools, wellness, training-status]
dependency_graph:
  requires: []
  provides: [README-climbing-tools-section, README-intro-refresh]
  affects: [README.md]
tech_stack:
  added: []
  patterns: [markdown-section-structure, tool-discovery-surface]
key_files:
  created: []
  modified:
    - README.md
decisions:
  - "Intro paragraph names three domains without tool enumeration (D-04)"
  - "Five subsections under ## Climbing tools; verify_custom_fields_setup excluded — already documented Phase 1 (D-03)"
  - "No docs/CLIMBING-WORKFLOW.md created — per-tool subsections are sufficient for v1 (D-05)"
  - "Custom-field table and Verifying the setup subsection preserved verbatim (D-15/SETUP-01)"
metrics:
  duration: "~5 minutes"
  completed: "2026-04-29T12:02:55Z"
  tasks_completed: 2
  files_modified: 1
---

# Phase 05 Plan 02: README Tool Discovery Refresh Summary

README updated to surface the milestone's tool set: intro paragraph names the three new domains (climbing session completion, wellness writes, training-status report) and a new `## Climbing tools` section with five `### <tool_name>` subsections provides what/when/example discovery for each new tool.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Rewrite README intro paragraph (D-04) | 2f01dc1 | README.md |
| 2 | Insert `## Climbing tools` section with five subsections (D-03) | 21fd58e | README.md |

## What Was Built

### Task 1 — Intro paragraph refresh (line 3)

Replaced the stale "tools for authentication and data retrieval for activities, events, and wellness data" pitch with a single domain-naming sentence that mentions:
- Creating and enriching climbing activities (discipline, grades, RPE, session focus)
- Writing wellness entries (sleep, soreness, HRV, RHR, subjective metrics)
- Getting a single training-status report blending CTL/ATL/TSB with recent wellness signals

### Task 2 — `## Climbing tools` section

Inserted a new top-level section between `## Climbing setup — required Intervals.icu custom fields` (ends line 117) and `## Updating` (now line 173). Contains five subsections:

- `### \`write_wellness_entry\`` — log wellness with upsert semantics
- `### \`enrich_activity_climbing\`` — add climbing metadata + RPE to existing activity
- `### \`create_climbing_activity\`` — create activity from scratch with duplicate guard
- `### \`complete_climbing_session\`` — mark planned calendar event done with climbing metadata
- `### \`get_training_status\`` — single status report blending load metrics with wellness

Each subsection is ~5 lines: heading + one-sentence what + one-sentence when + paste-ready `text` code fence example. Canonical parameter detail lives in tool docstrings (Pitfall #6).

Pre-existing `## Climbing setup` section, custom-field table (SETUP-01 canonical reference), and `### Verifying the setup` subsection preserved verbatim.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all five tool subsections have real paste-ready examples with concrete parameter values. No placeholder text present.

## Threat Flags

None — documentation-only change. No new code paths, no new HTTP, no new credential handling, no new user input parsing. The placeholder activity IDs (`i12345`, `i98765`) and date (`2026-04-28`) in examples are clearly synthetic (T-05-04 accepted in plan threat model).

## Self-Check: PASSED

- README.md: FOUND
- 05-02-SUMMARY.md: FOUND
- Commit 2f01dc1 (Task 1): FOUND
- Commit 21fd58e (Task 2): FOUND
