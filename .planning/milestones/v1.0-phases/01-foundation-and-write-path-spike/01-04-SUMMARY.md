---
plan: 01-04
phase: 01-foundation-and-write-path-spike
status: complete
completed: 2026-04-24
---

# Plan 01-04 — Run spike against live Intervals.icu

## What was done

Executed `scripts/spike_write_endpoints.py` against the live Intervals.icu account at the far-future date `2099-01-01`, captured redacted results to `01-SPIKE-FINDINGS.md`, ran secret-leak gates, committed the findings file.

## Key findings (canonical reference for Plan 01-05 / Phase 2 / Phase 3)

| Question | Answer |
|----------|--------|
| Wellness PUT endpoint | `PUT /athlete/{athlete_id}/wellness/{date}` — 200 OK |
| Upsert semantics confirmed? | **Yes.** Partial second PUT preserved the first write's fields. Blank-via-`-1` also works for cleanup. |
| Activity create endpoint | **`POST /athlete/{athlete_id}/activities/manual`** (primary won; fallback not needed) |
| Activity id shape | `"id": "i142495224"` (prefixed `i` + numeric) |
| Custom-field top-level PUT roundtrip | **`false`** — account rejected with `422 "Unknown custom field [discipline]"`. SETUP-01 not yet completed by user. |
| DELETE available for cleanup? | **Yes.** Activity `i142495224` was automatically deleted — no manual web-UI cleanup required. |
| Custom-field definitions endpoint discovery | `/custom-fields` → 404. `/activity-fields` → 404. `/sport-settings` → **200 OK** (winning_endpoint). Plan 01-05 should try this first; fall back to readback-heuristic if the response shape doesn't include user-defined activity custom fields. |

## Downstream impact

- **Plan 01-05** reads `winning_endpoint: "/athlete/{athlete_id}/sport-settings"` from findings to choose its verify-strategy. If that endpoint's payload exposes definitions, use it directly; otherwise fall back to readback heuristic documented in 01-RESEARCH.md.
- **Phase 2** (`enrich_activity_climbing`, `write_wellness_entry`) can rely on confirmed upsert semantics and the confirmed `/activities/manual` create URL.
- **SETUP-01** remains a real user prerequisite: until the user defines `discipline`, `icu_rpe`, etc. in their Intervals.icu athlete account, write attempts will 422. The `verify_custom_fields_setup` tool (Plan 01-05) must surface this clearly.

## Secret-leak verification

- Real athlete id (`i507957`) → **0 matches** in committed findings (redacted as `{athlete_id}` — 19 occurrences).
- 32+ char token grep → **0 matches** in committed findings.
- All `i{digits}` matches in the findings are the response activity id (`i142495224`), which per plan acceptance criteria is allowed (response ids, not credentials).

## Cleanup

- Orphan activity at `2099-01-01` automatically deleted by the spike's DELETE step (`delete_available: true`).
- Wellness row at `2099-01-01` was blanked via the `-1` convention in the third PUT.
- **No manual web-UI cleanup was required.**

## Deviations

None. Script ran cleanly; all probes returned either the expected 2xx or an informative error that became a finding (the 422 on custom-field roundtrip is the finding, not a failure — it confirms A2).

## Surprises Phase 2/3 planners should know

1. **422 `Invalid fatigue: 5`** on the second wellness PUT — the spike used `fatigue=5` which Intervals.icu rejected. Phase 2's `write_wellness_entry` must validate fatigue against Intervals.icu's allowed range before PUT (likely 0–4 or 1–5 depending on definition; confirm from a GET `/wellness/{date}` response).
2. `sport-settings` is the only surviving definitions-candidate endpoint. If its response payload does NOT include per-athlete activity custom fields, Plan 01-05 must fall back to readback heuristic.
3. Activity id shape is `i` + digits (e.g., `i142495224`). Duplicate-guard code in Phase 3 should treat ids as opaque strings.

## Artifacts

- `.planning/phases/01-foundation-and-write-path-spike/01-SPIKE-FINDINGS.md` (committed `5470db6`) — canonical reference file.
