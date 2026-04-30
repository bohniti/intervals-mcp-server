# Phase 3: Activity Creation and Session Completion - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `03-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-04-27
**Phase:** 03-activity-creation-and-session-completion
**Areas discussed:** Duplicate guard semantics, complete_climbing_session linking, POST + enrich atomicity, Parameter shape & defaults

---

## Duplicate guard semantics

### Q1: Match criteria

| Option | Description | Selected |
|--------|-------------|----------|
| date + type | Matches research's stated criterion (Pitfall #1). Fires on any same-date WeightTraining activity. | ✓ |
| date + type + name | Tighter — only fires when the same `name` template is being re-created. | |
| date alone | Most aggressive — any activity at all on this date triggers the guard. | |

**User's choice:** date + type (Recommended)
**Notes:** Catches Garmin-synced records and prior MCP retries equally. Most protective per Pitfall #1.

### Q2: Hit behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Refuse + return existing id | Clear error naming existing activity_id; suggest enrich_activity_climbing. | ✓ |
| Auto-enrich existing | Skip POST, internally call enrich on the existing id. | |
| Create anyway with override flag | `force_create=True` parameter for legitimate dups (AM/PM). | |

**User's choice:** Refuse + return existing id (Recommended)
**Notes:** Stateless, non-destructive, lets Claude (LLM) drive next step.

### Q3: Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Both tools | Same guard on create_climbing_activity AND complete_climbing_session. | ✓ |
| Only create_climbing_activity | Argue event_id makes complete_climbing_session intent unique. | |

**User's choice:** Both tools (Recommended)
**Notes:** complete_climbing_session also POSTs an activity — same retry/reconnect risk per Pitfall #1.

### Q4: Match output

| Option | Description | Selected |
|--------|-------------|----------|
| Single match list, no distinction | Return all matches uniformly; let LLM reason. | ✓ |
| Separate climbing vs non-climbing matches | Detect by `discipline` custom field; distinguish in error. | |

**User's choice:** Single match list, no distinction (Recommended)
**Notes:** Keep tool output simple. Less code, less to test.

---

## complete_climbing_session linking

### Q1: Event input

| Option | Description | Selected |
|--------|-------------|----------|
| event_id required, fetch event server-side | User passes event_id; tool reads event for date/type/name. | ✓ |
| event_id optional, accept date+type explicitly | More flexible; risks user-date drifting from event date. | |
| event_date + workout_type, no event_id | Trust auto-match entirely. No audit trail. | |

