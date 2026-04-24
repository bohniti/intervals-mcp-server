# Phase 1: Foundation and Write-Path Spike - Pattern Map

**Mapped:** 2026-04-24
**Files analyzed:** 9 (6 source + 2 tests + 1 doc/script)
**Analogs found:** 9 / 9

## File Classification

| New / Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------------|------|-----------|----------------|---------------|
| `scripts/spike_write_endpoints.py` | script (standalone async) | request-response (write + readback) | `src/intervals_mcp_server/tools/events.py` (`add_or_update_event`) + `src/intervals_mcp_server/tools/custom_items.py` (`create_custom_item`, `update_custom_item`) | role-different (tool not script) / data-flow match |
| `src/intervals_mcp_server/utils/grades.py` | utility (pure validation) | transform (str in → str out / raise) | `src/intervals_mcp_server/utils/validation.py` (`validate_date`, `validate_athlete_id`) | exact (role + flow) |
| `src/intervals_mcp_server/utils/climbing.py` | utility (enums + constants) | static data | `src/intervals_mcp_server/utils/types.py` (StrEnum + `@dataclass` patterns) | exact |
| `src/intervals_mcp_server/utils/formatting.py` (extended) | utility (formatter) | transform (dict in → str out) | `src/intervals_mcp_server/utils/formatting.py` (`format_activity_summary`, `format_wellness_entry`) | exact (same file) |
| `src/intervals_mcp_server/tools/climbing.py` | MCP tool module | request-response | `src/intervals_mcp_server/tools/wellness.py` (minimal one-tool module) | exact |
| `src/intervals_mcp_server/server.py` (1-line edit) | server wiring | import-side-effect | existing block at lines 72–94 (`from intervals_mcp_server.tools.X import …`) | exact |
| `README.md` (new section) | docs | N/A | existing setup sections at lines 14–74 | partial (only heading style) |
| `tests/test_grades.py` | test (pure function) | unit | `tests/test_value.py` (tests types from a single module) | exact |
| `tests/test_climbing.py` | test (enums + alignment + tool) | unit + monkeypatch | `tests/test_value.py` (enum test) + `tests/test_server.py` (monkeypatch `make_intervals_request`) | exact |

---

## Pattern Assignments

### `src/intervals_mcp_server/utils/grades.py` (utility, transform)

**Analog:** `src/intervals_mcp_server/utils/validation.py`

**Module docstring + imports pattern** (validation.py lines 1-10):
```python
"""
Validation utilities for Intervals.icu MCP Server

This module contains validation functions for input parameters.
"""

import re
from datetime import datetime

from intervals_mcp_server.utils.dates import parse_date_range
```
→ `grades.py` header mirrors this: top-level docstring, `import re`, local import `from intervals_mcp_server.utils.climbing import Discipline`.

**Validator signature + ValueError raise** (validation.py lines 31-47, `validate_date`):
```python
def validate_date(date_str: str) -> str:
    """Validate that a date string is in YYYY-MM-DD format.

    Args:
        date_str: The date string to validate.

    Returns:
        The validated date string if valid.

    Raises:
        ValueError: If the date string is not in YYYY-MM-DD format.
    """
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError as exc:
        raise ValueError("Invalid date format. Please use YYYY-MM-DD.") from exc
```
→ `validate_grade(grade: str, discipline: Discipline) -> str` copies this exact shape: Google-style docstring with Args/Returns/Raises, returns the validated string on success, raises `ValueError` with a message naming the expected scale on failure. Per D-06, the message should say e.g. `f"Invalid {discipline.value} grade '{grade}'. Expected Font (uppercase, e.g. 6A, 6A+)."`.

**Regex constant pattern** (validation.py line 25, inline `re.fullmatch`):
```python
if athlete_id and not re.fullmatch(r"i?\d+", athlete_id):
```
→ `grades.py` promotes the regex to a module-level constant per D-05: `FONT_RE = re.compile(r'^[3-9][A-C](\+)?$|^[1-2]$')` and `FRENCH_SPORT_RE = re.compile(r'^[3-9][abc](\+)?$')`. Per D-06 do **not** pass `re.IGNORECASE` — case is the cross-scale guard.

---

### `src/intervals_mcp_server/utils/climbing.py` (utility, static data)

**Analog:** `src/intervals_mcp_server/utils/types.py`

