# Architecture Research

**Domain:** MCP server extension — climbing-aware training loop for Intervals.icu
**Researched:** 2026-04-24
**Confidence:** HIGH (based on direct codebase analysis)

## Standard Architecture

### System Overview

Existing layers (unchanged) with new components in brackets marked `[NEW]`:

```
┌──────────────────────────────────────────────────────────────────────┐
│                    MCP Client (Claude Desktop)                        │
└───────────────────────────┬──────────────────────────────────────────┘
                            │ MCP Protocol (stdio/SSE/http)
┌───────────────────────────▼──────────────────────────────────────────┐
│                       FastMCP Instance                                │
│                    (mcp_instance.py singleton)                        │
└──────┬───────────┬──────────────┬───────────────┬────────────────────┘
       │           │              │               │
┌──────▼──┐  ┌────▼──────┐  ┌───▼──────┐  ┌────▼──────────────────┐
│activities│  │ events.py │  │wellness  │  │  climbing.py  [NEW]   │
│   .py   │  │           │  │   .py    │  │                        │
│         │  │           │  │          │  │ complete_climbing_     │
│(no new  │  │(unchanged)│  │+ write_  │  │   session()           │
│ tools)  │  │           │  │ wellness │  │ create_climbing_       │
│         │  │           │  │ [NEW]    │  │   activity()          │
└────┬────┘  └────┬──────┘  └───┬──────┘  │ enrich_activity_      │
     │            │             │         │   climbing()          │
     │            │             │         │ get_training_status() │
     │            │             │         └────────┬──────────────┘
     │            │             │                  │
└────┴────────────┴─────────────┴──────────────────┴─────────────────┐
│                     API Client Layer                                  │
│              make_intervals_request()  ←  single HTTP boundary        │
└─────────────────────────────────────────────────────────────────────┘
                             │
                    Intervals.icu REST API
```

```
utils/ (shared, leaf deps — no imports from tools/ or api/)
├── formatting.py     ← + format_climbing_session() [NEW]
├── validation.py     ← + validate_climbing_fields() [NEW functions]
├── types.py          ← + ClimbingSession, GradeRange dataclasses [NEW]
├── grading.py        ← grade parsing/normalisation [NEW MODULE]
└── dates.py          (unchanged)
```

### Component Responsibilities

| Component | Responsibility | New vs Existing |
|-----------|----------------|-----------------|
| `tools/climbing.py` | All new climbing-domain MCP tools | NEW |
| `tools/wellness.py` | Existing reads + new `write_wellness_entry` | EXTEND (one new tool) |
| `tools/activities.py` | Read tools only — unchanged | UNCHANGED |
| `utils/grading.py` | Parse Font / French sport grades; validate; normalise | NEW MODULE |
| `utils/types.py` | `ClimbingSession`, `GradeRange` dataclasses added | EXTEND |
| `utils/validation.py` | `validate_climbing_fields()` added | EXTEND |
| `utils/formatting.py` | `format_climbing_session()`, `format_training_status()` added | EXTEND |
| `api/client.py` | `make_intervals_request()` — no changes needed | UNCHANGED |

## Module Boundary Decision: `climbing.py` vs extending `activities.py`

**Decision: New `tools/climbing.py` module. Do not extend `activities.py`.**

Rationale:

`activities.py` is 382 lines today with four pylint complexity waivers already in place (`too-many-arguments`, `too-many-return-statements`, `too-many-branches`, `too-many-positional-arguments`). The CONCERNS.md audit explicitly flags it as a file where new tools should not pile on. The new climbing tools add four new `@mcp.tool()` functions, each with significant parameter lists and domain-specific logic — that would push `activities.py` past 600 lines and compound the existing complexity problem.

The climbing domain is also semantically distinct. `activities.py` is a pure read layer (list, detail, intervals, streams, messages, plus one write: `add_activity_message`). Climbing tools write to activities (PUT), create activities (POST), and orchestrate multi-endpoint reads. Mixing that into the read-dominant `activities.py` muddies the module's purpose.

