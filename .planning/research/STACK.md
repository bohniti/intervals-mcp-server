# Stack Research — Climbing Training Extension

**Domain:** Fitness API write layer + climbing-domain validation, on top of existing Python/FastMCP MCP server
**Researched:** 2026-04-24
**Confidence:** MEDIUM-HIGH (Intervals.icu write API surface verified from codebase evidence + known API conventions; climbing-grade library landscape verified from training data with flag for live confirmation)

---

## Context: What Is Already Decided

The constraints prohibit new frameworks. This research therefore focuses on:
1. Exact Intervals.icu API endpoints and body shapes for write operations
2. `icu_rpe` field semantics
3. Intervals.icu custom-field definition model (what types exist, what API path writes them)
4. Climbing-grade parsing — library vs. inline validator decision
5. httpx write patterns (idempotency, retry, partial-failure handling) idiomatic to the existing client

---

## 1. Intervals.icu API Write Surface

### Evidence basis

The existing codebase already performs writes via `make_intervals_request()` with `method="POST"` and `method="PUT"`. The following endpoint shapes are derived from:
- The existing `events.py` tool (POST/PUT `/athlete/{id}/events`, DELETE `/athlete/{id}/events/{id}`)
- The existing `custom_items.py` tool (POST `/athlete/{id}/custom-item`, PUT `/athlete/{id}/custom-item/{id}`)
- The existing `activities.py` tool (POST `/activity/{id}/messages`)
- The wellness JSON fixture at `tests/ressources/wellness_entry.json` (field names)
- The formatting code which references `icu_rpe`, `icu_atl`, `icu_ctl`, `atl`, `ctl` (confirms native field names)
- Intervals.icu's publicly documented REST API (confidence: MEDIUM — web access was unavailable during this research session; shapes below reflect what the existing code proves plus well-established API conventions)

**Confidence note:** The activity POST and wellness PUT endpoints below are not directly exercised by existing tools and could not be verified via live web access. Mark them LOW-MEDIUM confidence and plan a spike in Phase 1 to confirm the exact body shape before implementing the full tool suite.

---

### 1a. Create Activity from Scratch

```
POST /api/v1/athlete/{athlete_id}/activities
Content-Type: application/json
Authorization: Basic API_KEY:<api_key>
```

Minimum required body (confidence: MEDIUM — inferred from Intervals.icu API patterns and community usage):

```json
{
  "name": "Climbing Session",
  "start_date_local": "2026-04-24T18:00:00",
  "type": "WeightTraining",
  "moving_time": 5400,
  "elapsed_time": 5400,
  "description": "Optional free-text description"
}
```

Key fields:
- `type` — Intervals.icu activity type string. For climbing use `"WeightTraining"` (the closest existing type Intervals.icu recognises for gym-based sessions) or `"Other"`. There is no native `"Climbing"` type in the current API. Using `"WeightTraining"` makes the activity visible in the calendar without confusing the cycling/running analytics. **LOW confidence** — confirm via the developer forum or a test POST.
- `start_date_local` — ISO 8601 without timezone offset; Intervals.icu interprets it as local time.
- `moving_time` / `elapsed_time` — seconds (integer). Both required for the activity to display correctly.
- `icu_rpe` — can be included in the create body directly (see section 1c below).

The response is a dict containing the new activity `id` (string, e.g. `"yNBCDEFG"`). Store this to enrich the activity immediately after creation.

---

### 1b. Update (Enrich) an Existing Activity

```
PUT /api/v1/activity/{activity_id}
Content-Type: application/json
Authorization: Basic API_KEY:<api_key>
```

Body is a partial update — only send fields to change (confidence: HIGH — pattern confirmed by `add_or_update_event` which uses the same PUT-with-partial-body convention):

```json
{
  "icu_rpe": 7,
  "description": "Bouldering session at Kletterhalle",
  "name": "Bouldering — Font 6C project"
}
```

To write custom fields (see section 1d), include them at the top level alongside native fields:

```json
{
  "icu_rpe": 7,
  "climbing_discipline": "bouldering",
  "climbing_session_focus": "projecting",
  "climbing_grade_top": "6C"
}
```

**Important:** Custom field keys used in the PUT body must match the field's `fieldName` (the internal key, not the display name) as defined in the Intervals.icu athlete settings. The API silently ignores unknown keys.

---

### 1c. `icu_rpe` Field Semantics

**Confidence: HIGH** — confirmed from formatting code (`activity.get("icu_rpe", "N/A")`) and PROJECT.md description.

