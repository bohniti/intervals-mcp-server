# Phase 5: Server Wiring and Acceptance — Pattern Map

**Mapped:** 2026-04-29
**Files analyzed:** 6 (2 modified, 4 created)
**Analogs found:** 6 / 6 (all exact role + data-flow matches; every new artifact has a shipped sibling in the repo)

This phase ships **no new tool surface and no new HTTP**. Every change either repeats an existing pattern (the `__all__` block, the README setup-section style, the live-smoke script template, the prior phase findings layout) or asserts that those patterns hold (the registration test, the manual checklist). All line numbers are stable as of HEAD; the planner can hand verbatim references to the executor.

---

## File Classification

| New/Modified File | Action | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|--------|------|-----------|----------------|---------------|
| `src/intervals_mcp_server/server.py` | MODIFY | re-export wiring (entry point) | static (import-time registration + `__all__`) | itself — existing activities/events/custom_items named-import + `__all__` blocks (lines 72–94, 100–122) | exact (self-analog; D-01 extends the same template) |
| `README.md` | MODIFY | doc | static prose | itself — existing "Climbing setup — required Intervals.icu custom fields" section (lines 75–117) and "Verifying the setup" subsection (lines 106–117) | exact (sibling section, same heading depth + tone) |
| `tests/test_server_registration.py` | CREATE | test | request-response (await `mcp.list_tools()`) | `tests/test_server.py` (header + `from intervals_mcp_server.server import …` pattern, lines 1–46) + `tests/test_climbing.py` (`asyncio` + `monkeypatch` + `os.environ.setdefault`, lines 1–19) | exact (same `sys.path` insert + import-driven registration, plus async-list-tools query) |
| `scripts/smoke_phase5.py` | CREATE | script (live smoke) | live request-response (POST/PUT/GET/DELETE via `make_intervals_request`) | `scripts/smoke_phase2.py` (header, redaction, far-future date, `try/finally` cleanup, exit codes) + `scripts/spike_write_endpoints.py` (findings-write helper) | exact (Phase 2 is the immediate predecessor; same shape, more steps) |
| `.planning/phases/05-server-wiring-and-acceptance/05-LIVE-SMOKE.md` | CREATE | planning artifact (manual checklist) | static (human-driven) | `.planning/phases/02-wellness-write-and-activity-enrichment/02-HUMAN-UAT.md` (lines 1–35) | role-match (HUMAN-UAT is a checklist; LIVE-SMOKE is one row per tool) |
| `.planning/phases/05-server-wiring-and-acceptance/05-SMOKE-FINDINGS.md` | CREATE (script-written or hand-curated) | planning artifact (findings) | static (script output → markdown) | `.planning/phases/01-foundation-and-write-path-spike/01-SPIKE-FINDINGS.md` (lines 1–6 header) + `.planning/phases/02-wellness-write-and-activity-enrichment/02-SPIKE-FINDINGS.md` (lines 1–7 header + JSON-fence body) | exact (same header skeleton + redacted JSON-fence pattern) |

Cross-cutting analogs referenced from multiple new files:
- `src/intervals_mcp_server/api/client.py::make_intervals_request` — sole HTTP boundary (PROJECT.md / D-13). Smoke script imports this and nothing else for HTTP.
- `src/intervals_mcp_server/mcp_instance.py` — the `mcp` singleton. The registration test queries `await mcp.list_tools()`.
- `src/intervals_mcp_server/tools/wellness.py::write_wellness_entry` (lines 87–101) — public param surface the smoke script calls.
- `src/intervals_mcp_server/tools/climbing.py` — public surfaces the smoke script calls: `verify_custom_fields_setup` (376–408), `enrich_activity_climbing` (420–432), `create_climbing_activity` (542–556), `complete_climbing_session` (732–744).
- `src/intervals_mcp_server/tools/status.py::get_training_status` (lines 41–45) — read-only call in smoke step 6.
- `src/intervals_mcp_server/tools/events.py::add_or_update_event` (282–292) — used by smoke step 5 to create a planned event before `complete_climbing_session`.

---

## Pattern Assignments

### `src/intervals_mcp_server/server.py` (re-export wiring; MODIFY)

**Analog:** itself. The file already contains the exact pattern D-01 extends — three named-import blocks (activities, events, custom_items) plus `__all__`. Phase 5 extends the wellness import (currently single-name) and the climbing import (currently single-name) to match.

#### A. Module docstring "MCP tools provided" list (D-02)

**Existing block at lines 23–42:**

```python
    MCP tools provided:
        - get_activities
        - get_activity_details
        - get_activity_intervals
        - get_activity_streams
        - get_activity_messages
        - add_activity_message
        - get_events
        - get_event_by_id
        - add_or_update_event
        - delete_event
        - delete_events_by_date_range
        - get_wellness_data
        - get_custom_items
        - get_custom_item_by_id
        - create_custom_item
        - update_custom_item
        - delete_custom_item

    See the README for more details on configuration and usage.
```