STRUCTURE.md already names the pattern: "New MCP tool for a new domain → New module in `src/intervals_mcp_server/tools/`, import into `server.py`." Climbing is a new domain relative to the existing activity-reading domain.

`tools/climbing.py` calls `make_intervals_request()` just like every other tool module — the HTTP boundary rule is maintained.

## Where Domain Types Live

**`utils/types.py`** — extend with new dataclasses following the existing pattern.

Add:
- `ClimbingSession` — holds all climbing-specific fields: discipline, gym_or_outdoor, sends (list of grades), attempts (list of grades), session_focus, rpe, duration_minutes, notes. Matches the data Claude gathers conversationally before the single tool call.
- `GradeRange` — a lightweight value type wrapping a validated grade string and its system (Font / French sport). Used inside `ClimbingSession`.

Both get `to_dict()` / `from_dict()` per existing convention. `ClimbingSession.to_dict()` produces the payload shape that maps to Intervals.icu custom fields — it is the transform layer between the domain model and the API write.

**Do not create a new types module.** `types.py` is 586 lines but that is a pre-existing concern. Adding two focused dataclasses does not worsen the underlying cyclomatic complexity problem (those methods are complex because `Step` and `WorkoutDoc` have 20+ optional fields — `ClimbingSession` will have 8-10, keeping methods simple).

## Where Grade Parsers Live

**New `utils/grading.py` module.** Do not add to `validation.py`.

`validation.py` today is 88 lines covering athlete ID and date validation — generic input hygiene. Grade parsing is domain logic: recognising "7b+", "8A", "6c" as valid; rejecting "V5" (V-scale, out of scope); normalising case ("7B+" → "7b+"); comparing grade difficulty for grade-range reporting. That semantic weight belongs in its own module.

`utils/grading.py` exports:
- `parse_font_grade(s: str) -> str` — validates and normalises a Fontainebleau bouldering grade
- `parse_french_sport_grade(s: str) -> str` — validates and normalises a French sport climbing grade
- `validate_grade_list(grades: list[str], system: str) -> tuple[list[str], str | None]` — returns normalised list + optional error message (matches `resolve_athlete_id` error-tuple pattern)

`utils/validation.py` gets `validate_climbing_fields()` — a higher-level function that validates the full `ClimbingSession` (discipline is one of the allowed values, rpe is 1–10, etc.) by calling into `grading.py`. This keeps `validation.py` as the single entry point tools call for input checking, while grade logic is encapsulated separately.

## Recommended Project Structure (additions only)

```
src/intervals_mcp_server/
├── tools/
│   ├── climbing.py          [NEW] — 4 MCP tools
│   └── wellness.py          [EXTEND] — 1 new MCP tool (write_wellness_entry)
└── utils/
    ├── grading.py           [NEW] — Font + French sport grade parsing
    ├── types.py             [EXTEND] — ClimbingSession, GradeRange dataclasses
    ├── validation.py        [EXTEND] — validate_climbing_fields()
    └── formatting.py        [EXTEND] — format_climbing_session(), format_training_status()

tests/
├── test_climbing.py         [NEW] — tool + formatter tests
├── test_grading.py          [NEW] — grade parse/validate unit tests
└── ressources/              [EXTEND] — add climbing fixture JSON
```

`server.py` gets one additional import: `import intervals_mcp_server.tools.climbing  # noqa: F401`

## Architectural Patterns

### Pattern 1: LLM-gathered parameters as single tool call

**What:** Claude conversationally collects all climbing session fields from the user, then issues a single tool call with those fields as parameters. The tool does not ask follow-up questions — all required fields arrive in one invocation.

**When to use:** All new write tools (`complete_climbing_session`, `create_climbing_activity`, `enrich_activity_climbing`, `write_wellness_entry`).

**Trade-offs:** Puts all field-gathering burden on the LLM's conversation layer, which is where it belongs. Keeps tools stateless (MCP requirement). The cost is that tool parameter lists are longer — mitigated by making optional fields optional with sensible defaults.