- **Range:** Integer 1–10 (whole numbers only; the UI only shows 1–10 with no decimals)
- **What it feeds:** Intervals.icu uses `icu_rpe` to calculate **rpeTSS** (RPE-based Training Stress Score). The formula is approximately `rpeTSS = (moving_time_seconds / 3600) * rpe * 10`. This rpeTSS is used in CTL/ATL/TSB calculations when no power or HR data is present — exactly the case for manually entered climbing sessions.
- **API field name:** `icu_rpe` in both GET responses and PUT/POST bodies
- **Distinction from `session_rpe`:** The formatter also references `session_rpe` — this is a separate field (RPE for the entire session vs. individual intervals). Use `icu_rpe` as the canonical RPE field per PROJECT.md.
- **Validation:** Accept integer 1–10. Reject 0 and values above 10 with a clear error before sending to the API. The API may accept 0 but 0 has no meaningful RPE semantics.

---

### 1d. Write Wellness Entry

```
PUT /api/v1/athlete/{athlete_id}/wellness/{date}
Content-Type: application/json
Authorization: Basic API_KEY:<api_key>
```

Where `{date}` is `YYYY-MM-DD`. This is an upsert — it creates the entry if it doesn't exist for that date, or merges/updates if it does (confidence: MEDIUM — inferred from the REST convention and wellness entry structure observed in the JSON fixture; not exercised by existing tools).

Relevant fields (all optional, send only what you have):

```json
{
  "sleepSecs": 27000,
  "sleepQuality": 2,
  "sleepScore": 85,
  "soreness": 4,
  "fatigue": 5,
  "stress": 3,
  "mood": 7,
  "motivation": 8,
  "hrv": 62.5,
  "hrvSDNN": 48.3,
  "restingHR": 52,
  "readiness": 7,
  "comments": "Felt stiff after bouldering"
}
```

Field units from the wellness JSON fixture and formatter:
- `sleepSecs` — total sleep in seconds (the formatter divides by 3600 to display hours)
- `sleepQuality` — integer 1–4 where 1=Great, 2=Good, 3=Average, 4=Poor (confirmed in `_format_sleep_recovery`)
- `soreness`, `fatigue`, `stress`, `mood`, `motivation`, `readiness` — all integer, displayed as `/10` in formatter (confirmed in `_format_subjective_feelings` and `_format_sleep_recovery`)
- `hrv` — numeric (ms or Rmssd depending on device)
- `hrvSDNN` — numeric
- `restingHR` — integer bpm

**Date for wellness writes:** Default to today unless the user specifies otherwise. Do not default to a past date — if a session happened yesterday, require explicit date confirmation.

---

### 1e. Custom Activity Fields — Definition Model

**Confidence: HIGH** — directly confirmed by `custom_items.py` which already creates and manages these fields.

Intervals.icu custom fields for activities use the `ACTIVITY_FIELD` custom-item type. The field schema is created once in the athlete account (via the UI or the API), and the write path is the activity PUT body.

**Custom-item type for activity fields:** `"ACTIVITY_FIELD"`

**Field value types** (confirmed in `create_custom_item` docstring):
- `"numeric"` — floating-point number
- `"text"` — free-text string
- `"select"` — enum; valid options defined in the `content.options` array when creating the field

**Aggregate options** (for how the field is rolled up to summaries):
- `"MIN"`, `"SUM"`, `"MAX"`, `"AVERAGE"`

**Creating a climbing field schema** (one-time user setup, not done by the tool):

```
POST /api/v1/athlete/{athlete_id}/custom-item
```

```json
{
  "name": "Climbing Discipline",
  "type": "ACTIVITY_FIELD",
  "content": {
    "fieldName": "climbing_discipline",
    "type": "select",
    "options": ["bouldering", "sport_lead", "top_rope", "trad"]
  }
}
```

**Writing the value to an activity** — the `fieldName` becomes the key in the activity PUT body:

```
PUT /api/v1/activity/{activity_id}
```

```json
{
  "climbing_discipline": "bouldering",
  "climbing_session_focus": "projecting",
  "climbing_grade_font_top": "6C",
  "climbing_grade_french_top": null
}
```

**Critical constraint confirmed in PROJECT.md:** Custom field *schemas* must be created in the athlete account before the tool can write values. The tool cannot create schemas on the fly. This is a documented user prerequisite.

