# Phase 2: Wellness Write and Activity Enrichment - Research

**Researched:** 2026-04-25
**Domain:** Intervals.icu write-path tooling — wellness PUT (subjective + objective scales) and activity enrichment PUT (custom fields + native `icu_rpe`) over an existing FastMCP / httpx async stack
**Confidence:** HIGH for the existing-codebase patterns (Phase 1 left a clean trail), MEDIUM for the open API contracts the second probe must close (custom-field PUT body shape, wellness subjective-field scales, `icu_rpe` write co-location)

## Summary

Phase 2 ships two write tools on top of the Phase 1 utility layer: `write_wellness_entry` (in `tools/wellness.py`) and `enrich_activity_climbing` (in `tools/climbing.py`). Both must route through the existing `make_intervals_request()` HTTP boundary, follow MCP statelessness (single-shot, all params on the call site), readback-verify every supplied field, and never silently overwrite prior data. CONTEXT.md locks 25 decisions across API resolution, parameter shape, validation, readback, and module placement — research scope is therefore narrow and prescriptive: confirm what the Phase 1 spike already established, surface what the Phase 2 second probe must close, and document the patterns the planner copies into plans.

The phase's center of gravity is **Plan 02-01**, the targeted second probe (D-01..D-05). The Phase 1 spike confirmed the wellness PUT body shape works for `sleepSecs` + `soreness` and confirmed upsert semantics, but `fatigue: 5` returned 422 (D-01b open) and the activity custom-field PUT returned 422 with all variations the Phase 1 spike tried (D-01a open). The probe must resolve both before any tool implementation, with a hard-stop fallback (D-05): if the activity custom-field PUT cannot be made to work via any reasonable body shape, **stop Phase 2 and re-discuss** rather than ship a half-broken `enrich_activity_climbing`. This is load-bearing — the Key Decision "structured climbing data → Intervals.icu custom fields" depends on it.

**Primary recommendation:** Plan 02-01 as a strictly-bounded second probe (one new SPIKE-FINDINGS file), Plans 02-02/02-03 (wellness side, depends only on D-01b results) parallelizable, Plans 02-04/02-05 (enrichment side) sequenced after probe review. Every write-tool plan MUST include readback verification as a verification step, NOT as a polish item.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Wellness PUT body construction (drop-None, name translation, unit conversion) | Utility (`utils/wellness.py`) | — | Pure transformation; reusable; testable in isolation |
| Wellness range validation | Utility (`utils/wellness.py`) | Tool (`tools/wellness.py`) | Range table is the single source of truth; tool layer raises ValueError before any HTTP call |
| Wellness PUT + readback orchestration | Tool (`tools/wellness.py`) | API (`api/client.py`) | Single tool call drives PUT then GET readback; HTTP itself owned by `make_intervals_request()` |
| Activity-enrichment validation (grade/discipline coupling, at-least-one-supplied, conflict detection) | Tool (`tools/climbing.py`) | Utility (`utils/grades.py`, `utils/climbing.py`) | Validation runs in tool before HTTP; utilities provide regex + enums |
| Custom-field write to activity (the open D-01a) | API (`make_intervals_request()`) | Tool (`tools/climbing.py`) | All HTTP through the single boundary; tool layer constructs body and verifies readback |
| `icu_rpe` write (native field) | API (single PUT or split per probe outcome) | Tool (`tools/climbing.py`) | Co-located with custom fields by default (D-16); tool decides single-PUT vs split based on probe |
| Re-enrichment guard + audit trail (override flag + add_activity_message) | Tool (`tools/climbing.py`) | API (`make_intervals_request()`) | Override gate is tool-layer logic; audit trail is a POST to `/activity/{id}/messages` (existing `add_activity_message` pattern) |
| Custom-field setup pre-write guard | Tool (`tools/climbing.py`) | Tool (`tools/climbing.py`) | `_verify_custom_fields_setup_impl` (Phase 1) consumed by `enrich_activity_climbing` |
| Spike-script live API probe | Standalone script (`scripts/`) | API (`make_intervals_request()`) | Same auth/retry path as real tools; not a pytest test (writes live data) |
| Phase 2 smoke-test (D-25) | Standalone script (`scripts/`) | API (`make_intervals_request()`) | Live write, far-future date, DELETE cleanup; not in CI |
| Test layer (mocked PUT/GET) | Test (`tests/test_wellness_write.py`, `tests/test_climbing_write.py`) | — | `monkeypatch` `make_intervals_request`; `asyncio.run`; no live HTTP |

## User Constraints (from CONTEXT.md)

### Locked Decisions

**API uncertainty resolution (open from Phase 1 spike):**
- **D-01:** Plan 02-01 is a targeted second-probe script that resolves all three open unknowns before any tool implementation begins:
  - **(a) Activity custom-field PUT shape** — try variations of the failing `PUT /activity/{id}` body (top-level keys, nested envelopes, alternate URLs like `PUT /athlete/{id}/activity/{id}` and `POST /activity/{id}`) until a body roundtrips through readback.
  - **(b) Wellness subjective-field valid scales** — probe `fatigue`, `stress`, `motivation`, `mood`, `soreness`, `sleep_quality` with values across 1-4 and 1-10; record which range each accepts.
  - **(c) `icu_rpe` write path** — try `icu_rpe: 6` in the same PUT as custom fields; if the call fails, isolate `icu_rpe` to its own PUT to confirm write semantics.
- **D-02:** Findings land in `.planning/phases/02-wellness-write-and-activity-enrichment/02-SPIKE-FINDINGS.md` (new file). Phase 1's spike findings stay closed; Phase 2 owns its own discovery artifacts.
- **D-03:** The probe script uses `make_intervals_request()` against `SPIKE_DATE = "2099-01-01"`, follows the Phase 1 spike script structure (`scripts/spike_write_endpoints_phase2.py` or extend `scripts/spike_write_endpoints.py` — planner picks; either is acceptable as long as the new findings file is the canonical reference).
- **D-04:** Plan 02-04 (`enrich_activity_climbing`) cannot start until D-01's findings are reviewed. Plan 02-02 / 02-03 (wellness side) can start in parallel as soon as D-01's wellness scale results land — they don't depend on the activity-write probe.
- **D-05:** **Hard-stop fallback.** If the second probe still cannot land custom fields on an activity via any reasonable body shape, **stop Phase 2 and re-discuss**. Do not ship a half-broken `enrich_activity_climbing`. The Key Decision "Structured climbing data → Intervals.icu custom fields" in PROJECT.md may need revisiting (description-as-structured-text fallback or scope-cut to RPE-only) — that decision is explicitly out of scope for this phase to make unilaterally.

**`write_wellness_entry` API surface:**
- **D-06:** Explicit named params, no escape hatch. One Optional param per supported field: `date` (required, `YYYY-MM-DD`), `sleep_hours`, `sleep_quality`, `soreness`, `fatigue`, `motivation`, `stress`, `mood`, `hrv`, `resting_hr`, plus `athlete_id` / `api_key`.
- **D-07:** Hard scale validation, ranges locked from D-01(b) probe results. `WELLNESS_RANGES` constant in `utils/wellness.py` maps each numeric param to its `(min, max)` tuple. Out-of-range raises `ValueError`.
- **D-08:** User-friendly units in, API units inside. `sleep_hours: float` → `sleepSecs = int(round(sleep_hours * 3600))`. HRV (ms) and `resting_hr` (bpm) pass through unchanged.
- **D-09:** Upsert via drop-None. `_PARAM_TO_API_FIELD` dict in `tools/wellness.py` maps public param → API field name.
- **D-10:** Reject empty calls. If only `date` is supplied, return error.
- **D-11:** Readback after PUT. GET `/athlete/{id}/wellness?oldest={date}&newest={date}`; verify each supplied field roundtrips.

**`enrich_activity_climbing` API surface:**
- **D-12:** Parameter contract — `activity_id` required, climbing fields all optional. Signature exactly as specified in CONTEXT.md (10 climbing/control params + athlete_id/api_key). At-least-one-supplied check; if any of `top_grade_sent`/`top_grade_attempted`, `discipline` is also required.
- **D-13:** Discipline-aware grade validation runs before any API call via `validate_grade(grade, discipline)`.
- **D-14:** Re-enrichment: default-deny + explicit `override=True`. GET activity first; conflict detection on supplied fields including `icu_rpe`. On override=True, proceed with write AND immediately call `add_activity_message` recording the override and prior values.
- **D-15:** Readback verifies only supplied fields. After PUT, GET `/activity/{id}` and confirm exact values. On missing/different values, return clear error including `_README_POINTER` when custom fields are involved.
- **D-16:** `icu_rpe` write co-located with custom fields, contingent on probe. If single-PUT works (D-01c), do that. If `icu_rpe` requires separate endpoint, fall back to two writes in fixed sequence (RPE first, then custom fields). On partial failure, return explicit error naming what landed.

**Module placement & guard pattern:**
- **D-17:** `write_wellness_entry` lives in `tools/wellness.py`.
- **D-18:** `enrich_activity_climbing` lives in `tools/climbing.py`.
- **D-19:** New `utils/wellness.py` module — `WELLNESS_RANGES`, `sleep_hours_to_secs`, `build_wellness_put_body(params: dict) -> dict`.
- **D-20:** Verify-fields guard fires conditionally on `enrich_activity_climbing`. Only when any of the 7 climbing custom-field params is supplied. Skip for RPE-only writes.
- **D-21:** No verify-fields guard on `write_wellness_entry`. Wellness fields are native.