**StrEnum pattern** (types.py lines 11, 94-100):
```python
from enum import Enum, StrEnum
...

class TransportAliases(StrEnum):
    """Enumeration of supported MCP transport types."""

    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"
    STREAMABLE_HTTP = "streamable-http"
```
→ `Discipline(StrEnum)` and `SessionFocus(StrEnum)` follow this exact shape per D-07/D-08. `TransportAliases` is the canonical lowercase StrEnum precedent; copy it. Members:

```python
class Discipline(StrEnum):
    BOULDERING = "bouldering"
    SPORT_LEAD = "sport_lead"
    TOP_ROPE = "top_rope"
    TRAD = "trad"

class SessionFocus(StrEnum):
    POWER = "power"
    ENDURANCE = "endurance"
    TECHNIQUE = "technique"
    PROJECTING = "projecting"
    MILEAGE = "mileage"
```

**Dataclass pattern** (types.py lines 9, 108-115):
```python
from dataclasses import dataclass
...

@dataclass
class Value:
    """Represents a value with units for workout step intensity (power, heart rate, pace, cadence).
    ...
    """

    value: Optional[float] = None
    start: Optional[float] = None
    ...
```
→ Per D-10 and the "FieldSpec is a `@dataclass(frozen=True)` or `NamedTuple`" discretion point in CONTEXT, use `@dataclass(frozen=True)` — matches the `types.py` convention (all existing dataclasses there are `@dataclass` with named fields, not NamedTuples). Shape:

```python
@dataclass(frozen=True)
class FieldSpec:
    key: str
    type: str            # "select" | "bool" | "text" | "integer"
    options: tuple[str, ...] | None = None
```

**Module `__all__` pattern** (types.py lines 15-27):
```python
__all__ = [
    "Option",
    "WorkoutTarget",
    ...
]
```
→ `utils/climbing.py` exports `__all__ = ["Discipline", "SessionFocus", "FieldSpec", "CUSTOM_FIELD_KEYS"]`.

**UPPER_SNAKE_CASE constant pattern:** `CUSTOM_FIELD_KEYS` is a `dict[str, FieldSpec]` literal at module scope (no precedent for a frozen-dict in the codebase — plain dict is fine; tests enforce immutability by never mutating it, and mypy/ruff catch accidental writes).

---

### `src/intervals_mcp_server/utils/formatting.py` (extended — add `format_climbing_activity`)

**Analog:** `src/intervals_mcp_server/utils/formatting.py` itself — `format_activity_summary` (lines 32-118) and `format_wellness_entry` (lines 271-364).

**Simple formatter pattern** (formatting.py lines 32-48, `format_activity_summary` head):
```python
def format_activity_summary(activity: dict[str, Any]) -> str:
    """Format an activity into a readable string."""
    start_time = activity.get("startTime", activity.get("start_date", "Unknown"))

    if isinstance(start_time, str) and len(start_time) > 10:
        # Format datetime if it's a full ISO string
        try:
            dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            start_time = dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

    rpe = activity.get("perceived_exertion", None)
    if rpe is None:
        rpe = activity.get("icu_rpe", "N/A")
    if isinstance(rpe, (int, float)):
        rpe = f"{rpe}/10"
```
→ `format_climbing_activity(activity: dict) -> str`: signature is `(activity: dict[str, Any]) -> str`, takes the raw activity dict, uses `.get(key, "N/A")` for missing values, formats `icu_rpe` the same way (`f"{rpe}/10"`). Per D-15, render only the Phase 1 fields: `discipline`, `indoor`, `session_focus`, `top_grade_sent`, `top_grade_attempted`, `sends`, `attempts`, `icu_rpe`. Per D-20, do **not** touch existing functions.

**Line-builder pattern (multi-section formatter)** (formatting.py lines 301-364, `format_wellness_entry`):
```python
lines = ["Wellness Data:"]
lines.append(f"Date: {entries.get('id', 'N/A')}")
lines.append("")
...
return "\n".join(lines)
```
→ Prefer this `lines = [...]; lines.append(...); return "\n".join(lines)` idiom for `format_climbing_activity` — it's the cleaner of the two in-file patterns and fits a small number of fields better than the big f-string block used by `format_activity_summary`.

**Placement:** Append the new function at the bottom of `formatting.py` (after `format_intervals`), before any `if __name__` guard (there is none). No new imports needed.

---

### `src/intervals_mcp_server/tools/climbing.py` (new MCP tool module)

**Analog:** `src/intervals_mcp_server/tools/wellness.py` (the whole file, 71 lines — smallest/cleanest tool module).