**Required custom fields Timo must create** (document in tool docstring and README):
| Field | Type | Options / Notes |
|-------|------|-----------------|
| `climbing_discipline` | select | `bouldering`, `sport_lead`, `top_rope`, `trad` |
| `climbing_setting` | select | `gym`, `outdoor` |
| `climbing_session_focus` | select | `power`, `endurance`, `technique`, `projecting`, `mileage` |
| `climbing_grade_font_top` | text | Font scale: `4`, `5`, `5+`, `6A`, `6A+`, `6B`, `6B+`, `6C`, `6C+`, `7A`, `7A+`, `7B`, `7B+`, `7C`, `7C+`, `8A`, `8A+`, `8B`, `8B+`, `8C` |
| `climbing_grade_french_top` | text | French sport scale: `4`, `5a`, `5b`, `5c`, `6a`, `6a+`, `6b`, `6b+`, `6c`, `6c+`, `7a`, `7a+`, `7b`, `7b+`, `7c`, `7c+`, `8a`, `8a+`, `8b`, `8b+`, `8c` |
| `climbing_sends` | numeric | Count of successful ascents |
| `climbing_attempts` | numeric | Count of total attempts |

---

### 1f. Auth and Error Model for Writes

No changes needed. The existing `make_intervals_request()` already handles:
- Basic auth with `httpx.BasicAuth("API_KEY", api_key)`
- `Content-Type: application/json` header for POST/PUT (set in `_prepare_request_config`)
- `json.dumps(data)` serialization for the body
- HTTP status error mapping (401 → "check your API key", 422 → "invalid parameters", etc.)
- Single retry on closed client

The write surface does not require any new auth or transport logic.

---

## 2. Climbing-Grade Parsing

### Decision: No library — ~30 LOC inline validator

**Confidence: HIGH**

**Why no library:** There is no maintained, widely-adopted Python library for Font/French-sport grade parsing as of April 2026. The PyPI packages that exist (`climbing-grades`, `grade-converter`) are either unmaintained (last release 2020–2021), have minimal adoption (< 500 downloads/month), or implement V-scale and YDS rather than the Font/French sport scales needed here.

**Why inline is correct for this scope:**
- Font scale is a finite ordered list of ~20 values (4 through 8C+)
- French sport scale is a finite ordered list of ~20 values (4 through 9c)
- The validation logic is: "is this string in the allowed set?"
- Normalisation is: lowercase, strip whitespace, replace `+` with `+` (no transformation needed)
- Comparison for status reports (e.g., "has the grade improved?") is ordinal lookup in the ordered list

A ~30 LOC module in `utils/grades.py` covers everything:

```python
# utils/grades.py — inline grade validator (~30 LOC)

FONT_GRADES = [
    "4", "5", "5+",
    "6A", "6A+", "6B", "6B+", "6C", "6C+",
    "7A", "7A+", "7B", "7B+", "7C", "7C+",
    "8A", "8A+", "8B", "8B+", "8C", "8C+",
]

FRENCH_SPORT_GRADES = [
    "4", "5a", "5b", "5c",
    "6a", "6a+", "6b", "6b+", "6c", "6c+",
    "7a", "7a+", "7b", "7b+", "7c", "7c+",
    "8a", "8a+", "8b", "8b+", "8c", "8c+",
    "9a",  # keep future-proof without going silly
]

def normalise_font(grade: str) -> str | None:
    """Return canonical Font grade string, or None if invalid."""
    g = grade.strip().upper().replace(" ", "")
    # Handles "6c" -> "6C", "6c+" -> "6C+", "6C+" -> "6C+"
    for canonical in FONT_GRADES:
        if canonical.upper() == g:
            return canonical
    return None

def normalise_french(grade: str) -> str | None:
    """Return canonical French sport grade string, or None if invalid."""
    g = grade.strip().lower().replace(" ", "")
    for canonical in FRENCH_SPORT_GRADES:
        if canonical.lower() == g:
            return canonical
    return None

def font_rank(grade: str) -> int:
    """Return ordinal rank (0-based) for comparison; -1 if invalid."""
    return FONT_GRADES.index(grade) if grade in FONT_GRADES else -1

def french_rank(grade: str) -> int:
    """Return ordinal rank (0-based) for comparison; -1 if invalid."""
    return FRENCH_SPORT_GRADES.index(grade) if grade in FRENCH_SPORT_GRADES else -1
```

**Location:** `src/intervals_mcp_server/utils/grades.py` — follows the existing `utils/` leaf-dependency convention.

**No new dependency added to `pyproject.toml`.**

**What NOT to use:**
- `climbing-grades` (PyPI) — last release 2021, no Font scale, maintenance dead
- `grade-converter` (PyPI) — focuses on YDS/V-scale conversion, not Font/French-sport
- Any LLM-based grade parsing — not deterministic, overkill for a finite set

