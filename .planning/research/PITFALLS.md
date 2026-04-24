# Pitfalls Research

**Domain:** Climbing-aware training loop extension to a FastMCP / Intervals.icu MCP server
**Researched:** 2026-04-24
**Confidence:** HIGH (codebase read directly; Intervals.icu API behaviour inferred from existing
patterns, known constraints documented in PROJECT.md, and domain-specific analysis)

---

## Critical Pitfalls

### Pitfall 1: Activity Creation Without Idempotency — Silent Duplicates on Retry

**What goes wrong:**
The LLM retries a `complete_climbing_session` tool call (due to timeout, MCP reconnect, or Claude
re-running on apparent no-response). Each call POSTs to `/athlete/{id}/activities`. Intervals.icu
does not deduplicate by content — two POSTs with the same `start_date_local` and `type` produce
two distinct activity records. The user ends up with duplicate sessions in their calendar and
double-counted training load.

**Why it happens:**
`make_intervals_request()` in `api/client.py` already retries once internally (on `RuntimeError`
"client has been closed"). A new climbing tool will build on this, but neither the client nor the
tool layer tracks whether the write already succeeded. MCP's stateless contract means the tool has
no memory of prior calls in the same conversation.

**How to avoid:**
Before POSTing, query activities for the target date and sport type first. If an activity on that
date already exists, return its ID and offer to enrich it instead of creating a new one. Make the
`complete_climbing_session` tool accept an optional `existing_activity_id` parameter — if provided,
skip creation and go straight to enrichment (PUT). Document this "check-before-create" as a
required step in the tool's implementation. The existing `get_activities()` tool can serve as the
duplicate check.

**Warning signs:**
- Tool returns success but no `activity_id` in the response, followed by a second call
- User reports two identical sessions appearing on the same date
- Integration tests that call `complete_climbing_session` twice in sequence without checking

**Phase to address:**
Phase covering activity creation (the "completion" phase). The check-before-create guard must be
part of the first implementation of `complete_climbing_session`, not a follow-up hardening step.

---

### Pitfall 2: Custom Field Writes Silently Succeed but Store Nothing

**What goes wrong:**
The tool sends climbing-specific custom fields (discipline, grade, session-focus) in the PUT body
to `/athlete/{id}/activity/{id}`. The API returns HTTP 200 with the updated activity object — but
the fields are absent from the response and from the UI. The custom fields were not pre-defined in
the athlete's Intervals.icu account settings, so the API silently ignores unknown fields rather
than rejecting the request.

**Why it happens:**
Intervals.icu custom fields must be defined in the account (via the web UI) before they can be
written via API. The API does not validate or error on unknown field names. This is explicitly
documented in PROJECT.md as a user prerequisite, but nothing in the tool layer enforces or checks
it at runtime.

**How to avoid:**
(1) Document the required custom field names clearly as a numbered setup checklist in the README
and in the tool's docstring — include the exact field key names the API expects.
(2) After the PUT, read back the activity and verify the custom fields appear. If they are absent,
return a warning string: "Fields were sent but not confirmed in API response — verify custom
fields are defined in your Intervals.icu account settings."
(3) Add a one-time `verify_custom_fields_setup` helper tool that reads the athlete's field
definitions and confirms each required climbing field exists.

**Warning signs:**
- PUT returns 200 but climbing data is missing when fetching the activity back
- No error, no 422, just absent fields
- User reports the activity shows on the calendar but has no climbing metadata

**Phase to address:**
Phase covering activity enrichment. Readback verification is not optional — it prevents a
silent data-loss failure that is invisible to both the LLM and the user.

---

### Pitfall 3: Grade System Ambiguity Causes Cross-Scale Contamination

**What goes wrong:**
Font 6A (boulder) and French sport 6a (route) look nearly identical in text and are distinct
rating scales. V-scale V5 and YDS 5.10a also appear as short strings. An LLM gathering grades
conversationally may confuse them. If the system accepts free-text grades, "6A" could be stored
as either a Font boulder grade or a French sport route grade, making future comparisons and
progress tracking meaningless.