**Apply:** append the six milestone tools (already-shipped: `verify_custom_fields_setup`, plus the four new ones, plus `get_training_status`) to this list. Insertion order is acceptable per CONTEXT specifics ("bullet ordering is cosmetic"); recommend grouping the climbing block together at the bottom for git-blame clarity:

```python
        - verify_custom_fields_setup
        - write_wellness_entry
        - enrich_activity_climbing
        - create_climbing_activity
        - complete_climbing_session
        - get_training_status
```

#### B. Wellness named-import line (line 87) — D-01

**Existing (single name):**

```python
from intervals_mcp_server.tools.wellness import get_wellness_data  # pylint: disable=wrong-import-position  # noqa: E402
```

**Pattern to copy from (multi-name template):** lines 72–79:

```python
from intervals_mcp_server.tools.activities import (  # pylint: disable=wrong-import-position  # noqa: E402
    add_activity_message,
    get_activities,
    get_activity_details,
    get_activity_intervals,
    get_activity_messages,
    get_activity_streams,
)
```

**Apply (verbatim shape) — convert wellness import to multi-name parenthesized form:**

```python
from intervals_mcp_server.tools.wellness import (  # pylint: disable=wrong-import-position  # noqa: E402
    get_wellness_data,
    write_wellness_entry,
)
```

Keep the trailing `# pylint: disable=wrong-import-position  # noqa: E402` on the opening line — every other multi-name block in this file uses that exact comment shape.

#### C. Climbing named-import line (line 95) — D-01

**Existing (single name):**

```python
from intervals_mcp_server.tools.climbing import verify_custom_fields_setup  # pylint: disable=wrong-import-position  # noqa: E402
```

**Apply — extend to four names, alphabetized per CONTEXT specifics ("alphabetically within the climbing block"):**

```python
from intervals_mcp_server.tools.climbing import (  # pylint: disable=wrong-import-position  # noqa: E402
    complete_climbing_session,
    create_climbing_activity,
    enrich_activity_climbing,
    verify_custom_fields_setup,
)
```

#### D. `__all__` extension (lines 100–122) — D-01

**Existing block:**

```python
__all__ = [
    "make_intervals_request",
    "httpx_client",  # Re-exported for test compatibility
    "add_activity_message",
    ...
    "delete_custom_item",
    "verify_custom_fields_setup",
    "get_training_status",
]
```

**Apply — append 4 new names without re-sorting (CONTEXT specifics: "Don't re-sort — minimizes diff and preserves git blame"):**

```python
    "verify_custom_fields_setup",
    "enrich_activity_climbing",
    "create_climbing_activity",
    "complete_climbing_session",
    "write_wellness_entry",
    "get_training_status",
```