**Cross-cutting / Pitfall guards:**
- **D-22:** No `_`-prefix imports from sibling tool modules.
- **D-23:** Tests in `tests/test_wellness_write.py` and `tests/test_climbing_write.py`. `pytest --collect-only` must discover them.
- **D-24:** No regression to existing tools. `format_climbing_activity` extended (additive only).
- **D-25:** Smoke-test gating. Standalone script, not pytest. Writes to far-future date, uses DELETE for cleanup.

### Claude's Discretion

- Exact wellness API field-name mapping (`mood` vs `feel`, etc.) — confirm from Phase 1 spike's wellness response and lock in `_PARAM_TO_API_FIELD`.
- Whether the second probe extends `scripts/spike_write_endpoints.py` or creates `scripts/spike_write_endpoints_phase2.py` — planner picks.
- Exact mechanics of `add_activity_message` for override audit trail (call format, message text template).
- Order of arguments in `enrich_activity_climbing` after `activity_id` — rough grouping (discipline → grade-related → counts → rpe → override → ids) is fine.
- Pre-existing test file `tests/test_climbing.py` may grow new sections OR a new file `test_climbing_write.py` may be created (planner's call based on file size after D-23 lands).
- Whether to wire any user-friendly `feel` parameter (1-5 emoji-style) — currently not in scope; defer unless probe surfaces an Intervals.icu equivalent worth supporting.

### Deferred Ideas (OUT OF SCOPE)

- Explicit wellness clear-field mechanism (passing `clear_fields=[...]` to send `null`).
- `extra_fields` escape hatch for wellness writes.
- Improving the verify-fields readback heuristic (false-positive on never-populated fields).
- Auto-generating the docstring or wellness range table from a single source.
- Status-tool-side data-quality flag for missing wellness fields (Phase 4).
- Generic non-climbing manual-activity creation tool (`write_activity`) — v2.
- Finger / skin condition wellness field — v2.
- Dedicated `set_activity_rpe` tool — rejected; `icu_rpe` rides inside `enrich_activity_climbing`.

## Project Constraints (from CLAUDE.md)

| Constraint | How research honors it |
|------------|------------------------|
| All Intervals.icu HTTP through `make_intervals_request()` | Both write tools and the spike call `make_intervals_request()`; no direct httpx [VERIFIED: codebase grep — only `api/client.py` imports httpx for tool layer] |
| MCP statelessness — no hidden conversational state | Both tools accept all fields as params on a single call (D-06, D-12); no module-level mutable state between calls |
| No local shadow data store | Readback is GET-then-compare against Intervals.icu; no caching, no SQLite |
| Custom-field schemas must be user-defined first | `enrich_activity_climbing` runs `_verify_custom_fields_setup_impl` before PUT (D-20); enriched error message points to README setup section |
| Grade systems: Font (bouldering) + French sport (routes) | `validate_grade(grade, discipline)` called before any API call (D-13); existing test matrix in `tests/test_grades.py` |
| Custom-field writes must be readback-verified | Mandatory readback after PUT for both tools (D-11, D-15); `_README_POINTER` reused in error messages for custom-field misses |
| uv / pytest / ruff / mypy tooling | All test patterns use `pytest`, `monkeypatch`, `asyncio.run`; type hints required; line length 100; ruff-formatted |
| Brownfield — honor `.planning/codebase/CONVENTIONS.md` | Google-style docstrings, snake_case, `# pylint: disable=too-many-arguments` for many-arg tools, error dicts → user-facing strings |
| New climbing tools go in `tools/climbing.py` | `enrich_activity_climbing` joins this module (D-18); `write_wellness_entry` in `tools/wellness.py` (D-17) |

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WELL-01 | User can log wellness entry for a date with subjective metrics (sleep hours, sleep quality, soreness, fatigue, motivation, stress) | `write_wellness_entry` D-06 covers all 6 subjective params; D-07 hard-validates ranges per D-01(b) probe; D-09 drop-None upsert |
| WELL-02 | User can log objective wellness metrics (HRV, resting HR) in same tool call | Same tool surface — `hrv` and `resting_hr` params on `write_wellness_entry`; D-08 confirms HRV (ms) and RHR (bpm) pass through unchanged |
| WELL-03 | Wellness writes use upsert semantics — fields not supplied don't clobber existing values | D-09 drop-None body builder — only supplied (non-None) fields appear in PUT; Phase 1 spike already CONFIRMED upsert semantics for `sleepSecs` + `soreness` with separate writes (`upsert_semantics_confirmed: true` in 01-SPIKE-FINDINGS.md) |
| CLIMB-03 | User can enrich existing activity by ID — adds climbing metadata + RPE | `enrich_activity_climbing(activity_id, ...)` D-12 signature; D-15 readback confirms write |
| CLIMB-04 | All climbing completion tools accept discipline (bouldering / sport_lead / top_rope / trad, gym vs outdoor) | `discipline` and `indoor` params on `enrich_activity_climbing`; backed by `Discipline` StrEnum + `indoor: bool` per Phase 1 D-07 |
| CLIMB-05 | All climbing completion tools accept volume & grades (sends, attempts, Font/French scales) | `top_grade_sent`, `top_grade_attempted`, `sends`, `attempts` params; D-13 validates against discipline |
| CLIMB-06 | All climbing completion tools accept session focus | `session_focus` param backed by `SessionFocus` StrEnum from Phase 1 D-08 |
| CLIMB-07 | All climbing completion tools accept RPE (1-10) and write to native `icu_rpe` field | `rpe` param on `enrich_activity_climbing` writes to `icu_rpe`; range 1-10 validated; D-16 covers single-PUT vs split-PUT path |
| CLIMB-10 | Custom-field writes are readback-verified — clear error if schema missing | D-15 readback verification + `_verify_custom_fields_setup_impl` pre-write guard (D-20) + `_README_POINTER` in error messages |

## Standard Stack

### Core (no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12+ | Runtime | Already locked in `pyproject.toml` `requires-python = ">=3.12"` [VERIFIED: codebase] |
| `mcp[cli]` | >=1.4.0 | FastMCP server / `@mcp.tool()` decorator | Existing dependency; tools register via `from intervals_mcp_server.mcp_instance import mcp` then `@mcp.tool()` [VERIFIED: codebase grep] |
| `httpx` | >=0.25.0 | Async HTTP client | Wrapped by `make_intervals_request()`; do not import directly in new code [VERIFIED: codebase] |
| `python-dotenv` | >=1.0.0 | Config loading | Existing; `Config` singleton in `config.py` already loads `.env` [VERIFIED: codebase] |

### Supporting (existing utilities — Phase 2 imports, doesn't extend)

| Module | Purpose | Phase 2 Use |
|--------|---------|-------------|
| `utils/grades.py` | `validate_grade(grade, discipline)` | Called by `enrich_activity_climbing` before any HTTP (D-13) |
| `utils/climbing.py` | `Discipline`, `SessionFocus`, `CUSTOM_FIELD_KEYS`, `FieldSpec` | Read-only in Phase 2 (per D-19) — Phase 2 does NOT modify |
| `utils/validation.py` | `resolve_athlete_id`, `validate_date` | Both new tools call `resolve_athlete_id(athlete_id, config.athlete_id)` |
| `utils/formatting.py` | `format_climbing_activity` | Extended (additive only) to render readback after enrichment per D-24 |
| `tools/climbing.py` (Phase 1) | `_verify_custom_fields_setup_impl`, `_README_POINTER` | Internal helper consumed by `enrich_activity_climbing` (D-20); pointer reused in error messages (D-15) |
| `tools/activities.py` (existing) | `add_activity_message(activity_id, content)` | Called by `enrich_activity_climbing` after override write to leave audit trail (D-14) |
| `api/client.py` | `make_intervals_request(url, api_key, params, method, data)` | Single HTTP boundary for all PUT/GET/POST/DELETE in Phase 2 |

### New code Phase 2 introduces

| File | Purpose | Why new |
|------|---------|---------|
| `src/intervals_mcp_server/utils/wellness.py` | `WELLNESS_RANGES`, `sleep_hours_to_secs`, `build_wellness_put_body` | Mirrors `utils/grades.py` shape; D-19 keeps `utils/climbing.py` climbing-only |
| `tests/test_wellness_write.py` | Unit tests for the wellness write tool surface | D-23; new file (existing `test_server.py` covers the read tool only) |
| `tests/test_climbing_write.py` (or appended to `tests/test_climbing.py`) | Unit tests for `enrich_activity_climbing` | D-23; planner's call (Claude's Discretion) |
| `scripts/spike_write_endpoints_phase2.py` (or extension to `scripts/spike_write_endpoints.py`) | Plan 02-01 second probe | D-03; planner picks shape |
| `.planning/phases/02-wellness-write-and-activity-enrichment/02-SPIKE-FINDINGS.md` | Probe results, canonical reference for Plans 02-02 onwards | D-02 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Drop-None body builder | Send all fields with `null` for unsupplied | Intervals.icu treats `null` as "clear this field" [CITED: research/PITFALLS.md Integration Gotchas table] — clobbers existing values, breaks WELL-03. Drop-None is the only correct option. |
| Single-tool single-PUT for `enrich_activity_climbing` | Two-tool split (`enrich_activity` + `set_activity_rpe`) | Rejected per CONTEXT.md Deferred — single tool, all fields per "Climbing fields collected as optional tool parameters" Key Decision (PROJECT.md). |
| Override flag (default-deny re-enrichment) | Always-overwrite | Pitfall #10 — silent history mutation. Default-deny + explicit `override=True` + `add_activity_message` audit trail is the only safe path. |
| Top-level keys for custom-field PUT | Nested `customFields: {...}` envelope | Phase 1 spike confirmed top-level `{"discipline": "bouldering", "icu_rpe": 6}` returned 422 [VERIFIED: 01-SPIKE-FINDINGS.md `custom_field_write_response`]. The Phase 2 second probe must enumerate body shapes — top-level may yet work with different keys/values, or a different shape may be required. |