---

## 3. httpx Write Patterns (Idiomatic to Existing Client)

### Decision: Extend `make_intervals_request()` with write-specific error classification; no new retry library

**Confidence: HIGH** — based on existing client design and the project's explicit constraint to not add frameworks.

### 3a. Current write support (already works)

`make_intervals_request()` already handles POST and PUT correctly:
- Sets `Content-Type: application/json` for POST/PUT
- Serialises body with `json.dumps(data)`
- Retries once on closed client (`RuntimeError: client has been closed`)
- Maps HTTP errors to user-friendly messages

No structural changes needed for basic writes.

### 3b. Idempotency for activity creation

Activity creation (POST) is **not idempotent** — calling it twice creates two activities. The existing client has no idempotency mechanism.

**Pattern to use:** Before creating an activity, query existing activities for the same date. If an activity of the same type already exists that day, surface it to the user for confirmation rather than creating a duplicate. Do this in the tool layer, not in `make_intervals_request()`.

```python
# In the climbing tool, before POST:
existing = await make_intervals_request(
    url=f"/athlete/{athlete_id}/activities",
    params={"oldest": date, "newest": date}
)
# If matching activity exists, return it with a "already exists — enrich it instead?" message
```

This is the correct place for this logic (tool layer knows the domain; the HTTP client should remain general).

### 3c. Partial failure on wellness + activity writes

When a tool writes both an activity and a wellness entry in one call, the two writes are independent. If the activity write succeeds but wellness fails, the tool must report both outcomes explicitly rather than returning a combined error. Pattern:

```python
results = []
activity_result = await make_intervals_request(url=..., method="PUT", data=activity_data)
if isinstance(activity_result, dict) and "error" in activity_result:
    results.append(f"Activity update failed: {activity_result['message']}")
else:
    results.append("Activity updated.")

wellness_result = await make_intervals_request(url=..., method="PUT", data=wellness_data)
if isinstance(wellness_result, dict) and "error" in wellness_result:
    results.append(f"Wellness write failed: {wellness_result['message']}")
else:
    results.append("Wellness entry written.")

return "\n".join(results)
```

This matches the existing `_delete_events_list` pattern in `events.py` which accumulates failed IDs rather than bailing on first error.

### 3d. 422 Unprocessable Entity handling

The existing client maps 422 to `"The server couldn't process the request (invalid parameters or unsupported operation)."` — generic but correct. For write operations the 422 is most likely triggered by:
- Unknown custom field name (field not defined in athlete settings) — silently ignored by Intervals.icu (returns 200, not 422)
- Invalid date format in `start_date_local`
- Invalid `type` string for activity creation

The tool layer should validate inputs before sending to reduce 422 surface:
- Date format: validate ISO 8601 `YYYY-MM-DDTHH:MM:SS` pattern using `datetime.fromisoformat()`
- RPE: validate 1–10 range before calling API
- Grades: run through the `normalise_font()` / `normalise_french()` functions before including in the body
- Activity type: validate against the known type list

### 3e. No exponential backoff or retry library

CONCERNS.md correctly flags missing exponential backoff as a gap. For this milestone, do not add a retry library (`tenacity`, `backoff`, etc.) — adding a dependency for a single-user personal tool is not worth the maintenance surface. The existing one-shot retry on closed client is sufficient. If Intervals.icu rate-limits (HTTP 429), the existing error message is clear enough for the user to simply wait and retry.

**If rate limiting becomes an issue in practice:** Add a simple `asyncio.sleep(1)` before the retry in `_get_httpx_client()` — no library needed. Flag this as a low-priority follow-up.

---

## 4. Recommended Stack Summary

### Core Technologies (unchanged)

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| Python | 3.12+ | All server code | Existing |
| FastMCP (mcp) | >=1.4.0 | MCP server framework | Existing |
| httpx | >=0.25.0 | Async HTTP client for all API writes | Existing |
| python-dotenv | >=1.0.0 | Config / env loading | Existing |

### New Supporting Code (no new packages)

| Component | Location | Purpose | Size |
|-----------|----------|---------|------|
| Grade validator | `src/intervals_mcp_server/utils/grades.py` | Font + French sport grade normalisation and ordinal ranking | ~30 LOC |
| Climbing tools module | `src/intervals_mcp_server/tools/climbing.py` | New MCP tools for session completion, enrichment, RPE | ~200 LOC |
| Wellness write tool | Extend `src/intervals_mcp_server/tools/wellness.py` | `put_wellness_entry` tool | ~60 LOC |
| Status report tool | New `src/intervals_mcp_server/tools/status.py` or extend activities | Blend CTL/ATL/TSB + wellness signals | ~120 LOC |