**How Claude knows which fields to gather:** Tool docstrings. FastMCP surfaces the full docstring (including `Args:` section) as the tool description in the MCP schema. Thorough `Args:` documentation with descriptions like "discipline: one of 'bouldering', 'sport_lead', 'top_rope', 'trad'" gives Claude the vocabulary to ask the right questions before calling the tool. No companion "describe required fields" tool is needed — that would require two round trips and add protocol complexity.

**Example signature skeleton:**
```python
@mcp.tool()
async def complete_climbing_session(
    event_id: str,
    discipline: str,                        # "bouldering" | "sport_lead" | "top_rope" | "trad"
    location_type: str,                     # "gym" | "outdoor"
    session_focus: str,                     # "power" | "endurance" | "technique" | "projecting" | "mileage"
    rpe: int,                               # 1-10
    duration_minutes: int | None = None,
    sends: list[str] | None = None,         # e.g. ["7b+", "7b+", "7c"]
    attempts: list[str] | None = None,      # grades attempted but not sent
    notes: str | None = None,
    api_key: str | None = None,
) -> str:
```

### Pattern 2: Single HTTP boundary, sequential reads for status report

**What:** `get_training_status()` makes three sequential `make_intervals_request()` calls (fitness/form endpoint → wellness endpoint → activities endpoint), then synthesises in the tool layer.

**When to use:** Status report tool only.

**Trade-offs:** Sequential means ~3× latency vs. parallel. Parallel `asyncio.gather()` is tempting but introduces complexity and is not used anywhere in the existing codebase — introducing it for one tool would be inconsistent. For a single-user tool invoked conversationally, 2–3 seconds total is acceptable. Introduce `asyncio.gather()` only if latency becomes a real problem.

The tool layer, not `utils/`, synthesises the three payloads into the report. Synthesis requires knowing which API fields mean what in context (e.g., CTL > 80 with TSB < -20 means "high load, accumulated fatigue") — that is business logic, not formatting. `utils/formatting.py` gets `format_training_status(fitness, wellness, activities)` which renders the already-synthesised data to a prose report. The tool decides what to say; the formatter decides how to say it.

**No "multi-fetch" helper** is warranted. Three sequential calls sharing the same `make_intervals_request()` path is explicit and testable without a new abstraction layer.

### Pattern 3: Single PUT round trip for custom field writes

**What:** Writing climbing metadata to an activity (custom fields + `icu_rpe`) is one `PUT /activity/{id}` call with all fields in a single JSON body.

**When to use:** `complete_climbing_session`, `create_climbing_activity`, `enrich_activity_climbing`.

**Trade-offs:** The Intervals.icu API accepts partial activity updates — only fields present in the PUT body are changed. Send all custom fields + `icu_rpe` in one dict. Do not loop and issue one request per field. One round trip is cheaper, simpler, and avoids partial-write failure states where some fields saved and some did not.

**`ClimbingSession.to_dict()`** produces the PUT body. The tool calls it, merges in any additional native fields (name, type), then calls `make_intervals_request()` once.

### Pattern 4: Activity create for manual sessions (no Garmin device)

**What:** `create_climbing_activity` POSTs to `POST /athlete/{id}/activities` to create the activity record, then immediately PUTs climbing metadata to the returned activity ID.

**When to use:** When there is no existing activity to enrich (pure manual entry).

**Trade-offs:** Two API calls — unavoidable because the activity ID is not known until after creation. The tool chains them: POST → extract ID from response → PUT custom fields. Treat the pair as an atomic operation from the tool's perspective; if the PUT fails, return an error that includes the created activity ID so the user can retry enrichment with `enrich_activity_climbing`.

## Data Flow

### Flow 1: Complete a planned session (linked activity)