**Installation:** No new packages. The tooling is already complete:

```bash
uv sync --all-extras  # already done; no new dependencies in Phase 2
```

**Version verification:** All dependencies locked in `uv.lock` from Phase 0/1. No version probes needed for Phase 2 — versions are already in production [VERIFIED: codebase grep of pyproject.toml].

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  LLM (Claude)                                                   │
│  Conversationally gathers fields per docstring → single call    │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼  @mcp.tool() entry
┌─────────────────────────────────────────────────────────────────┐
│  Tool layer (tools/wellness.py, tools/climbing.py)              │
│  ┌─────────────────────┐    ┌────────────────────────────────┐  │
│  │ write_wellness_entry│    │ enrich_activity_climbing       │  │
│  │ ───────────────────│    │ ──────────────────────────────│  │
│  │ 1. resolve_athlete │    │ 1. resolve_athlete             │  │
│  │ 2. range validate │    │ 2. at-least-one + grade check  │  │
│  │ 3. reject empty   │    │ 3. verify_custom_fields (cond.)│  │
│  │ 4. build PUT body │    │ 4. GET activity (conflict scan)│  │
│  │ 5. PUT wellness   │    │ 5. PUT activity (cf + icu_rpe) │  │
│  │ 6. GET readback   │    │ 6. GET readback (verify exact) │  │
│  │ 7. format result  │    │ 7. add_activity_message (over.)│  │
│  └─────────────────────┘    └────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Utility layer (leaf modules — no tool/api imports)             │
│  ┌────────────────┐ ┌────────────────┐ ┌─────────────────────┐  │
│  │ utils/wellness │ │ utils/grades   │ │ utils/climbing      │  │
│  │ ─────────────│ │ ─────────────│ │ ──────────────────│  │
│  │ WELLNESS_     │ │ FONT_RE,      │ │ Discipline,         │  │
│  │   RANGES      │ │ FRENCH_SPORT_RE│ │ SessionFocus,       │  │
│  │ build_put_body│ │ validate_grade │ │ CUSTOM_FIELD_KEYS   │  │
│  │ sleep_hours_  │ │                │ │ (read-only Phase 2) │  │
│  │   to_secs     │ │                │ │                     │  │
│  │ (NEW PHASE 2) │ │ (Phase 1)      │ │ (Phase 1)           │  │
│  └────────────────┘ └────────────────┘ └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼  every HTTP call
┌─────────────────────────────────────────────────────────────────┐
│  api/client.py — make_intervals_request(url, api_key,           │
│                  params, method, data)                          │
│  Single boundary: auth, retry on closed client, error mapping   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
                Intervals.icu REST API
```

### Recommended Project Structure (Phase 2 deltas only)

```
src/intervals_mcp_server/
├── tools/
│   ├── wellness.py        # ADD write_wellness_entry (existing get_wellness_data unchanged)
│   └── climbing.py        # ADD enrich_activity_climbing (existing verify_custom_fields_setup unchanged)
└── utils/
    ├── wellness.py        # NEW — WELLNESS_RANGES, build_wellness_put_body, sleep_hours_to_secs
    └── formatting.py      # EXTEND format_climbing_activity additively (D-24)

scripts/
└── spike_write_endpoints_phase2.py  # NEW — second probe (or extension to spike_write_endpoints.py per D-03)

tests/
├── test_wellness_write.py     # NEW — D-23
└── test_climbing_write.py     # NEW (or appended to test_climbing.py per Discretion)

.planning/phases/02-wellness-write-and-activity-enrichment/
└── 02-SPIKE-FINDINGS.md       # NEW — D-02, written by Plan 02-01
```

### Pattern 1: Many-arg async @mcp.tool() with explicit Optional params

**What:** A tool accepting one optional param per supported field. The docstring is the LLM's instruction sheet.

**When to use:** Whenever an LLM needs to gather many independent fields conversationally — Pitfall #5 (MCP statelessness) and Pitfall #6 (terse docstrings) both demand this shape.

**Exemplar in codebase:** `get_activities` in `tools/activities.py` lines 103-122. Note the `# pylint: disable=too-many-arguments,too-many-return-statements,too-many-branches,too-many-positional-arguments` comment immediately after the decorator, the return type `-> str`, the use of `resolve_athlete_id` and `resolve_date_params`.

**Template for write tools:**

```python
# Source: pattern abstracted from tools/activities.py:103-167 + tools/climbing.py:104-144
@mcp.tool()
async def write_wellness_entry(  # pylint: disable=too-many-arguments
    date: str,                              # required, YYYY-MM-DD
    sleep_hours: float | None = None,
    sleep_quality: int | None = None,       # range from probe (D-01b)
    soreness: int | None = None,
    fatigue: int | None = None,
    motivation: int | None = None,
    stress: int | None = None,
    mood: int | None = None,
    hrv: float | None = None,               # ms — pass-through
    resting_hr: int | None = None,          # bpm — pass-through
    athlete_id: str | None = None,
    api_key: str | None = None,
) -> str:
    """Log a wellness entry for an athlete on a given date.

    Before calling this tool, ask the user for any subset of:
    - sleep hours (e.g., 7.5)
    - sleep quality (1-N scale, where 1 is great)
    - soreness, fatigue, motivation, stress, mood (1-N scales)
    - HRV (ms), resting HR (bpm)

    Fields NOT supplied are not sent — they preserve existing values for
    that day (upsert semantics). At least one wellness field must be set;
    a call with only `date` is rejected.

    Args:
        date: Date in YYYY-MM-DD format. Required.
        sleep_hours: Hours of sleep last night (e.g. 8.0). Converted to
            sleepSecs internally.
        sleep_quality: Sleep quality on the Intervals.icu scale.
        soreness: Subjective soreness.
        fatigue: Subjective fatigue.
        motivation: Subjective motivation.
        stress: Subjective stress.
        mood: Subjective mood.
        hrv: Heart-rate variability in ms (pass-through).
        resting_hr: Resting heart rate in bpm (pass-through).
        athlete_id: Optional Intervals.icu athlete ID.
        api_key: Optional Intervals.icu API key.

    Returns:
        Human-readable success or error string.
    """
    ...
```

### Pattern 2: Drop-None body builder (utility)

**What:** Convert a dict of public-param-name → value into the API's expected key names, dropping any None.