**Module docstring + imports pattern** (wellness.py lines 1-15):
```python
"""
Wellness-related MCP tools for Intervals.icu.

This module contains tools for retrieving athlete wellness data.
"""

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.formatting import format_wellness_entry
from intervals_mcp_server.utils.validation import resolve_athlete_id, resolve_date_params

# Import mcp instance from shared module for tool registration
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401

config = get_config()
```
→ `tools/climbing.py` copies this header exactly, with imports adjusted:
```python
"""
Climbing-related MCP tools for Intervals.icu.

This module contains tools for the climbing training loop: custom-field
prerequisite verification, session completion, and climbing enrichment.
"""

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.climbing import CUSTOM_FIELD_KEYS, FieldSpec
from intervals_mcp_server.utils.validation import resolve_athlete_id

from intervals_mcp_server.mcp_instance import mcp  # noqa: F401

config = get_config()
```

**`@mcp.tool()` + `resolve_athlete_id` + error-dict check pattern** (wellness.py lines 18-52):
```python
@mcp.tool()
async def get_wellness_data(
    athlete_id: str | None = None,
    api_key: str | None = None,
    ...
) -> str:
    """Get wellness data for an athlete from Intervals.icu.
    ...
    Args:
        athlete_id: The Intervals.icu athlete ID (optional, will use ATHLETE_ID from .env if not provided)
        api_key: The Intervals.icu API key (optional, will use API_KEY from .env if not provided)
        ...
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg
    ...
    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/wellness", api_key=api_key, params=params
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error fetching wellness data: {result.get('message')}"
```
→ `verify_custom_fields_setup` copies this opening block verbatim (minus `resolve_date_params`):
- `@mcp.tool()` decorator
- `async def verify_custom_fields_setup(athlete_id: str | None = None, api_key: str | None = None) -> str:`
- Google-style docstring — per D-13 the docstring **mirrors the README field table** so Claude sees the setup checklist in-context when fields are missing.
- `resolve_athlete_id(athlete_id, config.athlete_id)` opening
- `make_intervals_request(url=f"/athlete/{athlete_id_to_use}/custom-item", api_key=api_key)` — reuse the `GET /custom-item` endpoint already exercised by `tools/custom_items.py` line 37 to list existing custom-field definitions.
- `if isinstance(result, dict) and "error" in result: return f"Error fetching …: {result.get('message')}"`

**Dual MCP-tool-and-internal-helper pattern (D-11):** There is no existing precedent in this codebase (all current tools are single-purpose). Implementation shape:
```python
async def _verify_custom_fields_setup_impl(
    athlete_id_to_use: str, api_key: str | None
) -> tuple[bool, list[FieldSpec]]:
    """Internal helper. Returns (ok, missing_specs)."""
    ...

@mcp.tool()
async def verify_custom_fields_setup(
    athlete_id: str | None = None, api_key: str | None = None
) -> str:
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg
    ok, missing = await _verify_custom_fields_setup_impl(athlete_id_to_use, api_key)
    if ok:
        return "All required climbing custom fields are present."
    lines = ["Missing required Intervals.icu custom fields:"]
    for spec in missing:
        lines.append(f"- {spec.key} ({spec.type})")
    lines.append("")
    lines.append("See README section 'Climbing setup — required Intervals.icu custom fields' for setup instructions.")
    return "\n".join(lines)
```
Phase 2 write tools will call `_verify_custom_fields_setup_impl()` as a pre-write guard (D-12: hard block on missing fields).

---

### `src/intervals_mcp_server/server.py` (one import line added)

**Integration point** (server.py lines 72-94):
```python
# Import tool modules to register them (tools register themselves via @mcp.tool() decorators)
# Import tool functions for re-export
from intervals_mcp_server.tools.activities import (  # pylint: disable=wrong-import-position  # noqa: E402
    add_activity_message,
    get_activities,
    ...
)
from intervals_mcp_server.tools.events import (  # pylint: disable=wrong-import-position  # noqa: E402
    ...
)
from intervals_mcp_server.tools.wellness import get_wellness_data  # pylint: disable=wrong-import-position  # noqa: E402
from intervals_mcp_server.tools.custom_items import (  # pylint: disable=wrong-import-position  # noqa: E402
    ...
)
```
→ Add one line in the same style, placed alongside the other `from intervals_mcp_server.tools.X import …` lines:
```python
from intervals_mcp_server.tools.climbing import verify_custom_fields_setup  # pylint: disable=wrong-import-position  # noqa: E402
```
And append `"verify_custom_fields_setup"` to `__all__` (lines 98-118). Per D-17, this is the **only** Phase 1 edit to `server.py`; Phase 2 tools will be added to `tools/climbing.py` without touching `server.py` again.

