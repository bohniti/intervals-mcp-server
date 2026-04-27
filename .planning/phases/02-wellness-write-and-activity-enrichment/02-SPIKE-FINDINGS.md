# Spike findings - Phase 2 second probe

**Spike date (target):** 2099-01-01

All occurrences of the live athlete id are redacted to `{athlete_id}`.

This file is the canonical reference for Plans 02-02 (wellness ranges) and 02-04 (activity enrichment). Paste the LOCKED code blocks below into the corresponding modules verbatim.

## Activity custom-field PUT shape (UNRESOLVED - SETUP-01 PREREQUISITE NOT MET)

**Diagnosis.** Every PUT with the climbing custom-field keys at the top level returned `422 "Unknown custom field [<key>]"`. This error pattern means the Intervals.icu API recognized the body shape (top-level keys is the right envelope) but the custom-field SCHEMAS have not been defined on the athlete's account yet. This is exactly the SETUP-01 prerequisite documented in PROJECT.md ("User prerequisite: Intervals.icu custom fields must exist in the athlete's account before the tools that write them will work").

**Required action by user (does NOT invalidate any Key Decision):**

1. Open Intervals.icu web UI -> athlete settings -> custom fields.
2. Create the seven custom-field schemas the README's SETUP-01 section lists: `discipline`, `indoor`, `session_focus`, `top_grade_sent`, `top_grade_attempted`, `sends`, `attempts` (with the exact keys and types from `src/intervals_mcp_server/utils/climbing.py` `CUSTOM_FIELD_KEYS`).
3. Re-run `uv run python scripts/spike_write_endpoints_phase2.py` to confirm all seven keys roundtrip — that re-run will rewrite this section to LOCKED with the paste-ready body.

**Body shape working hypothesis (to confirm by post-SETUP-01 re-run):** top-level keys via `PUT /activity/{id}` — this is what the 422 error messages strongly suggest. The other body envelopes (`custom_fields`, `customFields`, `fields`) all returned the SAME "Unknown custom field [X]" pattern with the envelope name as `[X]`, which confirms the API treats top-level keys as candidate custom-field names — exactly what we want.

**Plan 02-04 disposition:** Plan 02-04 implementation can proceed **after** the user finishes SETUP-01 and the spike re-run confirms the body shape. The existing `verify_custom_fields_setup` MCP tool from Phase 1 (D-11) is the runtime guard that protects `enrich_activity_climbing` from this same failure mode in production (D-20).

**All attempts (full audit trail):**

```json
[
  {
    "body_label": "top_level_keys",
    "endpoint_label": "PUT_/activity/{id}",
    "method": "PUT",
    "url_template": "/activity/{activity_id}",
    "write_response": {
      "error": true,
      "status_code": 422,
      "message": "422 Unprocessable Content: The server couldn't process the request (invalid parameters or unsupported operation)."
    },
    "readback_partial_match_keys": [],
    "all_keys_roundtripped": false
  },
  {
    "body_label": "top_level_keys",
    "endpoint_label": "PUT_/athlete/{aid}/activity/{id}",
    "method": "PUT",
    "url_template": "/athlete/{athlete_id}/activity/{activity_id}",
    "write_response": {
      "error": true,
      "status_code": 404,
      "message": "404 Not Found: The requested endpoint or ID doesn't exist."
    },
    "readback_partial_match_keys": [],
    "all_keys_roundtripped": false
  },
  {
    "body_label": "top_level_keys",
    "endpoint_label": "POST_/activity/{id}",
    "method": "POST",
    "url_template": "/activity/{activity_id}",
    "write_response": {
      "error": true,
      "status_code": 405,
      "message": "{\"timestamp\":\"2026-04-25T09:42:05.873+00:00\",\"status\":405,\"error\":\"Method Not Allowed\",\"path\":\"/api/v1/activity/i142762273\"}"
    },
    "readback_partial_match_keys": [],
    "all_keys_roundtripped": false
  },
  {
    "body_label": "top_level_keys",
    "endpoint_label": "PUT_/activity/{id}/custom-fields",
    "method": "PUT",
    "url_template": "/activity/{activity_id}/custom-fields",
    "write_response": {
      "error": true,
      "status_code": 404,
      "message": "404 Not Found: The requested endpoint or ID doesn't exist."
    },
    "readback_partial_match_keys": [],
    "all_keys_roundtripped": false
  },
  {
    "body_label": "nested_custom_fields_envelope",
    "endpoint_label": "PUT_/activity/{id}",
    "method": "PUT",
    "url_template": "/activity/{activity_id}",
    "write_response": {
      "error": true,
      "status_code": 422,
      "message": "422 Unprocessable Content: The server couldn't process the request (invalid parameters or unsupported operation)."
    },
    "readback_partial_match_keys": [],
    "all_keys_roundtripped": false
  },
  {
    "body_label": "nested_custom_fields_envelope",
    "endpoint_label": "PUT_/athlete/{aid}/activity/{id}",
    "method": "PUT",
    "url_template": "/athlete/{athlete_id}/activity/{activity_id}",
    "write_response": {
      "error": true,
      "status_code": 404,
      "message": "404 Not Found: The requested endpoint or ID doesn't exist."
    },
    "readback_partial_match_keys": [],
    "all_keys_roundtripped": false
  },
  {
    "body_label": "nested_custom_fields_envelope",
    "endpoint_label": "POST_/activity/{id}",
    "method": "POST",
    "url_template": "/activity/{activity_id}",
    "write_response": {
      "error": true,
      "status_code": 405,
      "message": "{\"timestamp\":\"2026-04-25T09:42:09.515+00:00\",\"status\":405,\"error\":\"Method Not Allowed\",\"path\":\"/api/v1/activity/i142762273\"}"
    },
    "readback_partial_match_keys": [],
    "all_keys_roundtripped": false
  },
  {
    "body_label": "nested_custom_fields_envelope",
    "endpoint_label": "PUT_/activity/{id}/custom-fields",
    "method": "PUT",
    "url_template": "/activity/{activity_id}/custom-fields",
    "write_response": {
      "error": true,
      "status_code": 404,
      "message": "404 Not Found: The requested endpoint or ID doesn't exist."
    },
    "readback_partial_match_keys": [],
    "all_keys_roundtripped": false
  },
  {
    "body_label": "nested_customFields_camelCase",
    "endpoint_label": "PUT_/activity/{id}",
    "method": "PUT",
    "url_template": "/activity/{activity_id}",
    "write_response": {
      "error": true,
      "status_code": 422,
      "message": "422 Unprocessable Content: The server couldn't process the request (invalid parameters or unsupported operation)."
    },
    "readback_partial_match_keys": [],
    "all_keys_roundtripped": false
  },
  {
    "body_label": "nested_customFields_camelCase",
    "endpoint_label": "PUT_/athlete/{aid}/activity/{id}",
    "method": "PUT",
    "url_template": "/athlete/{athlete_id}/activity/{activity_id}",
    "write_response": {
      "error": true,
      "status_code": 404,
      "message": "404 Not Found: The requested endpoint or ID doesn't exist."
    },
    "readback_partial_match_keys": [],
    "all_keys_roundtripped": false
  },
  {
    "body_label": "nested_customFields_camelCase",
    "endpoint_label": "POST_/activity/{id}",
    "method": "POST",
    "url_template": "/activity/{activity_id}",
    "write_response": {
      "error": true,
      "status_code": 405,
      "message": "{\"timestamp\":\"2026-04-25T09:42:13.205+00:00\",\"status\":405,\"error\":\"Method Not Allowed\",\"path\":\"/api/v1/activity/i142762273\"}"
    },
    "readback_partial_match_keys": [],
    "all_keys_roundtripped": false
  },
  {
    "body_label": "nested_customFields_camelCase",
    "endpoint_label": "PUT_/activity/{id}/custom-fields",
    "method": "PUT",
    "url_template": "/activity/{activity_id}/custom-fields",
    "write_response": {
      "error": true,
      "status_code": 404,
      "message": "404 Not Found: The requested endpoint or ID doesn't exist."
    },
    "readback_partial_match_keys": [],
    "all_keys_roundtripped": false
  },
  {
    "body_label": "nested_fields_envelope",
    "endpoint_label": "PUT_/activity/{id}",
    "method": "PUT",
    "url_template": "/activity/{activity_id}",
    "write_response": {
      "error": true,
      "status_code": 422,
      "message": "422 Unprocessable Content: The server couldn't process the request (invalid parameters or unsupported operation)."
    },
    "readback_partial_match_keys": [],
    "all_keys_roundtripped": false
  },
  {
    "body_label": "nested_fields_envelope",
    "endpoint_label": "PUT_/athlete/{aid}/activity/{id}",
    "method": "PUT",
    "url_template": "/athlete/{athlete_id}/activity/{activity_id}",
    "write_response": {
      "error": true,
      "status_code": 404,
      "message": "404 Not Found: The requested endpoint or ID doesn't exist."
    },
    "readback_partial_match_keys": [],
    "all_keys_roundtripped": false
  },
  {
    "body_label": "nested_fields_envelope",
    "endpoint_label": "POST_/activity/{id}",
    "method": "POST",
    "url_template": "/activity/{activity_id}",
    "write_response": {
      "error": true,
      "status_code": 405,
      "message": "{\"timestamp\":\"2026-04-25T09:42:16.858+00:00\",\"status\":405,\"error\":\"Method Not Allowed\",\"path\":\"/api/v1/activity/i142762273\"}"
    },
    "readback_partial_match_keys": [],
    "all_keys_roundtripped": false
  },
  {
    "body_label": "nested_fields_envelope",
    "endpoint_label": "PUT_/activity/{id}/custom-fields",
    "method": "PUT",
    "url_template": "/activity/{activity_id}/custom-fields",
    "write_response": {
      "error": true,
      "status_code": 404,
      "message": "404 Not Found: The requested endpoint or ID doesn't exist."
    },
    "readback_partial_match_keys": [],
    "all_keys_roundtripped": false
  }
]
```