```
Claude invokes complete_climbing_session(event_id, discipline, ...)
    ↓
tools/climbing.py
    ↓ validate_climbing_fields() → utils/validation.py + utils/grading.py
    ↓ ClimbingSession(**params) → utils/types.py
    ↓
    [1] POST /athlete/{id}/activities  ← make_intervals_request() (creates linked activity)
    ↓ returns {id: activity_id, ...}
    ↓
    [2] PUT /activity/{activity_id}    ← make_intervals_request() (writes custom fields + rpe)
        body: ClimbingSession.to_dict() merged with {icu_rpe: rpe, type: "WeightTraining"}
    ↓
format_climbing_session(session, activity_id) → utils/formatting.py
    ↓
return str to MCP client
```

Note: Intervals.icu auto-matches the new activity to the planned event by date and workout type. The tool does not manipulate the event record directly.

### Flow 2: Enrich an existing activity (Garmin-synced)

```
Claude invokes enrich_activity_climbing(activity_id, discipline, ...)
    ↓
tools/climbing.py
    ↓ validate_climbing_fields()
    ↓ ClimbingSession(**params).to_dict()
    ↓
    [1] PUT /activity/{activity_id}    ← make_intervals_request() (single round trip)
    ↓
format_climbing_session(session, activity_id) → utils/formatting.py
    ↓
return str to MCP client
```

### Flow 3: Create a manual climbing activity (no device)

```
Claude invokes create_climbing_activity(date, discipline, ...)
    ↓
tools/climbing.py
    ↓ validate_climbing_fields()
    ↓
    [1] POST /athlete/{id}/activities  ← make_intervals_request() (create bare activity)
        body: {start_date_local, type: "WeightTraining", name: ..., moving_time, ...}
    ↓ returns {id: activity_id}
    ↓
    [2] PUT /activity/{activity_id}    ← make_intervals_request() (write climbing custom fields)
        body: ClimbingSession.to_dict() + {icu_rpe: rpe}
    ↓
format_climbing_session(session, activity_id) → utils/formatting.py
    ↓
return str
```

### Flow 4: Write wellness entry

```
Claude invokes write_wellness_entry(date, sleep_secs, hrv, rhr, soreness, ...)
    ↓
tools/wellness.py
    ↓ resolve_athlete_id()  ← utils/validation.py
    ↓ validate_date()
    ↓ build payload dict (only non-None fields included)
    ↓
    [1] PUT /athlete/{id}/wellness/{YYYY-MM-DD}  ← make_intervals_request()
    ↓
return confirmation string
```

Intervals.icu wellness PUT is date-keyed and accepts partial payloads. No read-before-write needed.

### Flow 5: Training status report

```
Claude invokes get_training_status(lookback_days)
    ↓
tools/climbing.py
    ↓ resolve_athlete_id(), resolve_date_params()
    ↓
    [1] GET /athlete/{id}/fitness     ← make_intervals_request() → CTL, ATL, TSB, form
    ↓
    [2] GET /athlete/{id}/wellness    ← make_intervals_request() → sleep, HRV, RHR, soreness
        params: oldest=today-7d, newest=today
    ↓
    [3] GET /athlete/{id}/activities  ← make_intervals_request() → recent activity names/loads
        params: oldest=today-14d, newest=today, limit=10
    ↓
synthesise in tool layer:
    - derive readiness signal from TSB + HRV + soreness
    - derive weekly load from ATL vs CTL
    - derive trend from CTL delta
    ↓
format_training_status(fitness_data, wellness_data, activities) → utils/formatting.py
    ↓
return str
```

The tool layer does synthesis (business logic). `format_training_status()` does rendering (prose output). Keeping them separate means the formatter is unit-testable without API mocks.

## Component Boundaries Summary

| Boundary | Rule |
|----------|------|
| `tools/climbing.py` → API | Only via `make_intervals_request()` |
| `tools/climbing.py` → utils | May import from any `utils/` module |
| `tools/climbing.py` → `tools/activities.py` | No cross-tool imports — shared logic lives in utils, not in other tool modules |
| `tools/wellness.py` → `tools/climbing.py` | No cross-tool imports |
| `utils/grading.py` → other utils | May import `utils/validation.py` helpers only; no imports from `tools/` or `api/` |
| `utils/types.py` → other utils | Stdlib only; no imports from `tools/`, `api/`, or other `utils/` |
| `utils/formatting.py` → other utils | Stdlib + `utils/types.py` only |
| `server.py` → `tools/climbing.py` | Import triggers decorator registration (same pattern as existing tools) |