**When to use:** Wellness PUT body construction (D-09). Intervals.icu treats `null` as "clear this field" (Pitfall #2 integration table) — only supplied keys may appear.

**Template for `utils/wellness.py`:**

```python
# Source: shape inferred from utils/grades.py + utils/climbing.py module skeletons
"""Wellness-domain ranges and PUT-body construction.

Single source of truth for wellness field range validation and the
public-param → API field-name mapping. Mirrors utils/grades.py shape
(constants + small helpers, no tool/api imports).
"""

from typing import Any

__all__ = [
    "WELLNESS_RANGES",
    "PARAM_TO_API_FIELD",
    "sleep_hours_to_secs",
    "build_wellness_put_body",
]

# Ranges locked from Phase 2 second-probe results (D-01b → D-07).
# (min, max) inclusive. Out-of-range values must raise ValueError in the
# tool layer before the PUT.
WELLNESS_RANGES: dict[str, tuple[int, int]] = {
    # Confirmed by Plan 02-01 probe — values are placeholders pending probe:
    # "sleep_quality": (1, 4),
    # "soreness":      (1, 4),
    # "fatigue":       (1, 4),
    # "motivation":    (1, 4),
    # "stress":        (1, 4),
    # "mood":          (1, 4),
}

# Public param name → Intervals.icu API field name. Confirmed from the
# Phase 1 spike's wellness response shape. Re-verify in Plan 02-01.
PARAM_TO_API_FIELD: dict[str, str] = {
    "sleep_hours":   "sleepSecs",   # converted via sleep_hours_to_secs
    "sleep_quality": "sleepQuality",
    "soreness":      "soreness",
    "fatigue":       "fatigue",
    "motivation":    "motivation",
    "stress":        "stress",
    "mood":          "mood",
    "hrv":           "hrv",
    "resting_hr":    "restingHR",
}


def sleep_hours_to_secs(hours: float) -> int:
    """Convert user-friendly hours-of-sleep to Intervals.icu's sleepSecs."""
    return int(round(hours * 3600))


def build_wellness_put_body(params: dict[str, Any]) -> dict[str, Any]:
    """Build the PUT /wellness/{date} body — drop-None + name translation.

    Only keys whose values are not None appear in the output. Keys not
    listed in PARAM_TO_API_FIELD are silently dropped (defensive).

    Args:
        params: Mapping of public param names (sleep_hours, soreness, ...)
            to user-supplied values (or None).

    Returns:
        Dict suitable for `make_intervals_request(data=..., method='PUT')`.
    """
    body: dict[str, Any] = {}
    for public_name, api_name in PARAM_TO_API_FIELD.items():
        value = params.get(public_name)
        if value is None:
            continue
        if public_name == "sleep_hours":
            value = sleep_hours_to_secs(value)
        body[api_name] = value
    return body
```

### Pattern 3: Readback verification (value equality, not just presence)

**What:** After every write, GET the resource and confirm each supplied field roundtripped at the exact value sent.

**When to use:** Mandatory for both Phase 2 tools per D-11 (wellness) and D-15 (activity). Pitfall #2 says silent custom-field writes are class-A data-loss failures.

**Difference from Phase 1's verify-presence:** Phase 1's `_verify_custom_fields_setup_impl` only checks whether a key APPEARS on any recent activity — it's a setup probe, not a value comparison. Phase 2 needs **value equality**: the field exists AND equals what we sent.

**Type-coercion drift to watch for:**
- Phase 1 spike submitted `icu_rpe: 6` — readback would return `6` (int) or possibly `6.0` (float). `==` with int comparison is fine; isinstance check before formatting.
- `indoor: True` (Python bool) — Intervals.icu may roundtrip as `True` or as the string `"True"`. Verify by direct equality first; if probe shows coercion, normalize before compare.
- `sends: 5` (int) — JSON only has `number`; `5 == 5.0` is True in Python so int/float coercion is a non-issue.
- `discipline: "bouldering"` — string; direct `==` is fine.
- `top_grade_sent: "6A"` — string; direct `==` is fine.

**Template (sketch):**

```python
# Source: pattern derived from CONTEXT.md D-11/D-15 + Phase 1 spike's roundtrip check
def _readback_diff(
    sent: dict[str, Any],
    received: dict[str, Any],
) -> list[str]:
    """Return list of human-readable mismatches between sent and received.

    Empty list = full roundtrip success.
    """
    diffs: list[str] = []
    for key, expected in sent.items():
        actual = received.get(key)
        if actual is None:
            diffs.append(f"{key}: NOT FOUND in readback (expected {expected!r})")
        elif actual != expected:
            diffs.append(f"{key}: expected {expected!r}, got {actual!r}")
    return diffs
```

### Pattern 4: Conflict detection + override + audit message

**What:** Default-deny re-enrichment. GET first, refuse if any supplied field already has a non-null value, unless `override=True` — in which case, write AND post an audit message.

**Existing tool used:** `add_activity_message(activity_id, content)` in `tools/activities.py:352-382`. POSTs to `/activity/{id}/messages` with `{"content": "..."}`. Returns success/error string. **It's an `@mcp.tool()` — but Python imports work fine; tool registration doesn't prevent other code from calling it.** [VERIFIED: codebase read]

**Gotcha:** `add_activity_message` is registered as an MCP tool AND a regular async function. Calling it from `enrich_activity_climbing` is a normal `await add_activity_message(...)` — Pitfall #11 is about NOT importing private (`_`-prefix) helpers from sibling tool modules; public tool functions imported directly are fine because they're public API. Verify the import works in tests; if it triggers re-registration warnings, refactor to a shared `utils/` helper (per D-22 spirit).

**Audit message format (per CONTEXT.md `<specifics>`):**

```
[enrich override] discipline: bouldering→sport_lead, top_grade_sent: 6A→6A+ (prior values preserved here)
```

Searchable (`grep "[enrich override]"` finds them all), parsable (`field: old→new` pairs comma-separated), schema-free (lives in Intervals.icu's existing message log — no shadow store).

### Anti-Patterns to Avoid

- **Sending `null` to clear a field implicitly.** [CITED: research/PITFALLS.md Integration Gotchas table — "Wellness write: Sending null values for fields the user did not provide" → "Omit absent keys from the PUT body entirely; Intervals.icu treats null as 'clear this field'"]
- **Importing `_verify_custom_fields_setup_impl` AND treating its result as a value-roundtrip check.** It's a presence-on-recent-activities heuristic only (D-20 from Phase 1, see code in `tools/climbing.py:34-100`).
- **Skipping the GET-before-PUT conflict scan because "the LLM should know better."** Pitfall #10 is silent history mutation; LLMs retry, users change minds, the override gate is the only mechanism that preserves audit history.
- **Writing partial state on RPE/custom-field split (D-16) without an explicit error.** If `icu_rpe` lands but custom fields don't (or vice versa), the tool MUST return an error naming what landed vs didn't. Silent partial state is worse than total failure.
- **Calling `httpx` directly from new code.** Single HTTP boundary is non-negotiable per CLAUDE.md.
- **Using `_PARAM_TO_API_FIELD` from `tools/wellness.py` in `tools/climbing.py`.** D-22 forbids `_`-prefix sibling imports — promote to `utils/wellness.py` if needed (already there in this design).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Date validation (YYYY-MM-DD) | Custom regex | `validate_date()` in `utils/validation.py:31-47` | Already raises ValueError with named format; matches existing tool patterns |
| Athlete ID resolution / fallback to env | Reading env directly | `resolve_athlete_id(athlete_id, config.athlete_id)` in `utils/validation.py:50-70` | Returns `(id_to_use, error_message_or_None)` — used by every existing tool |
| HTTP retry on closed client | New retry logic | `make_intervals_request()` already retries once on closed-client RuntimeError | One HTTP boundary, one place to evolve retry behavior |
| Error message formatting per status code | Inline `if status == 422: ...` | `_get_error_message()` in `api/client.py:84-99` (called inside `make_intervals_request`) | Centralized 401/403/404/422/429/500/503 mapping |
| Grade regex / discipline coupling | Inline `if discipline == "bouldering" and not grade.match(...)` | `validate_grade(grade, discipline)` in `utils/grades.py:33-63` | Phase 1 ships this; cross-scale guard via case sensitivity |
| Custom-field setup verification | New verification logic | `_verify_custom_fields_setup_impl(athlete_id, api_key)` from `tools/climbing.py:34-100` | Returns `(ok, missing_keys, human_message)` — exactly what D-20 needs |
| Audit-trail storage for overrides | New message log / file / database | `add_activity_message(activity_id, content)` in `tools/activities.py:352-382` | Intervals.icu's own activity-message log; no shadow store; Pitfall #10 mitigation |
| Wellness response rendering | New formatter | `format_wellness_entry(entries, include_all_fields)` in `utils/formatting.py:271-364` | Existing renderer; covers training/vital/sleep/subjective/nutrition sections |
| Climbing readback rendering | New formatter | `format_climbing_activity(activity)` in `utils/formatting.py:552-592`, EXTEND additively per D-24 | Phase 1 already renders 11 fields; Phase 2 only extends; Pitfall #12 (no shared-utility regression) |

**Key insight:** The Phase 1 utility layer is comprehensive. Phase 2's job is mostly to **plumb** — wire validators in front of `make_intervals_request()`, run readback after, and return formatted results. The only genuinely new code is `utils/wellness.py` (range table + body builder) and the two tool functions themselves.

## Runtime State Inventory

> Phase 2 is greenfield code addition (new tools, new utils module, new tests). No rename, refactor, migration, or string-replacement work. Section omitted intentionally.

## Common Pitfalls

(Drawn from `.planning/research/PITFALLS.md` and the Phase 1 spike's confirmed failure modes; numbered to match research/PITFALLS.md.)

### Pitfall #2: Custom-field writes silently succeed but store nothing

**What goes wrong:** PUT returns 200; the activity readback shows the field is absent (or unchanged). User believes the write landed; data is lost.

**Why it happens:** Intervals.icu silently ignores unknown field keys when the user-defined custom-field schemas are missing in the athlete account.

**How to avoid:**
1. Run `_verify_custom_fields_setup_impl(...)` BEFORE any PUT that touches custom fields (D-20).
2. Run readback (GET activity) AFTER the PUT and assert each supplied custom-field key is present with the exact value sent (D-15).
3. On readback failure, return an error that includes `_README_POINTER` so Claude/user knows where to fix the schema.

**Warning signs:** PUT response 200, but `readback_after_custom_field_put.discipline == None` despite PUT body containing `{"discipline": "bouldering"}`. The Phase 1 spike's findings file (`custom_field_roundtripped: false`) is exactly this failure observed live.

### Pitfall #3: Grade-discipline coupling

**What goes wrong:** `top_grade_sent="6A"` (Font, uppercase) supplied with `discipline="sport_lead"` (route discipline expecting French sport lowercase) — silent contamination if not validated.

**Why it happens:** The two scales' textual forms are visually similar; nothing in the API enforces consistency.

**How to avoid:** Call `validate_grade(grade, discipline)` for each supplied grade BEFORE any HTTP call (D-13). The function already raises ValueError with a message naming the expected scale. If `top_grade_sent` is supplied without `discipline`, refuse the call upfront (D-12 — "if any of `top_grade_sent`/`top_grade_attempted` is supplied, `discipline` must also be supplied").

**Warning signs:** Test matrix in `tests/test_grades.py` already covers Font-on-route and French-on-boulder rejection — Phase 2 reuses this; failing tests there indicate broken cross-scale guard.

### Pitfall #5: MCP statelessness — no multi-tool state

**What goes wrong:** Phase 2 splits the enrichment into a `begin_enrichment` and `commit_enrichment` pair, or stores partial state in a module-level dict between MCP tool calls. Reconnect or retry breaks the partial state.

**Why it happens:** Form-style multi-step UX is intuitive but wrong for MCP. Each tool call is independent.

**How to avoid:** Single tool, all params (D-06, D-12). The tool docstring tells Claude what to gather conversationally before calling. No `_in_progress_writes` dict, no session/correlation IDs.

**Warning signs:** Any module-level mutable state in `tools/wellness.py` or `tools/climbing.py` beyond the existing `config = get_config()` singleton. Any param named `session_id` / `correlation_id`.

### Pitfall #6: Tool docstrings too terse

**What goes wrong:** Docstring says "Log a wellness entry." Claude calls with only `date` because that's the only required arg; user told Claude about sleep hours and soreness in the same conversation but those never make it into the call.

**Why it happens:** Existing read tools are terse (LLM only needs to know what they return). Write tools that gather subjective data have a fundamentally different role: the docstring is the LLM's instruction sheet on what to ask the user before calling.

**How to avoid:** Use the `verify_custom_fields_setup` docstring (`tools/climbing.py:108-136`) as the template. It explicitly enumerates the 7 required custom fields, links to README, and specifies the optional/required split. Phase 2 docstrings must:
1. State conversationally what to gather BEFORE calling the tool
2. Explain each parameter's meaning AND format (e.g., `sleep_hours: float, e.g. 7.5` — not just `sleep_hours: float`)
3. Distinguish required (`date`, `activity_id`) from optional (everything else)
4. Note upsert semantics for wellness ("fields not supplied preserve existing values")
5. Note default-deny re-enrichment for climbing ("re-enrichment requires override=True; prior values preserved as activity message")

**Warning signs:** Docstring under 5 lines for a write tool. No mention of "ask the user" or "before calling, gather". No format hint for numeric ranges.

### Pitfall #10: Retroactive grade overwrite (silent history mutation)

**What goes wrong:** User logs 6A as `top_grade_sent`. Later realizes it was 6A+. Calls `enrich_activity_climbing` again; the PUT silently overwrites 6A with 6A+. Trend analysis ("when did I first send 6A?") becomes wrong.

**Why it happens:** Intervals.icu custom fields are unversioned. PUT replaces value.

**How to avoid (D-14):**
1. GET the activity before any PUT — scan supplied fields for non-null current values.
2. If any conflict AND `override=False` → refuse with a list of conflicting fields + their current values + hint to pass `override=True`.
3. If `override=True` → proceed AND `await add_activity_message(activity_id, "[enrich override] field1: old→new, field2: old→new ...")`.
4. Include `icu_rpe` in the conflict scan — overwriting prior RPE is also history mutation.

**Warning signs:** Test mocking `make_intervals_request` for a PUT but no GET-before-PUT in the trace. A test that calls `enrich_activity_climbing` twice on the same id with different values without `override=True` and the second succeeds. `icu_rpe` not included in the conflict-detection set.

### Pitfall #11: Coupling new tools to private helpers in sibling tool modules

**What goes wrong:** `tools/climbing.py` imports `_parse_activities_from_result` from `tools/activities.py` to reuse parsing logic. A later fix to that helper breaks the climbing tool silently.

**Why it happens:** Code reuse is natural; the underscore prefix is easy to ignore.

**How to avoid (D-22):** No `_`-prefix imports across `tools/` modules. If `tools/wellness.py` and `tools/climbing.py` need to share something, promote it to `utils/`. Public tool functions (no `_` prefix) are still fine to call across `tools/` — `add_activity_message` from `tools/activities.py` is public API.

**Warning signs:** `from intervals_mcp_server.tools.activities import _parse_activities_from_result` or similar. Import line ending with `_anything` from a sibling `tools/` module.

### Pitfall #12: Regressing existing tools while extending utilities

**What goes wrong:** `format_climbing_activity` is rewritten to handle Phase 2's extra readback scenarios. The rewrite changes whitespace; a downstream test asserting the exact output string in some other phase breaks.

**Why it happens:** The path of least resistance is "rewrite the function to be cleaner now that I'm here."

**How to avoid (D-24, Phase 1 D-15 carried forward):** EXTEND, don't rewrite. The byte-identical regression test in `tests/test_format_climbing_activity.py:96-123` (`test_format_activity_summary_byte_identical_regression_guard`) is the established pattern — replicate it for any formatter touched.

**Warning signs:** Diff in `utils/formatting.py` shows large block deletions on lines that already worked. CI passes locally because string-contains assertions still hold, but other tests using snapshot comparison fail.

### Pitfall #14: Test discovery drift

**What goes wrong:** Test file `tests/climbing_write_tests.py` (or `tests/test-climbing-write.py`) — pytest doesn't discover it; coverage silently drops to zero.

**How to avoid (D-23):**
1. Files MUST be `test_*.py` (`test_wellness_write.py`, `test_climbing_write.py`).
2. Functions MUST be `test_*`.
3. Verify with `pytest --collect-only` (count must increase after Plans 02-02..02-05 land).
4. Tests must be runnable via `uv run pytest -v tests` (the pre-commit hook command).

**Warning signs:** New `.py` file in `tests/` whose name doesn't start with `test_`. New test function whose name doesn't start with `test_`. `pytest --collect-only | wc -l` unchanged after merge.

## Code Examples

Verified patterns from the existing codebase.

### Tool registration + import (zero server.py changes for Phase 2)

```python
# Source: src/intervals_mcp_server/tools/climbing.py:1-17 — Phase 1 module skeleton
"""
Climbing-related MCP tools for Intervals.icu.

This module contains tools for the climbing training loop: ...
"""

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.climbing import CUSTOM_FIELD_KEYS
from intervals_mcp_server.utils.validation import resolve_athlete_id

# Import mcp instance from shared module for tool registration
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401

config = get_config()

@mcp.tool()
async def enrich_activity_climbing(...) -> str:
    ...
```

`server.py` already imports `tools/climbing.py` (Phase 1 D-17) and `tools/wellness.py` — Phase 2 needs ZERO `server.py` edits to register the new tools (decorator runs at import time).

### Error-dict check + user-facing string return (existing pattern)

```python
# Source: src/intervals_mcp_server/tools/wellness.py:51-52 (existing tool)
result = await make_intervals_request(url=..., api_key=api_key, params=params)

if isinstance(result, dict) and "error" in result:
    return f"Error fetching wellness data: {result.get('message')}"
```

### POST audit message (existing reusable function)

```python
# Source: src/intervals_mcp_server/tools/activities.py:352-382
@mcp.tool()
async def add_activity_message(
    activity_id: str,
    content: str,
    api_key: str | None = None,
) -> str:
    result = await make_intervals_request(
        url=f"/activity/{activity_id}/messages",
        api_key=api_key,
        method="POST",
        data={"content": content},
    )
    if isinstance(result, dict) and "error" in result:
        return f"Error adding message to activity: {result.get('message', 'Unknown error')}"
    ...
```

Phase 2 import: `from intervals_mcp_server.tools.activities import add_activity_message`. Then in the override branch: `await add_activity_message(activity_id, audit_text)`.

### Test mock pattern (monkeypatch + asyncio.run)

```python
# Source: tests/test_climbing.py:122-138 (Phase 1 pattern)
def test_write_wellness_entry_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    from intervals_mcp_server.tools.wellness import write_wellness_entry

    calls: list[dict] = []

    async def fake_request(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        # Simulate PUT response then GET readback
        if kwargs.get("method") == "PUT":
            return {"id": "2026-04-25", "sleepSecs": 28800, "soreness": 3}
        # GET readback
        return [{"id": "2026-04-25", "sleepSecs": 28800, "soreness": 3}]

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.wellness.make_intervals_request", fake_request
    )

    result = asyncio.run(write_wellness_entry(
        athlete_id="i1",
        date="2026-04-25",
        sleep_hours=8.0,
        soreness=3,
    ))
    assert "success" in result.lower() or "logged" in result.lower()
    # Verify the PUT body shape
    put_call = next(c for c in calls if c["kwargs"].get("method") == "PUT")
    assert put_call["kwargs"]["data"] == {"sleepSecs": 28800, "soreness": 3}
```

**Note:** Phase 1's `test_climbing.py` tests monkey-patch BOTH `intervals_mcp_server.api.client.make_intervals_request` AND `intervals_mcp_server.tools.climbing.make_intervals_request` because of how the import lands at module load. Phase 2 follows the same pattern (per the existing tests).

### Range-table alignment test (mirror Phase 1's enum alignment)

```python
# Source: pattern abstracted from tests/test_climbing.py:34-41
import inspect

def test_wellness_ranges_align_with_signature() -> None:
    from intervals_mcp_server.tools.wellness import write_wellness_entry
    from intervals_mcp_server.utils.wellness import WELLNESS_RANGES

    sig = inspect.signature(write_wellness_entry)
    range_keys = set(WELLNESS_RANGES.keys())
    # Every numeric param in the signature (except date/athlete_id/api_key/HRV/RHR
    # — those don't have hard ranges) must have a WELLNESS_RANGES entry.
    expected = {"sleep_quality", "soreness", "fatigue", "motivation", "stress", "mood"}
    assert range_keys == expected, (
        f"WELLNESS_RANGES drift from signature: "
        f"missing={expected - range_keys}, extra={range_keys - expected}"
    )
```

### Plan 02-01 second-probe skeleton

```python
# Source: pattern derived from scripts/spike_write_endpoints.py + CONTEXT.md D-01..D-05
"""
Plan 02-01: Second probe for write-path contracts.

Resolves three open unknowns from 01-SPIKE-FINDINGS.md:
  (a) Activity custom-field PUT body shape (Phase 1 saw 422 on top-level keys)
  (b) Wellness subjective-field valid scales (Phase 1 saw 422 on `fatigue: 5`)
  (c) icu_rpe write path — single PUT vs split

Findings → .planning/phases/02-wellness-write-and-activity-enrichment/02-SPIKE-FINDINGS.md.

NOT A PYTEST TEST. Run by hand:
    uv run scripts/spike_write_endpoints_phase2.py

Hard-stop fallback (D-05): if no body shape lands custom fields on an activity
via readback verification, EXIT 2 and write the failure to the findings file.
The phase planner will then trigger /gsd-discuss-phase 2 to revisit.
"""

import asyncio, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config

SPIKE_DATE = "2099-01-01"
ATHLETE_REDACTED = "{athlete_id}"
FINDINGS_PATH = Path(__file__).resolve().parents[1] / ".planning" / "phases" / \
    "02-wellness-write-and-activity-enrichment" / "02-SPIKE-FINDINGS.md"


# Probe (a): Activity custom-field PUT body shape variations.
ACTIVITY_PUT_VARIANTS = [
    # Variant 1: top-level keys (Phase 1 already tried — record again with fresh activity)
    {"shape": "top_level", "body": {"discipline": "bouldering", "icu_rpe": 6}},
    # Variant 2: nested envelope
    {"shape": "nested_custom_fields",
     "body": {"custom_fields": {"discipline": "bouldering"}, "icu_rpe": 6}},
    # Variant 3: separate icu_rpe-only PUT (isolating native vs custom)
    {"shape": "icu_rpe_only", "body": {"icu_rpe": 6}},
    # Variant 4: name field tag (some Intervals endpoints expect tags array)
    {"shape": "tags_array",
     "body": {"tags": ["discipline:bouldering"], "icu_rpe": 6}},
    # Variant 5: alternate URL — PUT /athlete/{id}/activity/{id}
    {"shape": "athlete_scoped_url", "body": {"discipline": "bouldering"},
     "url_template": "/athlete/{athlete_id}/activity/{activity_id}"},
    # Variant 6: POST instead of PUT (some APIs use POST for partial update)
    {"shape": "post_partial", "body": {"discipline": "bouldering"}, "method": "POST"},
    # ... more variants per planner judgement
]


# Probe (b): Wellness subjective-field scale ranges.
SUBJECTIVE_FIELDS = ["fatigue", "stress", "motivation", "mood", "soreness", "sleep_quality"]
SCALE_PROBE_VALUES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]  # which accept which


async def probe_activity_custom_field_put(athlete_id: str) -> dict:
    """Try each variant against a fresh spike activity. Record what roundtrips."""
    findings: dict = {"variants": []}
    # Create fresh spike activity (Phase 1 confirmed this works)
    create_resp = await make_intervals_request(
        url=f"/athlete/{athlete_id}/activities/manual",
        method="POST",
        data={"start_date_local": f"{SPIKE_DATE}T00:00:00",
              "type": "WeightTraining",
              "name": "PHASE2 SPIKE — DELETE ME",
              "moving_time": 3600},
    )
    activity_id = create_resp.get("id") if isinstance(create_resp, dict) else None
    if not activity_id:
        findings["create_failed"] = create_resp
        return findings

    findings["activity_id"] = activity_id
    for variant in ACTIVITY_PUT_VARIANTS:
        method = variant.get("method", "PUT")
        url = variant.get("url_template",
                           "/activity/{activity_id}").format(
            athlete_id=athlete_id, activity_id=activity_id
        )
        resp = await make_intervals_request(url=url, method=method, data=variant["body"])
        readback = await make_intervals_request(url=f"/activity/{activity_id}")
        roundtripped = (
            isinstance(readback, dict)
            and all(readback.get(k) == v
                    for k, v in variant["body"].items()
                    if k != "custom_fields")  # nested case handled separately
        )
        findings["variants"].append({
            "shape": variant["shape"],
            "body_sent": variant["body"],
            "method": method,
            "url": url.replace(athlete_id, ATHLETE_REDACTED),
            "response_status": (resp.get("status_code") if isinstance(resp, dict)
                                and "error" in resp else 200),
            "roundtripped": roundtripped,
        })
        if roundtripped:
            findings["winning_variant"] = variant["shape"]
            break  # First win is the canonical answer

    # Cleanup
    await make_intervals_request(url=f"/activity/{activity_id}", method="DELETE")
    return findings


async def probe_wellness_subjective_scales(athlete_id: str) -> dict:
    """For each subjective field, find the range it accepts."""
    findings: dict = {}
    for field in SUBJECTIVE_FIELDS:
        accepted: list[int] = []
        rejected: list[int] = []
        for value in SCALE_PROBE_VALUES:
            resp = await make_intervals_request(
                url=f"/athlete/{athlete_id}/wellness/{SPIKE_DATE}",
                method="PUT",
                data={field: value},
            )
            if isinstance(resp, dict) and resp.get("error"):
                rejected.append(value)
            else:
                # Verify roundtrip — some accepts may silently coerce
                readback = await make_intervals_request(
                    url=f"/athlete/{athlete_id}/wellness",
                    params={"oldest": SPIKE_DATE, "newest": SPIKE_DATE},
                )
                if isinstance(readback, list) and readback:
                    if readback[0].get(field) == value:
                        accepted.append(value)
                    else:
                        rejected.append(value)  # silent coercion = effective reject
        findings[field] = {"accepted": accepted, "rejected": rejected,
                           "range": (min(accepted), max(accepted)) if accepted else None}
        # Cleanup field
        await make_intervals_request(
            url=f"/athlete/{athlete_id}/wellness/{SPIKE_DATE}",
            method="PUT", data={field: -1},
        )
    return findings


async def main() -> int:
    config = get_config()
    if not config.athlete_id or not config.api_key:
        print("ERROR: API_KEY and ATHLETE_ID must be set in .env", file=sys.stderr)
        return 1
    activity_findings = await probe_activity_custom_field_put(config.athlete_id)
    wellness_findings = await probe_wellness_subjective_scales(config.athlete_id)
    # ... write findings to FINDINGS_PATH (with redaction, see Phase 1 spike) ...
    if not activity_findings.get("winning_variant"):
        # D-05 hard-stop signal
        print("HARD STOP: No activity custom-field PUT variant roundtripped.", file=sys.stderr)
        print(f"See {FINDINGS_PATH}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

The shape above is illustrative; the planner finalizes the variant list during plan writing. The two probe functions and the hard-stop exit code (D-05) are the load-bearing pieces.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Phase 1 spike's single `top-level-keys` PUT for custom fields | Phase 2 second probe enumerates ≥6 body shapes including alternate URLs and methods | Phase 1 → Phase 2 (this phase) | Eliminates the open question that blocked Phase 1; CONTEXT.md D-01 makes the variant enumeration explicit |
| `null` to clear a wellness field | Drop-None body builder; never send `null` from a write tool | Established by research/PITFALLS.md integration table; codified in CONTEXT.md D-09 | Prevents silent clobbering of fields the user didn't mention (WELL-03) |
| One single-call PUT for activity custom-fields | Single PUT preferred; split-PUT fallback if `icu_rpe` requires separate endpoint | D-16, contingent on probe (D-01c) | Phase 2 must record the chosen path in 02-SPIKE-FINDINGS.md and the tool docstring; planner picks based on probe results |
| Verify-fields presence check (Phase 1's heuristic, recent-activities scan) | Value-equality readback (Phase 2 enrichment) | Phase 1 → Phase 2 | Phase 1 only proves field is DEFINED; Phase 2's tool must prove the value LANDED |
| Phase 1 spike findings carried forward verbatim | Phase 1 spike findings stay closed (D-02); Phase 2 owns its own discovery file | Phase 1 → Phase 2 | Audit trail: 01-SPIKE-FINDINGS.md = Phase 1 closure; 02-SPIKE-FINDINGS.md = Phase 2 discoveries; no cross-edits |

**Deprecated/outdated within this codebase:**
- The `complete_climbing_session` and `create_climbing_activity` references in older code/research — those are Phase 3, not Phase 2. The CONTEXT.md is explicit: only `write_wellness_entry` and `enrich_activity_climbing` ship in Phase 2.
- Any "two-tool" wellness-write design — replaced by single-tool, all-fields-as-params per Pitfall #5 + D-06.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The Phase 1 wellness PUT body keys (`sleepSecs`, `soreness`, `restingHR`, `hrv`, `mood`, `motivation`, `stress`, `fatigue`, `sleepQuality`) match the readback shape from 01-SPIKE-FINDINGS.md exactly | `_PARAM_TO_API_FIELD` mapping in Pattern 2 | LOW — directly derived from 01-SPIKE-FINDINGS.md `write_1_response` field names; the probe (D-01b) re-verifies during normal operation |
| A2 | `add_activity_message` is callable from `tools/climbing.py` via direct import without re-registration warnings | Pattern 4 | LOW — public function, no re-decorator effect; if a registration warning surfaces in tests, refactor to `utils/audit.py` per D-22 spirit |
| A3 | Phase 1's `_verify_custom_fields_setup_impl` heuristic remains usable as a pre-write guard | D-20, Don't Hand-Roll table | LOW — heuristic's known false-positive on never-populated fields is documented; D-20 explicitly says the guard runs only for custom-field-touching writes |
| A4 | Wellness subjective scales are 1-N integer (where N is 4 or 10 per field) | Pattern 2 placeholder ranges | MEDIUM — Phase 1 confirmed `fatigue: 5` returned 422 (range upper bound is < 5); the actual range per field is unknown until Plan 02-01 probes 1..10 systematically |
| A5 | The activity custom-field PUT body shape is closeable by the second probe (i.e., some shape will roundtrip) | D-05 hard-stop branch | HIGH — if FALSE, Phase 2 stops and re-discusses. The whole phase pivots on this; the hard-stop is the explicit acknowledgment of risk |
| A6 | Single PUT can carry both `icu_rpe` and custom fields | D-16 default branch | MEDIUM — Phase 1 spike's failed PUT bundled both; failure may have been due to body-shape issue (D-01a) NOT co-location issue. Probe variant 3 (`icu_rpe_only`) isolates this. |
| A7 | `pytest --collect-only` discovers `tests/test_wellness_write.py` and `tests/test_climbing_write.py` automatically given the existing pyproject.toml config | D-23, Pitfall #14 | LOW — pyproject.toml's pytest section uses default discovery; existing `test_*.py` files are picked up [VERIFIED: `pytest -q` passes on the current suite] |

**Action for planner:** Line up Plan 02-01 to resolve A4, A5, A6 before Plan 02-04 begins. A1 is a sanity check that happens during 02-02 implementation.

## Open Questions (RESOLVED via Plan 02-01 execution)

> Each question's `Recommendation` line is the resolution path; Plan 02-01's `02-SPIKE-FINDINGS.md` carries the actual locked values that closed each question. Inline `**RESOLVED via Plan 02-01:**` markers below make the resolution traceable per Nyquist Dimension 11 (research_resolution).

1. **Activity custom-field PUT body shape (Plan 02-01 closes)**
   - What we know: Phase 1 spike tried top-level keys → 422; readback showed unchanged activity. DELETE works, so cleanup is feasible.
   - What's unclear: Which body shape (top-level, nested envelope, alternate URL, alternate method, tags-array hybrid) lands the write. CONTEXT.md `<specifics>` requires the probe to produce paste-ready code blocks for the winning shape.
   - **RESOLVED via Plan 02-01:** Recommendation: Plan 02-01 enumerates ≥6 variants in fixed order; first roundtrip wins; if all fail, exit code 2 → re-discuss (D-05).

2. **Wellness subjective-field ranges (Plan 02-01 closes)**
   - What we know: `fatigue: 5` returned 422; `soreness: 3` worked. Range upper bound is somewhere between 3 and 5 for `fatigue` (likely 1-4, common in Intervals.icu UI).
   - What's unclear: Which fields use 1-4 vs 1-10 vs other. Documentation is sparse.
   - **RESOLVED via Plan 02-01:** Recommendation: Plan 02-01 probes 1..10 per field, records `accepted/rejected/range` per field; ranges land in `WELLNESS_RANGES` dict (D-07, D-19).

3. **Single-PUT vs split-PUT for icu_rpe + custom fields (Plan 02-01 closes)**
   - What we know: Phase 1's `{"discipline": "bouldering", "icu_rpe": 6}` returned 422. Cause could be (a) body shape (open Q1), (b) co-location, or (c) both.
   - What's unclear: Once body shape is closed (Q1), does a single PUT carrying both fields work, or must `icu_rpe` go separately?
   - **RESOLVED via Plan 02-01:** Recommendation: Plan 02-01 probe variant 3 (`icu_rpe_only`) separately to isolate the native-field write path. D-16 handles either outcome.

4. **`feel` field as alternative to `mood`**
   - What we know: Intervals.icu UI has both `mood` and `feel` per the wellness response (Phase 1 readback). Sport settings show `showFeel: true`.
   - What's unclear: Whether to expose a `feel` param. CONTEXT.md Discretion bullet says "currently not in scope; defer unless probe surfaces an Intervals.icu equivalent worth supporting."
   - **RESOLVED via Plan 02-01:** Recommendation: Plan 02-01 probe SHOULD probe `feel` alongside `mood` to record its acceptance and scale. If both behave identically, defer (one is enough). If `feel` is the canonical 1-5 emoji-style, surface as a v2 ticket — do NOT add to Phase 2 scope.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | All code | ✓ (assumed — Phase 1 ran) | 3.12+ per pyproject.toml | — |
| `uv` | Tooling | ✓ | per AGENTS.md | — |
| `pytest` | Tests | ✓ | >=8.3.5 (locked in pyproject.toml dev extras) | — |
| `ruff` | Lint/format | ✓ | >=0.1.0 | — |
| `mypy` | Type-check | ✓ | >=1.0.0 | — |
| `pytest-asyncio` | Async tests | ✓ | >=0.21 | — |
| Intervals.icu API | Spike + smoke | ✓ (live, used in Phase 1) | n/a | — — D-05 hard-stop is the fallback for body-shape failure, not unavailability |
| `.env` with `API_KEY` and `ATHLETE_ID` | Spike + smoke | ✓ (Phase 1 used it) | — | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

**Skip note:** Plan 02-01's probe and Plan 02-05's smoke-test depend on live API access; Plans 02-02..02-04 (the unit tests + tool implementation) do NOT — they monkey-patch `make_intervals_request`. So planner can sequence probe execution and unit-test work in parallel for human time use.

## Validation Architecture

> Nyquist validation enabled per `.planning/config.json` `workflow.nyquist_validation: true`. The planner MUST derive `02-VALIDATION.md` from this section.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >=8.3.5 + pytest-asyncio >=0.21 (already in `pyproject.toml` dev extras) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` section [VERIFIED: codebase] |
| Quick run command | `uv run pytest -q tests/test_wellness_write.py tests/test_climbing_write.py` |
| Full suite command | `uv run pytest -v tests` (matches `.pre-commit-config.yaml` pre-push hook) |
| Discovery check | `uv run pytest --collect-only` (Pitfall #14) |
| Type-check | `uv run mypy src tests` |
| Lint | `uv run ruff check . && uv run ruff format --check .` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WELL-01 | `write_wellness_entry(date=..., sleep_hours=8.0, soreness=3)` builds correct PUT body and reads back values | unit | `pytest tests/test_wellness_write.py::test_subjective_metrics_round_trip -x` | ❌ Wave 0 |
| WELL-02 | `write_wellness_entry(date=..., hrv=42.5, resting_hr=51)` includes both `hrv` and `restingHR` keys in PUT body | unit | `pytest tests/test_wellness_write.py::test_objective_metrics_pass_through -x` | ❌ Wave 0 |
| WELL-03 | Calling `write_wellness_entry` with `sleep_hours=8` then a separate call with `soreness=3` does NOT clobber `sleepSecs` (drop-None ensures only supplied keys appear in each body) | unit | `pytest tests/test_wellness_write.py::test_drop_none_preserves_unrelated_fields -x` | ❌ Wave 0 |
| WELL-03 | (Live confirmation) Phase 1 spike already confirmed upsert semantics in `01-SPIKE-FINDINGS.md` `upsert_semantics_confirmed: true` | smoke (already done in Phase 1) | n/a — read 01-SPIKE-FINDINGS.md | ✅ |
| CLIMB-03 | `enrich_activity_climbing(activity_id="iX", discipline="bouldering", rpe=6)` issues PUT to correct URL with correct body | unit | `pytest tests/test_climbing_write.py::test_enrich_minimal_call_issues_correct_put -x` | ❌ Wave 0 |
| CLIMB-04 | `discipline="bouldering"` and `indoor=True` both appear in PUT body | unit | `pytest tests/test_climbing_write.py::test_discipline_and_indoor_in_put_body -x` | ❌ Wave 0 |
| CLIMB-05 | `top_grade_sent="6A"` with `discipline="bouldering"` validates and writes; `top_grade_sent="6A"` with `discipline="sport_lead"` raises ValueError naming "French sport" | unit | `pytest tests/test_climbing_write.py::test_grade_validation_before_http -x` | ❌ Wave 0 |
| CLIMB-05 | `sends=5, attempts=8` appear in PUT body | unit | `pytest tests/test_climbing_write.py::test_sends_attempts_in_put_body -x` | ❌ Wave 0 |
| CLIMB-06 | `session_focus="power"` appears in PUT body | unit | `pytest tests/test_climbing_write.py::test_session_focus_in_put_body -x` | ❌ Wave 0 |
| CLIMB-07 | `rpe=6` ends up as `icu_rpe: 6` in the PUT body (key translation, native-field write) | unit | `pytest tests/test_climbing_write.py::test_rpe_param_writes_to_icu_rpe -x` | ❌ Wave 0 |
| CLIMB-07 | RPE-only call (no custom-field params) skips the `_verify_custom_fields_setup_impl` guard (D-20) | unit | `pytest tests/test_climbing_write.py::test_rpe_only_skips_verify_guard -x` | ❌ Wave 0 |
| CLIMB-10 | When `_verify_custom_fields_setup_impl` reports missing fields, `enrich_activity_climbing` returns the named-field error WITHOUT issuing PUT | unit | `pytest tests/test_climbing_write.py::test_missing_custom_fields_blocks_put -x` | ❌ Wave 0 |
| CLIMB-10 | Readback after PUT detects silent ignore (PUT 200 but readback shows field unchanged) and returns error containing the field name + README pointer | unit | `pytest tests/test_climbing_write.py::test_readback_failure_named_in_error -x` | ❌ Wave 0 |
| (D-10 reject empty) | `write_wellness_entry(date="2026-04-25")` with no other fields returns error without HTTP call | unit | `pytest tests/test_wellness_write.py::test_empty_call_rejected -x` | ❌ Wave 0 |
| (D-11 readback wellness) | After PUT, GET against `?oldest={date}&newest={date}` and verify each supplied field roundtripped | unit | `pytest tests/test_wellness_write.py::test_readback_diff_detection -x` | ❌ Wave 0 |
| (D-14 override) | Calling enrich a 2nd time with conflicting values WITHOUT `override=True` returns error listing conflicts | unit | `pytest tests/test_climbing_write.py::test_default_deny_re_enrichment -x` | ❌ Wave 0 |
| (D-14 audit) | `override=True` triggers `add_activity_message` call with `[enrich override]` prefix and `field: old→new` pairs | unit | `pytest tests/test_climbing_write.py::test_override_posts_audit_message -x` | ❌ Wave 0 |
| (D-16 split-PUT) | If split-PUT path is chosen (probe-dependent): RPE PUT first, then custom-field PUT; partial failure → explicit error naming what landed | unit | `pytest tests/test_climbing_write.py::test_split_put_partial_failure_named -x` (only if D-16 split branch chosen) | ❌ Wave 0, contingent |
| (D-25 smoke) | Live write to far-future date, readback confirms, DELETE cleans up | manual smoke (NOT pytest) | `uv run scripts/smoke_test_phase2.py` (or similar) | ❌ Wave 0 |
| (alignment test, mirrors Phase 1 enum-alignment) | `WELLNESS_RANGES` keys ↔ `write_wellness_entry` numeric param names match exactly | unit | `pytest tests/test_wellness_write.py::test_wellness_ranges_align_with_signature -x` | ❌ Wave 0 |
| (test discovery, Pitfall #14) | `pytest --collect-only` count after Phase 2 > count before | meta | `uv run pytest --collect-only -q | tail -1` (compare counts) | n/a |

### Sampling Rate

- **Per task commit:** `uv run pytest -q tests/test_wellness_write.py tests/test_climbing_write.py` (≤30s) — verifies the unit-tests for the modified module.
- **Per wave merge:** `uv run pytest -v tests` (full suite, includes existing `test_grades.py`, `test_climbing.py`, `test_format_climbing_activity.py`, `test_server.py`, `test_formatting.py`, `test_make_intervals_request.py`, `test_value.py` — Pitfall #12 regression guard).
- **Phase gate (before `/gsd-verify-work`):**
  1. `uv run ruff check . && uv run ruff format --check .`
  2. `uv run mypy src tests`
  3. `uv run pytest -v tests` (full suite green)
  4. `uv run pytest --collect-only` count increased (Pitfall #14 — Test Drift)
  5. Plan 02-01 outcome: 02-SPIKE-FINDINGS.md exists AND `winning_variant` is non-null (or D-05 was triggered → Phase 2 in re-discuss state, gate fails)
  6. Plan 02-05 outcome: smoke-script live run succeeded (verified in 02-VERIFICATION.md by Timo)

### Wave 0 Gaps

- [ ] `tests/test_wellness_write.py` — covers WELL-01, WELL-02, WELL-03 (drop-None), D-10 (empty rejection), D-11 (readback), alignment test
- [ ] `tests/test_climbing_write.py` — covers CLIMB-03, CLIMB-04, CLIMB-05, CLIMB-06, CLIMB-07, CLIMB-10, D-14 (override + audit), D-15 (readback), D-16 (split-PUT, contingent)
- [ ] `scripts/spike_write_endpoints_phase2.py` (or equivalent extension) — Plan 02-01 probe; produces `02-SPIKE-FINDINGS.md`
- [ ] `scripts/smoke_test_phase2.py` (or equivalent name) — D-25 standalone smoke-test; live writes, readback, DELETE cleanup
- [ ] `02-SPIKE-FINDINGS.md` — written by spike script, referenced by all subsequent Phase 2 plans
- [ ] **Framework install:** None — `pytest`, `pytest-asyncio`, `mypy`, `ruff` all already in `pyproject.toml` dev extras [VERIFIED: codebase]

## Security Domain

> CLAUDE.md does not flag a strict security-enforcement requirement. Phase 2 is internal-tooling additions (no new auth, no new endpoints exposed externally, no new data leaving the local machine) — including the section per the project default per .planning/config.json.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (existing) | HTTP Basic via `make_intervals_request()` (`API_KEY` env var); Phase 2 does NOT change auth |
| V3 Session Management | no | MCP is request/response; no sessions |
| V4 Access Control | no | Single-athlete, single-user; ATHLETE_ID is config |
| V5 Input Validation | yes | `validate_grade()` (Phase 1), `validate_date()` (existing), new `WELLNESS_RANGES` (Phase 2). Reject before any HTTP call. |
| V6 Cryptography | no | API key in env via python-dotenv; no new crypto introduced |

### Known Threat Patterns for Python/FastMCP/httpx + Intervals.icu

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key leakage in logs | Information Disclosure | `api/client.py` already logs request body at DEBUG only; do NOT add INFO-level log of full PUT bodies in Phase 2 (matches Pitfall research §Security Mistakes). The probe script DOES log bodies — that's acceptable in a hand-run script writing to a local findings file, but the file MUST redact `athlete_id` (Phase 1 spike already does this; Plan 02-01 inherits the pattern). |
| Injection via grade or discipline string | Tampering | All values land in JSON body via `make_intervals_request(data=...)` — no URL/query interpolation. Validators (`validate_grade`, range checks) reject malformed inputs before HTTP. |
| Returning Intervals.icu error body verbatim | Information Disclosure | `_get_error_message()` in `api/client.py` already maps status codes to user-friendly strings; Phase 2 tools should NOT pass the upstream error message verbatim if it might contain schema details — they should add their own context (e.g., "Error writing wellness data: <mapped message>"). |
| `add_activity_message` audit text containing user-supplied raw input | Tampering | Override audit text is constructed by the tool from validated values (already `validate_grade`'d, range-checked); raw user input never appears unsanitized in the message. |
| Spike script committing `athlete_id` to git | Information Disclosure | Phase 1 spike script established `_redact()` for `athlete_id` → `{athlete_id}` (`scripts/spike_write_endpoints.py:61-69`); Plan 02-01 reuses or replicates this. Test files use `i1` as a fake; never the real id. |

## Sources

### Primary (HIGH confidence)

- `.planning/phases/02-wellness-write-and-activity-enrichment/02-CONTEXT.md` — 25 locked decisions; canonical authority for Phase 2
- `.planning/REQUIREMENTS.md` — WELL-01..03 + CLIMB-03..07 + CLIMB-10 (the 9 requirements this phase ships)
- `.planning/PROJECT.md` — Key Decisions table; Constraints; Out of Scope
- `.planning/ROADMAP.md` §"Phase 2: Wellness Write and Activity Enrichment" — Goal + 4 Success Criteria
- `.planning/phases/01-foundation-and-write-path-spike/01-CONTEXT.md` — Phase 1 carry-forward decisions D-09, D-11, D-12, D-15, D-17, D-18, D-19, D-20
- `.planning/phases/01-foundation-and-write-path-spike/01-SPIKE-FINDINGS.md` — confirmed wellness PUT shape (sleepSecs+soreness), confirmed POST `/activities/manual`, confirmed DELETE `/activity/{id}`, confirmed activity readback shape (including native `icu_rpe`); the **two unclosed 422s** that Plan 02-01 must close
- `.planning/research/PITFALLS.md` — #2, #3, #5, #6, #10, #11, #12, #14 (the eight pitfalls Phase 2 directly addresses)
- `src/intervals_mcp_server/api/client.py` — `make_intervals_request()` signature, retry logic, error mapping
- `src/intervals_mcp_server/tools/climbing.py` — `_verify_custom_fields_setup_impl`, `_README_POINTER`, the Phase 1 module skeleton Phase 2 extends
- `src/intervals_mcp_server/tools/activities.py:352-382` — `add_activity_message(activity_id, content)` signature
- `src/intervals_mcp_server/tools/activities.py:103-167` — `get_activities` exemplar for many-arg async tools
- `src/intervals_mcp_server/tools/wellness.py` — current 71-line module shape; `write_wellness_entry` joins it
- `src/intervals_mcp_server/utils/grades.py` — `validate_grade(grade, discipline)` signature; `FONT_RE`/`FRENCH_SPORT_RE`
- `src/intervals_mcp_server/utils/climbing.py` — `Discipline`, `SessionFocus`, `CUSTOM_FIELD_KEYS`, `FieldSpec`
- `src/intervals_mcp_server/utils/validation.py` — `resolve_athlete_id`, `validate_date`
- `src/intervals_mcp_server/utils/formatting.py:552-592` — `format_climbing_activity` (Phase 1; extend additively)
- `tests/test_climbing.py` — Phase 1 test patterns (alignment tests, monkeypatch+asyncio.run, error-dict simulation)
- `tests/test_grades.py` — Phase 1 grade validation matrix
- `tests/test_format_climbing_activity.py:96-123` — byte-identical regression-guard pattern (Pitfall #12)
- `scripts/spike_write_endpoints.py` — Plan 02-01 reference structure
- `pyproject.toml` — version locks, pytest config, ruff/mypy config
- `.planning/codebase/STRUCTURE.md`, `CONVENTIONS.md`, `INTEGRATIONS.md`, `TESTING.md` — codebase patterns
- `.planning/config.json` — `workflow.nyquist_validation: true` (Validation Architecture section required)

### Secondary (MEDIUM confidence)

- `.planning/research/SUMMARY.md` — domain context for the broader Climbing Training Loop milestone (used to confirm Phase 2 scope alignment with the milestone narrative)
- `.planning/codebase/CONCERNS.md` (referenced by CONTEXT.md but not directly read this round) — module-size warning informs D-17/D-18 placement decisions
- `AGENTS.md` — uv / pytest / ruff / mypy tooling commands

### Tertiary (LOW confidence)

- (none — every Phase 2 claim is traceable to a primary or secondary source above)

## Metadata

**Confidence breakdown:**
- Existing codebase patterns (HTTP boundary, tool registration, test mocking, formatter shape, error handling): HIGH — direct codebase read; Phase 1 left a clean precedent.
- Phase 1 carry-forward (Discipline, SessionFocus, CUSTOM_FIELD_KEYS, validate_grade, _verify_custom_fields_setup_impl, _README_POINTER, format_climbing_activity): HIGH — code is in `main`, tests pass.
- Wellness PUT body keys + upsert semantics: HIGH — confirmed live in 01-SPIKE-FINDINGS.md.
- Activity custom-field PUT body shape: LOW until Plan 02-01 closes (the open question is the whole point of D-01a).
- Wellness subjective-field ranges: LOW until Plan 02-01 closes (D-01b).
- icu_rpe single-PUT vs split-PUT: LOW until Plan 02-01 closes (D-01c).
- `add_activity_message` reusability from `tools/climbing.py`: MEDIUM — public function, normal Python imports work; first cross-tool import in this codebase, so test it explicitly in unit tests.

**Research date:** 2026-04-25
**Valid until:** 2026-05-25 (30 days; CONTEXT.md decisions are locked, but the open API contracts close in Plan 02-01 — once findings land, this RESEARCH.md may need a small update note for `WELLNESS_RANGES` exact values and the `winning_variant` body shape).