---

### `scripts/spike_write_endpoints.py` (standalone async script)

**Analogs:**
- `tools/events.py` `_prepare_event_data` (lines 42-63) and `_create_or_update_event_request` (line 376) for activity POST shape.
- `tools/custom_items.py` `update_custom_item` (lines 144-203) for PUT shape.
- `tools/wellness.py` (whole file) for the `make_intervals_request` call signature.

**POST body shape** (events.py lines 55-63):
```python
return {
    "start_date_local": start_date + "T00:00:00",
    "category": "WORKOUT",
    "name": name,
    "description": str(workout_doc) if workout_doc else None,
    "type": resolved_workout_type,
    "moving_time": moving_time,
    "distance": distance,
}
```
→ Spike's activity POST uses the same `YYYY-MM-DDT00:00:00` local-time format (per specifics section of CONTEXT, "must already use `YYYY-MM-DDT00:00:00` format so Phase 3 inherits a correct pattern from the start"). Per D-04, spike resolves the `type` question (`"WeightTraining"` vs `"Other"`).

**PUT call pattern** (custom_items.py lines 190-195):
```python
result = await make_intervals_request(
    url=f"/athlete/{athlete_id_to_use}/custom-item/{item_id}",
    api_key=api_key,
    data=data,
    method="PUT",
)
```
→ Spike's wellness PUT copies this exactly, URL becomes `f"/athlete/{athlete_id}/wellness/{date}"`, `method="PUT"`, `data={"ctl": ..., ...}`.

**Standalone-script entrypoint pattern:** No existing script in `scripts/` (directory does not exist per initial directory listing — planner creates it). Use the standard:
```python
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```
This mirrors the usage inside `test_*` files (`asyncio.run(...)` at line 69, 95, 117 of `test_server.py`) and `test_make_intervals_request.py` line 98.

**Per D-02:** All HTTP goes through `make_intervals_request()` — no direct `httpx`. Script imports `from intervals_mcp_server.api.client import make_intervals_request` and the standard env config path (`from intervals_mcp_server.config import get_config`). Uses the same `resolve_athlete_id` path as tools do.

**Per D-03:** Use `2099-01-01` as the spike date. After PUT/POST, call the same endpoint with `method="GET"` (or `method="DELETE"` for activities if the endpoint exists) to verify and clean up. Document any cleanup residue in `01-SPIKE-FINDINGS.md`.

**Readback-for-rendering:** After POST, the spike can call `format_climbing_activity(response_dict)` (the newly added formatter from D-15) to render what Intervals.icu actually accepted — this exercises the formatter end-to-end with real data and is called out in CONTEXT as "This enables the spike to render its own readback."

---

### `tests/test_grades.py` (new test file)

**Analog:** `tests/test_value.py` (whole file, 22 lines — single-module test, no fixtures).

**Test file imports + structure** (test_value.py lines 1-10):
```python
"""
Unit tests for the Value dataclass in intervals_mcp_server.utils.types.

These tests verify that the Value dataclass correctly handles:
- String formatting for percent FTP units
- Ramp intervals (start/end values)
"""

from intervals_mcp_server.utils.types import Value, ValueUnits


def test_str_percent_ftp():
    """Test formatting percentage FTP values."""
    val = Value(value=95.0, units=ValueUnits.PERCENT_FTP)
    assert str(val) == "95% ftp"
```
→ `test_grades.py`:
```python
"""
Unit tests for grade validation in intervals_mcp_server.utils.grades.
"""

import pytest

from intervals_mcp_server.utils.climbing import Discipline
from intervals_mcp_server.utils.grades import FONT_RE, FRENCH_SPORT_RE, validate_grade


def test_font_valid():
    assert validate_grade("6A", Discipline.BOULDERING) == "6A"
    assert validate_grade("7A+", Discipline.BOULDERING) == "7A+"

def test_font_rejects_lowercase():
    with pytest.raises(ValueError, match="Font"):
        validate_grade("6a", Discipline.BOULDERING)

def test_french_sport_valid():
    assert validate_grade("6a", Discipline.SPORT_LEAD) == "6a"

def test_french_sport_rejects_uppercase():
    with pytest.raises(ValueError, match="French"):
        validate_grade("6A", Discipline.SPORT_LEAD)
```
Cover the D-06 case-as-guard explicitly (uppercase for Font, lowercase for French sport, both cases rejected cross-scale, slashes/descriptors rejected).