## Suggested Build Order

Build order follows the dependency graph — leaf modules first, tools last.

**Phase 1 — Foundation (no external dependencies)**

1. `utils/grading.py` — pure functions, no deps. Enables grade validation. Testable in isolation with `test_grading.py`.
2. `utils/types.py` extension — add `GradeRange` and `ClimbingSession` dataclasses. Depends on `grading.py` for grade normalisation in `from_dict()`.
3. `utils/validation.py` extension — add `validate_climbing_fields()`. Depends on `types.py` and `grading.py`.
4. `utils/formatting.py` extension — add `format_climbing_session()` and `format_training_status()`. Depends on `types.py`.

**Phase 2 — Write tools (depend on Phase 1)**

5. `tools/wellness.py` extension — add `write_wellness_entry`. Simple: one PUT call, uses existing `resolve_athlete_id`/`validate_date` validators. Good smoke test that the write path through `make_intervals_request()` works.
6. `tools/climbing.py` — `enrich_activity_climbing` first (one PUT, fewest API interactions). Then `create_climbing_activity` (POST + PUT). Then `complete_climbing_session` (POST + PUT with event linkage).

**Phase 3 — Read/aggregate tool (depends on Phase 1 + existing read tools)**

7. `tools/climbing.py` — `get_training_status`. Add last because it exercises the multi-endpoint read pattern and depends on `format_training_status()` being stable.

**Phase 4 — Server wiring**

8. Add `import intervals_mcp_server.tools.climbing  # noqa: F401` to `server.py`.
9. Update `.env.example` if any new config is needed (unlikely — all climbing tools use the existing `ATHLETE_ID` / `API_KEY`).

**Rationale for ordering:** Formatters and types are independent; build them before tools so tools can be written and tested against real formatter output from the start. Wellness write goes before climbing tools because it exercises the write path with minimal complexity — if the PUT pattern to `make_intervals_request()` has an issue (wrong method, auth problem), you discover it on the simplest tool before building more complex ones. `get_training_status` goes last because it is the most complex orchestration and relies on the formatter being stable.

## Integration Points

### External Services

| Service | Endpoint | Method | Notes |
|---------|----------|--------|-------|
| Intervals.icu activities create | `POST /athlete/{id}/activities` | POST | Returns `{id}` for subsequent PUT |
| Intervals.icu activity update | `PUT /activity/{id}` | PUT | Partial update — omit fields you don't want to change |
| Intervals.icu wellness write | `PUT /athlete/{id}/wellness/{date}` | PUT | Date-keyed, partial update |
| Intervals.icu fitness/form | `GET /athlete/{id}/fitness` | GET | Returns CTL, ATL, TSB, form history |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `climbing.py` ↔ `utils/grading.py` | Direct function call | Grade validation happens before building ClimbingSession |
| `climbing.py` ↔ `utils/types.py` | Direct instantiation | `ClimbingSession(**params)` built in tool, `.to_dict()` produces API body |
| `climbing.py` ↔ `utils/formatting.py` | Direct function call | Tool calls formatter at end; formatter never calls back into tool |
| `wellness.py` ↔ `utils/validation.py` | Direct function call | Same as existing pattern |

## Anti-Patterns

### Anti-Pattern 1: Adding climbing tools to `activities.py`

**What people do:** Extend the most semantically nearby module to avoid creating a new file.

**Why it's wrong:** `activities.py` already has four pylint complexity waivers. Adding four new tools with parameter-heavy signatures would push it to 600+ lines and further compound the existing `too-many-branches` / `too-many-arguments` problem the CONCERNS audit already flags. More practically, the module's character would become confused — it currently has one write tool (`add_activity_message`); climbing tools are primarily write tools with domain-specific validation.

**Do this instead:** New `tools/climbing.py`. The module boundary cost (one import in `server.py`) is trivially low.

