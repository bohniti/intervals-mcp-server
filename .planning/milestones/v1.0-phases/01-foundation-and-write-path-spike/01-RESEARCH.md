# Phase 1: Foundation and Write-Path Spike — Research

**Researched:** 2026-04-24
**Domain:** Intervals.icu write-API spike + climbing-domain utility scaffolding in an existing FastMCP Python server
**Confidence:** HIGH (codebase read directly; API contracts MEDIUM — deliberately so, because confirming them *is* the phase's goal)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Spike Execution
- **D-01:** The spike runs as a **standalone async script** at `scripts/spike_write_endpoints.py`, executed via `uv run`. Not a pytest test (spike ≠ test; it writes to live data and must not run in CI).
- **D-02:** The script uses `make_intervals_request()` — no direct `httpx` — so that the same auth/retry/error paths the real tools use are exercised.
- **D-03:** Spike target date is **far-future** (use `2099-01-01` or similar). Script writes, reads back, and attempts to delete/blank the entries. If an activity `DELETE` endpoint is not confirmed available, the script leaves a manual cleanup checklist at the bottom of `01-SPIKE-FINDINGS.md` (delete via Intervals.icu web UI).
- **D-04:** Confirmed findings — request body shape, response shape, upsert vs replace semantics for wellness PUT, required vs optional fields for activities POST, native `icu_rpe` write behaviour, the viable `type` value for climbing activities (`"WeightTraining"` vs `"Other"`) — are written to `.planning/phases/01-foundation-and-write-path-spike/01-SPIKE-FINDINGS.md` as the canonical reference for Phase 2 and Phase 3 planners.

#### Grade / Discipline Validation
- **D-05:** `utils/grades.py` provides **regex + typed helpers** — `FONT_RE`, `FRENCH_SPORT_RE`, and `validate_grade(grade: str, discipline: Discipline) -> str` that raises `ValueError` with a message naming the expected scale. No parser, no enum-of-all-grades.
- **D-06:** **Strict case + bare modifiers:**
  - Font must be uppercase (`6A`, `6A+`) — `FONT_RE = r'^[3-9][A-C](\+)?$|^[1-2]$'` (tune range for top-end if needed)
  - French sport must be lowercase (`6a`, `6a+`) — `FRENCH_SPORT_RE = r'^[3-9][abc](\+)?$'`
  - `+` allowed. Slashes, descriptors, cross-case input rejected. Case **is** the cross-scale guard — do not normalize.
- **D-07:** `Discipline` is a `StrEnum` in `utils/climbing.py` with `BOULDERING = "bouldering"`, `SPORT_LEAD = "sport_lead"`, `TOP_ROPE = "top_rope"`, `TRAD = "trad"`. `indoor: bool` is a separate tool parameter.
- **D-08:** `SessionFocus` is a `StrEnum` in `utils/climbing.py`: `POWER`, `ENDURANCE`, `TECHNIQUE`, `PROJECTING`, `MILEAGE` (values lowercase).

#### Custom-Field Prerequisite System
- **D-09:** **Field key convention:** lowercase underscore, unprefixed. 7 pinned v1 keys: `discipline` (select), `indoor` (bool), `session_focus` (select), `top_grade_sent` (text), `top_grade_attempted` (text), `sends` (integer), `attempts` (integer). Select-option strings must match `Discipline` / `SessionFocus` `.value`s exactly (asserted by test).
- **D-10:** `CUSTOM_FIELD_KEYS` is a **frozen dict of `FieldSpec` dataclasses** in `utils/climbing.py`. Single source of truth.
- **D-11:** `verify_custom_fields_setup` is **both** a Claude-callable MCP tool **and** an internal helper function used by every climbing-write tool as a pre-write guard. One implementation, two call sites.
- **D-12:** On missing fields: **hard block with named-field error.** No warn-and-proceed.
- **D-13:** Setup docs live in **README + verify-tool docstring**. The docstring mirrors the README table.

#### Utility Layout
- **D-14:** Phase 1 creates two new files: `utils/grades.py` and `utils/climbing.py`.
- **D-15:** `utils/formatting.py` is **extended** (not replaced) with a minimal `format_climbing_activity(activity: dict) -> str`. Phase 1 renders discipline, indoor, session_focus, top_grade_sent/attempted, sends, attempts, `icu_rpe`.
- **D-16:** `utils/types.py` and `utils/validation.py` are **not modified** in Phase 1.
- **D-17:** `tools/climbing.py` created in Phase 1 solely to register `verify_custom_fields_setup`. Establishes file + `server.py` import now, so Phase 2 adds to an already-wired module.

#### Cross-Cutting / Pitfall Guards
- **D-18:** **No `_`-prefixed imports from sibling tool modules** (Pitfall #11).
- **D-19:** `tests/test_grades.py` and `tests/test_climbing.py` must be discovered by `pytest --collect-only` (Pitfall #14).
- **D-20:** Phase 1 is **purely additive**. No regression risk to existing tests (Pitfall #12).

### Claude's Discretion
- Exact regex bounds for top-end grades — planner picks a sensible range, documents choice.
- Exact readback retry / timing after Intervals.icu PUT — implementation detail.
- Log level for the spike script (info vs debug).
- Whether `FieldSpec` is `@dataclass(frozen=True)` or `NamedTuple` — pick whichever reads best given how `utils/types.py` currently does dataclasses. **Recommendation below: `@dataclass(frozen=True)`.**

### Deferred Ideas (OUT OF SCOPE)
- V-scale and YDS grade support.
- Grade-rank comparison / arithmetic.
- Finger / skin condition field (v2).
- Venue / crag field (v2).
- Auto-generating README field table from `CUSTOM_FIELD_KEYS` — test asserts mapping matches instead (optional; planner decides).
- Delete endpoint for activities — spike confirms or denies; if denied, manual cleanup + Phase 3 duplicate guard absorbs the limitation.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **SETUP-01** | README (or dedicated setup doc) documents exact Intervals.icu custom fields (names, types, example values) before climbing tools can write them | D-13 (README + docstring); `CUSTOM_FIELD_KEYS` in `utils/climbing.py` is single source for the 7-field table; Phase 1 ships the README section and docstring. **Note:** Traceability table says SETUP-01 is Phase 5, but Phase 1's `verify_custom_fields_setup` docstring + README additions are the *authoring* of that doc; Phase 5 is the *acceptance* re-read. This is consistent. |
| **SETUP-02** | A verification path exists (diagnostic tool or self-check at first write) confirming required custom fields are present in athlete account, reporting missing ones by name | D-11, D-12; `verify_custom_fields_setup` as MCP tool + internal helper with hard-block-and-name-fields semantics. Spike confirms which endpoint lists custom-field definitions. |
| **CLIMB-08** | Grade values validated against declared discipline — Font rejected on sport route, French sport rejected on boulder, clear error naming expected scale | D-05, D-06; `validate_grade(grade, discipline)` in `utils/grades.py` with `FONT_RE` + `FRENCH_SPORT_RE`; strict case as cross-scale guard; tests in `tests/test_grades.py`. |

**Phase 1 is the foundation for every subsequent phase.** Phase 2 depends on `CUSTOM_FIELD_KEYS`, `validate_grade`, `format_climbing_activity`, and the confirmed write-API contract from the spike. Phase 3 depends on the confirmed `POST /activities` body shape and the `start_date_local` format pattern.
</phase_requirements>

---

## Summary

Phase 1 has two independently-shippable tracks that share zero runtime dependencies, plus one small integration ceremony:

1. **Write-path spike** — a standalone async script that exercises two API endpoints (`PUT /athlete/{id}/wellness/{date}` and the activity-create endpoint) against Timo's live account using a far-future date, then reads back, then cleans up. Output is a canonical findings file that Phase 2/3 planners read. **The spike replaces uncertainty; it is not code we ship.**
2. **Utility scaffold** — `utils/grades.py` + `utils/climbing.py` + a `format_climbing_activity` addition to `utils/formatting.py`. All pure-Python, all stdlib, all unit-testable without mocking.
3. **Tool stub** — `tools/climbing.py` registers `verify_custom_fields_setup` (only). One `server.py` import line. This establishes the module so Phase 2 adds to it instead of touching `server.py` again.

Six findings carry the phase:

- The **activity-create endpoint is very likely `POST /athlete/{id}/activities/manual`** (not `/activities` plain), based on forum cookbook references to `/activities/manual/bulk`. `[VERIFIED: forum search]` for `/activities/manual/bulk`; `[ASSUMED]` the singular `/activities/manual` exists. **The spike must confirm.**
- **Custom fields are written as top-level keys on the activity JSON**, not nested under `custom_fields`. `[VERIFIED: forum thread 25515]` This means `CUSTOM_FIELD_KEYS` keys go directly into the PUT body.
- **The custom-field definitions endpoint is the phase's biggest single unknown.** The existing `/athlete/{id}/custom-item` endpoint the codebase already hits is for charts/zones/INPUT_FIELD items — **not** for custom *activity* fields. There is likely a distinct endpoint (candidate: `/athlete/{id}/custom-fields` or `/athlete/{id}/activity-fields`). **The spike must discover which.** If no definitions-list endpoint exists, the fallback is a readback-against-known-activity heuristic.
- **Wellness PUT accepts partial bodies and is upsert-semantics** (merge, not replace). To clear a numeric field, send `-1` — not `null`. `[VERIFIED: forum cookbook]` This is the single most important write-semantics fact; it shapes the Phase 2 `write_wellness_entry` tool.
- **Existing `add_or_update_event` shows the full POST pattern we need to mirror**: `make_intervals_request(..., method="POST", data=event_data)` returns the created record as dict with `id`, and `start_date_local` is the key field for planned/actual linking (`YYYY-MM-DDT00:00:00` format).
- **Activity `type` value for climbing** — forum search confirms `"WeightTraining"` accepts manual-entry payloads with `kg_lifted`-style fields, and there is no native `"Climbing"` type. **Spike confirms** whether `WeightTraining` produces rpeTSS correctly for a climbing activity with `icu_rpe` set, and whether `"Other"` would be a cleaner fit.

**Primary recommendation:** Structure the spike as one async `main()` function with two independent sub-blocks (`spike_wellness_put()` and `spike_activity_create()`) that each return a findings dict. Top-level runner serializes findings to `01-SPIKE-FINDINGS.md` verbatim with copy-pasteable code fences. Every failure mode (404 on manual endpoint, 422 on body, etc.) gets captured in the findings file too — **"failure is a finding."** The utility scaffold proceeds in parallel and has zero dependency on the spike.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Live API write spike (wellness PUT, activity POST) | `scripts/` (ops/dev tier) | `api/client.py` (HTTP layer) | The spike is a dev-time probe, not a shipping artifact. It uses the production HTTP layer to exercise the real contract. |
| Grade regex + validation | `utils/grades.py` (pure utility) | none | Leaf-dependency; no HTTP, no I/O, no enum imports. Imported by Phase 2 write tools and the spike-findings file's own readback check. |
| Domain enums + field spec table | `utils/climbing.py` (pure utility) | imported by `tools/climbing.py`, `utils/grades.py` (for Discipline type hint) | Single source of truth for lowercase string values that must match `CUSTOM_FIELD_KEYS` options. |
| Climbing-activity formatter | `utils/formatting.py` (presentation layer) | consumed by spike-readback + Phase 2 tools | Additive extension; does not touch existing `format_activity_summary`. |
| Custom-field definitions verify | `tools/climbing.py` (MCP tool layer) | `utils/climbing.py` for the expected-field table | MCP-decorated + internal-helper dual-purpose per D-11. |
| `server.py` wiring | Entry point | imports `tools.climbing` | One line; triggers decorator registration on startup. |

**Important tier-correction:** The spike **does not belong in `tests/`** even though it resembles a test. It belongs in `scripts/` because (1) it writes to live data, (2) it must not run in CI, and (3) pytest discovery rules would accidentally pick up a misnamed file in `tests/` (Pitfall #14 inverted). D-01 is correct.

---

## Standard Stack

### Core (all already present — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12+ | StrEnum, `dict[str, X]` syntax, `str \| None` unions | Project requirement `[VERIFIED: pyproject.toml read via codebase/STRUCTURE.md]` |
| FastMCP | `mcp[cli]>=1.4.0` | `@mcp.tool()` decorator for tool registration | Existing singleton at `src/intervals_mcp_server/mcp_instance.py` `[VERIFIED: direct read]` |
| httpx | latest | Async HTTP client backing `make_intervals_request` | All tools route through `api/client.py` — spike does too, per D-02 `[VERIFIED: direct read]` |
| python-dotenv | latest | `.env` loading via `config.py` | Existing pattern — spike inherits this by calling `get_config()` via `make_intervals_request` indirectly `[VERIFIED: config.py read]` |
| pytest + pytest-asyncio | 8.3.5+ / 0.21+ | Tests for `utils/grades.py` and `utils/climbing.py` | Existing — `asyncio_default_fixture_loop_scope = "function"` `[VERIFIED: TESTING.md]` |
| ruff | latest | Formatter + linter, 100-char line length | Existing config in `pyproject.toml` `[VERIFIED: CONVENTIONS.md]` |
| mypy | latest | Type-checking | Existing; new modules must pass `mypy src tests` per AGENTS.md `[VERIFIED: AGENTS.md]` |

### Supporting (new Python code — no new packages)

| Module | Path | Purpose | When to Use |
|--------|------|---------|-------------|
| `FONT_RE`, `FRENCH_SPORT_RE`, `validate_grade` | `utils/grades.py` | Regex + dispatch validator | Called by `verify_custom_fields_setup` optionally; called by Phase 2/3 tools before any PUT/POST |
| `Discipline`, `SessionFocus`, `FieldSpec`, `CUSTOM_FIELD_KEYS` | `utils/climbing.py` | Enums + frozen spec table | Imported everywhere — verify tool, Phase 2/3 write tools, the formatter, tests |
| `format_climbing_activity(activity: dict) -> str` | extension to `utils/formatting.py` | Renders discipline/indoor/focus/grades/sends/attempts/icu_rpe from an activity dict | Spike readback rendering; Phase 2 `enrich_activity_climbing` response rendering |
| `verify_custom_fields_setup` | `tools/climbing.py` | MCP tool + internal helper — lists missing fields by name, blocks writes when missing | Claude diagnostic; Phase 2 pre-write guard |

### Alternatives Considered

| Instead of | Could Use | Tradeoff — why we don't |
|------------|-----------|-----|
| `@dataclass(frozen=True)` for `FieldSpec` | `typing.NamedTuple` | NamedTuple is 1 line shorter but doesn't match the project's existing dataclass pattern (`Config`, `Value`, `Step`, `WorkoutDoc` all use `@dataclass`). **Recommend: `@dataclass(frozen=True)`.** `[VERIFIED: utils/types.py read — every structured type in the project is a dataclass]` |
| `MappingProxyType(dict(...))` for `CUSTOM_FIELD_KEYS` | Plain dict with a comment | `MappingProxyType` gives true read-only semantics at the type level. **Recommend: `MappingProxyType(dict(...))` wrapping the dataclass spec dict.** Prevents accidental mutation by future tools. |
| `enum.Enum` for Discipline / SessionFocus | `enum.StrEnum` | StrEnum auto-provides string identity (`Discipline.BOULDERING == "bouldering"`) which is what D-07/D-08 require for direct comparison against custom-field option strings. **Recommend: StrEnum** — matches existing `TransportAliases(StrEnum)` in `utils/types.py`. `[VERIFIED: types.py line 94]` |
| Pytest-based spike (test that writes to live API) | Standalone script | pytest auto-discovery risks running the spike in CI. Script pattern in `scripts/` is explicit, manually invoked, and clearly non-test. D-01 locks this. |
| `datetime.datetime(2099, 1, 1, 0, 0, 0).isoformat()` for `start_date_local` | Hardcoded string `"2099-01-01T00:00:00"` | Existing `events.py` pattern uses string concatenation: `start_date + "T00:00:00"`. **Match existing pattern** — avoids Pitfall #4 (timezone format drift). `[VERIFIED: events.py line 56]` |

**Installation:** No installs. All dependencies already in `uv.lock`.

**Version verification:** Skipped — phase adds no new packages.

---

## Architecture Patterns

### Phase 1 Component Data Flow

```
                                   Phase 1 deliverables
                                   ====================

  ┌──────────────────────────────────────────────────────────────────────┐
  │  Dev-time (run once)                                                 │
  │                                                                      │
  │   scripts/spike_write_endpoints.py                                   │
  │           │                                                          │
  │           │  uv run scripts/spike_write_endpoints.py                 │
  │           ▼                                                          │
  │   asyncio.run(main())                                                │
  │           │                                                          │
  │           ├──► spike_wellness_put()  ──► make_intervals_request      │
  │           │       (PUT /athlete/{id}/wellness/2099-01-01)            │
  │           │       → readback via GET                                 │
  │           │       → attempt blank/cleanup                            │
  │           │       → findings dict                                    │
  │           │                                                          │
  │           ├──► spike_activity_create() ──► make_intervals_request    │
  │           │       (POST /athlete/{id}/activities/manual OR variant)  │
  │           │       → readback via GET /activity/{id}                  │
  │           │       → attempt DELETE (or record "no delete endpoint")  │
  │           │       → findings dict                                    │
  │           │                                                          │
  │           └──► write_findings_md(wellness, activity)                 │
  │                   → 01-SPIKE-FINDINGS.md                             │
  │                                                                      │
  └──────────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────────┐
  │  Ship-time utilities (additive, no HTTP)                             │
  │                                                                      │
  │   utils/climbing.py                utils/grades.py                   │
  │   ┌─────────────────────┐          ┌──────────────────────┐          │
  │   │ Discipline(StrEnum) │◄─────────│ validate_grade(      │          │
  │   │ SessionFocus(StrE)  │          │   grade, discipline) │          │
  │   │ @dataclass FieldSpec│          │                      │          │
  │   │ CUSTOM_FIELD_KEYS   │          │ FONT_RE              │          │
  │   └─────────────────────┘          │ FRENCH_SPORT_RE      │          │
  │          ▲                         └──────────────────────┘          │
  │          │                                  ▲                        │
  │          │                                  │                        │
  │          │       utils/formatting.py        │                        │
  │          │       ┌──────────────────────────┴────┐                   │
  │          └──────►│ format_climbing_activity(     │                   │
  │                  │   activity: dict) -> str      │                   │
  │                  │ (additive — does NOT touch    │                   │
  │                  │  format_activity_summary)     │                   │
  │                  └───────────────────────────────┘                   │
  │                                                                      │
  └──────────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────────┐
  │  MCP tool registration                                               │
  │                                                                      │
  │   tools/climbing.py                                                  │
  │   ┌────────────────────────────────────────────────────┐             │
  │   │ from intervals_mcp_server.mcp_instance import mcp  │             │
  │   │ from ..utils.climbing import CUSTOM_FIELD_KEYS     │             │
  │   │ from ..utils.validation import resolve_athlete_id  │             │
  │   │                                                    │             │
  │   │ async def _verify_custom_fields_setup_impl(...)    │             │
  │   │     ↑ internal helper (used by Phase 2 pre-write)  │             │
  │   │                                                    │             │
  │   │ @mcp.tool()                                        │             │
  │   │ async def verify_custom_fields_setup(...)          │             │
  │   │     return await _verify_custom_fields_setup_impl()│             │
  │   └────────────────────────────────────────────────────┘             │
  │                                                                      │
  │                        ▲                                             │
  │                        │ one import added                            │
  │                                                                      │
  │   server.py   (gains ONE line next to existing tool imports)         │
  │   ┌────────────────────────────────────────────────────┐             │
  │   │ from intervals_mcp_server.tools.climbing import (  │             │
  │   │     verify_custom_fields_setup,                    │             │
  │   │ )  # pylint: disable=wrong-import-position         │             │
  │   │    # noqa: E402                                    │             │
  │   └────────────────────────────────────────────────────┘             │
  │                                                                      │
  └──────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure (deltas only)

```
intervals-mcp-server/
├── scripts/                               ← NEW directory if not present
│   └── spike_write_endpoints.py           ← NEW (Phase 1 only artifact here)
├── src/intervals_mcp_server/
│   ├── server.py                          ← +1 import line
│   ├── tools/
│   │   └── climbing.py                    ← NEW (verify_custom_fields_setup only)
│   └── utils/
│       ├── grades.py                      ← NEW
│       ├── climbing.py                    ← NEW
│       └── formatting.py                  ← +1 function (format_climbing_activity)
├── tests/
│   ├── test_grades.py                     ← NEW
│   └── test_climbing.py                   ← NEW
├── .planning/phases/01-foundation-and-write-path-spike/
│   └── 01-SPIKE-FINDINGS.md               ← NEW (output of spike run)
└── README.md                              ← +1 section ("Climbing setup")
```

### Pattern 1: Async tool module with mcp registration

**Source:** direct read of `src/intervals_mcp_server/tools/wellness.py` `[VERIFIED]`

```python
"""
Climbing-related MCP tools for Intervals.icu.

This module contains tools for verifying the custom-field prerequisites
and (later phases) writing climbing metadata to activities.
"""

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.climbing import CUSTOM_FIELD_KEYS
from intervals_mcp_server.utils.validation import resolve_athlete_id

# Import mcp instance from shared module for tool registration
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401

config = get_config()


async def _verify_custom_fields_setup_impl(
    athlete_id: str | None = None,
    api_key: str | None = None,
) -> tuple[bool, list[str], str]:
    """Internal helper. Returns (ok, missing_field_keys, human_message)."""
    # …implementation that hits the custom-field-definitions endpoint…


@mcp.tool()
async def verify_custom_fields_setup(
    athlete_id: str | None = None,
    api_key: str | None = None,
) -> str:
    """Verify that required Intervals.icu climbing custom fields are defined.

    Before the climbing tools can write discipline, grades, session focus,
    sends, and attempts, the following custom fields must exist in the
    athlete's Intervals.icu account settings:

      - discipline (select: bouldering, sport_lead, top_rope, trad)
      - indoor (bool)
      - session_focus (select: power, endurance, technique, projecting, mileage)
      - top_grade_sent (text)
      - top_grade_attempted (text)
      - sends (integer)
      - attempts (integer)

    See the README section "Climbing setup — required Intervals.icu custom
    fields" for the full table and setup instructions.

    Args:
        athlete_id: The Intervals.icu athlete ID (optional, uses ATHLETE_ID
            from .env if not provided).
        api_key: The Intervals.icu API key (optional, uses API_KEY from .env
            if not provided).

    Returns:
        A human-readable string reporting which required fields are defined
        and which (if any) are missing by name.
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg
    ok, missing, message = await _verify_custom_fields_setup_impl(
        athlete_id_to_use, api_key
    )
    return message
```

**Pattern notes:**
- `# noqa: F401` on the `mcp` import — matches existing modules (`wellness.py` line 13) `[VERIFIED]`
- `config = get_config()` at module top — matches existing modules `[VERIFIED]`
- Internal helper is a plain `async def` (not `@mcp.tool()`-decorated). D-11 says one implementation, two call sites; the MCP-decorated wrapper delegates.
- Return from internal helper is a tuple `(ok, missing, message)` so Phase 2's write tools can branch on `ok` *without* re-parsing a prose string. This is the "one implementation, two call sites" discipline in action.

### Pattern 2: Existing POST with body — what the spike mirrors

**Source:** `src/intervals_mcp_server/tools/events.py` `add_or_update_event` `[VERIFIED: direct read]`

```python
# From events.py — this is the template for the spike's activity POST call:
url = f"/athlete/{athlete_id}/events"       # Spike changes to /activities/manual
if event_id:                                 # (spike does NOT provide an id)
    url += f"/{event_id}"
result = await make_intervals_request(
    url=url,
    api_key=api_key,
    data=event_data,                         # Spike: dict with type, start_date_local, moving_time
    method="PUT" if event_id else "POST",    # Spike: always POST for create
)
# …
# Response handling:
if isinstance(result, dict) and "error" in result:
    error_message = result.get("message", "Unknown error")
    return f"Error creating activity: {error_message}"
# …success path: result["id"] is the new activity id
```

Existing `_prepare_event_data` shows the exact `start_date_local` format the spike must use `[VERIFIED: events.py line 56]`:

```python
return {
    "start_date_local": start_date + "T00:00:00",   # ← "YYYY-MM-DDT00:00:00", no offset
    "category": "WORKOUT",
    "name": name,
    "description": str(workout_doc) if workout_doc else None,
    "type": resolved_workout_type,
    "moving_time": moving_time,
    "distance": distance,
}
```

**This format is non-negotiable for Phase 3** per Pitfall #4 (timezone mismatch breaks event↔activity linking). The spike must use exactly this shape so Phase 3 inherits a correct pattern.

### Pattern 3: Existing PUT — what the spike mirrors for wellness

There is no existing `wellness` PUT tool in the codebase — that's the point of the spike. But the pattern is the same as `events.py` with method PUT and a date-scoped URL:

```python
# Spike pattern for PUT /athlete/{id}/wellness/2099-01-01
result = await make_intervals_request(
    url=f"/athlete/{athlete_id}/wellness/{date}",   # date is "YYYY-MM-DD"
    api_key=api_key,
    data={"sleepSecs": 28800, "soreness": 3},       # partial body — upsert test
    method="PUT",
)
# Spike then GETs /athlete/{id}/wellness?oldest={date}&newest={date}
# and records: which keys round-tripped, whether unspecified keys were preserved
# or cleared, what happens when you send -1 vs null for numeric fields.
```

### Anti-Patterns to Avoid

- **Do not monkeypatch the spike via pytest.** The spike is in `scripts/`, not `tests/`. It accepts `--athlete-id` and `--api-key` flags (or reads env) but never imports `monkeypatch`. Keeping it out of `tests/` prevents accidental CI execution (inverted Pitfall #14).
- **Do not create a custom HTTP client in the spike.** D-02: use `make_intervals_request`. This exercises the exact error-handling path that Phase 2/3 tools will use — if there's a bug at that boundary, the spike surfaces it.
- **Do not normalize case in `validate_grade`.** D-06: case is the cross-scale guard. Lowercasing inputs before regex-matching defeats the entire purpose of the strict uppercase/lowercase distinction (Pitfall #3).
- **Do not put climbing types in `utils/types.py`.** D-16: `types.py` is for workout/step types. Climbing types go in `utils/climbing.py`. Grep discoverability — "climbing" must return exactly one utility file.
- **Do not import `_parse_activities_from_result` from `tools/activities.py`.** D-18 / Pitfall #11. If the spike or verify tool needs activity-list parsing, either re-implement locally or promote to `utils/` with a public name.
- **Do not touch `format_activity_summary`.** D-20 / Pitfall #12. `format_climbing_activity` is a new function in the same file, additive only.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP auth + retry for Intervals.icu | Custom `httpx.AsyncClient()` in the spike | `make_intervals_request()` from `api/client.py` | Already handles BasicAuth with `API_KEY` username, client-closed retry, JSON-decode fallback, uniform error dict. D-02 locks this. |
| Athlete-ID resolution with env fallback | Read `os.getenv("ATHLETE_ID")` in the spike | `resolve_athlete_id()` from `utils/validation.py` | Pattern exists and is tested. Spike should call `get_config()` once and pass `config.athlete_id` through. |
| Date-string validation | Regex against `YYYY-MM-DD` inline in spike | `validate_date()` from `utils/validation.py` | Exists, raises `ValueError` with a good message. |
| Dict-to-string formatter for spike readback | Inline `f"..."` template in the spike | `format_climbing_activity()` — a new sibling to `format_wellness_entry` | This is one of the Phase 1 deliverables. The spike's readback *is* its first consumer. |
| Writing "are these fields defined?" logic from scratch | Comparing strings manually | `CUSTOM_FIELD_KEYS` frozen dict + a small diff function | Single source of truth (D-10). Phase 2/3 tools consume the same dict. |

**Key insight:** Phase 1's biggest do-not-hand-roll item is the **spike itself**. It must use production code paths (`make_intervals_request`, `resolve_athlete_id`, `validate_date`, `format_climbing_activity`) so the findings file captures behaviour of the exact call chain Phase 2/3 will use. Using alternative code paths in the spike would produce findings that don't generalize.

---

## Runtime State Inventory

> Phase 1 is purely additive — no rename, no refactor, no migration. Inventory still completed per rename-aware discipline.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — Intervals.icu is source of truth; no local DB. Spike writes to live Intervals.icu at a far-future date (2099-01-01). | After spike run, manual cleanup checklist in `01-SPIKE-FINDINGS.md` if DELETE endpoint unavailable. |
| Live service config | None — no CI env changes, no secrets added. Spike reuses existing `API_KEY` + `ATHLETE_ID` env vars. | None. |
| OS-registered state | None — not a service, not a daemon, no pm2/launchd/systemd/Task Scheduler entries. | None. |
| Secrets/env vars | `API_KEY` and `ATHLETE_ID` already exist in `.env` (loaded by `get_config()`). Spike does **not** introduce new env vars. | None — existing vars reused. |
| Build artifacts / installed packages | None — no dependency changes; Phase 1 adds only Python source files that the existing `hatch` build picks up automatically. | Verify `pytest --collect-only` count increases by exactly the two new test files (Pitfall #14). |

**Nothing found in any category** other than the explicit live-write side effect to Intervals.icu at 2099-01-01, which is exactly the scoped risk the phase is budgeted for (D-03).

---

## Common Pitfalls

This phase is explicitly shaped around the PITFALLS.md guards the CONTEXT.md singles out. Mapping:

### Pitfall #2 — Custom Fields Silently Succeed But Store Nothing

**What goes wrong:** Writing a custom field whose key isn't defined in the athlete account returns HTTP 200, no error, and the field doesn't appear on readback.

**How this phase guards it:**
- `verify_custom_fields_setup` reads field definitions and hard-blocks if any of the 7 required keys are missing (D-12).
- Spike readback step for both wellness PUT and activity POST: after every write, GET the resource and assert the written keys appear. This becomes the canonical "readback is mandatory" pattern Phase 2/3 inherits.
- `CUSTOM_FIELD_KEYS` is the single source of truth (D-10) — no drift between tool code, README, and docstring possible without a test failure.

**Grep-verifiable acceptance:** `grep -r "verify_custom_fields_setup" src/` returns both `tools/climbing.py` (definition) and an import in `server.py`. Phase 2+ grep for it at write-tool call sites.

### Pitfall #3 — Grade Scale Contamination

**What goes wrong:** Font `6A` (boulder) and French sport `6a` (route) look nearly identical; free text lets the LLM or user mix them.

**How this phase guards it:**
- D-06: strict case, no normalization. `FONT_RE = r'^[3-9][A-C](\+)?$'` and `FRENCH_SPORT_RE = r'^[3-9][abc](\+)?$'` — uppercase vs lowercase is the cross-scale guard.
- `validate_grade(grade, discipline)` dispatches on `Discipline` enum: bouldering → Font only; sport_lead/top_rope/trad → French sport only.
- Error message names the expected scale: `"Expected Font grade (uppercase, e.g. 6A, 7B+) for discipline=bouldering, got '6a'."`

**Grep-verifiable acceptance:** `tests/test_grades.py` covers the 4-quadrant matrix (valid/invalid × Font/French) and 3 cross-scale rejection cases.

### Pitfall #5 — MCP Statelessness

**What goes wrong:** A multi-step wizard that stores partial state between tool calls.

**How this phase guards it:**
- `verify_custom_fields_setup` is a single-shot read → report. No state. No correlation ID.
- Spike script is process-local; no module-level mutable state survives past `asyncio.run(main())`.

**Grep-verifiable acceptance:** `grep -r "global\|_state" src/intervals_mcp_server/tools/climbing.py src/intervals_mcp_server/utils/climbing.py` returns nothing.

### Pitfall #11 — Private-Helper Coupling to Sibling Tool Modules

**What goes wrong:** `tools/climbing.py` imports `_parse_activities_from_result` from `tools/activities.py`; later refactor in activities.py silently breaks climbing.

**How this phase guards it:**
- D-18: no `_`-prefixed imports from sibling tool modules. If climbing needs shared logic, it goes in `utils/` with a public name.
- Phase 1 doesn't currently need any sibling logic — `verify_custom_fields_setup` only reads the custom-field definitions endpoint, no activity list parsing.

**Grep-verifiable acceptance:**
```bash
grep -E "^from intervals_mcp_server\.tools\.(activities|wellness|events|custom_items) import _" \
  src/intervals_mcp_server/tools/climbing.py src/intervals_mcp_server/utils/climbing.py \
  src/intervals_mcp_server/utils/grades.py
# Expected: empty (no match)
```

### Pitfall #12 — Regressing Shared Utilities

**What goes wrong:** Extending `format_activity_summary()` for climbing breaks every existing consumer because string-contains tests don't catch format drift.

**How this phase guards it:**
- D-15 / D-20: `format_climbing_activity` is a new function. `format_activity_summary` is untouched.
- `utils/types.py` and `utils/validation.py` are not modified (D-16).
- Full existing test suite must pass unchanged before merge — no snapshot updates allowed in Phase 1 for any pre-existing test file.

**Grep-verifiable acceptance:** `git diff main -- src/intervals_mcp_server/utils/types.py src/intervals_mcp_server/utils/validation.py` is empty at Phase 1 end.

### Pitfall #14 — Test Drift / CI Blindspot

**What goes wrong:** New test file doesn't follow `test_*.py` pattern, or sits outside `tests/`, and is invisible to `pytest --collect-only`.

**How this phase guards it:**
- D-19: both new test files named `test_grades.py` and `test_climbing.py`, placed in `tests/`.
- Acceptance criterion: `pytest --collect-only` count increases by exactly the expected count (document the delta in PLAN.md).

**Grep-verifiable acceptance:**
```bash
pytest --collect-only tests/test_grades.py tests/test_climbing.py -q
# Expected: non-empty collection of test functions
```

---

## Code Examples

Verified patterns from the existing codebase. Every snippet below is traced back to a direct file read.

### Spike script skeleton (recommended structure)

```python
#!/usr/bin/env python3
"""
Spike: confirm write-path contracts for Intervals.icu wellness + activities.

NOT A PYTEST TEST. Writes to live Intervals.icu at a far-future date and
attempts cleanup. Output is written to:

    .planning/phases/01-foundation-and-write-path-spike/01-SPIKE-FINDINGS.md

Run:
    uv run scripts/spike_write_endpoints.py
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

# Ensure src/ is on path (mirrors tests/ pattern in test_make_intervals_request.py)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.formatting import format_climbing_activity

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("spike")

SPIKE_DATE = "2099-01-01"  # far-future; no real user data on that date
FINDINGS_PATH = Path(__file__).resolve().parents[1] / ".planning" / "phases" / \
    "01-foundation-and-write-path-spike" / "01-SPIKE-FINDINGS.md"


async def spike_wellness_put(athlete_id: str) -> dict[str, Any]:
    """Exercise PUT /athlete/{id}/wellness/{date} with partial body; readback; cleanup."""
    findings: dict[str, Any] = {"endpoint": f"/athlete/{athlete_id}/wellness/{SPIKE_DATE}"}
    # 1. Write minimal body
    write_body = {"sleepSecs": 28800, "soreness": 3}
    write_result = await make_intervals_request(
        url=f"/athlete/{athlete_id}/wellness/{SPIKE_DATE}",
        data=write_body, method="PUT",
    )
    findings["write_body_sent"] = write_body
    findings["write_response"] = write_result
    # 2. Readback
    readback = await make_intervals_request(
        url=f"/athlete/{athlete_id}/wellness",
        params={"oldest": SPIKE_DATE, "newest": SPIKE_DATE},
    )
    findings["readback"] = readback
    # 3. Partial-body upsert test: write a DIFFERENT key and re-read
    await make_intervals_request(
        url=f"/athlete/{athlete_id}/wellness/{SPIKE_DATE}",
        data={"fatigue": 5}, method="PUT",
    )
    readback2 = await make_intervals_request(
        url=f"/athlete/{athlete_id}/wellness",
        params={"oldest": SPIKE_DATE, "newest": SPIKE_DATE},
    )
    findings["readback_after_second_write"] = readback2
    # Human-readable assertion: did sleepSecs survive the second write?
    findings["upsert_confirmed"] = (
        isinstance(readback2, (dict, list))
        and "sleepSecs" in (readback2[0] if isinstance(readback2, list) else readback2)
    )
    # 4. Cleanup: try to clear numeric fields with -1 per forum cookbook
    await make_intervals_request(
        url=f"/athlete/{athlete_id}/wellness/{SPIKE_DATE}",
        data={"sleepSecs": -1, "soreness": -1, "fatigue": -1}, method="PUT",
    )
    return findings


async def spike_activity_create(athlete_id: str) -> dict[str, Any]:
    """Exercise POST /athlete/{id}/activities/manual; readback; cleanup."""
    findings: dict[str, Any] = {}
    # Candidate endpoint #1: /activities/manual
    create_body = {
        "start_date_local": f"{SPIKE_DATE}T00:00:00",   # matches events.py pattern
        "type": "WeightTraining",                        # per forum search
        "name": "SPIKE — DELETE ME",
        "moving_time": 3600,
    }
    result = await make_intervals_request(
        url=f"/athlete/{athlete_id}/activities/manual",
        data=create_body, method="POST",
    )
    findings["endpoint_tried"] = f"/athlete/{athlete_id}/activities/manual"
    findings["create_body_sent"] = create_body
    findings["create_response"] = result
    # If 404, try the plain /activities endpoint as fallback
    if isinstance(result, dict) and result.get("status_code") == 404:
        findings["fallback_tried"] = f"/athlete/{athlete_id}/activities"
        result = await make_intervals_request(
            url=f"/athlete/{athlete_id}/activities",
            data=create_body, method="POST",
        )
        findings["fallback_response"] = result
    # Capture the id for cleanup
    activity_id = result.get("id") if isinstance(result, dict) else None
    findings["activity_id"] = activity_id
    if activity_id:
        # Readback
        readback = await make_intervals_request(url=f"/activity/{activity_id}")
        findings["readback"] = readback
        # Now try to write a custom field via PUT and verify it sticks
        findings["custom_field_write"] = await make_intervals_request(
            url=f"/activity/{activity_id}",
            data={"discipline": "bouldering", "icu_rpe": 6},
            method="PUT",
        )
        readback2 = await make_intervals_request(url=f"/activity/{activity_id}")
        findings["readback_after_custom_field_put"] = readback2
        findings["custom_field_roundtripped"] = (
            isinstance(readback2, dict) and readback2.get("discipline") == "bouldering"
        )
        # Cleanup: try DELETE
        del_result = await make_intervals_request(
            url=f"/activity/{activity_id}", method="DELETE",
        )
        findings["delete_response"] = del_result
        findings["delete_available"] = not (
            isinstance(del_result, dict) and del_result.get("error")
        )
    return findings


def write_findings(wellness: dict[str, Any], activity: dict[str, Any]) -> None:
    """Dump findings to 01-SPIKE-FINDINGS.md with copy-pasteable code fences."""
    FINDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    content = [
        "# Spike findings — write-path probes\n",
        f"**Run date:** {SPIKE_DATE} (target date used in live API calls)\n",
        "## Wellness PUT\n",
        "```json\n" + json.dumps(wellness, indent=2, default=str) + "\n```\n",
        "## Activity POST\n",
        "```json\n" + json.dumps(activity, indent=2, default=str) + "\n```\n",
        "## Manual cleanup (if DELETE unavailable)\n",
        f"- Wellness at {SPIKE_DATE}: cleared with `-1` values in spike; verify in UI.\n",
        f"- Activity id: {activity.get('activity_id')} — if DELETE returned error, delete manually via Intervals.icu web UI.\n",
    ]
    FINDINGS_PATH.write_text("".join(content), encoding="utf-8")


async def main() -> None:
    config = get_config()
    if not config.athlete_id or not config.api_key:
        logger.error("ATHLETE_ID and API_KEY must be set in .env")
        sys.exit(1)
    logger.info("Spike against athlete=%s at date=%s", config.athlete_id, SPIKE_DATE)
    wellness = await spike_wellness_put(config.athlete_id)
    activity = await spike_activity_create(config.athlete_id)
    write_findings(wellness, activity)
    logger.info("Wrote %s", FINDINGS_PATH)


if __name__ == "__main__":
    asyncio.run(main())
```

**Why this shape:**
- Mirrors the `sys.path.insert` pattern from `tests/test_make_intervals_request.py` so the spike runs against `src/` without `uv sync --editable` gymnastics.
- One `async def main()` with two sub-probes (D-01). Each sub-probe returns a findings dict.
- Findings writer is separated — if a probe raises mid-way, the caller can wrap in try/except and still persist partial findings.
- Every API call returns through `make_intervals_request`, so every call uses the production auth + error path (D-02).

### `utils/climbing.py` — enum + FieldSpec + frozen dict

```python
"""
Climbing-domain types and custom-field specification.

This module is the single source of truth for:
- Discipline and session-focus enums used across the climbing tools.
- The Intervals.icu custom-field key spec (`CUSTOM_FIELD_KEYS`) that the
  user must pre-define in their athlete account before the climbing
  tools can write them.

The README section "Climbing setup — required Intervals.icu custom fields"
mirrors `CUSTOM_FIELD_KEYS`. A test asserts they match; if you change the
spec here, update the README (and vice versa).
"""

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Literal


class Discipline(StrEnum):
    """Climbing discipline. Values match the `discipline` custom-field options."""

    BOULDERING = "bouldering"
    SPORT_LEAD = "sport_lead"
    TOP_ROPE = "top_rope"
    TRAD = "trad"


class SessionFocus(StrEnum):
    """Session focus. Values match the `session_focus` custom-field options."""

    POWER = "power"
    ENDURANCE = "endurance"
    TECHNIQUE = "technique"
    PROJECTING = "projecting"
    MILEAGE = "mileage"


FieldType = Literal["select", "bool", "text", "integer"]


@dataclass(frozen=True)
class FieldSpec:
    """Specification of one required Intervals.icu custom activity field."""

    key: str
    field_type: FieldType
    options: tuple[str, ...] = ()  # non-empty only for `select` fields
    description: str = ""


CUSTOM_FIELD_KEYS: MappingProxyType[str, FieldSpec] = MappingProxyType({
    "discipline": FieldSpec(
        key="discipline",
        field_type="select",
        options=tuple(d.value for d in Discipline),
        description="Climbing discipline (bouldering / sport_lead / top_rope / trad).",
    ),
    "indoor": FieldSpec(
        key="indoor",
        field_type="bool",
        description="True if the session was indoors (gym), False if outdoors.",
    ),
    "session_focus": FieldSpec(
        key="session_focus",
        field_type="select",
        options=tuple(f.value for f in SessionFocus),
        description="Primary training intent for this session.",
    ),
    "top_grade_sent": FieldSpec(
        key="top_grade_sent",
        field_type="text",
        description="Hardest grade sent this session (Font for boulders, French sport for routes).",
    ),
    "top_grade_attempted": FieldSpec(
        key="top_grade_attempted",
        field_type="text",
        description="Hardest grade attempted this session.",
    ),
    "sends": FieldSpec(
        key="sends",
        field_type="integer",
        description="Total successful sends (clean completions) this session.",
    ),
    "attempts": FieldSpec(
        key="attempts",
        field_type="integer",
        description="Total attempts (including sends) this session.",
    ),
})
```

**Why this shape:**
- `StrEnum` values are lowercase (D-07/D-08) and used directly to populate `options` tuples so a rename of an enum member propagates to `CUSTOM_FIELD_KEYS` automatically. The alignment test then just asserts `tuple(Discipline)[i].value == CUSTOM_FIELD_KEYS["discipline"].options[i]` for each i — if they drift, the test fails loudly.
- `MappingProxyType` wraps the dict to make it truly read-only — any code that tries to mutate `CUSTOM_FIELD_KEYS["discipline"] = ...` raises `TypeError` at runtime. `[VERIFIED: Python 3.12 stdlib behaviour]`
- `FieldSpec` matches existing dataclass patterns in the project (`Value`, `Step`, `WorkoutDoc` in `utils/types.py`). `frozen=True` signals intent. `[VERIFIED: utils/types.py read]`
- `Literal[...]` for `field_type` gives mypy a tight type; invalid field types fail at `mypy src tests`.

### `utils/grades.py` — regex + dispatch validator

```python
"""
Climbing grade validation for Font (bouldering) and French sport (routes).

Strict case is the cross-scale guard — Font is uppercase, French sport is
lowercase. A grade that matches the wrong scale for the declared discipline
is rejected with an error naming the expected scale.

No normalization. No grade arithmetic. String-in → string-out.
"""

import re

from intervals_mcp_server.utils.climbing import Discipline

# Font bouldering: 3A .. 9C+ (bare uppercase letter, optional '+')
# Extended low end to include 1 and 2 which are plain numeric — this is purely
# defensive; Timo's range starts much higher. Adjust top end if user's range grows.
FONT_RE = re.compile(r"^[3-9][A-C]\+?$|^[12]$")

# French sport: 3a .. 9c+ (lowercase letter, optional '+')
FRENCH_SPORT_RE = re.compile(r"^[3-9][abc]\+?$")


_ROUTE_DISCIPLINES = frozenset({Discipline.SPORT_LEAD, Discipline.TOP_ROPE, Discipline.TRAD})


def validate_grade(grade: str, discipline: Discipline) -> str:
    """Validate a climbing grade against the declared discipline.

    Args:
        grade: The grade string as entered by the user (e.g. "6A", "6a+").
        discipline: The declared climbing discipline.

    Returns:
        The validated grade string (unchanged — no normalization).

    Raises:
        ValueError: If the grade does not match the expected scale for the
            discipline. The message names the expected scale so Claude (and
            the user) get a clear correction hint.
    """
    if discipline is Discipline.BOULDERING:
        if not FONT_RE.match(grade):
            raise ValueError(
                f"Expected Font grade (uppercase, e.g. 6A, 7B+) for "
                f"discipline=bouldering, got '{grade}'."
            )
    elif discipline in _ROUTE_DISCIPLINES:
        if not FRENCH_SPORT_RE.match(grade):
            raise ValueError(
                f"Expected French sport grade (lowercase, e.g. 6a, 7b+) for "
                f"discipline={discipline.value}, got '{grade}'."
            )
    else:
        # Defensive branch — should be unreachable with StrEnum, but mypy
        # doesn't know that since Discipline could in theory gain members.
        raise ValueError(f"Unknown discipline: {discipline!r}")
    return grade
```

**Why this shape:**
- Regex pre-compiled at module import (negligible perf cost, cleaner call site).
- `_ROUTE_DISCIPLINES` as a `frozenset` of enum members — `in` check is O(1) and reads as domain knowledge.
- Returns the input unchanged — no normalization. This is load-bearing per D-06.
- `ValueError` with user-facing message — matches existing pattern in `utils/validation.py` (`validate_date`, `validate_athlete_id`). `[VERIFIED: direct read]`

### `utils/formatting.py` — additive `format_climbing_activity`

```python
# Added at the end of utils/formatting.py — do not modify existing functions.

def format_climbing_activity(activity: dict[str, Any]) -> str:
    """Format a climbing activity (custom fields + RPE) into a readable string.

    Renders only the fields Phase 1 establishes:
    discipline, indoor, session_focus, top_grade_sent, top_grade_attempted,
    sends, attempts, icu_rpe. Activities without these fields render
    mostly-N/A lines, which is exactly what we want for a readback of a
    freshly-created activity before enrichment.

    Args:
        activity: Dict shaped like an Intervals.icu activity JSON. Custom
            fields are expected as top-level keys (matches the API shape).

    Returns:
        A formatted multi-line string.
    """
    indoor = activity.get("indoor")
    indoor_str = "Yes" if indoor is True else "No" if indoor is False else "N/A"

    rpe = activity.get("icu_rpe")
    rpe_str = f"{rpe}/10" if isinstance(rpe, (int, float)) else "N/A"

    return (
        f"Climbing Activity\n"
        f"  ID: {activity.get('id', 'N/A')}\n"
        f"  Name: {activity.get('name', 'Unnamed')}\n"
        f"  Date: {activity.get('start_date_local', 'Unknown')}\n"
        f"  Discipline: {activity.get('discipline', 'N/A')}\n"
        f"  Indoor: {indoor_str}\n"
        f"  Session focus: {activity.get('session_focus', 'N/A')}\n"
        f"  Top grade sent: {activity.get('top_grade_sent', 'N/A')}\n"
        f"  Top grade attempted: {activity.get('top_grade_attempted', 'N/A')}\n"
        f"  Sends: {activity.get('sends', 'N/A')}\n"
        f"  Attempts: {activity.get('attempts', 'N/A')}\n"
        f"  RPE: {rpe_str}\n"
    )
```

**Why this shape:**
- Mirrors `format_activity_summary` shape — f-string block, dict `.get()` with default, no complex branching `[VERIFIED: formatting.py read]`.
- Does NOT use `_KeyTracker` — the phase-1 field set is small and fixed; tracker is only useful when an `include_all_fields` flag needs to surface unknown keys (as in `format_wellness_entry`).
- Returns a trailing newline, matching `format_activity_summary` which ends with a newline after `File Type:`. `[VERIFIED: formatting.py line 117]`
- Custom fields accessed as top-level keys — matches the API shape `[VERIFIED: forum thread 25515]`.

### `tests/test_grades.py` — coverage matrix

```python
"""Unit tests for utils/grades.py."""

import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

import pytest  # pylint: disable=wrong-import-position

from intervals_mcp_server.utils.climbing import Discipline  # pylint: disable=wrong-import-position
from intervals_mcp_server.utils.grades import (  # pylint: disable=wrong-import-position
    FONT_RE,
    FRENCH_SPORT_RE,
    validate_grade,
)


@pytest.mark.parametrize("grade", ["3A", "6A", "6A+", "7B", "7C+", "8A", "9C+"])
def test_font_re_accepts_canonical_grades(grade: str) -> None:
    assert FONT_RE.match(grade) is not None


@pytest.mark.parametrize("grade", ["6a", "6A/6B", "V5", "hard 6A", "6D", "6", "6A +"])
def test_font_re_rejects_non_canonical(grade: str) -> None:
    assert FONT_RE.match(grade) is None


@pytest.mark.parametrize("grade", ["3a", "6a", "6a+", "7b", "7c+", "8a", "9c+"])
def test_french_sport_re_accepts_canonical_grades(grade: str) -> None:
    assert FRENCH_SPORT_RE.match(grade) is not None


@pytest.mark.parametrize("grade", ["6A", "5.11a", "6a/6b", "6d", "6a +"])
def test_french_sport_re_rejects_non_canonical(grade: str) -> None:
    assert FRENCH_SPORT_RE.match(grade) is None


def test_validate_grade_font_on_boulder_ok() -> None:
    assert validate_grade("6A+", Discipline.BOULDERING) == "6A+"


def test_validate_grade_french_on_route_ok() -> None:
    assert validate_grade("6a+", Discipline.SPORT_LEAD) == "6a+"
    assert validate_grade("7b", Discipline.TOP_ROPE) == "7b"
    assert validate_grade("6c", Discipline.TRAD) == "6c"


def test_validate_grade_font_on_route_rejected() -> None:
    with pytest.raises(ValueError, match="French sport"):
        validate_grade("6A", Discipline.SPORT_LEAD)


def test_validate_grade_french_on_boulder_rejected() -> None:
    with pytest.raises(ValueError, match="Font"):
        validate_grade("6a", Discipline.BOULDERING)


def test_validate_grade_gibberish_rejected() -> None:
    with pytest.raises(ValueError):
        validate_grade("hard 6A", Discipline.BOULDERING)
```

**Why this shape:**
- `sys.path.insert` + `os.environ.setdefault` at top — matches `tests/test_server.py` and `tests/test_make_intervals_request.py` `[VERIFIED]`.
- `@pytest.mark.parametrize` for table-driven assertions — keeps the cross-scale matrix explicit.
- `match="French sport"` / `match="Font"` — asserts the *expected scale name* appears in the error, which is the user-facing assertion Phase 2 relies on.

### `tests/test_climbing.py` — enum + spec alignment

```python
"""Unit tests for utils/climbing.py — enum ↔ CUSTOM_FIELD_KEYS alignment."""

import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

from intervals_mcp_server.utils.climbing import (  # pylint: disable=wrong-import-position
    CUSTOM_FIELD_KEYS,
    Discipline,
    FieldSpec,
    SessionFocus,
)


def test_discipline_values_are_lowercase_snake_case() -> None:
    for d in Discipline:
        assert d.value.islower() or "_" in d.value
        assert d.value == d.value.strip()


def test_session_focus_values_are_lowercase() -> None:
    for f in SessionFocus:
        assert f.value.islower()


def test_discipline_options_match_custom_field_spec() -> None:
    spec_options = CUSTOM_FIELD_KEYS["discipline"].options
    assert spec_options == tuple(d.value for d in Discipline)


def test_session_focus_options_match_custom_field_spec() -> None:
    spec_options = CUSTOM_FIELD_KEYS["session_focus"].options
    assert spec_options == tuple(f.value for f in SessionFocus)


def test_custom_field_keys_covers_seven_fields() -> None:
    assert set(CUSTOM_FIELD_KEYS.keys()) == {
        "discipline", "indoor", "session_focus",
        "top_grade_sent", "top_grade_attempted",
        "sends", "attempts",
    }


def test_custom_field_spec_types_are_valid() -> None:
    for spec in CUSTOM_FIELD_KEYS.values():
        assert isinstance(spec, FieldSpec)
        assert spec.field_type in {"select", "bool", "text", "integer"}
        if spec.field_type == "select":
            assert spec.options, f"select field {spec.key} must have options"
        else:
            assert spec.options == (), f"non-select field {spec.key} must not have options"


def test_custom_field_keys_is_read_only() -> None:
    import pytest
    with pytest.raises(TypeError):
        CUSTOM_FIELD_KEYS["new_field"] = FieldSpec(key="new_field", field_type="text")  # type: ignore[index]
```

**Why this shape:**
- Direct alignment assertions — the test fails if anyone renames a `Discipline` member without updating the spec.
- `test_custom_field_keys_is_read_only` locks `MappingProxyType` behaviour — catches anyone tempted to mutate the spec at runtime.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `typing.Optional[X]` | `X \| None` | Python 3.10 PEP 604 | All new code uses `X \| None`. Existing codebase mostly uses `\|`; a few legacy `Optional[X]` appear in `utils/types.py` but are being replaced organically. New code in Phase 1: **always `X \| None`**. |
| `enum.Enum` + `.value` comparisons | `enum.StrEnum` with identity comparisons | Python 3.11 | `TransportAliases` already uses `StrEnum`. All new enums (Discipline, SessionFocus) use `StrEnum` per D-07/D-08. |
| Plain `dict` for frozen lookups | `types.MappingProxyType` | stdlib (always available) | `CUSTOM_FIELD_KEYS` uses `MappingProxyType` for true read-only semantics. `[VERIFIED: Python 3.12 docs]` |
| `from typing import List, Dict` | `list[X]`, `dict[str, X]` | Python 3.9 PEP 585 | New code: always PEP 585. Existing `utils/types.py` uses old-style; don't touch (D-16). |

**Deprecated/outdated — do not use:**
- `Optional[X]` for new type hints — use `X \| None`.
- `typing.List`/`typing.Dict` for new type hints — use `list[...]`/`dict[...]`.
- `@pytest.mark.asyncio` around `asyncio.run(...)` — the existing codebase does not use `pytest-asyncio` decorators; it calls `asyncio.run(...)` inside sync test functions (see `test_server.py`). Match that pattern.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The activity-create endpoint is `POST /athlete/{id}/activities/manual` (singular, non-bulk). Forum confirms `/activities/manual/bulk`; singular variant is inferred. | Standard Stack, Code Examples — spike skeleton | LOW — spike has a fallback branch that retries `/activities` plain if manual returns 404. **The spike exists specifically to kill this assumption.** |
| A2 | Custom fields are written as top-level keys on the activity JSON (not nested under `custom_fields`). | Architecture Patterns, Code Examples — spike sets `discipline` at top level | MEDIUM — forum thread 25515 shows read-path custom fields as top-level keys, but write-path is not explicitly shown. The spike's `custom_field_write` probe confirms or refutes. If wrong, `enrich_activity_climbing` payload shape in Phase 2 changes. |
| A3 | Writing `-1` clears numeric wellness fields (forum cookbook). | Code Examples — spike cleanup | LOW — if `-1` doesn't clear, spike records "field still set to -1" in findings; Phase 2 picks a different clearing strategy. Not blocking. |
| A4 | Activity `type: "WeightTraining"` accepts manual-create payloads and eventually produces rpeTSS when `icu_rpe` is set. | Architecture Patterns, spike | MEDIUM — forum references `WeightTraining` with `kg_lifted`-style fields, but whether rpeTSS populates correctly for this type is empirically unverified. Spike records the initial response; subsequent Intervals.icu daily load recalculation confirms rpeTSS in a follow-up manual check. Phase 3 decision about `"WeightTraining"` vs `"Other"` reads this. |
| A5 | The custom-field-definitions endpoint exists — likely at `/athlete/{id}/custom-fields`, `/athlete/{id}/activity-fields`, or `/athlete/{id}/sport-settings`. The existing `/athlete/{id}/custom-item` is for charts/zones, NOT activity fields. | Summary, Validation Architecture | HIGH — if no definitions-list endpoint exists, `verify_custom_fields_setup` cannot list required fields positively. Fallback is a **readback heuristic**: PUT a probe field to a throwaway activity, GET it back, see whether it persisted. Ugly but workable. Spike MUST determine this. |
| A6 | Activity DELETE endpoint exists at `DELETE /activity/{id}` or `/athlete/{id}/activity/{id}`. | Code Examples — spike cleanup | LOW — if DELETE unavailable, spike records "no delete endpoint, manual cleanup required via web UI" in findings. D-03 pre-approved this contingency. |
| A7 | `MappingProxyType[str, FieldSpec]` is a valid generic form in Python 3.12. | Code Examples — utils/climbing.py | LOW — MappingProxyType is generic-subscriptable since Python 3.9 (PEP 585). `[VERIFIED: Python 3.12 stdlib]` Risk near zero; included for completeness. |
| A8 | `pytest-asyncio` is NOT required for tests in `test_grades.py` and `test_climbing.py` because they test pure sync functions (validate_grade, enum comparisons, dict alignment). | Validation Architecture | LOW — no async code in the utilities; tests are plain sync `def test_*()`. Spike is async but runs via `asyncio.run` in `__main__`, not under pytest. |

**Confirmation protocol:** Assumptions A1, A2, A4, A5, A6 are the direct subject of the spike. A3 is confirmed as a side-effect of the spike cleanup step. A7, A8 are internal-code assumptions with near-zero risk. **The planner must NOT treat A1–A6 as locked decisions** — they are the questions the spike answers.

---

## Open Questions

1. **Does a custom-field definitions endpoint exist, and what is its URL?**
   - What we know: the codebase's `/athlete/{id}/custom-item` endpoint returns charts/zones/INPUT_FIELD items (confirmed by reading `tools/custom_items.py`). That is not the same as custom *activity* fields defined per-athlete or per-sport (confirmed by forum thread 25515 describing fields as "per athlete" and "available as columns on the activity list view").
   - What's unclear: the list-definitions URL. Candidates include `/athlete/{id}/custom-fields`, `/athlete/{id}/activity-fields`, `/athlete/{id}/sport-settings`, or fields might only be readable as part of a full athlete-profile GET.
   - Recommendation: spike tries each candidate URL in priority order; first successful GET is captured verbatim in `01-SPIKE-FINDINGS.md`. If all 4xx, **fallback design** — `verify_custom_fields_setup` creates a throwaway activity at the spike date, PUTs each required field, reads back, deletes the activity. This is expensive (1 POST + 7 PUTs + 1 GET + 1 DELETE) but verifies presence without needing a definitions endpoint. Trade-off captured in the findings file; planner decides which strategy to lock in for Phase 2.

2. **Does the same POST body shape work for `/activities/manual` and `/events`, or is there divergence?**
   - What we know: `events.py` uses `start_date_local`, `category`, `name`, `description`, `type`, `moving_time`, `distance`. Forum indicates `/activities/manual/bulk` accepts arrays of `{type, start_date_local, moving_time, name}`.
   - What's unclear: whether `category` is required for activities (it's `"WORKOUT"` for events), whether `description` is supported, whether additional required fields exist for `WeightTraining`.
   - Recommendation: spike sends a minimal body first (`type`, `start_date_local`, `name`, `moving_time`). If 422, incrementally add fields from the event shape until success. Exact minimum required body is captured verbatim.

3. **Does `icu_rpe` write back correctly on a freshly-created WeightTraining activity?**
   - What we know: `icu_rpe` is the canonical native RPE field (`format_activity_summary` reads it at line 46). Intervals.icu computes rpeTSS from `icu_rpe` + duration.
   - What's unclear: whether `icu_rpe` can be set at creation-time in the POST body, or must be a follow-up PUT.
   - Recommendation: spike tests both — (a) POST with `icu_rpe` in body, readback; (b) POST without `icu_rpe`, PUT `icu_rpe` separately, readback. Whichever works goes into findings; if both work, prefer the single-call path.

4. **Exact shape of the custom-field definitions response, once the endpoint is found.**
   - What we know: the response likely includes at minimum `name` (key), `type` (select/text/bool/numeric), and for select fields an options list.
   - What's unclear: exact JSON key names (`name` vs `key` vs `field_name`; `type` vs `field_type`; `options` vs `values` vs `enum`).
   - Recommendation: spike dumps the full response verbatim to findings. `verify_custom_fields_setup` is implemented in Phase 1 against whatever shape the spike documents. If spike is not yet run when the utility files are drafted, the planner may need to stub `verify_custom_fields_setup` to read the shape from `01-SPIKE-FINDINGS.md` deterministically (i.e., write utilities first, wire verify-tool implementation after spike findings land). **Recommended sequencing inside Phase 1: (1) utilities + tests, (2) spike, (3) verify-tool implementation + server wiring, (4) README.**

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | All | ✓ | per `pyproject.toml` | — |
| `uv` | `uv run`, test runner | ✓ | per AGENTS.md | — |
| `pytest` + `pytest-asyncio` | Tests | ✓ | 8.3.5+ / 0.21+ | — |
| `ruff` | Lint + format | ✓ | per `pyproject.toml` | — |
| `mypy` | Type check | ✓ | per AGENTS.md | — |
| Intervals.icu API reachability | Spike only | assumed ✓ | — | Spike fails-loud with error dict; planner retries with valid creds |
| `API_KEY` + `ATHLETE_ID` in `.env` | Spike only | assumed ✓ | — | Spike prints clear "set API_KEY and ATHLETE_ID in .env" message and exits 1 |
| `.planning/phases/01-foundation-and-write-path-spike/` directory | Spike findings output | ✓ | exists (contains 01-CONTEXT.md) | — |
| `scripts/` directory | Spike location | **likely absent** | — | Spike script creates it on first run (planner verifies `ls scripts/` before execution) |

**Missing dependencies with no fallback:**
- None blocking. All critical tooling is in place.

**Missing dependencies with fallback:**
- `scripts/` directory — Phase 1 task creates it. Trivial. No fallback needed beyond "`mkdir -p scripts`".

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3.5+ with pytest-asyncio 0.21+ |
| Config file | `pyproject.toml` under `[tool.pytest.ini_options]`; `asyncio_default_fixture_loop_scope = "function"` |
| Quick run command | `pytest tests/test_grades.py tests/test_climbing.py -q` |
| Full suite command | `pytest -v tests` |
| Collection sanity | `pytest --collect-only` — count must increase after Phase 1 merge |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| **CLIMB-08** | Font grade accepted on bouldering | unit | `pytest tests/test_grades.py::test_validate_grade_font_on_boulder_ok -x` | ❌ Wave 0 |
| **CLIMB-08** | French sport grade accepted on route disciplines | unit | `pytest tests/test_grades.py::test_validate_grade_french_on_route_ok -x` | ❌ Wave 0 |
| **CLIMB-08** | Font grade rejected on sport lead with "French sport" in error | unit | `pytest tests/test_grades.py::test_validate_grade_font_on_route_rejected -x` | ❌ Wave 0 |
| **CLIMB-08** | French sport grade rejected on boulder with "Font" in error | unit | `pytest tests/test_grades.py::test_validate_grade_french_on_boulder_rejected -x` | ❌ Wave 0 |
| **CLIMB-08** | Regex matrix — canonical grades accepted | unit (parametrize) | `pytest tests/test_grades.py -k 'accepts_canonical' -x` | ❌ Wave 0 |
| **CLIMB-08** | Regex matrix — non-canonical/cross-scale rejected | unit (parametrize) | `pytest tests/test_grades.py -k 'rejects' -x` | ❌ Wave 0 |
| **SETUP-01** | `CUSTOM_FIELD_KEYS` covers exactly the 7 required keys | unit | `pytest tests/test_climbing.py::test_custom_field_keys_covers_seven_fields -x` | ❌ Wave 0 |
| **SETUP-01** | `Discipline` enum values align with `CUSTOM_FIELD_KEYS["discipline"].options` | unit | `pytest tests/test_climbing.py::test_discipline_options_match_custom_field_spec -x` | ❌ Wave 0 |
| **SETUP-01** | `SessionFocus` enum values align with `CUSTOM_FIELD_KEYS["session_focus"].options` | unit | `pytest tests/test_climbing.py::test_session_focus_options_match_custom_field_spec -x` | ❌ Wave 0 |
| **SETUP-01** | `CUSTOM_FIELD_KEYS` is read-only (MappingProxyType) | unit | `pytest tests/test_climbing.py::test_custom_field_keys_is_read_only -x` | ❌ Wave 0 |
| **SETUP-01** | README contains the 7-field setup table | manual / smoke | Grep: `grep -c "\`discipline\`\|\`indoor\`\|\`session_focus\`\|\`top_grade_sent\`\|\`top_grade_attempted\`\|\`sends\`\|\`attempts\`" README.md` returns ≥7 | — (README diff) |
| **SETUP-02** | `verify_custom_fields_setup` is registered as MCP tool | integration | `pytest tests/test_climbing.py::test_verify_tool_registered -x` (new, uses pattern from test_server.py) | ❌ Wave 0 |
| **SETUP-02** | `verify_custom_fields_setup` returns named-field error when fields missing | integration (mocked) | `pytest tests/test_climbing.py::test_verify_tool_reports_missing_by_name -x` | ❌ Wave 0 |
| **SETUP-02** | `verify_custom_fields_setup` internal helper returns `(ok, missing, message)` tuple | unit (mocked) | `pytest tests/test_climbing.py::test_verify_internal_helper_returns_tuple -x` | ❌ Wave 0 |
| Spike output | `01-SPIKE-FINDINGS.md` exists after `uv run scripts/spike_write_endpoints.py` | manual | `test -s .planning/phases/01-foundation-and-write-path-spike/01-SPIKE-FINDINGS.md` | — (spike run artifact) |
| Existing tests | Full suite passes unchanged | regression | `pytest -v tests` green | ✅ existing |
| Test collection | Test count increased by exactly expected delta | smoke | `pytest --collect-only -q \| tail -1` | — (run pre/post) |

### Sampling Rate

- **Per task commit:** `pytest tests/test_grades.py tests/test_climbing.py -q` (< 2 seconds)
- **Per wave merge:** `pytest -v tests` (full suite; pre-push hook already enforces this via `.pre-commit-config.yaml`)
- **Phase gate:** Full suite green + `pytest --collect-only` delta matches plan + spike findings file exists and is non-empty before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_grades.py` — covers CLIMB-08 (regex matrix + dispatch validator)
- [ ] `tests/test_climbing.py` — covers SETUP-01 (enum/spec alignment, 7-key coverage) and SETUP-02 (verify tool registration + behavior)
- [ ] No shared `conftest.py` needed — existing pattern puts `sys.path.insert` + `os.environ.setdefault` at the top of each test file (`test_server.py`, `test_make_intervals_request.py`) `[VERIFIED: direct read]`
- [ ] Framework install: not needed — `pytest`, `pytest-asyncio`, `pytest-mock` already in dev extras `[VERIFIED: STRUCTURE.md line 90]`
- [ ] Regression baseline: `pytest --collect-only -q | tail -1` captured BEFORE Phase 1 work begins, compared to post-Phase-1 count (Pitfall #14 enforcement)

**Spike is NOT a pytest test.** It is a script in `scripts/`. No test-side validation applies. The spike's own output (`01-SPIKE-FINDINGS.md`) is the validation artifact; reviewing that file by eye is the human-in-the-loop gate before Phase 2 planning.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | HTTP Basic Auth against Intervals.icu via `make_intervals_request` — existing `[VERIFIED: api/client.py]`. Phase 1 adds no new auth surface. |
| V3 Session Management | no | Stateless MCP tools; no session state. |
| V4 Access Control | yes | `ATHLETE_ID` scopes all API calls to the configured athlete. Spike respects this by reading `config.athlete_id`. |
| V5 Input Validation | yes | `validate_grade`, `validate_date`, `resolve_athlete_id` — all raise `ValueError` with user-facing messages on bad input. Grade regex is whitelist-style (Pitfall #3 mitigation). |
| V6 Cryptography | no | No crypto primitives in Phase 1. TLS is handled by `httpx` + Intervals.icu. |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key leaking into debug logs | Information Disclosure | `api/client.py` already logs only POST body (not auth header) at DEBUG. Spike must not log `api_key` or request auth directly. **Recommendation:** spike logs at INFO; request-body logging is delegated to the existing client. `[VERIFIED: api/client.py line 180]` |
| Spike writing to production data | Tampering (self-inflicted) | Far-future date (D-03) isolates spike writes from real data. Cleanup step (blank wellness with `-1`; DELETE activity if available). Manual checklist if DELETE unavailable. |
| Accidental CI execution of the spike | Tampering (self-inflicted) | Spike lives in `scripts/` not `tests/` (D-01). pytest discovery does not find it. `.github/workflows/python-app.yml` runs pytest — spike is invisible. |
| Grade / discipline input injection | Tampering | All values sent in JSON body (not URL params) per `make_intervals_request(data=...)`. Grade regex is whitelist. Discipline is `StrEnum` (rejects arbitrary strings at API boundary). `[VERIFIED: client.py line 188]` |
| Overly verbose error surface from Intervals.icu leaked to user | Information Disclosure | Existing `_get_error_message` mapping intercepts status codes. New code uses existing error paths — no new leak surface. `[VERIFIED: api/client.py lines 84–99]` |
| Spike committed with real athlete ID or API key in findings | Information Disclosure | `01-SPIKE-FINDINGS.md` must **not** contain `API_KEY` or full athlete ID. Findings should redact or use placeholder (`{athlete_id}`). **Planner task:** explicit acceptance criterion — `grep -E "i[0-9]{5,}" 01-SPIKE-FINDINGS.md` returns empty. |

---

## Project Constraints (from CLAUDE.md)

Extracted from `./CLAUDE.md` (read 2026-04-24) — these are authoritative and the plan must not recommend approaches that contradict them:

- **All Intervals.icu HTTP goes through `make_intervals_request()`** (`src/intervals_mcp_server/api/client.py`). No direct `httpx` from tools or the spike. **Enforces D-02.**
- **MCP tools are stateless** — no hidden conversational state; Claude gathers inputs and calls tools single-shot. **Enforces D-11 behaviour: verify tool is single-call.**
- **No local shadow data store** — Intervals.icu is source of truth. **Enforces spike cleanup strategy.**
- **Custom-field schemas must be user-defined first** — SETUP-01/02 documented prerequisite, not something the tools can create. **Enforces D-12 hard-block.**
- **Grade systems:** Font (bouldering) + French sport (routes). Validate against declared discipline. **Enforces CLIMB-08 / D-05 / D-06.**
- **Custom-field writes must be readback-verified** — Intervals.icu silently ignores writes to undefined field keys. **Enforces spike's readback step and Pitfall #2 mitigation.**
- **Duplicate-activity guard on every `POST /activities`** — non-idempotent endpoint. **Phase 1 note:** spike posts only one activity per run (at a far-future date); duplicate guard is Phase 3's responsibility. Spike's readback step confirms whether a duplicate check against `/activities?oldest=&newest=` works (Phase 3 prerequisite).
- **New climbing tools go in `src/intervals_mcp_server/tools/climbing.py`** — not piled into `activities.py`. **Enforces D-17.**
- **Honor existing conventions** (`.planning/codebase/CONVENTIONS.md`, `STRUCTURE.md`). Code snippets above match Google-style docstrings, 100-char line, `snake_case`/`PascalCase`/`UPPER_SNAKE_CASE`, import ordering (stdlib → third-party → local). **Enforces D-15 additive style.**
- **Brownfield — existing codebase has shape.** Purely additive changes; no refactor of existing modules. **Enforces D-16 / D-20.**

Tooling (`AGENTS.md`):
- `uv sync --all-extras` for environment; `uv run` for the spike.
- `pytest` from repo root (not `python -m pytest`); `ruff .`; `mypy src tests`.
- All three must pass before commit.

---

## Sources

### Primary (HIGH confidence — verified by direct file read or repeatedly cited)

- `src/intervals_mcp_server/api/client.py` — `make_intervals_request` signature, error return shape, auth pattern `[VERIFIED 2026-04-24]`
- `src/intervals_mcp_server/mcp_instance.py` — FastMCP singleton location `[VERIFIED 2026-04-24]`
- `src/intervals_mcp_server/tools/wellness.py` — existing read-side tool; template for new tool module `[VERIFIED 2026-04-24]`
- `src/intervals_mcp_server/tools/events.py` — `add_or_update_event` POST pattern; `start_date_local` format `[VERIFIED 2026-04-24]`
- `src/intervals_mcp_server/tools/activities.py` — error-dict handling pattern; private helpers to AVOID importing `[VERIFIED 2026-04-24]`
- `src/intervals_mcp_server/tools/custom_items.py` — confirms `/athlete/{id}/custom-item` is for charts/zones, NOT activity custom fields `[VERIFIED 2026-04-24]`
- `src/intervals_mcp_server/utils/validation.py` — `resolve_athlete_id`, `validate_date`, ValueError pattern `[VERIFIED 2026-04-24]`
- `src/intervals_mcp_server/utils/types.py` — existing dataclass patterns, `TransportAliases(StrEnum)` reference `[VERIFIED 2026-04-24]`
- `src/intervals_mcp_server/utils/formatting.py` — `format_wellness_entry`, `format_activity_summary`, `_KeyTracker` pattern `[VERIFIED 2026-04-24]`
- `src/intervals_mcp_server/server.py` — tool-import / decorator-registration pattern `[VERIFIED 2026-04-24]`
- `src/intervals_mcp_server/config.py` — `get_config()` singleton `[VERIFIED 2026-04-24]`
- `tests/test_server.py` — mock pattern for `make_intervals_request`; `sys.path.insert` pattern `[VERIFIED 2026-04-24]`
- `tests/test_make_intervals_request.py` — `MockAsyncClient` pattern, `asyncio.run()` inside sync tests `[VERIFIED 2026-04-24]`
- `.planning/codebase/STRUCTURE.md`, `CONVENTIONS.md`, `CONCERNS.md`, `INTEGRATIONS.md`, `TESTING.md` — source for "where code goes" and naming/error patterns `[VERIFIED 2026-04-24]`
- `.planning/research/PITFALLS.md` — Pitfalls #2, #3, #5, #11, #12, #14 `[VERIFIED 2026-04-24]`
- `AGENTS.md` — uv / pytest / ruff / mypy tooling guide `[VERIFIED 2026-04-24]`

### Secondary (MEDIUM confidence — one authoritative source)

- [Intervals.icu Forum — Custom activity fields](https://forum.intervals.icu/t/custom-activity-fields/25515) `[CITED]` — confirms custom fields are top-level keys on activity JSON; "per athlete" and "read and update via API".
- [Intervals.icu Forum — API Integration Cookbook](https://forum.intervals.icu/t/intervals-icu-api-integration-cookbook/80090) `[CITED]` — wellness PUT uses upsert semantics; `-1` to clear numeric fields; event POST body shape.
- [Intervals.icu Forum — Custom activity fields on sports](https://forum.intervals.icu/t/custom-activity-fields-on-sports/111867) `[CITED]` — sport-level custom fields copy onto new activities (informational; Phase 1 does not exercise sport-level fields).
- [Intervals.icu Forum — WeightTraining structured upload](https://forum.intervals.icu/t/is-there-structure-way-to-upload-a-weight-training-activity/126508) `[CITED]` — confirms `WeightTraining` as a valid `type` for manual activities, with `kg_lifted` fields for strength-training payloads.
- Python 3.12 stdlib documentation for `enum.StrEnum`, `types.MappingProxyType`, `re` module `[CITED]` — training knowledge + stdlib reference.

### Tertiary (LOW confidence — needs spike verification)

- [Intervals.icu API docs landing page](https://intervals.icu/api-docs.html) — client-rendered, WebFetch cannot extract content. `[ASSUMED]` contains full schema; access via browser + DevTools if spike run reveals a gap.
- Inferred endpoint path `/athlete/{id}/activities/manual` — forum confirms `/activities/manual/bulk`; singular variant inferred. **Spike must confirm.** `[ASSUMED]`
- Candidate custom-field definitions endpoints (`/athlete/{id}/custom-fields`, `/athlete/{id}/activity-fields`, `/athlete/{id}/sport-settings`) — speculative. **Spike must discover.** `[ASSUMED]`

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every recommendation traces to an existing codebase pattern via direct file read.
- Architecture (utility layer, tool scaffolding, formatter extension): HIGH — purely additive; all patterns established.
- Spike design: MEDIUM-HIGH — structure is solid, but the precise API endpoints it probes are deliberately uncertain (the spike IS the research for those).
- API write contracts: MEDIUM — upsert semantics and `-1` for clearing numerics are forum-confirmed; exact activity-create URL, custom-field definitions URL, and WeightTraining-with-rpeTSS behaviour are the spike's job.
- Pitfalls: HIGH — research pitfalls document is explicit and this phase maps to it directly.
- Validation architecture: HIGH — new test files follow an exact existing template; requirement-to-test mapping is one-to-one.

**Research date:** 2026-04-24
**Valid until:** 2026-05-24 (30 days — API contracts are stable; codebase is under active development but no planned refactors affecting Phase 1 surface).