## Wellness subjective-field ranges (LOCKED)

Plan 02-02 copies this dict literal into `WELLNESS_RANGES` in `src/intervals_mcp_server/utils/wellness.py`. Fields with `None` are unresolved - leave them out of `WELLNESS_RANGES` until re-probed.

**Paste-ready Python literal:**

```python
WELLNESS_RANGES_LOCKED = {
    'fatigue': (1, 4),
    'stress': (1, 4),
    'motivation': (1, 4),
    'mood': (1, 4),
    'soreness': (1, 4),
    'sleep_quality': (1, 4),
}
```

## icu_rpe write path (LOCKED)

Plan 02-04 writes `icu_rpe` in a separate PUT BEFORE the custom-field PUT (RPE first, custom fields second). On partial failure (RPE landed, custom fields didn't, or vice versa) the tool returns an explicit error naming what landed and what didn't (see D-16).

**Paste-ready pattern:**

```python
# Step 1: RPE first.
await make_intervals_request(
    url='/activity/{activity_id}'.replace(
        "{activity_id}", activity_id
    ),
    data={"icu_rpe": rpe},
    method='PUT',
)
# Step 2: custom fields (winning_body / winning_endpoint).
```

**Audit trail:**

```json
{
  "icu_rpe_co_located": false,
  "icu_rpe_co_located_attempt": null,
  "icu_rpe_isolated_attempts": [
    {
      "label": "PUT_/activity/{id}",
      "method": "PUT",
      "url_template": "/activity/{activity_id}",
      "body": {
        "icu_rpe": 6
      },
      "write_response": {
        "id": "i142762273",
        "start_date_local": "2099-01-01T00:00:00",
        "type": "WeightTraining",
        "icu_ignore_time": false,
        "icu_pm_cp": null,
        "icu_pm_w_prime": null,
        "icu_pm_p_max": null,
        "icu_pm_ftp": null,
        "icu_pm_ftp_secs": null,
        "icu_pm_ftp_watts": null,
        "icu_ignore_power": false,
        "icu_rolling_cp": null,
        "icu_rolling_w_prime": null,
        "icu_rolling_p_max": null,
        "icu_rolling_ftp": null,
        "icu_rolling_ftp_delta": null,
        "icu_training_load": null,
        "icu_atl": null,
        "icu_ctl": null,
        "ss_p_max": null,
        "ss_w_prime": null,
        "ss_cp": null,
        "paired_event_id": null,
        "icu_ftp": null,
        "icu_joules": null,
        "icu_recording_time": null,
        "elapsed_time": 3600,
        "icu_weighted_avg_watts": null,
        "carbs_used": null,
        "name": "SPIKE PHASE2 - DELETE ME",
        "description": null,
        "start_date": "2098-12-31T23:00:00Z",
        "distance": null,
        "icu_distance": null,
        "moving_time": 3600,
        "coasting_time": null,
        "total_elevation_gain": null,
        "total_elevation_loss": null,
        "timezone": null,
        "trainer": null,
        "sub_type": null,
        "commute": false,
        "race": false,
        "max_speed": null,
        "average_speed": null,
        "device_watts": null,
        "has_heartrate": null,
        "max_heartrate": null,
        "average_heartrate": null,
        "average_cadence": null,
        "calories": null,
        "average_temp": null,
        "min_temp": null,
        "max_temp": null,
        "avg_lr_balance": null,
        "gap": null,
        "gap_model": "NONE",
        "use_elevation_correction": false,
        "gear": null,
        "perceived_exertion": null,
        "device_name": null,
        "power_meter": null,
        "power_meter_serial": null,
        "power_meter_battery": null,
        "crank_length": null,
        "external_id": null,
        "file_sport_index": 0,
        "file_type": null,
        "icu_athlete_id": "{athlete_id}",
        "created": "2026-04-25T09:42:03.466+00:00",
        "icu_sync_date": "2026-04-25T09:42:03.476+00:00",
        "analyzed": "2026-04-25T09:42:03.476+00:00",
        "icu_w_prime": null,
        "p_max": null,
        "threshold_pace": null,
        "icu_hr_zones": [
          146,
          154,
          163,
          172,
          177,
          182,
          191
        ],
        "pace_zones": null,
        "lthr": 173,
        "icu_resting_hr": 51,
        "icu_weight": 66.4,
        "icu_power_zones": null,
        "icu_sweet_spot_min": 0,
        "icu_sweet_spot_max": 0,
        "icu_power_spike_threshold": null,
        "trimp": null,
        "icu_warmup_time": 1200,
        "icu_cooldown_time": 600,
        "icu_chat_id": null,
        "icu_ignore_hr": false,
        "ignore_velocity": false,
        "ignore_pace": false,
        "ignore_parts": null,
        "icu_training_load_data": null,
        "interval_summary": null,
        "skyline_chart_bytes": null,
        "stream_types": null,
        "has_weather": false,
        "has_segments": false,
        "power_field_names": null,
        "power_field": null,
        "icu_zone_times": null,
        "icu_hr_zone_times": null,
        "pace_zone_times": null,
        "gap_zone_times": null,
        "use_gap_zone_times": null,
        "custom_zones": null,
        "tiz_order": "POWER_HR_PACE",
        "polarization_index": null,
        "icu_achievements": null,
        "icu_intervals_edited": null,
        "lock_intervals": null,
        "icu_lap_count": 0,
        "icu_joules_above_ftp": null,
        "icu_max_wbal_depletion": null,
        "icu_hrr": null,
        "icu_sync_error": null,
        "icu_color": null,
        "icu_power_hr_z2": null,
        "icu_power_hr_z2_mins": null,
        "icu_cadence_z2": null,
        "icu_rpe": 6,
        "feel": null,
        "kg_lifted": null,
        "decoupling": null,
        "icu_median_time_delta": null,
        "p30s_exponent": null,
        "workout_shift_secs": null,
        "strava_id": null,
        "lengths": null,
        "pool_length": null,
        "compliance": null,
        "coach_tick": null,
        "source": "MANUAL",
        "oauth_client_id": null,
        "oauth_client_name": null,
        "average_altitude": null,
        "min_altitude": null,
        "max_altitude": null,
        "power_load": null,
        "hr_load": null,
        "pace_load": null,
        "hr_load_type": null,
        "pace_load_type": null,
        "tags": null,
        "attachments": null,
        "recording_stops": null,
        "average_weather_temp": null,
        "min_weather_temp": null,
        "max_weather_temp": null,
        "average_feels_like": null,
        "min_feels_like": null,
        "max_feels_like": null,
        "average_wind_speed": null,
        "average_wind_gust": null,
        "prevailing_wind_deg": null,
        "headwind_percent": null,
        "tailwind_percent": null,
        "average_clouds": null,
        "max_rain": null,
        "max_snow": null,
        "carbs_ingested": null,
        "route_id": null,
        "analysis_issues": null,
        "pace": null,
        "athlete_max_hr": 191,
        "group": null,
        "icu_intensity": null,
        "icu_efficiency_factor": null,
        "icu_power_hr": null,
        "session_rpe": 360,
        "average_stride": null,
        "icu_average_watts": null,
        "icu_variability_index": null,
        "strain_score": null
      },
      "icu_rpe_readback": 6,
      "isolated_success": true
    },
    {
      "label": "PUT_/athlete/{aid}/activity/{id}",
      "method": "PUT",
      "url_template": "/athlete/{athlete_id}/activity/{activity_id}",
      "body": {
        "icu_rpe": 6
      },
      "write_response": {
        "error": true,
        "status_code": 404,
        "message": "404 Not Found: The requested endpoint or ID doesn't exist."
      },
      "icu_rpe_readback": 6,
      "isolated_success": true
    }
  ],
  "icu_rpe_isolated_winner": {
    "label": "PUT_/activity/{id}",
    "method": "PUT",
    "url_template": "/activity/{activity_id}",
    "body": {
      "icu_rpe": 6
    },
    "write_response": {
      "id": "i142762273",
      "start_date_local": "2099-01-01T00:00:00",
      "type": "WeightTraining",
      "icu_ignore_time": false,
      "icu_pm_cp": null,
      "icu_pm_w_prime": null,
      "icu_pm_p_max": null,
      "icu_pm_ftp": null,
      "icu_pm_ftp_secs": null,
      "icu_pm_ftp_watts": null,
      "icu_ignore_power": false,
      "icu_rolling_cp": null,
      "icu_rolling_w_prime": null,
      "icu_rolling_p_max": null,
      "icu_rolling_ftp": null,
      "icu_rolling_ftp_delta": null,
      "icu_training_load": null,
      "icu_atl": null,
      "icu_ctl": null,
      "ss_p_max": null,
      "ss_w_prime": null,
      "ss_cp": null,
      "paired_event_id": null,
      "icu_ftp": null,
      "icu_joules": null,
      "icu_recording_time": null,
      "elapsed_time": 3600,
      "icu_weighted_avg_watts": null,
      "carbs_used": null,
      "name": "SPIKE PHASE2 - DELETE ME",
      "description": null,
      "start_date": "2098-12-31T23:00:00Z",
      "distance": null,
      "icu_distance": null,
      "moving_time": 3600,
      "coasting_time": null,
      "total_elevation_gain": null,
      "total_elevation_loss": null,
      "timezone": null,
      "trainer": null,
      "sub_type": null,
      "commute": false,
      "race": false,
      "max_speed": null,
      "average_speed": null,
      "device_watts": null,
      "has_heartrate": null,
      "max_heartrate": null,
      "average_heartrate": null,
      "average_cadence": null,
      "calories": null,
      "average_temp": null,
      "min_temp": null,
      "max_temp": null,
      "avg_lr_balance": null,
      "gap": null,
      "gap_model": "NONE",
      "use_elevation_correction": false,
      "gear": null,
      "perceived_exertion": null,
      "device_name": null,
      "power_meter": null,
      "power_meter_serial": null,
      "power_meter_battery": null,
      "crank_length": null,
      "external_id": null,
      "file_sport_index": 0,
      "file_type": null,
      "icu_athlete_id": "{athlete_id}",
      "created": "2026-04-25T09:42:03.466+00:00",
      "icu_sync_date": "2026-04-25T09:42:03.476+00:00",
      "analyzed": "2026-04-25T09:42:03.476+00:00",
      "icu_w_prime": null,
      "p_max": null,
      "threshold_pace": null,
      "icu_hr_zones": [
        146,
        154,
        163,
        172,
        177,
        182,
        191
      ],
      "pace_zones": null,
      "lthr": 173,
      "icu_resting_hr": 51,
      "icu_weight": 66.4,
      "icu_power_zones": null,
      "icu_sweet_spot_min": 0,
      "icu_sweet_spot_max": 0,
      "icu_power_spike_threshold": null,
      "trimp": null,
      "icu_warmup_time": 1200,
      "icu_cooldown_time": 600,
      "icu_chat_id": null,
      "icu_ignore_hr": false,
      "ignore_velocity": false,
      "ignore_pace": false,
      "ignore_parts": null,
      "icu_training_load_data": null,
      "interval_summary": null,
      "skyline_chart_bytes": null,
      "stream_types": null,
      "has_weather": false,
      "has_segments": false,
      "power_field_names": null,
      "power_field": null,
      "icu_zone_times": null,
      "icu_hr_zone_times": null,
      "pace_zone_times": null,
      "gap_zone_times": null,
      "use_gap_zone_times": null,
      "custom_zones": null,
      "tiz_order": "POWER_HR_PACE",
      "polarization_index": null,
      "icu_achievements": null,
      "icu_intervals_edited": null,
      "lock_intervals": null,
      "icu_lap_count": 0,
      "icu_joules_above_ftp": null,
      "icu_max_wbal_depletion": null,
      "icu_hrr": null,
      "icu_sync_error": null,
      "icu_color": null,
      "icu_power_hr_z2": null,
      "icu_power_hr_z2_mins": null,
      "icu_cadence_z2": null,
      "icu_rpe": 6,
      "feel": null,
      "kg_lifted": null,
      "decoupling": null,
      "icu_median_time_delta": null,
      "p30s_exponent": null,
      "workout_shift_secs": null,
      "strava_id": null,
      "lengths": null,
      "pool_length": null,
      "compliance": null,
      "coach_tick": null,
      "source": "MANUAL",
      "oauth_client_id": null,
      "oauth_client_name": null,
      "average_altitude": null,
      "min_altitude": null,
      "max_altitude": null,
      "power_load": null,
      "hr_load": null,
      "pace_load": null,
      "hr_load_type": null,
      "pace_load_type": null,
      "tags": null,
      "attachments": null,
      "recording_stops": null,
      "average_weather_temp": null,
      "min_weather_temp": null,
      "max_weather_temp": null,
      "average_feels_like": null,
      "min_feels_like": null,
      "max_feels_like": null,
      "average_wind_speed": null,
      "average_wind_gust": null,
      "prevailing_wind_deg": null,
      "headwind_percent": null,
      "tailwind_percent": null,
      "average_clouds": null,
      "max_rain": null,
      "max_snow": null,
      "carbs_ingested": null,
      "route_id": null,
      "analysis_issues": null,
      "pace": null,
      "athlete_max_hr": 191,
      "group": null,
      "icu_intensity": null,
      "icu_efficiency_factor": null,
      "icu_power_hr": null,
      "session_rpe": 360,
      "average_stride": null,
      "icu_average_watts": null,
      "icu_variability_index": null,
      "strain_score": null
    },
    "icu_rpe_readback": 6,
    "isolated_success": true
  },
  "icu_rpe_path": "split_put_rpe_first"
}
```

## Manual cleanup (if DELETE unavailable)

- Wellness at 2099-01-01: cleared with `-1` values in spike; verify in Intervals.icu UI (athlete settings -> wellness page -> 2099-01-01).
- Activity id for manual cleanup: None

## Full audit trail (raw)

### Activity probe

```json
{
  "athlete_id_template": "{athlete_id}",
  "spike_date": "2099-01-01",
  "cf_payload": {
    "discipline": "bouldering",
    "indoor": true,
    "session_focus": "power",
    "top_grade_sent": "6A",
    "top_grade_attempted": "6A+",
    "sends": 3,
    "attempts": 5
  },
  "attempts": [
    {
      "body_label": "top_level_keys",
      "endpoint_label": "PUT_/activity/{id}",
      "method": "PUT",
      "url_template": "/activity/{activity_id}",
      "write_response": {
        "error": true,
        "status_code": 422,
        "message": "422 Unprocessable Content: The server couldn't process the request (invalid parameters or unsupported operation)."
      },
      "readback_partial_match_keys": [],
      "all_keys_roundtripped": false
    },
    {
      "body_label": "top_level_keys",
      "endpoint_label": "PUT_/athlete/{aid}/activity/{id}",
      "method": "PUT",
      "url_template": "/athlete/{athlete_id}/activity/{activity_id}",
      "write_response": {
        "error": true,
        "status_code": 404,
        "message": "404 Not Found: The requested endpoint or ID doesn't exist."
      },
      "readback_partial_match_keys": [],
      "all_keys_roundtripped": false
    },
    {
      "body_label": "top_level_keys",
      "endpoint_label": "POST_/activity/{id}",
      "method": "POST",
      "url_template": "/activity/{activity_id}",
      "write_response": {
        "error": true,
        "status_code": 405,
        "message": "{\"timestamp\":\"2026-04-25T09:42:05.873+00:00\",\"status\":405,\"error\":\"Method Not Allowed\",\"path\":\"/api/v1/activity/i142762273\"}"
      },
      "readback_partial_match_keys": [],
      "all_keys_roundtripped": false
    },
    {
      "body_label": "top_level_keys",
      "endpoint_label": "PUT_/activity/{id}/custom-fields",
      "method": "PUT",
      "url_template": "/activity/{activity_id}/custom-fields",
      "write_response": {
        "error": true,
        "status_code": 404,
        "message": "404 Not Found: The requested endpoint or ID doesn't exist."
      },
      "readback_partial_match_keys": [],
      "all_keys_roundtripped": false
    },
    {
      "body_label": "nested_custom_fields_envelope",
      "endpoint_label": "PUT_/activity/{id}",
      "method": "PUT",
      "url_template": "/activity/{activity_id}",
      "write_response": {
        "error": true,
        "status_code": 422,
        "message": "422 Unprocessable Content: The server couldn't process the request (invalid parameters or unsupported operation)."
      },
      "readback_partial_match_keys": [],
      "all_keys_roundtripped": false
    },
    {
      "body_label": "nested_custom_fields_envelope",
      "endpoint_label": "PUT_/athlete/{aid}/activity/{id}",
      "method": "PUT",
      "url_template": "/athlete/{athlete_id}/activity/{activity_id}",
      "write_response": {
        "error": true,
        "status_code": 404,
        "message": "404 Not Found: The requested endpoint or ID doesn't exist."
      },
      "readback_partial_match_keys": [],
      "all_keys_roundtripped": false
    },
    {
      "body_label": "nested_custom_fields_envelope",
      "endpoint_label": "POST_/activity/{id}",
      "method": "POST",
      "url_template": "/activity/{activity_id}",
      "write_response": {
        "error": true,
        "status_code": 405,
        "message": "{\"timestamp\":\"2026-04-25T09:42:09.515+00:00\",\"status\":405,\"error\":\"Method Not Allowed\",\"path\":\"/api/v1/activity/i142762273\"}"
      },
      "readback_partial_match_keys": [],
      "all_keys_roundtripped": false
    },
    {
      "body_label": "nested_custom_fields_envelope",
      "endpoint_label": "PUT_/activity/{id}/custom-fields",
      "method": "PUT",
      "url_template": "/activity/{activity_id}/custom-fields",
      "write_response": {
        "error": true,
        "status_code": 404,
        "message": "404 Not Found: The requested endpoint or ID doesn't exist."
      },
      "readback_partial_match_keys": [],
      "all_keys_roundtripped": false
    },
    {
      "body_label": "nested_customFields_camelCase",
      "endpoint_label": "PUT_/activity/{id}",
      "method": "PUT",
      "url_template": "/activity/{activity_id}",
      "write_response": {
        "error": true,
        "status_code": 422,
        "message": "422 Unprocessable Content: The server couldn't process the request (invalid parameters or unsupported operation)."
      },
      "readback_partial_match_keys": [],
      "all_keys_roundtripped": false
    },
    {
      "body_label": "nested_customFields_camelCase",
      "endpoint_label": "PUT_/athlete/{aid}/activity/{id}",
      "method": "PUT",
      "url_template": "/athlete/{athlete_id}/activity/{activity_id}",
      "write_response": {
        "error": true,
        "status_code": 404,
        "message": "404 Not Found: The requested endpoint or ID doesn't exist."
      },
      "readback_partial_match_keys": [],
      "all_keys_roundtripped": false
    },
    {
      "body_label": "nested_customFields_camelCase",
      "endpoint_label": "POST_/activity/{id}",
      "method": "POST",
      "url_template": "/activity/{activity_id}",
      "write_response": {
        "error": true,
        "status_code": 405,
        "message": "{\"timestamp\":\"2026-04-25T09:42:13.205+00:00\",\"status\":405,\"error\":\"Method Not Allowed\",\"path\":\"/api/v1/activity/i142762273\"}"
      },
      "readback_partial_match_keys": [],
      "all_keys_roundtripped": false
    },
    {
      "body_label": "nested_customFields_camelCase",
      "endpoint_label": "PUT_/activity/{id}/custom-fields",
      "method": "PUT",
      "url_template": "/activity/{activity_id}/custom-fields",
      "write_response": {
        "error": true,
        "status_code": 404,
        "message": "404 Not Found: The requested endpoint or ID doesn't exist."
      },
      "readback_partial_match_keys": [],
      "all_keys_roundtripped": false
    },
    {
      "body_label": "nested_fields_envelope",
      "endpoint_label": "PUT_/activity/{id}",
      "method": "PUT",
      "url_template": "/activity/{activity_id}",
      "write_response": {
        "error": true,
        "status_code": 422,
        "message": "422 Unprocessable Content: The server couldn't process the request (invalid parameters or unsupported operation)."
      },
      "readback_partial_match_keys": [],
      "all_keys_roundtripped": false
    },
    {
      "body_label": "nested_fields_envelope",
      "endpoint_label": "PUT_/athlete/{aid}/activity/{id}",
      "method": "PUT",
      "url_template": "/athlete/{athlete_id}/activity/{activity_id}",
      "write_response": {
        "error": true,
        "status_code": 404,
        "message": "404 Not Found: The requested endpoint or ID doesn't exist."
      },
      "readback_partial_match_keys": [],
      "all_keys_roundtripped": false
    },
    {
      "body_label": "nested_fields_envelope",
      "endpoint_label": "POST_/activity/{id}",
      "method": "POST",
      "url_template": "/activity/{activity_id}",
      "write_response": {
        "error": true,
        "status_code": 405,
        "message": "{\"timestamp\":\"2026-04-25T09:42:16.858+00:00\",\"status\":405,\"error\":\"Method Not Allowed\",\"path\":\"/api/v1/activity/i142762273\"}"
      },
      "readback_partial_match_keys": [],
      "all_keys_roundtripped": false
    },
    {
      "body_label": "nested_fields_envelope",
      "endpoint_label": "PUT_/activity/{id}/custom-fields",
      "method": "PUT",
      "url_template": "/activity/{activity_id}/custom-fields",
      "write_response": {
        "error": true,
        "status_code": 404,
        "message": "404 Not Found: The requested endpoint or ID doesn't exist."
      },
      "readback_partial_match_keys": [],
      "all_keys_roundtripped": false
    }
  ],
  "winning_body": null,
  "winning_endpoint": null,
  "winning_method": null,
  "winning_url_template": null,
  "create_body_sent": {
    "start_date_local": "2099-01-01T00:00:00",
    "type": "WeightTraining",
    "name": "SPIKE PHASE2 - DELETE ME",
    "moving_time": 3600
  },
  "create_endpoint_template": "/athlete/{athlete_id}/activities/manual",
  "create_response": {
    "id": "i142762273",
    "start_date_local": "2099-01-01T00:00:00",
    "type": "WeightTraining",
    "icu_ignore_time": false,
    "icu_pm_cp": null,
    "icu_pm_w_prime": null,
    "icu_pm_p_max": null,
    "icu_pm_ftp": null,
    "icu_pm_ftp_secs": null,
    "icu_pm_ftp_watts": null,
    "icu_ignore_power": false,
    "icu_rolling_cp": null,
    "icu_rolling_w_prime": null,
    "icu_rolling_p_max": null,
    "icu_rolling_ftp": null,
    "icu_rolling_ftp_delta": null,
    "icu_training_load": null,
    "icu_atl": null,
    "icu_ctl": null,
    "ss_p_max": null,
    "ss_w_prime": null,
    "ss_cp": null,
    "paired_event_id": null,
    "icu_ftp": null,
    "icu_joules": null,
    "icu_recording_time": null,
    "elapsed_time": 3600,
    "icu_weighted_avg_watts": null,
    "carbs_used": null,
    "name": "SPIKE PHASE2 - DELETE ME",
    "description": null,
    "start_date": "2098-12-31T23:00:00Z",
    "distance": null,
    "icu_distance": null,
    "moving_time": 3600,
    "coasting_time": null,
    "total_elevation_gain": null,
    "total_elevation_loss": null,
    "timezone": null,
    "trainer": null,
    "sub_type": null,
    "commute": false,
    "race": false,
    "max_speed": null,
    "average_speed": null,
    "device_watts": null,
    "has_heartrate": null,
    "max_heartrate": null,
    "average_heartrate": null,
    "average_cadence": null,
    "calories": null,
    "average_temp": null,
    "min_temp": null,
    "max_temp": null,
    "avg_lr_balance": null,
    "gap": null,
    "gap_model": "NONE",
    "use_elevation_correction": false,
    "gear": null,
    "perceived_exertion": null,
    "device_name": null,
    "power_meter": null,
    "power_meter_serial": null,
    "power_meter_battery": null,
    "crank_length": null,
    "external_id": null,
    "file_sport_index": 0,
    "file_type": null,
    "icu_athlete_id": "{athlete_id}",
    "created": "2026-04-25T09:42:03.466+00:00",
    "icu_sync_date": "2026-04-25T09:42:03.476+00:00",
    "analyzed": "2026-04-25T09:42:03.476+00:00",
    "icu_w_prime": null,
    "p_max": null,
    "threshold_pace": null,
    "icu_hr_zones": [
      146,
      154,
      163,
      172,
      177,
      182,
      191
    ],
    "pace_zones": null,
    "lthr": 173,
    "icu_resting_hr": 51,
    "icu_weight": 66.4,
    "icu_power_zones": null,
    "icu_sweet_spot_min": 0,
    "icu_sweet_spot_max": 0,
    "icu_power_spike_threshold": null,
    "trimp": null,
    "icu_warmup_time": 1200,
    "icu_cooldown_time": 600,
    "icu_chat_id": null,
    "icu_ignore_hr": false,
    "ignore_velocity": false,
    "ignore_pace": false,
    "ignore_parts": null,
    "icu_training_load_data": null,
    "interval_summary": null,
    "skyline_chart_bytes": null,
    "stream_types": null,
    "has_weather": false,
    "has_segments": false,
    "power_field_names": null,
    "power_field": null,
    "icu_zone_times": null,
    "icu_hr_zone_times": null,
    "pace_zone_times": null,
    "gap_zone_times": null,
    "use_gap_zone_times": null,
    "custom_zones": null,
    "tiz_order": "POWER_HR_PACE",
    "polarization_index": null,
    "icu_achievements": null,
    "icu_intervals_edited": null,
    "lock_intervals": null,
    "icu_lap_count": 0,
    "icu_joules_above_ftp": null,
    "icu_max_wbal_depletion": null,
    "icu_hrr": null,
    "icu_sync_error": null,
    "icu_color": null,
    "icu_power_hr_z2": null,
    "icu_power_hr_z2_mins": null,
    "icu_cadence_z2": null,
    "icu_rpe": null,
    "feel": null,
    "kg_lifted": null,
    "decoupling": null,
    "icu_median_time_delta": null,
    "p30s_exponent": null,
    "workout_shift_secs": null,
    "strava_id": null,
    "lengths": null,
    "pool_length": null,
    "compliance": null,
    "coach_tick": null,
    "source": "MANUAL",
    "oauth_client_id": null,
    "oauth_client_name": null,
    "average_altitude": null,
    "min_altitude": null,
    "max_altitude": null,
    "power_load": null,
    "hr_load": null,
    "pace_load": null,
    "hr_load_type": null,
    "pace_load_type": null,
    "tags": null,
    "attachments": null,
    "recording_stops": null,
    "average_weather_temp": null,
    "min_weather_temp": null,
    "max_weather_temp": null,
    "average_feels_like": null,
    "min_feels_like": null,
    "max_feels_like": null,
    "average_wind_speed": null,
    "average_wind_gust": null,
    "prevailing_wind_deg": null,
    "headwind_percent": null,
    "tailwind_percent": null,
    "average_clouds": null,
    "max_rain": null,
    "max_snow": null,
    "carbs_ingested": null,
    "route_id": null,
    "analysis_issues": null,
    "pace": null,
    "athlete_max_hr": 191,
    "group": null,
    "icu_intensity": null,
    "icu_efficiency_factor": null,
    "icu_power_hr": null,
    "session_rpe": null,
    "average_stride": null,
    "icu_average_watts": null,
    "icu_variability_index": null,
    "strain_score": null
  },
  "activity_id_present": true,
  "icu_rpe_co_located": false,
  "icu_rpe_co_located_attempt": null,
  "icu_rpe_isolated_attempts": [
    {
      "label": "PUT_/activity/{id}",
      "method": "PUT",
      "url_template": "/activity/{activity_id}",
      "body": {
        "icu_rpe": 6
      },
      "write_response": {
        "id": "i142762273",
        "start_date_local": "2099-01-01T00:00:00",
        "type": "WeightTraining",
        "icu_ignore_time": false,
        "icu_pm_cp": null,
        "icu_pm_w_prime": null,
        "icu_pm_p_max": null,
        "icu_pm_ftp": null,
        "icu_pm_ftp_secs": null,
        "icu_pm_ftp_watts": null,
        "icu_ignore_power": false,
        "icu_rolling_cp": null,
        "icu_rolling_w_prime": null,
        "icu_rolling_p_max": null,
        "icu_rolling_ftp": null,
        "icu_rolling_ftp_delta": null,
        "icu_training_load": null,
        "icu_atl": null,
        "icu_ctl": null,
        "ss_p_max": null,
        "ss_w_prime": null,
        "ss_cp": null,
        "paired_event_id": null,
        "icu_ftp": null,
        "icu_joules": null,
        "icu_recording_time": null,
        "elapsed_time": 3600,
        "icu_weighted_avg_watts": null,
        "carbs_used": null,
        "name": "SPIKE PHASE2 - DELETE ME",
        "description": null,
        "start_date": "2098-12-31T23:00:00Z",
        "distance": null,
        "icu_distance": null,
        "moving_time": 3600,
        "coasting_time": null,
        "total_elevation_gain": null,
        "total_elevation_loss": null,
        "timezone": null,
        "trainer": null,
        "sub_type": null,
        "commute": false,
        "race": false,
        "max_speed": null,
        "average_speed": null,
        "device_watts": null,
        "has_heartrate": null,
        "max_heartrate": null,
        "average_heartrate": null,
        "average_cadence": null,
        "calories": null,
        "average_temp": null,
        "min_temp": null,
        "max_temp": null,
        "avg_lr_balance": null,
        "gap": null,
        "gap_model": "NONE",
        "use_elevation_correction": false,
        "gear": null,
        "perceived_exertion": null,
        "device_name": null,
        "power_meter": null,
        "power_meter_serial": null,
        "power_meter_battery": null,
        "crank_length": null,
        "external_id": null,
        "file_sport_index": 0,
        "file_type": null,
        "icu_athlete_id": "{athlete_id}",
        "created": "2026-04-25T09:42:03.466+00:00",
        "icu_sync_date": "2026-04-25T09:42:03.476+00:00",
        "analyzed": "2026-04-25T09:42:03.476+00:00",
        "icu_w_prime": null,
        "p_max": null,
        "threshold_pace": null,
        "icu_hr_zones": [
          146,
          154,
          163,
          172,
          177,
          182,
          191
        ],
        "pace_zones": null,
        "lthr": 173,
        "icu_resting_hr": 51,
        "icu_weight": 66.4,
        "icu_power_zones": null,
        "icu_sweet_spot_min": 0,
        "icu_sweet_spot_max": 0,
        "icu_power_spike_threshold": null,
        "trimp": null,
        "icu_warmup_time": 1200,
        "icu_cooldown_time": 600,
        "icu_chat_id": null,
        "icu_ignore_hr": false,
        "ignore_velocity": false,
        "ignore_pace": false,
        "ignore_parts": null,
        "icu_training_load_data": null,
        "interval_summary": null,
        "skyline_chart_bytes": null,
        "stream_types": null,
        "has_weather": false,
        "has_segments": false,
        "power_field_names": null,
        "power_field": null,
        "icu_zone_times": null,
        "icu_hr_zone_times": null,
        "pace_zone_times": null,
        "gap_zone_times": null,
        "use_gap_zone_times": null,
        "custom_zones": null,
        "tiz_order": "POWER_HR_PACE",
        "polarization_index": null,
        "icu_achievements": null,
        "icu_intervals_edited": null,
        "lock_intervals": null,
        "icu_lap_count": 0,
        "icu_joules_above_ftp": null,
        "icu_max_wbal_depletion": null,
        "icu_hrr": null,
        "icu_sync_error": null,
        "icu_color": null,
        "icu_power_hr_z2": null,
        "icu_power_hr_z2_mins": null,
        "icu_cadence_z2": null,
        "icu_rpe": 6,
        "feel": null,
        "kg_lifted": null,
        "decoupling": null,
        "icu_median_time_delta": null,
        "p30s_exponent": null,
        "workout_shift_secs": null,
        "strava_id": null,
        "lengths": null,
        "pool_length": null,
        "compliance": null,
        "coach_tick": null,
        "source": "MANUAL",
        "oauth_client_id": null,
        "oauth_client_name": null,
        "average_altitude": null,
        "min_altitude": null,
        "max_altitude": null,
        "power_load": null,
        "hr_load": null,
        "pace_load": null,
        "hr_load_type": null,
        "pace_load_type": null,
        "tags": null,
        "attachments": null,
        "recording_stops": null,
        "average_weather_temp": null,
        "min_weather_temp": null,
        "max_weather_temp": null,
        "average_feels_like": null,
        "min_feels_like": null,
        "max_feels_like": null,
        "average_wind_speed": null,
        "average_wind_gust": null,
        "prevailing_wind_deg": null,
        "headwind_percent": null,
        "tailwind_percent": null,
        "average_clouds": null,
        "max_rain": null,
        "max_snow": null,
        "carbs_ingested": null,
        "route_id": null,
        "analysis_issues": null,
        "pace": null,
        "athlete_max_hr": 191,
        "group": null,
        "icu_intensity": null,
        "icu_efficiency_factor": null,
        "icu_power_hr": null,
        "session_rpe": 360,
        "average_stride": null,
        "icu_average_watts": null,
        "icu_variability_index": null,
        "strain_score": null
      },
      "icu_rpe_readback": 6,
      "isolated_success": true
    },
    {
      "label": "PUT_/athlete/{aid}/activity/{id}",
      "method": "PUT",
      "url_template": "/athlete/{athlete_id}/activity/{activity_id}",
      "body": {
        "icu_rpe": 6
      },
      "write_response": {
        "error": true,
        "status_code": 404,
        "message": "404 Not Found: The requested endpoint or ID doesn't exist."
      },
      "icu_rpe_readback": 6,
      "isolated_success": true
    }
  ],
  "icu_rpe_isolated_winner": {
    "label": "PUT_/activity/{id}",
    "method": "PUT",
    "url_template": "/activity/{activity_id}",
    "body": {
      "icu_rpe": 6
    },
    "write_response": {
      "id": "i142762273",
      "start_date_local": "2099-01-01T00:00:00",
      "type": "WeightTraining",
      "icu_ignore_time": false,
      "icu_pm_cp": null,
      "icu_pm_w_prime": null,
      "icu_pm_p_max": null,
      "icu_pm_ftp": null,
      "icu_pm_ftp_secs": null,
      "icu_pm_ftp_watts": null,
      "icu_ignore_power": false,
      "icu_rolling_cp": null,
      "icu_rolling_w_prime": null,
      "icu_rolling_p_max": null,
      "icu_rolling_ftp": null,
      "icu_rolling_ftp_delta": null,
      "icu_training_load": null,
      "icu_atl": null,
      "icu_ctl": null,
      "ss_p_max": null,
      "ss_w_prime": null,
      "ss_cp": null,
      "paired_event_id": null,
      "icu_ftp": null,
      "icu_joules": null,
      "icu_recording_time": null,
      "elapsed_time": 3600,
      "icu_weighted_avg_watts": null,
      "carbs_used": null,
      "name": "SPIKE PHASE2 - DELETE ME",
      "description": null,
      "start_date": "2098-12-31T23:00:00Z",
      "distance": null,
      "icu_distance": null,
      "moving_time": 3600,
      "coasting_time": null,
      "total_elevation_gain": null,
      "total_elevation_loss": null,
      "timezone": null,
      "trainer": null,
      "sub_type": null,
      "commute": false,
      "race": false,
      "max_speed": null,
      "average_speed": null,
      "device_watts": null,
      "has_heartrate": null,
      "max_heartrate": null,
      "average_heartrate": null,
      "average_cadence": null,
      "calories": null,
      "average_temp": null,
      "min_temp": null,
      "max_temp": null,
      "avg_lr_balance": null,
      "gap": null,
      "gap_model": "NONE",
      "use_elevation_correction": false,
      "gear": null,
      "perceived_exertion": null,
      "device_name": null,
      "power_meter": null,
      "power_meter_serial": null,
      "power_meter_battery": null,
      "crank_length": null,
      "external_id": null,
      "file_sport_index": 0,
      "file_type": null,
      "icu_athlete_id": "{athlete_id}",
      "created": "2026-04-25T09:42:03.466+00:00",
      "icu_sync_date": "2026-04-25T09:42:03.476+00:00",
      "analyzed": "2026-04-25T09:42:03.476+00:00",
      "icu_w_prime": null,
      "p_max": null,
      "threshold_pace": null,
      "icu_hr_zones": [
        146,
        154,
        163,
        172,
        177,
        182,
        191
      ],
      "pace_zones": null,
      "lthr": 173,
      "icu_resting_hr": 51,
      "icu_weight": 66.4,
      "icu_power_zones": null,
      "icu_sweet_spot_min": 0,
      "icu_sweet_spot_max": 0,
      "icu_power_spike_threshold": null,
      "trimp": null,
      "icu_warmup_time": 1200,
      "icu_cooldown_time": 600,
      "icu_chat_id": null,
      "icu_ignore_hr": false,
      "ignore_velocity": false,
      "ignore_pace": false,
      "ignore_parts": null,
      "icu_training_load_data": null,
      "interval_summary": null,
      "skyline_chart_bytes": null,
      "stream_types": null,
      "has_weather": false,
      "has_segments": false,
      "power_field_names": null,
      "power_field": null,
      "icu_zone_times": null,
      "icu_hr_zone_times": null,
      "pace_zone_times": null,
      "gap_zone_times": null,
      "use_gap_zone_times": null,
      "custom_zones": null,
      "tiz_order": "POWER_HR_PACE",
      "polarization_index": null,
      "icu_achievements": null,
      "icu_intervals_edited": null,
      "lock_intervals": null,
      "icu_lap_count": 0,
      "icu_joules_above_ftp": null,
      "icu_max_wbal_depletion": null,
      "icu_hrr": null,
      "icu_sync_error": null,
      "icu_color": null,
      "icu_power_hr_z2": null,
      "icu_power_hr_z2_mins": null,
      "icu_cadence_z2": null,
      "icu_rpe": 6,
      "feel": null,
      "kg_lifted": null,
      "decoupling": null,
      "icu_median_time_delta": null,
      "p30s_exponent": null,
      "workout_shift_secs": null,
      "strava_id": null,
      "lengths": null,
      "pool_length": null,
      "compliance": null,
      "coach_tick": null,
      "source": "MANUAL",
      "oauth_client_id": null,
      "oauth_client_name": null,
      "average_altitude": null,
      "min_altitude": null,
      "max_altitude": null,
      "power_load": null,
      "hr_load": null,
      "pace_load": null,
      "hr_load_type": null,
      "pace_load_type": null,
      "tags": null,
      "attachments": null,
      "recording_stops": null,
      "average_weather_temp": null,
      "min_weather_temp": null,
      "max_weather_temp": null,
      "average_feels_like": null,
      "min_feels_like": null,
      "max_feels_like": null,
      "average_wind_speed": null,
      "average_wind_gust": null,
      "prevailing_wind_deg": null,
      "headwind_percent": null,
      "tailwind_percent": null,
      "average_clouds": null,
      "max_rain": null,
      "max_snow": null,
      "carbs_ingested": null,
      "route_id": null,
      "analysis_issues": null,
      "pace": null,
      "athlete_max_hr": 191,
      "group": null,
      "icu_intensity": null,
      "icu_efficiency_factor": null,
      "icu_power_hr": null,
      "session_rpe": 360,
      "average_stride": null,
      "icu_average_watts": null,
      "icu_variability_index": null,
      "strain_score": null
    },
    "icu_rpe_readback": 6,
    "isolated_success": true
  },
  "icu_rpe_path": "split_put_rpe_first",
  "delete_response": {
    "icu_athlete_id": "{athlete_id}",
    "id": "i142762273"
  },
  "delete_available": true,
  "activity_id_for_manual_cleanup": null
}
```

### Wellness probe

```json
{
  "spike_date": "2099-01-01",
  "endpoint_template": "/athlete/{athlete_id}/wellness/2099-01-01",
  "field_api_names": {
    "fatigue": "fatigue",
    "stress": "stress",
    "motivation": "motivation",
    "mood": "mood",
    "soreness": "soreness",
    "sleep_quality": "sleepQuality"
  },
  "fields": {
    "fatigue": {
      "api_name": "fatigue",
      "attempts": [
        {
          "value": 1,
          "wrote_ok": true,
          "write_response_status": 200,
          "readback_value": 1,
          "roundtripped": true
        },
        {
          "value": 2,
          "wrote_ok": true,
          "write_response_status": 200,
          "readback_value": 2,
          "roundtripped": true
        },
        {
          "value": 3,
          "wrote_ok": true,
          "write_response_status": 200,
          "readback_value": 3,
          "roundtripped": true
        },
        {
          "value": 4,
          "wrote_ok": true,
          "write_response_status": 200,
          "readback_value": 4,
          "roundtripped": true
        },
        {
          "value": 5,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 6,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 7,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 8,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 9,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 10,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        }
      ],
      "accepted_values": [
        1,
        2,
        3,
        4
      ],
      "accepted_min": 1,
      "accepted_max": 4
    },
    "stress": {
      "api_name": "stress",
      "attempts": [
        {
          "value": 1,
          "wrote_ok": true,
          "write_response_status": 200,
          "readback_value": 1,
          "roundtripped": true
        },
        {
          "value": 2,
          "wrote_ok": true,
          "write_response_status": 200,
          "readback_value": 2,
          "roundtripped": true
        },
        {
          "value": 3,
          "wrote_ok": true,
          "write_response_status": 200,
          "readback_value": 3,
          "roundtripped": true
        },
        {
          "value": 4,
          "wrote_ok": true,
          "write_response_status": 200,
          "readback_value": 4,
          "roundtripped": true
        },
        {
          "value": 5,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 6,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 7,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 8,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 9,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 10,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        }
      ],
      "accepted_values": [
        1,
        2,
        3,
        4
      ],
      "accepted_min": 1,
      "accepted_max": 4
    },
    "motivation": {
      "api_name": "motivation",
      "attempts": [
        {
          "value": 1,
          "wrote_ok": true,
          "write_response_status": 200,
          "readback_value": 1,
          "roundtripped": true
        },
        {
          "value": 2,
          "wrote_ok": true,
          "write_response_status": 200,
          "readback_value": 2,
          "roundtripped": true
        },
        {
          "value": 3,
          "wrote_ok": true,
          "write_response_status": 200,
          "readback_value": 3,
          "roundtripped": true
        },
        {
          "value": 4,
          "wrote_ok": true,
          "write_response_status": 200,
          "readback_value": 4,
          "roundtripped": true
        },
        {
          "value": 5,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 6,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 7,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 8,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 9,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 10,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        }
      ],
      "accepted_values": [
        1,
        2,
        3,
        4
      ],
      "accepted_min": 1,
      "accepted_max": 4
    },
    "mood": {
      "api_name": "mood",
      "attempts": [
        {
          "value": 1,
          "wrote_ok": true,
          "write_response_status": 200,
          "readback_value": 1,
          "roundtripped": true
        },
        {
          "value": 2,
          "wrote_ok": true,
          "write_response_status": 200,
          "readback_value": 2,
          "roundtripped": true
        },
        {
          "value": 3,
          "wrote_ok": true,
          "write_response_status": 200,
          "readback_value": 3,
          "roundtripped": true
        },
        {
          "value": 4,
          "wrote_ok": true,
          "write_response_status": 200,
          "readback_value": 4,
          "roundtripped": true
        },
        {
          "value": 5,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 6,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 7,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 8,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 9,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 10,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        }
      ],
      "accepted_values": [
        1,
        2,
        3,
        4
      ],
      "accepted_min": 1,
      "accepted_max": 4
    },
    "soreness": {
      "api_name": "soreness",
      "attempts": [
        {
          "value": 1,
          "wrote_ok": true,
          "write_response_status": 200,
          "readback_value": 1,
          "roundtripped": true
        },
        {
          "value": 2,
          "wrote_ok": true,
          "write_response_status": 200,
          "readback_value": 2,
          "roundtripped": true
        },
        {
          "value": 3,
          "wrote_ok": true,
          "write_response_status": 200,
          "readback_value": 3,
          "roundtripped": true
        },
        {
          "value": 4,
          "wrote_ok": true,
          "write_response_status": 200,
          "readback_value": 4,
          "roundtripped": true
        },
        {
          "value": 5,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 6,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 7,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 8,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 9,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 10,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        }
      ],
      "accepted_values": [
        1,
        2,
        3,
        4
      ],
      "accepted_min": 1,
      "accepted_max": 4
    },
    "sleep_quality": {
      "api_name": "sleepQuality",
      "attempts": [
        {
          "value": 1,
          "wrote_ok": true,
          "write_response_status": 200,
          "readback_value": 1,
          "roundtripped": true
        },
        {
          "value": 2,
          "wrote_ok": true,
          "write_response_status": 200,
          "readback_value": 2,
          "roundtripped": true
        },
        {
          "value": 3,
          "wrote_ok": true,
          "write_response_status": 200,
          "readback_value": 3,
          "roundtripped": true
        },
        {
          "value": 4,
          "wrote_ok": true,
          "write_response_status": 200,
          "readback_value": 4,
          "roundtripped": true
        },
        {
          "value": 5,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 6,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 7,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 8,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 9,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        },
        {
          "value": 10,
          "wrote_ok": false,
          "write_response_status": 422,
          "readback_value": null,
          "roundtripped": false
        }
      ],
      "accepted_values": [
        1,
        2,
        3,
        4
      ],
      "accepted_min": 1,
      "accepted_max": 4
    }
  },
  "WELLNESS_RANGES_LOCKED": {
    "fatigue": [
      1,
      4
    ],
    "stress": [
      1,
      4
    ],
    "motivation": [
      1,
      4
    ],
    "mood": [
      1,
      4
    ],
    "soreness": [
      1,
      4
    ],
    "sleep_quality": [
      1,
      4
    ]
  },
  "cleanup_response": {
    "id": "2099-01-01",
    "ctl": 2.9e-44,
    "atl": 4.2e-45,
    "rampRate": 0.0,
    "ctlLoad": 0.0,
    "atlLoad": 0.0,
    "sportInfo": [
      {
        "type": "Ride",
        "eftp": null,
        "wPrime": null,
        "pMax": null
      }
    ],
    "updated": "2026-04-25T09:42:02.882+00:00",
    "weight": 66.4,
    "restingHR": 51,
    "hrv": null,
    "hrvSDNN": null,
    "menstrualPhase": null,
    "menstrualPhasePredicted": null,
    "kcalConsumed": null,
    "sleepSecs": null,
    "sleepScore": null,
    "sleepQuality": null,
    "avgSleepingHR": null,
    "soreness": null,
    "fatigue": null,
    "stress": null,
    "mood": null,
    "motivation": null,
    "injury": null,
    "spO2": null,
    "systolic": null,
    "diastolic": null,
    "hydration": null,
    "hydrationVolume": null,
    "readiness": null,
    "baevskySI": null,
    "bloodGlucose": null,
    "lactate": null,
    "bodyFat": null,
    "abdomen": null,
    "vo2max": null,
    "comments": null,
    "steps": null,
    "respiration": null,
    "carbohydrates": null,
    "protein": null,
    "fatTotal": null,
    "locked": null,
    "tempWeight": true,
    "tempRestingHR": true
  }
}
```