### Anti-Pattern 2: Two-phase tool design for field gathering

**What people do:** Build a "start session" tool that stores partial state, then a "submit session" tool that finalises — to avoid long parameter lists.

**Why it's wrong:** MCP tools are stateless request/response. There is no session state between tool calls in the protocol. Simulating it with external storage (files, DB) violates the no-local-shadow-store constraint and breaks portability. Even if stored in the LLM's context window, the design is fragile: any context-window interruption loses the partial state.

**Do this instead:** Single tool call with all fields as optional parameters. Claude's conversation layer gathers fields naturally. The tool docstring (surfaced as MCP schema description) gives Claude the vocabulary it needs.

### Anti-Pattern 3: Cross-tool imports

**What people do:** `climbing.py` imports helper functions from `activities.py` to reuse logic (e.g., `_parse_activities_from_result`).

**Why it's wrong:** Creates hidden coupling between tool modules. If `activities.py` refactors its internal helper, `climbing.py` breaks. The existing codebase has zero cross-tool imports — all shared logic lives in `utils/`.

**Do this instead:** If `climbing.py` needs activity-parsing logic, move that logic to `utils/` and import from there. For the status report, `get_training_status` calls `make_intervals_request()` directly for its activities fetch — it does not call `get_activities()` the MCP tool.

### Anti-Pattern 4: One API call per custom field

**What people do:** Loop over climbing fields, issuing one PUT per field to avoid building a combined payload.

**Why it's wrong:** Three to eight API calls where one would do. Each call has ~200-500ms RTT; a field-by-field loop adds multiple seconds of latency. More critically, it creates partial-write failure modes — the session appears to have some fields but not others, with no atomic rollback.

**Do this instead:** Build the complete payload dict, issue one PUT. Intervals.icu's activity PUT accepts partial updates — fields not in the body are untouched.

### Anti-Pattern 5: Synthesis logic in `utils/formatting.py`

**What people do:** Put the "if CTL > 80 and TSB < -20 then say X" decision logic inside the formatter.

**Why it's wrong:** Formatters in this codebase are pure renderers — they take data and produce strings. Embedding business logic makes formatters untestable without meaningful data and creates a hidden second layer of business logic.

**Do this instead:** Synthesis in the tool function. The tool produces a structured intermediate dict or `NamedTuple` with interpreted values (e.g., `readiness_signal: str = "high_load_accumulated_fatigue"`), then passes it to the formatter which renders to prose.

## MCP Statelessness: Design Implications

Every new tool must honour the single-shot constraint:

1. **No hidden state between calls.** `complete_climbing_session` receives all climbing fields in one invocation. Claude accumulates them conversationally; the tool does not.

2. **No assumption about call ordering.** `enrich_activity_climbing` and `create_climbing_activity` are independent — neither requires the other to have been called first.

3. **Idempotency on retry.** If a PUT fails partway, the user can re-call the tool with the same parameters. `PUT /activity/{id}` is naturally idempotent (same payload → same result). `create_climbing_activity` is not idempotent (POST creates a new activity each time) — the tool should return the activity ID in its success message so the user can run `enrich_activity_climbing` separately if the create succeeded but the enrich failed.

4. **Error messages must be self-contained.** Tools cannot assume the LLM remembers context from a previous turn. Error strings should include the activity ID, the field that failed validation, and what the valid values are — enough for Claude to surface a corrective prompt in the same message.

---

## Sources

- Direct codebase analysis: `src/intervals_mcp_server/` (2026-04-24)
- `.planning/codebase/ARCHITECTURE.md`, `STRUCTURE.md`, `CONVENTIONS.md`, `CONCERNS.md`
- `.planning/PROJECT.md` (requirements, constraints, key decisions)
- Intervals.icu API design: inferred from existing tool patterns (`PUT /activity/{id}`, `POST /athlete/{id}/activities`, `PUT /athlete/{id}/wellness/{date}`)

---
*Architecture research for: intervals-mcp-server climbing-training-aware extension*
*Researched: 2026-04-24*