Additionally, discipline and grade are not independent: bouldering problems use Font scale;
sport routes use French sport scale; trad routes in the UK use a different adjectival system.
Writing a grade without validating it against the declared discipline creates nonsensical records
(e.g., Font grade on a sport lead, or French sport grade on a boulder).

**Why it happens:**
The user confirmed Font (bouldering) + French sport (routes) in PROJECT.md. Without an explicit
validation layer, the LLM or user can easily pass the wrong grade system. Free-text custom fields
in Intervals.icu have no schema enforcement.

**How to avoid:**
Implement a validation function that takes `discipline` and `grade` together and rejects
combinations that don't match expected patterns:
- Discipline in `{bouldering}` → grade must match Font pattern (e.g., `6A`, `6A+`, `7B+`, `8A`)
- Discipline in `{sport_lead, top_rope, trad}` → grade must match French pattern (e.g., `6a`, `6a+`,
  `7b+`, `8a`)
Define canonical regex patterns for each scale (Font grades are uppercase; French sport grades
are lowercase). Use `Literal` type hints or an enum for discipline. Reject invalid combinations
before the API call with a clear error message naming the expected format.

**Warning signs:**
- Grade strings that don't match either pattern (free text like "hard V6" or "solid 5.11")
- Discipline=bouldering with a lowercase French-format grade stored
- LLM asking "what grade scale should I use?" repeatedly because the schema is ambiguous

**Phase to address:**
Phase covering activity enrichment and the climbing data model. Validation logic must be unit
tested with representative valid and invalid inputs for both scales.

---

### Pitfall 4: Event-to-Activity Linking Fails on Timezone or Date Format Mismatch

**What goes wrong:**
Intervals.icu auto-matches planned events to completed activities by `start_date_local` and
`type`. If the planned event is stored as `2026-04-24T00:00:00` (local midnight) but the created
activity has `start_date_local` as `2026-04-23T23:00:00Z` (UTC — one hour earlier in CET), the
auto-matching fails. The planned event stays "pending" in the calendar and the activity appears as
unlinked. The user then has both a floating planned session and an unlinked activity, breaking the
close-the-loop value proposition.

**Why it happens:**
The existing `add_or_update_event` sets `start_date_local` to `{date}T00:00:00` (hardcoded local
midnight, no timezone). When creating an activity, if the tool uses UTC datetime from system time
or from a user's voice ("I just finished"), the date arithmetic can shift the day across midnight.
Intervals.icu's matching logic cares about the local date, not UTC.

**How to avoid:**
Always store `start_date_local` in the format `YYYY-MM-DDT00:00:00` (local midnight, no timezone
offset) when creating manual climbing activities — this matches the existing event creation
convention in `events.py`. Accept date from the user as `YYYY-MM-DD` and construct the datetime
explicitly. Never derive the activity date from `datetime.utcnow()`. Treat the user-supplied date
as the ground truth for `start_date_local`.

**Warning signs:**
- Planned events remain in "unmatched" state after session completion
- Activity appears on the wrong calendar date when viewed in Intervals.icu UI
- Tests using `datetime.now(UTC)` vs `datetime.now()` produce different dates near midnight

**Phase to address:**
Phase covering event-to-activity completion linking. Add an explicit test verifying that the
`start_date_local` written for a created activity matches the format used by existing event
creation, using dates near day-boundary (23:59) conditions.

---

### Pitfall 5: MCP Stateless Contract Violated by Conversational State in Tools

**What goes wrong:**
A multi-step "climbing completion wizard" is built where Tool A gathers discipline, Tool B gathers
grade, and Tool C finalises the write. This breaks the MCP stateless contract: each tool call is
an independent request/response with no guaranteed ordering or shared memory between calls. Under
reconnect, timeout, or parallel tool calls, partial state is lost and the tool chain silently
produces an incomplete write.

**Why it happens:**
This is the intuitive but wrong design for multi-field data collection. Developers familiar with
REST wizards or multi-step forms apply the same pattern to MCP tools. The existing codebase is
correctly stateless (one tool = one atomic operation), but new climbing tools need to maintain
this discipline.

