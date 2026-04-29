# Smoke findings — Phase 5 acceptance

**Smoke date (target):** 2099-01-01 (wellness + activity), 2099-01-02 (planned event)

All occurrences of the live athlete id are redacted to `{athlete_id}`.

This file is the canonical record of the Phase 5 live-API smoke run. It
is either auto-written by `scripts/smoke_phase5.py` or hand-curated from
its stdout (CONTEXT line 80 — Claude's discretion). Plan 05 fills it in
once the smoke script has run successfully against the live account.

## Step 1 — verify_custom_fields_setup

```text
[pending — populated during Plan 05 acceptance run]
```

verdict: [pending]

## Step 2 — write_wellness_entry

```json
{
  "request": {"date": "2099-01-01", "sleep_hours": 8.0, "soreness": 2},
  "tool_response": "[pending]",
  "readback_verdict": "[pending]"
}
```

## Step 3 — create_climbing_activity

```json
{
  "request": {"date": "2099-01-01", "duration_minutes": 60, "discipline": "bouldering", "indoor": true, "rpe": 6, "title": "SMOKE PHASE5 — DELETE ME (create)"},
  "tool_response": "[pending]",
  "captured_activity_id": "[pending]"
}
```

## Step 4 — enrich_activity_climbing

```json
{
  "request": {"activity_id": "[from step 3]", "discipline": "bouldering", "indoor": true, "session_focus": "power", "top_grade_sent": "6A+", "top_grade_attempted": "7A", "sends": 4, "attempts": 7, "rpe": 6},
  "tool_response": "[pending]",
  "readback_verdict": "[pending]"
}
```

## Step 5 — complete_climbing_session (with planned-event setup)

```json
{
  "step_5a_request": {"workout_type": "WeightTraining", "name": "SMOKE PHASE5 — DELETE ME (planned)", "start_date": "2099-01-02", "moving_time": 3600},
  "step_5a_tool_response": "[pending]",
  "captured_planned_event_id": "[pending]",
  "step_5b_request": {"event_id": "[from 5a]", "discipline": "sport_lead", "indoor": false, "session_focus": "projecting", "rpe": 7},
  "step_5b_tool_response": "[pending]",
  "captured_completion_activity_id": "[pending]",
  "paired_event_id_link_verdict": "[pending]"
}
```

## Step 6 — get_training_status

```json
{
  "request": {"as_of_date": "2099-01-01"},
  "report_char_count": "[pending]",
  "envelope_check_1200_to_2800_chars": "[pending]",
  "section_headers_present": {"## Today": "[pending]", "## This Week": "[pending]", "## Long-Term Trend": "[pending]"}
}
```

## Step 7 — Cleanup

```json
{
  "delete_create_activity": "[pending]",
  "delete_completion_activity": "[pending]",
  "delete_planned_event": "[pending]",
  "wellness_left_in_place_at": "2099-01-01",
  "wellness_left_in_place_rationale": "Far-future date, zero training-load impact (D-10)."
}
```

## Manual cleanup (if any DELETE failed)

- Activity ids needing manual cleanup: [list or 'none']
- Planned event id needing manual cleanup: [id or 'none']

## Verdict

- All steps passed: [pending]
- Failures: [list or 'none']
- Phase 5 success criteria 1, 2, 3, 4: [pending / pending / pending / pending]