---

### `tests/test_climbing.py` (new test file)

**Analogs:**
- `tests/test_value.py` (enum/dataclass test shape).
- `tests/test_server.py` lines 48-71 (monkeypatch `make_intervals_request` for tool tests).

**Monkeypatch pattern** (test_server.py lines 48-71):
```python
def test_get_activities(monkeypatch):
    sample = { ... }

    async def fake_request(*_args, **_kwargs):
        return [sample]

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(get_activities(athlete_id="1", limit=1, include_unnamed=True))
    assert "Morning Ride" in result
```
→ `test_climbing.py` uses the exact same monkeypatch-both-paths idiom, patching `intervals_mcp_server.tools.climbing.make_intervals_request` in addition to the api.client path:
```python
def test_verify_custom_fields_setup_all_present(monkeypatch):
    # Fake response: all 7 fields declared in athlete account
    fake_items = [{"id": 1, "name": "discipline", "type": "INPUT_FIELD", ...}, ...]

    async def fake_request(*_args, **_kwargs):
        return fake_items

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )
    result = asyncio.run(verify_custom_fields_setup(athlete_id="1"))
    assert "All required" in result

def test_verify_custom_fields_setup_missing(monkeypatch):
    async def fake_request(*_args, **_kwargs):
        return []  # No fields defined yet

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )
    result = asyncio.run(verify_custom_fields_setup(athlete_id="1"))
    # D-12: error lists every missing field
    assert "discipline" in result and "sends" in result and "attempts" in result
```

**Test path setup** (test_server.py lines 22-28) — required at top of the test file since tests can run before `conftest.py`:
```python
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")
```
→ Copy these three lines verbatim into `test_climbing.py` before importing the tool. (Not needed for `test_grades.py` because it only imports pure utils, but adding them costs nothing and matches `test_server.py`.)

**Alignment test (D-09 / D-19):** Unique to this phase — no existing precedent.
```python
def test_discipline_enum_aligns_with_custom_field_options():
    spec = CUSTOM_FIELD_KEYS["discipline"]
    assert spec.type == "select"
    assert set(spec.options) == {d.value for d in Discipline}

def test_session_focus_enum_aligns_with_custom_field_options():
    spec = CUSTOM_FIELD_KEYS["session_focus"]
    assert spec.type == "select"
    assert set(spec.options) == {s.value for s in SessionFocus}
```
Per D-09: "Tests must assert this alignment so a future rename of one side fails loudly."

**Tool-registration assertion pattern** (test_server.py imports the tool from `intervals_mcp_server.server`, line 28-44 — this implicitly verifies the tool is registered because the `server.py` import chain runs the decorator). For D-17 / D-19 / Pitfall #14, add:
```python
def test_verify_tool_registered():
    """Tool must be importable from server module (registers via decorator)."""
    from intervals_mcp_server.server import verify_custom_fields_setup  # noqa: F401
```

---

### `README.md` (new section)

**Analog:** existing setup sections at README.md lines 14–74 (`## Setup`, `### 1. Install uv`, etc.).

**Heading style:** `### N. <Section Title>` for numbered steps within a `## Setup` block; `##` for top-level sections. The new section can be a sibling `## Climbing setup — required Intervals.icu custom fields` or nested `### N. Climbing setup — required Intervals.icu custom fields` under `## Setup`. Planner picks placement; the naming is fixed by CONTEXT (D-13: "Setup docs live in README + verify-tool docstring").