**How to avoid:**
All climbing fields must be parameters on a single tool call. The LLM is responsible for gathering
inputs through conversation before calling the tool. The tool docstring must explicitly enumerate
which parameters the LLM should collect conversationally and which have sensible defaults. Example:
`complete_climbing_session(date, discipline, sends, top_grade, session_focus, rpe, ...)` — one call,
all fields. This is already the stated design in PROJECT.md ("Key Decisions: Climbing fields
collected as optional tool parameters, not two-phase tools") — the pitfall is forgetting this
under implementation pressure and splitting into multiple tools.

**Warning signs:**
- Tool function that stores partial data in a module-level dict or global variable between calls
- Tool parameter named `session_id` or `correlation_id` intended to link calls together
- A `begin_session` and `finish_session` tool pair appearing in the design

**Phase to address:**
Phase covering tool design and the climbing module. Include this as an explicit acceptance
criterion: "No module-level mutable state added for tracking in-progress tool calls."

---

### Pitfall 6: Tool Descriptions Too Terse for the LLM to Know What to Ask

**What goes wrong:**
The tool docstring says: `"Log a climbing session."` The LLM calls the tool with only `date` and
`rpe` because that is all it knows it needs — it was never told to ask about discipline, grade,
or session focus. The record is created with missing climbing metadata, defeating the purpose of
the enrichment.

**Why it happens:**
Existing tools in this codebase (e.g., `get_activities`) have terse but sufficient docstrings
because they are read-only — the LLM only needs to know what the tool returns. Write tools that
collect subjective data are different: the docstring is the LLM's instruction on what to ask the
user before calling the tool.

**How to avoid:**
The docstring for each climbing write tool must include:
(1) A sentence stating what information should be gathered conversationally before calling.
(2) The meaning and expected format of each parameter (as existing tools do for `api_key`,
    `athlete_id` — extend this pattern to domain-specific parameters).
(3) Which parameters are required for a useful write vs. which are optional.
Example addition: `"Before calling this tool, ask the user for: discipline (bouldering/sport lead/
top-rope/trad), whether gym or outdoor, number of sends at top grade, top grade reached (Font for
boulders, French for routes), session focus, RPE 1-10. Date defaults to today if not specified."`

**Warning signs:**
- Claude calls the tool with only 2-3 parameters despite the user having provided more information
  in the conversation
- Climbing activities appear in Intervals.icu without discipline or grade fields populated
- LLM asks about discipline/grade AFTER calling the tool, then tries to call again

**Phase to address:**
Phase covering tool design. Docstring quality is a first-class design concern for MCP write tools,
not documentation polish applied at the end.

---

### Pitfall 7: Returning Huge JSON Blobs from the Status Report Tool

**What goes wrong:**
The status report tool fetches recent activities, wellness entries, and CTL/ATL/TSB values, then
returns the raw API response as JSON. A 30-day activity list with wellness data can easily be
10,000+ tokens. This consumes the LLM's context budget, slows response time, and degrades the
quality of the status report reasoning because the LLM is processing noise rather than signal.

**Why it happens:**
The existing `format_activity_summary()` in `formatting.py` already produces ~50-line prose
blocks per activity. Multiplied across a 30-day window, the output of a naive status report
implementation is prohibitively large. The pattern of "return formatted string" works for
single-item tools but must be designed differently for aggregate analysis tools.

**How to avoid:**
The status report tool must aggregate and summarise before returning — not delegate summarisation
to the LLM. Return a structured plain-text report with fixed sections (Readiness today / Weekly
load summary / Trend). Each section should contain 3-5 key numbers plus 1-2 sentences of
interpretation context. Internally fetch all the data needed, but return only the distilled
summary. Budget the output at roughly 400-600 tokens. If the LLM or user needs the underlying
data, they can call `get_activities` or `get_wellness_data` separately.

**Warning signs:**
- Status report tool output is longer than 2000 tokens in test runs
- LLM produces generic or incoherent readiness recommendations (context crowding)
- Response latency is >10 seconds for the status report (large payload processing)

**Phase to address:**
Phase covering the status/readiness report tool. Define a token budget for the output as an
acceptance criterion. Review output size before shipping.

---

### Pitfall 8: CTL/ATL/TSB Without Climbing-Load Context Overstates Readiness

**What goes wrong:**
The status report reads CTL/ATL/TSB from the wellness endpoint (which Intervals.icu computes
natively). These metrics are based on the training stress scores (TSS) recorded for activities.
Manual climbing activities logged without power data or HR data will have low or zero TSS unless
`icu_rpe` is set (which feeds rpeTSS). If RPE is inconsistently logged, the CTL/ATL will
significantly undercount actual training stress. A "high fitness / low fatigue" reading may
actually mean "we don't have data to compute fatigue" — not that the athlete is fresh.

**Why it happens:**
Intervals.icu's TSS calculation for manual activities relies on `icu_rpe` + estimated duration to
compute rpeTSS. If `icu_rpe` is absent (i.e., logged before this milestone was in place, or if
the write tool fails silently), the activity contributes zero to training load. The status tool
has no way to distinguish "genuinely low load" from "load not recorded."

**How to avoid:**
(1) In the status report, count how many recent activities have `icu_rpe` set vs. null. If more
    than 30% of activities in the window lack RPE, include an explicit warning in the report:
    "Training load estimate may be incomplete — X of Y recent sessions missing RPE data."
(2) Treat absence of RPE as a data quality issue to surface, not silently ignore.
(3) When presenting TSB/readiness, always include a data-confidence qualifier alongside the
    number (e.g., "Based on 8 of 10 sessions with load data").

**Warning signs:**
- CTL reads unusually low despite subjective reports of heavy training
- Fitness trend flatlines over a period when the user knows they trained hard
- `icu_rpe` field is null on activities fetched via `get_activity_details`

**Phase to address:**
Phase covering the status report tool. Data-quality checks must be part of the report generation
logic, not a nice-to-have.

---

### Pitfall 9: Over-Interpreting Noisy Wellness Subjective Scores

**What goes wrong:**
The status report treats a single day's soreness=8 or fatigue=9 as a strong readiness signal and
recommends rest. But subjective wellness self-reports are high-variance — a particularly bad
morning, muscle soreness from a different cause (e.g., DOMS from unusual activity), or just
inconsistent self-assessment scale across days. Single-point subjective scores are not reliable
readiness indicators without trend context.

**Why it happens:**
It is easy to write `if fatigue > 7: recommend_rest()`. But subjective wellness scoring is
individually calibrated and noisy. Treating one data point as ground truth creates false positives
and erodes user trust in the tool.

**How to avoid:**
Always compute a rolling average (3-7 day window) of each subjective metric before using it in
readiness logic. Never make a strong recommendation from a single day's score. Present the trend
alongside the value: "Soreness today: 8/10 (avg past 5 days: 5.2)." Reserve strong "rest"
recommendations for combinations of signals: high subjective soreness AND low HRV AND high ATL —
not any single signal alone. The report should explain what combination triggered the
recommendation.

**Warning signs:**
- Status report recommends rest on a day the user reports feeling good
- User ignores the tool after several false-positive "rest day" recommendations
- Report shows single-day wellness values with no trend context

**Phase to address:**
Phase covering the status report tool. The rolling-window aggregation logic must be implemented
in the report generation, not left to the LLM to reason about from raw data.

---

### Pitfall 10: Retroactive Grade Updates Break Historical Grade Tracking

**What goes wrong:**
A user logs a session, then later decides the grade they assigned was wrong (common in climbing —
projecting sessions involve re-evaluation of a problem's difficulty). If the grade is stored in an
Intervals.icu custom field and later overwritten, the historical record is silently mutated. There
is no diff or audit trail. Trend analysis ("when did I first send Font 7A?") becomes unreliable.

**Why it happens:**
Intervals.icu custom fields do not version their values. A PUT to the activity simply overwrites
the field. If the enrichment tool is called twice on the same activity (e.g., once to log the
session and again to correct the grade), the first value is gone.

**How to avoid:**
(1) Treat grade writes as one-time at session completion. If correction is needed, require an
    explicit `override_grade=True` parameter to signal intentional mutation.
(2) Append corrections as an activity message/note via `add_activity_message` rather than
    silently overwriting the field. This preserves the history in the activity's message log.
(3) Document the mutability limitation clearly: "Grades stored in custom fields are not versioned.
    Use activity notes to record grade corrections with rationale."

**Warning signs:**
- User calls the enrichment tool twice on the same activity
- Climbing progress trends show inconsistencies that don't match user recollection
- No mechanism to see what grade was originally assigned before a correction

**Phase to address:**
Phase covering activity enrichment. The override guard must be implemented alongside the first
enrichment tool — not added reactively after a user reports lost data.

---

### Pitfall 11: Coupling New Climbing Tools to Private Helpers Not Designed as Internal API

**What goes wrong:**
The new `climbing.py` tool module imports and reuses a private helper from `activities.py` (e.g.,
`_parse_activities_from_result`, `_filter_named_activities`). A later change to `activities.py`
to fix its known parsing heuristic bug (flagged in CONCERNS.md) silently breaks the climbing
tool. The helper was never intended as a stable internal interface.

**Why it happens:**
Private helpers with `_` prefix in the existing modules are implementation details that could
change. Code reuse is natural — why re-implement `_parse_activities_from_result` when it
already exists? But it was designed for one calling pattern and may not handle the different
response shapes from activity-creation endpoints.

**How to avoid:**
(1) Any function shared between the climbing module and existing modules must be promoted to a
    shared utility location (`utils/`) with a public name and explicit test coverage.
(2) Do not import `_`-prefixed functions from sibling tool modules. If the function is worth
    sharing, move it.
(3) In particular: activity response parsing logic needed by the climbing tool should be
    re-examined and placed in `utils/` as a distinct, tested function, given the known heuristic
    bug in the current implementation (CONCERNS.md: "_parse_activities_from_result error dict
    misclassification").

**Warning signs:**
- `from intervals_mcp_server.tools.activities import _parse_activities_from_result` appearing in
  `climbing.py`
- A change to `activities.py` breaks a test in `test_climbing.py`
- Private helpers appearing in `__init__.py` as public exports

**Phase to address:**
Phase covering codebase extension and the climbing module structure. Module boundary decisions must
be made explicitly before writing the climbing tool, not refactored post-hoc.

---

### Pitfall 12: Regressing Existing Tool Signatures During Brownfield Extension

**What goes wrong:**
While adding the climbing module, a developer refactors a shared utility (`format_activity_summary`,
`resolve_athlete_id`, `make_intervals_request`) to accommodate climbing-specific needs. The
change inadvertently breaks an existing tool's behavior — for example, changing the response
format of `format_activity_summary` causes `get_activity_details` to omit fields the user was
relying on. Since the existing tests only assert `"Activity: Morning Ride" in result` (string
contains checks), the regression passes CI.

**Why it happens:**
The existing test coverage is characterised in TESTING.md and CONCERNS.md as: "concentrated on
the HTTP client + formatters," "only with sample data," and "only verifies happy path and basic
error cases." String-contains assertions do not catch formatter regressions that remove or
reformat fields.

**How to avoid:**
(1) Treat existing tool output formats as a contract. Before modifying any shared utility,
    snapshot its current output for representative inputs.
(2) Add regression tests that assert on the complete output structure of key formatters if
    modifying them — not just `in` checks.
(3) New climbing-specific formatting should live in a new `format_climbing_activity()` function,
    not modify `format_activity_summary()`. Extend, don't mutate.
(4) Run the full test suite before and after each utility change to detect regressions before
    merging.

**Warning signs:**
- Utility function signature changes (added required parameter, changed return shape)
- Existing test file for a utility is not updated when the utility is changed
- CI passes but manual smoke-test shows missing fields in existing tool output

**Phase to address:**
All phases involving shared utility modification. This is an ongoing discipline, not a one-time
task — establish it in the first brownfield phase with an explicit note in the PR checklist.

---

### Pitfall 13: MCP Server Restart Assumption — Tool Not Available Until Restart

**What goes wrong:**
A new climbing tool is implemented and deployed, but the user's Claude Desktop instance is still
running the old MCP server process. The new tool is invisible to the LLM. The user reports "the
tool doesn't work" when in fact it simply hasn't been registered yet. Alternatively, the developer
tests via a hot-reload assumption that doesn't apply to stdio MCP transport.

**Why it happens:**
FastMCP over stdio transport registers tools at server startup via `@mcp.tool()` decorator
import-time execution. There is no live tool-discovery refresh — the tool list is negotiated at
session start. This is implicit from the architecture but not documented as a deployment
constraint.

**How to avoid:**
Document explicitly: "After adding new tools, restart the MCP server process and reconnect the
Claude Desktop client." Add this to the CONTRIBUTING guide and any deployment checklist. In tests,
always import the tool module explicitly to trigger registration, rather than assuming it happens
automatically.

**Warning signs:**
- New tool not appearing in Claude's available tools list after deployment
- User reporting "Claude doesn't know about the climbing tool"
- Developer testing by modifying code without restarting the server process

**Phase to address:**
Phase covering initial climbing module setup. Document the restart requirement in the README
addition for this milestone.

---

### Pitfall 14: Test Drift — Climbing Tool Tests Not Wired to CI

**What goes wrong:**
Climbing tool tests are added to a new file `tests/test_climbing.py` but the file is not
discovered by pytest because of a naming or import issue, or because the developer runs a subset
of tests during development and never verifies the full suite runs. The CI pipeline never catches
bugs in the climbing-specific code paths.

**Why it happens:**
The existing test suite uses `pytest -v tests` (via `.pre-commit-config.yaml`). This auto-discovers
`test_*.py` files. A common mistake: naming the file `climbing_tests.py` (does not match the
`test_*.py` pattern) or placing it outside `tests/`. TESTING.md shows the existing structure
clearly, but it is easy to miss when adding files under time pressure.

**How to avoid:**
Name all new test files `test_climbing.py`, `test_wellness_write.py`, etc., and place them in
`tests/`. Verify that `pytest -q` discovers and runs them before considering a phase complete.
Use `pytest --collect-only` to confirm the test count increases. Mock pattern for new tests must
follow the established pattern (monkeypatch `make_intervals_request`, use `asyncio.run()`), as
documented in TESTING.md.

**Warning signs:**
- `pytest --collect-only` shows the same number of tests before and after adding a new test file
- A test file exists in `tests/` but does not follow the `test_*.py` naming convention
- Developer references a test by running it directly (`python tests/climbing_tests.py`) instead
  of via pytest

**Phase to address:**
Every phase that adds new tools. Treat "tests discovered by `pytest --collect-only`" as a done
criterion alongside "tests pass."

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip readback verification after custom field write | Simpler implementation | Silent data loss; user trusts the tool but data is not stored | Never — readback is cheap and prevents invisible failures |
| Use free-text grade field (no validation) | Faster to implement | Cross-scale contamination; trend analysis breaks | Never for this project — scale is fixed (Font + French) |
| Return raw API JSON from status report | No formatting code needed | Massive LLM context consumption; degrades report quality | Never — aggregation is the tool's job |
| Import private helpers from sibling tool modules | Avoids code duplication | Tight coupling; changes to source module break consumer silently | Never — promote to shared utility instead |
| Hardcode grade validation as inline `if` chains | Simple to write | Hard to extend to V-scale/YDS in v2 without rewriting | Acceptable in v1 if the validation function is clearly isolated behind one entry point |
| Log session data to activity `description` field instead of custom fields | No user setup required | Not queryable; can't build trend analysis; breaks if description already has content | Only as emergency fallback with explicit warning to user |
| Use `datetime.now()` for `start_date_local` | No user input required | Date shifts across midnight (timezone pitfall #4) | Never — always take date from user input |

---

## Integration Gotchas

Common mistakes when connecting to Intervals.icu.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Intervals.icu activity creation | POSTing without checking for existing activity on same date | GET activities for date first; offer enrichment if found |
| Intervals.icu custom field write | Writing fields before they are defined in account settings | Document required fields as user prerequisite; verify readback after write |
| Intervals.icu wellness write | Sending `null` values for fields the user did not provide | Omit absent keys from the PUT body entirely; Intervals.icu treats `null` as "clear this field" |
| Intervals.icu event↔activity linking | Using UTC datetime for `start_date_local` | Always use local midnight format `YYYY-MM-DDT00:00:00` (no offset) |
| Intervals.icu RPE field | Using a custom RPE field instead of native `icu_rpe` | Use `icu_rpe` (1-10 integer) — this is what feeds rpeTSS and Intervals.icu's own load math |
| Intervals.icu rate limits | Rapid burst of API calls in status report (activities + wellness + events in parallel) | Sequence calls; current client has no rate-limit handling — 429s return error dict, which propagates as a confusing tool error |
| `make_intervals_request()` error return | Checking `result["error"]` but not `result.get("error")` | The key is `"error": True` (boolean) — always use `.get("error")` or `isinstance` check as existing tools do |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Fetching 30 days of activities to find one session | Status report is slow (multiple serial API calls) | Narrow date range; use specific date lookup when available | Every status report call (this is day-1 behaviour, not a scale issue) |
| `format_activity_summary()` per activity × 30 days | Status report output is 10,000+ tokens | Aggregate at tool level, return distilled summary | Immediately — status report is the first caller at this scale |
| No caching of CTL/ATL/TSB | Fetching wellness endpoint on every status report call | Cache is out of scope (stateless server), so minimise the date range queried | Single user, low frequency — acceptable for v1, monitor |
| `_fetch_more_activities()` serial fallback in existing `get_activities` | Double API call when named activity count is low (climbing sessions are often named) | Not a new problem — climbing activities should be named, reducing the fallback frequency | Already present in codebase; climbing activities must be named at creation time |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Logging the full climbing session payload at DEBUG level | Grades, RPE, session notes appear in debug logs alongside API key body | `api/client.py` already logs POST body at DEBUG — ensure new climbing payloads do not include PII beyond what existing activities log |
| Returning Intervals.icu error body verbatim when custom field write fails | Error response may include field schema details | Already mitigated by `_get_error_message()` mapping — maintain this pattern in climbing tools |
| Accepting grade or discipline values in API calls without sanitisation | Injection into API URL or query parameter | All values are in JSON body (not URL params) via `make_intervals_request(data=...)`; validate with enum/regex before sending |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Status report with no "why" explanation | User sees "TSB: -12, consider rest" but doesn't know what drove it | Always include a 1-sentence explanation: "ATL (43) exceeds CTL (38) by more than 10% and sleep quality was poor yesterday" |
| Single-number readiness score | Hides which dimension drove the score; user can't act on it | Surface the 2-3 signals that most influenced the recommendation, not just a composite score |
| Asking "what grade did you send?" without context | Ambiguous for mixed-discipline sessions | Ask "was this bouldering or routes?" first, then ask for grade using the appropriate scale label explicitly |
| Reporting "no data" for wellness metrics not yet logged today | User thinks tool is broken | Distinguish "no data for today yet" from "no data exists in this date range" in the message |
| Completing a session without confirming the planned event was linked | User discovers planned and actual are unlinked days later | After creating an activity, check the planned event for that date and confirm or report linking status |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **`complete_climbing_session` tool:** Duplicate guard — verify a GET for existing activities on target date is implemented before POST
- [ ] **Custom field writes:** Readback verification — confirm custom fields appear in the activity after PUT, not just that PUT returned 200
- [ ] **Grade validation:** Cross-discipline check — grade pattern is validated against declared discipline, not just as a standalone string format
- [ ] **Wellness write:** Null-value handling — verify that fields the user did not mention are omitted from the PUT body, not sent as `null`
- [ ] **Status report:** Token budget — verify output is under ~600 tokens in a realistic scenario with 30 days of data
- [ ] **Status report:** Data-quality flag — verify report warns when >30% of recent activities lack RPE data
- [ ] **Test discovery:** Run `pytest --collect-only` and confirm all new test files appear in the collected test list
- [ ] **MCP restart:** Verify new tools appear in Claude's tool list after restart, not just in unit tests
- [ ] **Event linking:** Confirm the activity `start_date_local` format matches the planned event format (both `YYYY-MM-DDT00:00:00`, no offset)
- [ ] **Grade retroactive update:** Confirm calling enrichment tool twice on same activity either errors or requires explicit override flag

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Duplicate activity created | MEDIUM | Identify duplicate via `get_activities`; delete via Intervals.icu web UI (no delete-activity endpoint confirmed in current code); merge data manually |
| Custom fields not stored (silent write failure) | LOW | User defines fields in account settings; re-run enrichment tool; data from the session must be re-entered |
| Grade scale contamination | MEDIUM | Activity-by-activity audit via `get_activity_details`; manual correction via enrichment tool with override; no automated fix possible |
| Retroactive grade overwrite (lost original) | HIGH (if not mitigated) | Check activity messages for any logged correction history; otherwise original grade is permanently lost |
| Regression in existing tool formatter | LOW (if tests exist) | Revert the utility change; promote the climbing-specific variant to a separate function |
| Test file not discovered by CI | LOW | Rename to `test_*.py`, confirm with `pytest --collect-only`, push |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Duplicate activity on retry (P1) | Activity creation / completion phase | Integration test: call create twice, verify single activity returned |
| Silent custom field write failure (P2) | Activity enrichment phase | Test: mock API returning 200 with missing field; assert warning in response |
| Grade system ambiguity (P3) | Climbing data model / enrichment phase | Unit tests: valid and invalid grade+discipline combinations |
| Event↔activity timezone mismatch (P4) | Activity creation / completion phase | Test: `start_date_local` format equality between events and activities |
| Stateless contract violation (P5) | Tool design phase (first climbing tool) | Code review criterion: no module-level mutable state for in-progress calls |
| Tool docstrings too terse (P6) | Tool design phase | Manual test: Claude calls tool and asks all required fields without prompting |
| Huge JSON from status report (P7) | Status report phase | Output token count test: assert len(output) < 3000 chars for realistic input |
| CTL/ATL without climbing load context (P8) | Status report phase | Manual test: status report with mix of RPE-present and RPE-absent activities |
| Over-interpreting single wellness score (P9) | Status report phase | Unit test: single high soreness score does not trigger strong rest recommendation alone |
| Retroactive grade overwrite (P10) | Activity enrichment phase | Test: second enrichment call on same activity returns error or requires override |
| Coupling to private helpers (P11) | Climbing module structure phase | Code review: no `_`-prefixed imports from sibling tool modules |
| Regressing existing tool signatures (P12) | All phases touching shared utilities | Run full test suite before and after any shared utility change |
| MCP server restart assumption (P13) | Initial climbing module setup phase | Manual check: restart server, verify tool appears in Claude's list |
| Test drift / CI blindspot (P14) | Every phase adding new tools | `pytest --collect-only` count increases; run full suite to confirm |

---

## Sources

- Codebase direct read: `src/intervals_mcp_server/` (all modules, 2026-04-24)
- `.planning/PROJECT.md` — stated constraints, key decisions, known prerequisites
- `.planning/codebase/CONCERNS.md` — known issues, fragile areas, test coverage gaps
- `.planning/codebase/INTEGRATIONS.md` — Intervals.icu API endpoints and auth patterns
- `.planning/codebase/TESTING.md` — test structure, patterns, pre-commit hook configuration
- `.planning/codebase/ARCHITECTURE.md` — layer boundaries, data flow, error handling strategy
- `.planning/codebase/CONVENTIONS.md` — naming, error patterns, module design rules
- Domain knowledge: MCP stateless contract (FastMCP documentation pattern), climbing grade systems
  (Font, French sport nomenclature), Intervals.icu custom field semantics (account-defined prerequisite)

---
*Pitfalls research for: climbing-training-aware extension to intervals-mcp-server*
*Researched: 2026-04-24*