**User's choice:** event_id required, fetch event server-side (Recommended)
**Notes:** One source of truth. No drift between user-supplied date and planned event date (Pitfall #4 mitigation).

### Q2: Linking mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Set paired_event_id explicitly | Include paired_event_id: event_id in POST body; verify in readback. | ✓ |
| Trust auto-match by date+type | Skip paired_event_id; let Intervals.icu match. | |
| Probe in Phase 3 spike | Add a probe; defer the decision to spike findings. | |

**User's choice:** Set paired_event_id explicitly (Recommended)
**Notes:** Field is in the activity response shape (Phase 1 spike confirmed). Auto-match is LOW-MEDIUM confidence per STATE.md "Blockers/Concerns".

### Q3: Conflict resolution

| Option | Description | Selected |
|--------|-------------|----------|
| Activity uses event values verbatim, climbing fields enrich | Event date/type/name go in POST as-is; climbing fields enrich. | ✓ |
| User params override event values | User-supplied date/type/name override what's read from event. | |
| Refuse on any mismatch | Error if user-supplied date doesn't match event. | |

**User's choice:** Activity uses event values verbatim, climbing fields enrich (Recommended)
**Notes:** Planned event is the spec. No reconciliation logic needed.

### Q4: Climbing fields on the tool

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — single-shot complete + enrich | Accept all climbing-field params; internally run enrichment after POST. | ✓ |
| No — just create the linked activity | Tool focused on POST only; user calls enrich after. | |

**User's choice:** Yes — single-shot complete + enrich (Recommended)
**Notes:** One tool call closes the loop — matches Pitfall #5 single-shot principle.

---

## POST + enrich atomicity

### Q1: Enrichment failure after POST success

| Option | Description | Selected |
|--------|-------------|----------|
| Leave activity, return clear error | activity_id preserved in error; user retries via enrich_activity_climbing(override=True). | ✓ |
| Auto-rollback via DELETE | DELETE the activity to leave Intervals.icu in pre-call state. | |
| Surface as partial-success with action hint | Non-error string naming what landed/didn't; LLM decides. | |

**User's choice:** Leave activity, return clear error (Recommended)
**Notes:** No data loss. Matches D-16's "no silent partial state" principle from Phase 2.

### Q2: POST atomicity

| Option | Description | Selected |
|--------|-------------|----------|
| POST is atomic | Trust Intervals.icu — POST returns 4xx/5xx and no activity exists. | ✓ |
| Defensive readback after POST error | After POST error, GET activities to confirm nothing was created. | |

**User's choice:** POST is atomic — either fully created or not (Recommended)
**Notes:** No cleanup needed. Phase 1 spike confirmed.

### Q3: Code reuse pattern

| Option | Description | Selected |
|--------|-------------|----------|
| Promote enrich logic to private helper in tools/climbing.py | Refactor enrich body into `_enrich_impl(activity_id, ...) -> str`. | ✓ |
| Promote shared logic to utils/climbing.py | Move helpers (split-PUT, conflict-scan, readback) into utils/. | |
| Duplicate the enrichment code paths | Each tool implements enrichment inline. | |

**User's choice:** Promote enrich logic to private helper in tools/climbing.py (Recommended)
**Notes:** D-22 compliant — sibling-file private import is the rule, same-file private is fine.

### Q4: Override gate on fresh-POST enrich

| Option | Description | Selected |
|--------|-------------|----------|
| Skip override check on freshly created activity | Conflict-scan would never fire; skip the extra GET. | ✓ |
| Run the same override gate uniformly | Symmetry with enrich_activity_climbing; adds redundant GET. | |

**User's choice:** Skip override check on freshly created activity (Recommended)
**Notes:** No prior values on a brand-new activity; conflict-scan is wasted work.

---

## Parameter shape & defaults

### Q1: create_climbing_activity required fields

| Option | Description | Selected |
|--------|-------------|----------|
| date + duration_minutes | Minimum is the two facts only the user knows. Title auto-generated. | ✓ |
| date + duration + title | Match roadmap literally — user always passes a name. | |
| date only | Default duration to 60 minutes. Loses fidelity. | |

**User's choice:** date + duration_minutes (Recommended)
**Notes:** Climbing fields and title all optional like enrich.

### Q2: Duration unit

| Option | Description | Selected |
|--------|-------------|----------|
| minutes | Climbers think in minutes/hours. Tool converts internally. | ✓ |
| seconds | Match the API's native moving_time. Unnatural for Claude. | |
| Both via duration_seconds and duration_minutes | Two optional params; require exactly one. | |

**User's choice:** minutes (Recommended)
**Notes:** Same user-friendly-units pattern as P2 D-08.

### Q3: Activity type

| Option | Description | Selected |
|--------|-------------|----------|
| Hardcoded 'WeightTraining' | Phase 1 spike confirmed; v1 is climbing-only by scope. | ✓ |
| Optional `activity_type` param defaulting to 'WeightTraining' | Surface as override for rare future case. | |
| Spike both 'WeightTraining' and 'Other' | Add a probe; pick based on load math. | |

**User's choice:** Hardcoded 'WeightTraining' (Recommended)
**Notes:** Adding a parameter invites generic-activity scope creep (deferred to GEN-v2-01).

### Q4: Name parameter

| Option | Description | Selected |
|--------|-------------|----------|
| Optional; default template 'Climbing — {discipline} — {date}' | Template-built from supplied fields; falls back to 'Climbing — {date}'. | ✓ |
| Required, no template | User always passes a name string. Friction. | |
| Optional, default to literal 'Climbing' | Boring but bulletproof. Hard to scan in UI. | |

**User's choice:** Optional with template default (Recommended)
**Notes:** discipline_human map: bouldering→"Bouldering", sport_lead→"Sport lead", etc. Don't expose enum values verbatim in titles.

---

## Claude's Discretion

- Exact mechanics of the `_enrich_impl` extraction (single function vs small set of helpers).
- Whether to add a Phase 3 spike for `paired_event_id` behavior — recommend skip (readback verification suffices).
- Whether `complete_climbing_session` errors on already-paired event_id — recommend yes.
- Whether the duplicate-guard error lists ALL matches or just the first — recommend ALL.
- Whether `_skip_conflict_scan` is an explicit kwarg or a `_enrich_fresh` thin wrapper.
- Optional `scripts/smoke_phase3.py` — defer if Phase 2's smoke-test infrastructure is reusable.
- Whether `discipline_human` map lives in `utils/climbing.py` or `tools/climbing.py`.

## Deferred Ideas

- `force_create=True` flag for legitimate same-day duplicates.
- Free-text `description` / `notes` parameter on create_climbing_activity.
- `type="Other"` alternative for climbing activities.
- `duration_minutes` bounds (min/max).
- Generic non-climbing manual-activity creation (`GEN-v2-01`).
- Phase 4 concern: how duplicate-guarded planned events flow into CTL/ATL.
- Auto-generating titles from session_focus or grades.
- Improving the verify-fields readback heuristic (Phase 1 known limitation).