**Content (per D-09 table):** a markdown table with columns `Key | Intervals.icu type | Options`, one row per entry in `CUSTOM_FIELD_KEYS`. Per D-13, the `verify_custom_fields_setup` docstring **mirrors this table** — consider generating one from the other mentally (not programmatically — that's deferred per the "Auto-generating the README field table from `CUSTOM_FIELD_KEYS`" deferred item).

---

## Shared Patterns

### Google-style docstring + async tool signature
**Source:** `src/intervals_mcp_server/tools/wellness.py` lines 18-38; `src/intervals_mcp_server/tools/activities.py` lines 103-121.
**Apply to:** `tools/climbing.py:verify_custom_fields_setup`.
```python
@mcp.tool()
async def <tool_name>(
    athlete_id: str | None = None,
    api_key: str | None = None,
    ...
) -> str:
    """<one-line summary>.

    <paragraph description — for write tools, doubles as LLM's conversational
    instruction per Pitfall #6.>

    Args:
        athlete_id: The Intervals.icu athlete ID (optional, will use ATHLETE_ID from .env if not provided)
        api_key: The Intervals.icu API key (optional, will use API_KEY from .env if not provided)
        ...
    """
```

### `resolve_athlete_id` → error-string early-return
**Source:** `src/intervals_mcp_server/utils/validation.py` lines 50-70; used in `tools/wellness.py` line 39-41, `tools/activities.py` line 123-125, `tools/custom_items.py` lines 32-34, 71-73, 111-113.
**Apply to:** `tools/climbing.py:verify_custom_fields_setup` (and Phase 2 tools).
```python
athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
if error_msg:
    return error_msg
```

### Error-dict check after `make_intervals_request`
**Source:** `src/intervals_mcp_server/tools/wellness.py` lines 51-52; `tools/activities.py` lines 139-141; `tools/custom_items.py` lines 40-41, 135-136, 197-198.
**Apply to:** `tools/climbing.py`, `scripts/spike_write_endpoints.py`.
```python
if isinstance(result, dict) and "error" in result:
    return f"Error <verb>ing <thing>: {result.get('message')}"
```

### ValueError with user-facing message
**Source:** `src/intervals_mcp_server/utils/validation.py` lines 26-28, 46-47.
**Apply to:** `utils/grades.py:validate_grade`.
```python
raise ValueError(
    "<human-readable message naming the expected format/value>"
)
```

### `asyncio.run` + `monkeypatch.setattr` for tool tests
**Source:** `tests/test_server.py` lines 61-71 (pattern repeated ~20 times in that file).
**Apply to:** `tests/test_climbing.py`.
```python
async def fake_request(*_args, **_kwargs):
    return <sample>

monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
monkeypatch.setattr("intervals_mcp_server.tools.<module>.make_intervals_request", fake_request)
result = asyncio.run(<tool_function>(...))
assert "<expected fragment>" in result
```

### Import ordering (stdlib → third-party → local)
**Source:** Visible consistently in every source file; e.g. `tools/activities.py` lines 7-16, `tools/wellness.py` lines 7-13.
**Apply to:** all new files.
```python
# stdlib
import re
from dataclasses import dataclass
from enum import StrEnum

# third-party (none for Phase 1 utils)

# local
from intervals_mcp_server.utils.climbing import Discipline
```

### MCP-tool registration via shared `mcp` instance
**Source:** `src/intervals_mcp_server/mcp_instance.py` (the whole 12-line module).
**Apply to:** `tools/climbing.py`.
```python
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401
```
(Every existing tool module uses this exact import line with `# noqa: F401` — do not deviate.)

---

## No Analog Found

| File / Concern | Reason |
|----------------|--------|
| `scripts/` directory itself | Does not yet exist in this repo — planner creates it for the spike. The `scripts/` convention is called out in CONTEXT `<code_context>` as `"scripts/ directory may not exist yet — planner creates it if needed"`. |
| Dual MCP-tool-and-internal-helper pattern (D-11) | No existing precedent — all existing tools are single-purpose @mcp.tool()-decorated functions. The `_verify_custom_fields_setup_impl` / `verify_custom_fields_setup` split is new in Phase 1 and will be reused by Phase 2 write tools. |
| Frozen-dict / single-source field table (D-10) | No existing precedent — closest analog is `types.py`'s `__all__` export list and `Config` dataclass, but neither doubles as a runtime source-of-truth table. Planner establishes the pattern here. |
| Enum/option alignment assertion (D-09) | No existing test asserts cross-module alignment (`TransportAliases` has no coupled option list to align with). New test pattern introduced in `test_climbing.py`. |

## Metadata

**Analog search scope:**
- `src/intervals_mcp_server/tools/` (activities.py, events.py, wellness.py, custom_items.py)
- `src/intervals_mcp_server/utils/` (formatting.py, types.py, validation.py, dates.py)
- `src/intervals_mcp_server/api/` (client.py)
- `src/intervals_mcp_server/` (server.py, mcp_instance.py, config.py)
- `tests/` (test_server.py, test_formatting.py, test_make_intervals_request.py, test_value.py)
- `scripts/` — does not exist, no analogs
- `README.md` — heading style only

**Files scanned:** 16 source/test files + README.md + pyproject.toml.

**Pattern extraction date:** 2026-04-24.