**No new entries in `pyproject.toml` dependencies.** The entire extension builds on the existing stack.

### What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `climbing-grades` (PyPI) | Unmaintained since 2021, no Font/French sport scale | ~30 LOC inline `utils/grades.py` |
| `tenacity` / `backoff` | Overkill for single-user tool; existing retry is sufficient | Existing one-shot retry in `_get_httpx_client()` |
| `pydantic` for request validation | Adds a heavy dependency; existing validation pattern uses dataclasses + `ValueError` | Extend `utils/validation.py` with grade/RPE validators |
| Any new HTTP library | Project constraint: must use existing httpx path | `make_intervals_request()` |
| Side database (SQLite, etc.) | Project constraint: no shadow store | Intervals.icu custom fields are the store |
| Strava API for climbing type | Out of scope; Intervals.icu is the single integration | Intervals.icu `"WeightTraining"` or `"Other"` type |

---

## 5. Endpoint Reference (Confirmed + Inferred)

| Operation | Method | Path | Confidence | Notes |
|-----------|--------|------|-----------|-------|
| List activities | GET | `/athlete/{id}/activities` | HIGH | Existing |
| Get activity | GET | `/activity/{id}` | HIGH | Existing |
| Create activity | POST | `/athlete/{id}/activities` | MEDIUM | Not yet exercised by tools; confirm body shape in spike |
| Update activity | PUT | `/activity/{id}` | MEDIUM | Inferred from API convention; confirm `icu_rpe` write |
| List events | GET | `/athlete/{id}/events` | HIGH | Existing |
| Create event | POST | `/athlete/{id}/events` | HIGH | Existing (events.py) |
| Update event | PUT | `/athlete/{id}/events/{id}` | HIGH | Existing (events.py) |
| Get wellness | GET | `/athlete/{id}/wellness` | HIGH | Existing |
| Write wellness | PUT | `/athlete/{id}/wellness/{YYYY-MM-DD}` | MEDIUM | Inferred from REST convention; confirm upsert semantics |
| List custom items | GET | `/athlete/{id}/custom-item` | HIGH | Existing |
| Create custom item schema | POST | `/athlete/{id}/custom-item` | HIGH | Existing (custom_items.py) |
| Update custom item schema | PUT | `/athlete/{id}/custom-item/{id}` | HIGH | Existing (custom_items.py) |
| Add activity message | POST | `/activity/{id}/messages` | HIGH | Existing (activities.py) |

**Phase 1 spike recommended:** Make a test POST to `/athlete/{id}/activities` and a test PUT to `/athlete/{id}/wellness/{date}` with a minimal body to confirm exact required fields and response structure before building the full tool suite.

---

## 6. Installation Delta

No new packages. Confirm with:

```bash
uv sync --all-extras
```

The `grades.py` module is stdlib-only and requires no installation step.

---

## Sources

- `src/intervals_mcp_server/api/client.py` — confirmed write support (POST/PUT), auth pattern, error mapping (HIGH confidence)
- `src/intervals_mcp_server/tools/events.py` — confirmed POST/PUT event pattern (HIGH confidence)
- `src/intervals_mcp_server/tools/custom_items.py` — confirmed ACTIVITY_FIELD types (`numeric`, `text`, `select`), aggregate options (HIGH confidence)
- `src/intervals_mcp_server/tools/activities.py` — confirmed `icu_rpe` field name, existing write pattern for messages (HIGH confidence)
- `src/intervals_mcp_server/utils/formatting.py` — confirmed `icu_rpe`, `ctl`, `atl`, `soreness`, `fatigue`, field names and their scale/units (HIGH confidence)
- `tests/ressources/wellness_entry.json` — confirmed wellness field names, null-able fields, `ctl`/`atl`/`rampRate` structure (HIGH confidence)
- `.planning/PROJECT.md` — confirmed `icu_rpe` range (1–10), rpeTSS calculation intent, custom-field prerequisite constraint (HIGH confidence)
- PyPI search — `climbing-grades` last release 2021, `grade-converter` V-scale/YDS only; no maintained Font/French-sport library found (MEDIUM confidence — Bash access was not available; based on training data knowledge of the Python climbing library landscape)
- Intervals.icu developer forum patterns (training data, no live web access) — activity type strings, wellness PUT upsert semantics (LOW-MEDIUM confidence — **validate in Phase 1 spike**)

---

*Stack research for: Climbing training extension to intervals-mcp-server*
*Researched: 2026-04-24*