Recommended insertion: keep `verify_custom_fields_setup` first in the climbing group (Phase 1 anchor), append the three new climbing names directly after it, then `write_wellness_entry` (logically near `get_wellness_data` though that's already higher in the list — accept the cosmetic break for diff minimality), then keep `get_training_status` last.

#### E. What stays unchanged (D-15 carry-forward)

- All pre-existing import order, comments, the `# pylint: disable=duplicate-code` directive on line 99, and the `if __name__ == "__main__":` block (lines 126–132) stay verbatim.
- Tool modules themselves (`tools/wellness.py`, `tools/climbing.py`, `tools/status.py`) are read-only this phase.

---

### `README.md` (doc; MODIFY)

**Two changes:** intro paragraph refresh (D-04) + new top-level `## Climbing tools` section with five subsections (D-03).

#### A. Intro paragraph refresh (line 3) — D-04

**Existing line 3:**

```markdown
Model Context Protocol (MCP) server for connecting Claude and ChatGPT with the Intervals.icu API. It provides tools for authentication and data retrieval for activities, events, and wellness data.
```

**Apply — add the three new domains without enumerating every tool:**

```markdown
Model Context Protocol (MCP) server for connecting Claude and ChatGPT with the Intervals.icu API. It provides tools for retrieving activities, events, and wellness data; creating and enriching climbing activities (with discipline, grades, RPE, and session focus); writing wellness entries (sleep, soreness, HRV, RHR, subjective metrics); and getting a single training-status report blending CTL/ATL/TSB load metrics with recent wellness signals.
```

Keep one sentence. The pitch should mention climbing session completion, wellness writes, and the status report (D-04 explicit).

#### B. New "Climbing tools" top-level section — D-03

**Sibling-section template (style, heading depth, tone):** the existing "Climbing setup — required Intervals.icu custom fields" section at lines 75–117. Note the heading is `## Climbing setup — …` with subsections at `### Verifying the setup` (line 106). The new section uses the same `## Climbing tools` top-level heading and `### <tool_name>` subsections — five of them.

**Subsection mini-template (apply per tool — each ~5 lines):**

```markdown
### `<tool_name>`

<One sentence on what the tool does. Mirror the first sentence of the tool's docstring — Pitfall #6 carry-forward, README is the discovery surface, the canonical detail lives in the docstring.>

<One sentence on when Claude should use it / what context the user is in.>

```text
<One paste-ready example invocation showing the most common parameter shape. Plain-text fence; mirror tool function call style.>
```
```

**Tool-by-tool source for the "what it does" sentence (copy from the docstring's first line, paraphrase if needed):**

| Tool | Source location for the docstring lead | Suggested example invocation shape |
|------|----------------------------------------|------------------------------------|
| `write_wellness_entry` | `tools/wellness.py:102` ("Log a wellness entry for an athlete on a given date.") | `write_wellness_entry(date="2026-04-28", sleep_hours=7.5, soreness=2)` |
| `enrich_activity_climbing` | `tools/climbing.py:434` ("Enrich an existing Intervals.icu activity with climbing metadata + RPE.") | `enrich_activity_climbing(activity_id="i12345", discipline="bouldering", indoor=True, top_grade_sent="6A+", sends=4, attempts=7, rpe=6)` |
| `create_climbing_activity` | `tools/climbing.py:557` ("Create a climbing activity from scratch on Intervals.icu (CLIMB-02).") | `create_climbing_activity(date="2026-04-28", duration_minutes=90, discipline="sport_lead", indoor=False, top_grade_sent="6c+", rpe=7)` |
| `complete_climbing_session` | `tools/climbing.py:745` ("Complete a planned climbing event by creating a linked activity (CLIMB-01).") | `complete_climbing_session(event_id="i98765", discipline="bouldering", session_focus="projecting", rpe=8)` |
| `get_training_status` | `tools/status.py:46` ("Return a plain-text training-status report.") | `get_training_status()` (or `get_training_status(as_of_date="2026-04-28")`) |

#### C. Placement (CONTEXT line 125)

The new section lands as **a top-level `## Climbing tools` section AFTER the existing "Climbing setup" section**, before the existing `## Updating` heading at line 119. So the order becomes:

```
## Climbing setup — required Intervals.icu custom fields   (existing, lines 75–117)
## Climbing tools                                           (NEW — D-03)
## Updating                                                 (existing, line 119+)
```

Two top-level sections side-by-side: setup first (prerequisite), then the tools that depend on it. Mirrors the natural flow.

#### D. What stays unchanged

- The "Setup" / "Requirements" / "Climbing setup" / "Updating" / "Usage with Claude" / "Usage with ChatGPT" / "Development and testing" / "License" / "Featured" sections all stay verbatim.
- The custom-field table at lines 86–94 is the canonical SETUP-01 reference — Phase 5 does NOT duplicate or restate it.
- The existing `verify_custom_fields_setup` example at lines 112–114 is preserved; the new `## Climbing tools` section does NOT add a sixth subsection for `verify_custom_fields_setup` (D-03: "Five subsections — verify is already documented in Phase 1").

---

### `tests/test_server_registration.py` (test; CREATE)

**Primary analog (header + import-driven registration):** `tests/test_server.py` lines 1–46.
**Secondary analog (async + env-setup pattern):** `tests/test_climbing.py` lines 1–19.

#### A. File header and sys-path / env setup

**From `tests/test_server.py:19–44`:**

```python
import asyncio
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

from intervals_mcp_server.server import (  # pylint: disable=wrong-import-position
    add_activity_message,
    add_or_update_event,
    ...
)
```

**Apply — copy the sys.path + env block verbatim, then import the module-level `mcp` from `intervals_mcp_server.server`** (the import triggers registration via the chain `server → tools/* → @mcp.tool()`). The test does NOT need to call `register_tools()` — decorator side-effects on import handle it (per `tools/__init__.py:38`: "Tools are registered via decorators when modules are imported").

```python
"""
Registration assertion test for the Phase 5 milestone tool surface.

Imports `intervals_mcp_server.server` (which transitively imports every
tool module, triggering @mcp.tool() decorator registration), then queries
the FastMCP instance for its registered tool list and asserts the full
expected name set is present. Catches the silent-removal failure mode:
if a `from .tools.X import Y` line is deleted in server.py, the tool
quietly drops off `tools/list` — this test fails before that ships.
"""

import asyncio
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

# Importing server triggers tool registration via @mcp.tool() decorators.
from intervals_mcp_server import server  # noqa: F401  pylint: disable=wrong-import-position,unused-import
from intervals_mcp_server.mcp_instance import mcp  # pylint: disable=wrong-import-position
```

#### B. `EXPECTED_TOOLS` constant (D-06: "Single source of truth")

```python
# Single source of truth for "what tools this milestone ships".
# Mirrors src/intervals_mcp_server/server.py __all__ minus the two
# non-tool re-exports (`make_intervals_request`, `httpx_client`).
EXPECTED_TOOLS: frozenset[str] = frozenset(
    {
        # Activities (Phase 0 baseline)
        "get_activities",
        "get_activity_details",
        "get_activity_intervals",
        "get_activity_streams",
        "get_activity_messages",
        "add_activity_message",
        # Events (Phase 0 baseline)
        "get_events",
        "get_event_by_id",
        "add_or_update_event",
        "delete_event",
        "delete_events_by_date_range",
        # Wellness
        "get_wellness_data",
        "write_wellness_entry",        # Phase 2
        # Custom items (Phase 0 baseline)
        "get_custom_items",
        "get_custom_item_by_id",
        "create_custom_item",
        "update_custom_item",
        "delete_custom_item",
        # Climbing (Phase 1 + Phase 2 + Phase 3)
        "verify_custom_fields_setup",
        "enrich_activity_climbing",
        "create_climbing_activity",
        "complete_climbing_session",
        # Status (Phase 4)
        "get_training_status",
    }
)
```

#### C. Async query pattern — `await mcp.list_tools()`

**Verified API shape** (confirmed against the FastMCP version in `uv.lock` via `uv run`):

```text
mcp.list_tools() is an async coroutine returning list[Tool]
Tool has .name (str), .description (str), .inputSchema (dict)
```

**Apply — wrap in `asyncio.run` per `tests/test_server.py:69` ("`asyncio.run(get_activities(...))`") pattern:**

```python
def _registered_tool_names() -> frozenset[str]:
    """Return the set of tool names FastMCP currently has registered."""
    tools = asyncio.run(mcp.list_tools())
    return frozenset(t.name for t in tools)


def test_all_expected_tools_registered() -> None:
    """Every milestone tool is reachable via FastMCP's tool list."""
    registered = _registered_tool_names()
    missing = EXPECTED_TOOLS - registered
    assert not missing, (
        f"Tools missing from FastMCP registry: {sorted(missing)}. "
        f"Likely cause: a `from .tools.X import Y` line was deleted "
        f"in src/intervals_mcp_server/server.py. Re-add it."
    )


def test_no_unexpected_tools_registered() -> None:
    """No surprise tools — the expected set IS the milestone surface."""
    registered = _registered_tool_names()
    extra = registered - EXPECTED_TOOLS
    assert not extra, (
        f"Unexpected tool names registered: {sorted(extra)}. "
        f"Either add them to EXPECTED_TOOLS in this test, or remove the "
        f"@mcp.tool() decorator that registered them."
    )
```

The two-test split (missing vs extra) is optional but recommended — gives a clearer assertion message when either side drifts. Per D-06, a single `assert registered == EXPECTED_TOOLS` is also acceptable.

#### D. What NOT to do

- **No `monkeypatch`** — this test does not exercise HTTP, only the registry. Don't import `make_intervals_request` or any tool function directly (Pitfall #14 carry-forward keeps the test minimal).
- **No reaching into `_tool_manager`** — `list_tools()` is the public API; private state inspection is brittle (D-14 spirit).
- **No `pytest.mark.asyncio`** — the rest of the suite uses `asyncio.run(...)` inside sync tests (every existing async test in `test_server.py`, `test_climbing_write.py` does this). Match the convention.

---

### `scripts/smoke_phase5.py` (script, live smoke; CREATE)

**Primary analog:** `scripts/smoke_phase2.py` (lines 1–197). Phase 2's smoke script is the immediate template — same shape, same redaction, same `try/finally` cleanup; Phase 5 extends it to cover the four new tool surfaces plus the read-only status call.

**Secondary analog:** `scripts/spike_write_endpoints.py` (lines 252–289) for the `write_findings()` helper that emits a markdown findings file with redacted JSON fences.

#### A. File header (copy verbatim shape from `smoke_phase2.py:1–53`)

```python
#!/usr/bin/env python3
"""
Smoke test: Phase 5 acceptance — every milestone tool against live Intervals.icu.

NOT A PYTEST TEST. Writes to live Intervals.icu at far-future dates
(2099-01-01 wellness/activity, 2099-01-02 planned event) using the full
Phase 1–4 tool path:
  1. verify_custom_fields_setup — confirm SETUP-01 still satisfied
  2. write_wellness_entry — PUT wellness on 2099-01-01
  3. create_climbing_activity — POST climbing activity on 2099-01-01
  4. enrich_activity_climbing — add fields against the activity from step 3
  5. complete_climbing_session — create planned event on 2099-01-02, then complete
  6. get_training_status — read-only sanity check
  7. Cleanup: DELETE both created activities, DELETE the planned event

Run once, by hand:

    uv run scripts/smoke_phase5.py

Pre-requisites: API_KEY and ATHLETE_ID set in .env, plus the seven
climbing custom fields defined in the athlete's Intervals.icu account
(per README "Climbing setup" section / SETUP-01).

Exit codes:
    0  All steps OK; readback values matched sent values; cleanup succeeded.
    1  Configuration error OR a step failed OR cleanup failed.

This script complements the unit suite — unit tests prove logic; this
script proves end-to-end live API correctness for the milestone surface.
By design it is NOT discoverable by `pytest --collect-only` (file lives
under scripts/, file name does not start with test_, no def test_*).
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

# Mirror the sys.path pattern used by tests and prior smoke scripts.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from intervals_mcp_server.api.client import make_intervals_request  # noqa: E402
from intervals_mcp_server.config import get_config  # noqa: E402
from intervals_mcp_server.tools.climbing import (  # noqa: E402
    complete_climbing_session,
    create_climbing_activity,
    enrich_activity_climbing,
    verify_custom_fields_setup,
)
from intervals_mcp_server.tools.events import add_or_update_event  # noqa: E402
from intervals_mcp_server.tools.status import get_training_status  # noqa: E402
from intervals_mcp_server.tools.wellness import write_wellness_entry  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("smoke_phase5")

SMOKE_DATE = "2099-01-01"        # wellness + create_climbing_activity
SMOKE_EVENT_DATE = "2099-01-02"  # planned event for complete_climbing_session
ATHLETE_REDACTED = "{athlete_id}"
```

Note: `add_or_update_event` is imported because step 5 needs to create a planned event before `complete_climbing_session` can consume it (the script is end-to-end; CONTEXT specifics line 169: "complete_climbing_session against a freshly-created planned event").

#### B. Redaction helper (verbatim from `smoke_phase2.py:58–66`)

```python
def _redact(obj: Any, athlete_id: str) -> Any:
    """Recursively replace athlete_id with placeholder for logged output."""
    if isinstance(obj, str):
        return obj.replace(athlete_id, ATHLETE_REDACTED)
    if isinstance(obj, dict):
        return {k: _redact(v, athlete_id) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact(v, athlete_id) for v in obj]
    return obj
```

#### C. Main flow shape (extend `smoke_phase2.py:69–192`)

The Phase 2 script is the structural template: `async def main() -> int`, config check at top, `try` body for steps, `finally` block for cleanup, `failures: list[str]` accumulator, return 0 on no failures and 1 otherwise.

**Key extensions for Phase 5 (CONTEXT D-09 step ordering — verify first, status last):**

```python
async def main() -> int:  # pylint: disable=too-many-locals,too-many-statements,too-many-branches,too-many-return-statements
    config = get_config()
    athlete_id = config.athlete_id
    if not athlete_id:
        logger.error("ATHLETE_ID not set in environment — abort.")
        return 1
    if not config.api_key:
        logger.error("API_KEY not set in environment — abort.")
        return 1

    logger.warning(
        "About to write to live Intervals.icu at SMOKE_DATE=%s / SMOKE_EVENT_DATE=%s. "
        "Cleanup runs in finally.",
        SMOKE_DATE, SMOKE_EVENT_DATE,
    )

    create_activity_id: str | None = None
    completion_activity_id: str | None = None
    planned_event_id: str | None = None
    failures: list[str] = []

    try:
        # Step 1 — verify_custom_fields_setup (carry-over sanity / D-09 #1)
        # If this fails, every climbing-write step would hard-block on the
        # custom-field guard. Fail fast with a clear pointer to the README.
        logger.info("Step 1: verify_custom_fields_setup()")
        verify_result = await verify_custom_fields_setup()
        logger.info("Verify result:\n%s", _redact(verify_result, athlete_id))
        if "missing" in verify_result.lower() and "0 missing" not in verify_result.lower():
            failures.append("verify")
            logger.error("SETUP-01 not satisfied. Aborting subsequent steps.")
            return 1

        # Step 2 — write_wellness_entry (D-09 #2)
        ...

        # Step 3 — create_climbing_activity (D-09 #3); capture create_activity_id
        # Parse activity id from the success string OR readback the activity
        # by querying GET /athlete/{id}/activities?oldest=SMOKE_DATE&newest=SMOKE_DATE
        # filtered to type=WeightTraining. Either path is fine; the script
        # logs which it used.
        ...

        # Step 4 — enrich_activity_climbing(activity_id=create_activity_id, ...) (D-09 #4)
        ...

        # Step 5 — create planned event then complete_climbing_session (D-09 #5)
        # 5a. add_or_update_event(...) for SMOKE_EVENT_DATE — capture planned_event_id
        # 5b. complete_climbing_session(event_id=planned_event_id, ...) — capture completion_activity_id
        ...

        # Step 6 — get_training_status() (D-09 #6 — read-only, last)
        # CONTEXT D-09: "verifies it's in 400-600 token range".
        # Use a coarse char-count heuristic (~4 chars per token) → assert
        # 1600 < len(report) < 2400; log the actual char count.
        ...

    finally:
        # Cleanup pass (CONTEXT D-09 #7) — DELETE created activities and the
        # planned event. Wellness PUT at SMOKE_DATE is intentionally left in
        # place per D-10 (zero training-load impact at 2099-01-01).
        for label, aid in [("create", create_activity_id), ("completion", completion_activity_id)]:
            if aid:
                logger.info("Cleanup: DELETE /activity/%s (%s)", _redact(aid, athlete_id), label)
                resp = await make_intervals_request(url=f"/activity/{aid}", method="DELETE")
                logger.info("Delete response: %s", _redact(resp, athlete_id))
                if isinstance(resp, dict) and resp.get("error") is True:
                    failures.append(f"cleanup-activity-{label}")
        if planned_event_id:
            logger.info("Cleanup: DELETE planned event %s", _redact(planned_event_id, athlete_id))
            resp = await make_intervals_request(
                url=f"/athlete/{athlete_id}/events/{planned_event_id}",
                method="DELETE",
            )
            logger.info("Event delete response: %s", _redact(resp, athlete_id))
            if isinstance(resp, dict) and resp.get("error") is True:
                failures.append("cleanup-planned-event")

    if failures:
        logger.error("SMOKE FAILURES: %s", ", ".join(failures))
        return 1
    logger.info("SMOKE PHASE 5 — all steps OK")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

#### D. Patterns that MUST be preserved verbatim (CONTEXT D-13 / D-16)

- **Single HTTP boundary:** every cleanup `DELETE` goes through `make_intervals_request(url=..., method="DELETE")` — never a direct `httpx` call (D-13 / PROJECT.md). This matches `smoke_phase2.py:166–170` exactly.
- **Far-future dates:** `SMOKE_DATE = "2099-01-01"` (wellness + create) and `SMOKE_EVENT_DATE = "2099-01-02"` (planned event). D-10 + CONTEXT specifics line 170. The two-day gap prevents the `complete_climbing_session` duplicate guard (which checks date+type) from rejecting because of the activity created in step 3.
- **Idempotent cleanup:** every captured ID (`create_activity_id`, `completion_activity_id`, `planned_event_id`) is checked for `None` before its DELETE. Re-running the script after a partial failure must not double-delete or fail noisily.
- **Logged output is redacted:** every `logger.info("...", _redact(value, athlete_id))` pattern from `smoke_phase2.py` carries forward. Findings file entries also redacted.
- **Exit code discipline:** `return 1` on any failure (config, step, cleanup); `return 0` only when `failures` list is empty. Matches `smoke_phase2.py:188–192`.

#### E. Activity-ID parsing detail (CONTEXT D-09 #3)

`create_climbing_activity` returns a success string like `"Successfully created activity {id} on {date}."` (per `tools/climbing.py:703`) when only date+duration are given, OR a fuller `_enrich_impl` success string when climbing fields are passed. The smoke script must support both — recommended approach: regex `r"activity (\w+)"` against the success string, plus a defensive fallback that does `GET /athlete/{id}/activities?oldest=SMOKE_DATE&newest=SMOKE_DATE` and picks the WeightTraining match. The same parsing applies to `complete_climbing_session` (returns `"Successfully completed session: created activity {id} paired to event {event_id}."` per `tools/climbing.py:797–799`).

#### F. Planned-event creation for step 5 — analog `tools/events.py::add_or_update_event` (lines 282–292)

```python
event_call = await add_or_update_event(
    workout_type="WeightTraining",  # matches climbing custom-field write path (Phase 1 spike A4)
    name="SMOKE PHASE5 — DELETE ME",
    start_date=SMOKE_EVENT_DATE,
    moving_time=3600,  # 60 minutes — duplicate guard does NOT use moving_time, only date+type
)
# Parse event id from the success string per `tools/events.py::_handle_event_response` (line 79):
# "Successfully {action} event id: {result.get('id')}"
```

Note the `start_date` parameter (the public name on the events tool) maps to the smoke script's `SMOKE_EVENT_DATE` constant.

#### G. Findings-write helper (optional — Claude's discretion per CONTEXT line 80)

If the script writes findings inline rather than relying on hand-curation, use the `write_findings` shape from `spike_write_endpoints.py:252–289`:

```python
FINDINGS_PATH = (
    Path(__file__).resolve().parents[1]
    / ".planning"
    / "phases"
    / "05-server-wiring-and-acceptance"
    / "05-SMOKE-FINDINGS.md"
)
```

Same redaction, same JSON-fence body, same per-step section pattern. See "05-SMOKE-FINDINGS.md" entry below for layout.

---

### `.planning/phases/05-server-wiring-and-acceptance/05-LIVE-SMOKE.md` (manual checklist; CREATE)

**Analog:** `.planning/phases/02-wellness-write-and-activity-enrichment/02-HUMAN-UAT.md` (lines 1–35). The HUMAN-UAT pattern is "front-matter block, current-test pointer, numbered tests with expected/result lines, summary tally, gaps."

**Phase 5 simplification (CONTEXT D-11):** "one row per new tool with a checkbox" — five rows total. Optional: capture Claude Desktop's actual response text per row (Claude's discretion per CONTEXT line 82).

**Apply (full skeleton):**

```markdown
---
status: pending
phase: 05-server-wiring-and-acceptance
source: [05-CONTEXT.md, 05-PATTERNS.md]
started: 2026-04-29T00:00:00Z
updated: 2026-04-29T00:00:00Z
---

## Purpose

Manual checklist for the Claude Desktop side of Phase 5 acceptance.
Proves success-criterion-1 (`tools/list` in Claude Desktop shows the new tools)
and success-criterion-4 (each tool produces a non-error response in Claude
Desktop, not just via `scripts/smoke_phase5.py`). The unit registration test
catches structural drift; the smoke script catches API contract drift; this
checklist catches Claude Desktop tool-list rendering — three independent
checks (CONTEXT D-12).

Tick each row off in Claude Desktop running against the locally-installed
MCP server. Use far-future dates (2099-01-01 / 2099-01-02) to avoid
contaminating real training data; clean up afterwards via the smoke script
or by hand.

## Tests

### 1. write_wellness_entry — visible in tools/list AND callable
expected: Claude Desktop's tool list shows `write_wellness_entry`. Asking
Claude to "log a wellness entry for 2099-01-01 with 8 hours sleep and
soreness 2" results in a non-error response from the tool.
result: [pending]
claude_response_excerpt: [optional]

### 2. enrich_activity_climbing — visible AND callable
expected: tool visible in list. Asking Claude to "enrich activity
{ACTIVITY_ID} with bouldering, indoor, top grade sent 6A+, RPE 6" returns
a non-error response.
result: [pending]
claude_response_excerpt: [optional]

### 3. create_climbing_activity — visible AND callable
expected: tool visible. Asking Claude to "log a 90-minute bouldering
session indoors on 2099-01-01 with RPE 6 and a 6A+ send" returns a
non-error response.
result: [pending]
claude_response_excerpt: [optional]

### 4. complete_climbing_session — visible AND callable
expected: tool visible. Asking Claude to "complete planned event
{EVENT_ID} as a sport_lead session, RPE 7" returns a non-error response.
result: [pending]
claude_response_excerpt: [optional]

### 5. get_training_status — visible AND callable
expected: tool visible. Asking Claude "how should I train tomorrow?"
results in Claude calling get_training_status (or asking it directly
returns the report) — non-error response, three labeled sections
present (## Today, ## This Week, ## Long-Term Trend).
result: [pending]
claude_response_excerpt: [optional]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps

[populate during the manual run]
```

The front-matter shape (`status:`, `phase:`, `source:`, `started:`, `updated:`) is copied verbatim from `02-HUMAN-UAT.md:1–7`. The `expected: ... result: [pending]` per-row format mirrors `02-HUMAN-UAT.md:15–24`. The summary tally + gaps sections are also from `02-HUMAN-UAT.md:27–37`.

---

### `.planning/phases/05-server-wiring-and-acceptance/05-SMOKE-FINDINGS.md` (findings; CREATE)

**Primary analog:** `.planning/phases/01-foundation-and-write-path-spike/01-SPIKE-FINDINGS.md` (lines 1–6 header).
**Secondary analog:** `.planning/phases/02-wellness-write-and-activity-enrichment/02-SPIKE-FINDINGS.md` (lines 1–7 header + redacted-JSON-fence body sections).

**Header skeleton (verbatim shape from `01-SPIKE-FINDINGS.md:1–5` and `02-SPIKE-FINDINGS.md:1–6`):**

```markdown
# Smoke findings — Phase 5 acceptance

**Smoke date (target):** 2099-01-01 (wellness + activity), 2099-01-02 (planned event)

All occurrences of the live athlete id are redacted to `{athlete_id}`.

This file is the canonical record of the Phase 5 live-API smoke run. It is
either auto-written by `scripts/smoke_phase5.py` or hand-curated from its
stdout (CONTEXT line 80 — Claude's discretion).
```

**Per-step body shape (apply seven sections, one per smoke step, mirroring `01-SPIKE-FINDINGS.md`'s `## Wellness PUT` / `## Activity POST + custom-field PUT` / `## Custom-field definitions endpoint discovery` headings):**

```markdown
## Step 1 — verify_custom_fields_setup

```text
<verbatim tool output, redacted>
```

verdict: <ok | missing-fields-detected>

## Step 2 — write_wellness_entry

```json
{
  "request": {"date": "2099-01-01", "sleep_hours": 8.0, "soreness": 2},
  "tool_response": "<redacted>",
  "readback_verdict": "<roundtripped | mismatch>"
}
```

[... and so on for steps 3, 4, 5, 6 ...]

## Step 7 — Cleanup

```json
{
  "delete_create_activity": <redacted response>,
  "delete_completion_activity": <redacted response>,
  "delete_planned_event": <redacted response>,
  "wellness_left_in_place_at": "2099-01-01",
  "wellness_left_in_place_rationale": "Far-future date, zero training-load impact (D-10)."
}
```

## Manual cleanup (if any DELETE failed)

- Activity ids needing manual cleanup: <list or 'none'>
- Planned event id needing manual cleanup: <id or 'none'>

## Verdict

- All steps passed: <yes / no>
- Failures: <list or 'none'>
- Phase 5 success criteria 1, 2, 3, 4: <pass / pass / pass / pass>
```

The redacted JSON fence + `verdict:` line pattern is the established shape from both prior findings files. Hand-curation is also acceptable per CONTEXT — in that case the file can be a more readable narrative with the same section headings.

---

## Shared Patterns

### Single HTTP boundary (D-13 / PROJECT.md constraint)

**Source:** `src/intervals_mcp_server/api/client.py::make_intervals_request`
**Apply to:** every HTTP call in `scripts/smoke_phase5.py`, including DELETE cleanup.
**Negative example (must NOT happen):** any direct `httpx.AsyncClient(...)` or `httpx.put(...)` in the smoke script.

```python
# Verbatim from scripts/smoke_phase2.py:117–121:
create_resp = await make_intervals_request(
    url=f"/athlete/{athlete_id}/activities/manual",
    data=create_body,
    method="POST",
)
```

DELETE shape (`scripts/smoke_phase2.py:166–170`):

```python
delete_resp = await make_intervals_request(
    url=f"/activity/{activity_id}",
    method="DELETE",
)
```

### Athlete-id redaction in logs and findings

**Source:** `scripts/smoke_phase2.py:58–66` and `scripts/spike_write_endpoints.py:61–69` (identical bodies).
**Apply to:** smoke script logging and the findings-write helper.

```python
def _redact(obj: Any, athlete_id: str) -> Any:
    if isinstance(obj, str):
        return obj.replace(athlete_id, ATHLETE_REDACTED)
    if isinstance(obj, dict):
        return {k: _redact(v, athlete_id) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact(v, athlete_id) for v in obj]
    return obj
```

### Far-future date discipline

**Source:** `scripts/spike_write_endpoints.py:43`, `scripts/smoke_phase2.py:54`.
**Apply to:** `scripts/smoke_phase5.py` (CONTEXT D-10).

```python
SMOKE_DATE = "2099-01-01"        # wellness, activity
SMOKE_EVENT_DATE = "2099-01-02"  # planned event (so duplicate guard doesn't trip)
```

Two distinct dates because `complete_climbing_session` runs the same date+type duplicate-guard as `create_climbing_activity` (per `tools/climbing.py:625–664`) — putting the planned event on a different day side-steps the guard cleanly.

### Test sys.path + env-default header

**Source:** `tests/test_server.py:19–26`, `tests/test_climbing.py:1–10`, `tests/test_status.py` (same pattern).
**Apply to:** `tests/test_server_registration.py`.

```python
import asyncio
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")
```

These three setdefault lines satisfy `validate_athlete_id` if `Config` is constructed during the import chain, without polluting the real environment.

### Async tool invocation in sync tests

**Source:** `tests/test_server.py:69` (`asyncio.run(get_activities(...))`); the entire test suite uses sync test functions wrapping `asyncio.run(...)` rather than `pytest.mark.asyncio`.
**Apply to:** `tests/test_server_registration.py::_registered_tool_names`.

```python
tools = asyncio.run(mcp.list_tools())
```

### Markdown findings front-matter / heading skeleton

**Source:** `.planning/phases/01-foundation-and-write-path-spike/01-SPIKE-FINDINGS.md:1–5` for the date + redaction-note header; `.planning/phases/02-wellness-write-and-activity-enrichment/02-HUMAN-UAT.md:1–7` for the YAML-style front matter on planning artifacts.
**Apply to:** `05-LIVE-SMOKE.md` (front matter) and `05-SMOKE-FINDINGS.md` (header).

---

## No Analog Found

None. Every Phase 5 artifact has a direct sibling in the repo:

- `server.py` re-export change → repeats the existing activities/events/custom_items pattern in the same file.
- README "Climbing tools" section → mirrors the existing "Climbing setup" section style at the same heading depth.
- `tests/test_server_registration.py` → mirrors `tests/test_server.py` header + `tests/test_climbing.py` env-default pattern.
- `scripts/smoke_phase5.py` → direct extension of `scripts/smoke_phase2.py`.
- `05-LIVE-SMOKE.md` → mirrors `02-HUMAN-UAT.md` checklist shape.
- `05-SMOKE-FINDINGS.md` → mirrors `01-SPIKE-FINDINGS.md` / `02-SPIKE-FINDINGS.md` findings shape.

This is consistent with the phase's nature (acceptance + wiring, no new behavior).

---

## Metadata

**Analog search scope:**
- `src/intervals_mcp_server/server.py` (full file, 132 lines)
- `src/intervals_mcp_server/mcp_instance.py` (full file, 13 lines — confirmed `mcp` singleton + the `list_tools()` API on FastMCP)
- `src/intervals_mcp_server/tools/wellness.py` (header + signatures)
- `src/intervals_mcp_server/tools/climbing.py` (signatures + docstrings for all four public tools)
- `src/intervals_mcp_server/tools/status.py` (header + signature)
- `src/intervals_mcp_server/tools/events.py::add_or_update_event` (signature + body shape)
- `src/intervals_mcp_server/tools/__init__.py` (full file, 56 lines — confirmed decorator-driven registration)
- `tests/test_server.py` (header + `monkeypatch` + `asyncio.run` patterns)
- `tests/test_climbing.py` (env-default pattern)
- `scripts/smoke_phase2.py` (full file, 197 lines — primary smoke template)
- `scripts/spike_write_endpoints.py` (full file, 312 lines — findings-write helper)
- `README.md` (full file, 296 lines — section structure + intro)
- `.planning/phases/01-foundation-and-write-path-spike/01-SPIKE-FINDINGS.md` (header)
- `.planning/phases/02-wellness-write-and-activity-enrichment/02-SPIKE-FINDINGS.md` (header + body shape)
- `.planning/phases/02-wellness-write-and-activity-enrichment/02-HUMAN-UAT.md` (full file)

**FastMCP API verification:** `await mcp.list_tools()` returns `list[Tool]` with `.name: str`. Confirmed via `uv run python` against the FastMCP version pinned in `uv.lock`.

**Files scanned:** 16 source / test / script / planning files.

**Pattern extraction date:** 2026-04-29.
