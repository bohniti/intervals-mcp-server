# Phase 2: Wellness Write and Activity Enrichment - Pattern Map

**Mapped:** 2026-04-25
**Files analyzed:** 9 (3 new source + 1 modified source + 1 modified formatter + 2 new tests + 1 new script + 1 new doc)
**Analogs found:** 9 / 9

---

## File Classification

| New / Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------------|------|-----------|----------------|---------------|
| `src/intervals_mcp_server/utils/wellness.py` (NEW) | utility (constants + transform helpers) | static data + transform (dict→dict) | `src/intervals_mcp_server/utils/grades.py` | exact (role + flow + Phase 1 split sibling) |
| `src/intervals_mcp_server/tools/wellness.py` (MODIFIED — add `write_wellness_entry`) | MCP tool (write — many-arg async) | request-response (PUT + GET readback) | `src/intervals_mcp_server/tools/climbing.py::verify_custom_fields_setup` (write-side tool from Phase 1) + `src/intervals_mcp_server/tools/wellness.py::get_wellness_data` (sibling read tool) | exact (same module) |
| `src/intervals_mcp_server/tools/climbing.py` (MODIFIED — add `enrich_activity_climbing`) | MCP tool (write — many-arg async with guard + readback + audit) | request-response (verify-guard → GET conflict-scan → PUT → GET readback → POST audit) | `src/intervals_mcp_server/tools/climbing.py::verify_custom_fields_setup` (same module, the guard it consumes) + `src/intervals_mcp_server/tools/activities.py::add_activity_message` (audit POST) + `src/intervals_mcp_server/tools/activities.py::get_activity_details` (GET pattern) | exact (same module) |
| `src/intervals_mcp_server/utils/formatting.py` (MODIFIED — extend `format_climbing_activity`) | utility (formatter) | transform (dict in → str out) | `src/intervals_mcp_server/utils/formatting.py::format_climbing_activity` (extend in place — additive only per D-24) | exact (same function) |
| `tests/test_wellness_write.py` (NEW) | test (write tool — async + monkeypatch) | unit (mocked PUT + GET) | `tests/test_climbing.py` lines 122-217 (Phase 1 verify tool tests) | exact |
| `tests/test_climbing_write.py` (NEW) | test (write tool — async + monkeypatch + alignment) | unit (mocked PUT + GET + add_activity_message + WELLNESS_RANGES alignment mirror) | `tests/test_climbing.py` lines 22-69 (alignment tests) + 122-217 (tool monkeypatch tests) | exact |
| `scripts/spike_write_endpoints_phase2.py` OR extension to `scripts/spike_write_endpoints.py` (NEW) | script (standalone async) | request-response (probe + readback + redacted findings file) | `scripts/spike_write_endpoints.py` (Phase 1 spike) | exact |
| `.planning/phases/02-wellness-write-and-activity-enrichment/02-SPIKE-FINDINGS.md` (NEW) | doc (canonical probe results) | N/A | `.planning/phases/01-foundation-and-write-path-spike/01-SPIKE-FINDINGS.md` | exact |
| Smoke-test script (NEW, name TBD by planner — Plan 02-05 / D-25) | script (standalone async, end-to-end) | request-response (live PUT + GET + DELETE cleanup) | `scripts/spike_write_endpoints.py` (same scaffolding) | role-match |

---

## Pattern Assignments

### `src/intervals_mcp_server/utils/wellness.py` (NEW — utility, constants + transform)

**Analog:** `src/intervals_mcp_server/utils/grades.py` (Phase 1 sibling — exact same shape: module docstring + `__all__` + UPPER_SNAKE_CASE constant table + small pure helpers, no tool/api imports).

**Module-docstring + `__all__` pattern** (`src/intervals_mcp_server/utils/grades.py` lines 1-19):
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

__all__ = [
    "FONT_RE",
    "FRENCH_SPORT_RE",
    "validate_grade",
]
```
→ `utils/wellness.py` mirrors this: triple-quoted module docstring stating purpose ("wellness ranges + PUT-body construction"), no tool/api imports (utilities are leaf deps per `STRUCTURE.md`), `__all__` listing `WELLNESS_RANGES`, `PARAM_TO_API_FIELD`, `sleep_hours_to_secs`, `build_wellness_put_body`.

**Constant table pattern** (`src/intervals_mcp_server/utils/climbing.py` lines 60-98 — `CUSTOM_FIELD_KEYS`):
```python
CUSTOM_FIELD_KEYS: MappingProxyType[str, FieldSpec] = MappingProxyType({
    "discipline": FieldSpec(
        key="discipline",
        field_type="select",
        options=tuple(d.value for d in Discipline),
        description="Climbing discipline (bouldering / sport_lead / top_rope / trad).",
    ),
    ...
})
```
→ `WELLNESS_RANGES: dict[str, tuple[int, int]]` is the same idea: typed module-level constant, the **single source of truth** that tests will assert alignment against (mirrors how `tests/test_climbing.py::test_discipline_options_match_custom_field_spec` asserts Phase 1 alignment). Either `dict` or `MappingProxyType` (read-only) is fine; immutability test pattern is in `tests/test_climbing.py::test_custom_field_keys_is_read_only` lines 66-68 if the planner wants the same guard.

**Validator/helper signature + Google docstring** (`src/intervals_mcp_server/utils/grades.py` lines 33-63):
```python
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
    ...
```
→ `sleep_hours_to_secs(hours: float) -> int` and `build_wellness_put_body(params: dict[str, Any]) -> dict[str, Any]` use the same docstring shape. The drop-None body builder is a pure transform that takes a `dict[str, Any]` of public-param-name → user-supplied-value (or None), and returns a dict using `PARAM_TO_API_FIELD` to translate keys, dropping None entries — Intervals.icu treats `null` as "clear" (Pitfall #2 / Integration Gotchas), so only supplied keys may appear.

---

### `src/intervals_mcp_server/tools/wellness.py` — `write_wellness_entry` (NEW tool, MODIFY existing module)

**Analog:** Co-located `get_wellness_data` (lines 18-71 — same module, same imports, same `resolve_athlete_id` pattern, same `make_intervals_request` boundary, same error-string return) **plus** `tools/climbing.py::verify_custom_fields_setup` (Phase 1 — write-side tool with the docstring-as-LLM-instructions style of Pitfall #6).

**Imports + `config = get_config()` + `mcp` import pattern** (`src/intervals_mcp_server/tools/wellness.py` lines 1-15):
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
→ The new tool reuses these imports verbatim. Add new imports for the new utility module: `from intervals_mcp_server.utils.wellness import WELLNESS_RANGES, PARAM_TO_API_FIELD, build_wellness_put_body, sleep_hours_to_secs`. Update the module docstring to mention writing as well as reading (additive — D-24).

**Many-arg async tool signature with `# pylint: disable=too-many-arguments`** (`src/intervals_mcp_server/tools/activities.py` lines 103-122 — `get_activities`):
```python
@mcp.tool()
async def get_activities(  # pylint: disable=too-many-arguments,too-many-return-statements,too-many-branches,too-many-positional-arguments
    athlete_id: str | None = None,
    api_key: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 10,
    include_unnamed: bool = False,
) -> str:
    """Get a list of activities for an athlete from Intervals.icu

    Args:
        athlete_id: The Intervals.icu athlete ID (optional, will use ATHLETE_ID from .env if not provided)
        ...
    """
```
→ `write_wellness_entry` copies this exact shape: `@mcp.tool()` decorator, `async def`, `# pylint: disable=too-many-arguments,too-many-positional-arguments` (12 params: `date` + 9 wellness fields + `athlete_id` + `api_key` per D-06), `-> str` return type, Google-style docstring. Per Pitfall #6 the docstring is the LLM's instruction sheet — RESEARCH.md `## Pattern 1` lines 256-303 has the full template; planner copies it.

**`resolve_athlete_id` + early-return error pattern** (`src/intervals_mcp_server/tools/wellness.py` lines 39-41 + `src/intervals_mcp_server/tools/climbing.py` lines 137-139):
```python
athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
if error_msg:
    return error_msg
```
→ First operation in `write_wellness_entry` body. Same shape in both analogs; canonical pattern.

**API-error → user-string mapping** (`src/intervals_mcp_server/tools/wellness.py` lines 51-52):
```python
if isinstance(result, dict) and "error" in result:
    return f"Error fetching wellness data: {result.get('message')}"
```
→ Used after both the PUT and the GET-readback in `write_wellness_entry`. Wording adapted: `f"Error writing wellness entry: ..."` and `f"Error reading back wellness entry: ..."`.

**PUT call shape — `make_intervals_request(method='PUT', data=...)`** (`scripts/spike_write_endpoints.py` lines 86-90 — confirmed working in Phase 1 spike):
```python
findings["write_1_response"] = await make_intervals_request(
    url=f"/athlete/{athlete_id}/wellness/{SPIKE_DATE}",
    data=write_body_1,
    method="PUT",
)
```
→ `write_wellness_entry` calls `await make_intervals_request(url=f"/athlete/{athlete_id_to_use}/wellness/{date}", api_key=api_key, data=body, method="PUT")` where `body = build_wellness_put_body({...})`. URL shape `/athlete/{id}/wellness/{date}` is **CONFIRMED** by `01-SPIKE-FINDINGS.md`.

**GET-readback shape** (`src/intervals_mcp_server/tools/wellness.py` lines 47-49 — sibling read tool):
```python
result = await make_intervals_request(
    url=f"/athlete/{athlete_id_to_use}/wellness", api_key=api_key, params=params
)
```
→ Plus `params={"oldest": date, "newest": date}` for single-date readback per D-11. Result is a list (matches `get_wellness_data` lines 66-69).

**Validation-before-HTTP pattern** (Pitfall #6 — fail fast before the network call). Per D-07/D-10:
- Iterate the supplied numeric params; for each whose value is non-None, look up `WELLNESS_RANGES[name]` and raise `ValueError(f"{name}={value} out of range; expected {min}..{max}")`.
- After validation, build candidate dict; if every wellness field is None, return error string `"Error: at least one wellness field must be supplied (date alone is not enough)."` (D-10).

---

### `src/intervals_mcp_server/tools/climbing.py` — `enrich_activity_climbing` (NEW tool, MODIFY existing module)

**Analog (primary):** Co-located `verify_custom_fields_setup` + `_verify_custom_fields_setup_impl` in the same file (lines 34-144) — same `config = get_config()`, same `_README_POINTER`, same `make_intervals_request` boundary, same `resolve_athlete_id` early-return, same Google docstring shape.
**Analog (audit POST):** `src/intervals_mcp_server/tools/activities.py::add_activity_message` (lines 352-381) — exact pattern for the override audit POST per D-14.
**Analog (GET activity):** `src/intervals_mcp_server/tools/activities.py::get_activity_details` (lines 169-207) — GET `/activity/{id}` pattern for both the conflict-scan (D-14) and the readback (D-15).

**`_README_POINTER` reuse pattern** (`src/intervals_mcp_server/tools/climbing.py` lines 20-23):
```python
_README_POINTER = (
    "See README section 'Climbing setup — required Intervals.icu custom fields' "
    "for setup instructions."
)
```
→ Per D-15, `enrich_activity_climbing` reuses this constant in the readback-failure error string when **custom fields** are missing post-PUT (NOT when only `icu_rpe` is missing, which is a native field, NOT when wellness is missing — wellness is its own tool). Already imported because it's in the same module — no new import.

**Verify-fields guard call pattern** (`src/intervals_mcp_server/tools/climbing.py` lines 141-144):
```python
_ok, _missing, human_message = await _verify_custom_fields_setup_impl(
    athlete_id_to_use, api_key
)
return human_message
```
→ Per D-20, `enrich_activity_climbing` calls `_verify_custom_fields_setup_impl(...)` **conditionally** — only when at least one of the 7 custom-field params (`discipline`, `indoor`, `session_focus`, `top_grade_sent`, `top_grade_attempted`, `sends`, `attempts`) is supplied. RPE-only writes skip the guard. On `not ok`, return `human_message` immediately (already includes `_README_POINTER`). Add a one-line comment at the call site explaining why this guard does NOT apply when only RPE is supplied (D-21 carry-forward thinking).

**Many-arg async tool signature with `# pylint: disable=too-many-arguments`** — same template as `write_wellness_entry`. Per D-12, signature is exactly:
```python
@mcp.tool()
async def enrich_activity_climbing(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    activity_id: str,                      # required
    discipline: str | None = None,         # required if any grade is set
    indoor: bool | None = None,
    session_focus: str | None = None,
    top_grade_sent: str | None = None,
    top_grade_attempted: str | None = None,
    sends: int | None = None,
    attempts: int | None = None,
    rpe: int | None = None,                # 1-10 → icu_rpe (native)
    override: bool = False,                # Pitfall #10 guard bypass
    athlete_id: str | None = None,
    api_key: str | None = None,
) -> str:
```

**At-least-one-supplied + grade↔discipline coupling validation** — runs before any HTTP call (Pitfall #6 fail-fast). Per D-12:
- If every climbing field (everything except `activity_id`, `override`, `athlete_id`, `api_key`) is None → return error string "nothing to write".
- If any of `top_grade_sent` / `top_grade_attempted` is supplied AND `discipline` is None → return error string naming the dependency.
- For each supplied grade, call `validate_grade(grade, Discipline(discipline))` from `utils/grades.py` (D-13). Catch `ValueError` and return its message.
- For `rpe` if supplied, validate range 1-10 (D-12 + CLIMB-07).

**GET-then-PUT activity pattern** (`src/intervals_mcp_server/tools/activities.py::get_activity_details` lines 169-207):
```python
@mcp.tool()
async def get_activity_details(activity_id: str, api_key: str | None = None) -> str:
    ...
    result = await make_intervals_request(url=f"/activity/{activity_id}", api_key=api_key)

    if isinstance(result, dict) and "error" in result:
        error_message = result.get("message", "Unknown error")
        return f"Error fetching activity details: {error_message}"
    ...
    activity_data = result[0] if isinstance(result, list) and result else result
    if not isinstance(activity_data, dict):
        return f"Invalid activity format for activity {activity_id}."
```
→ `enrich_activity_climbing` does this GET twice: once for the conflict-scan (D-14, before PUT) and once for the readback (D-15, after PUT). The list-vs-dict normalization (`activity_data = result[0] if isinstance(result, list) ...`) is the established pattern — copy it.

**Conflict-scan default-deny pattern** (NEW logic, no exact codebase analog — closest pattern is the missing-field iteration in `_verify_custom_fields_setup_impl` lines 84-95 which iterates `CUSTOM_FIELD_KEYS` and produces a per-key error message). Per D-14:
- Walk supplied params (excluding `activity_id`, `override`, `athlete_id`, `api_key`).
- For each, look up the corresponding API field name on the GET-result dict (`indoor` → `indoor`, `rpe` → `icu_rpe`, etc.).
- If the existing value is non-null AND `override=False` → collect into a `conflicts: list[tuple[str, Any]]` and refuse with the per-line format from CONTEXT.md `<specifics>`: `f"{field}: {existing_value} (already set)"`, plus a hint to pass `override=True`.
- If `override=True` → proceed AND queue the audit message (see next pattern).

**PUT activity body pattern** — body shape locked by Plan 02-01 second probe (D-01a / D-16). Top-level `{key: value}` is what the Phase 1 spike tried and got 422 on; the second probe MUST land a working shape before this tool ships (D-05 hard-stop). Once locked, `enrich_activity_climbing` calls:
```python
result = await make_intervals_request(
    url=f"/activity/{activity_id}",  # OR alternate URL per probe
    api_key=api_key,
    data=put_body,                    # shape per probe
    method="PUT",                     # OR alternate method per probe
)
```
The probe must produce a paste-ready body shape that the planner copies verbatim into the tool. Per D-16, RPE rides in the same PUT body as custom fields IF the probe confirms it — else two writes in fixed order (RPE first, then custom fields), with explicit partial-failure error.

**Audit POST pattern** (`src/intervals_mcp_server/tools/activities.py::add_activity_message` lines 352-381) — exact template for the override audit per D-14:
```python
@mcp.tool()
async def add_activity_message(
    activity_id: str,
    content: str,
    api_key: str | None = None,
) -> str:
    ...
    result = await make_intervals_request(
        url=f"/activity/{activity_id}/messages",
        api_key=api_key,
        method="POST",
        data={"content": content},
    )

    if isinstance(result, dict) and "error" in result:
        error_message = result.get("message", "Unknown error")
        return f"Error adding message to activity: {error_message}"
    ...
```
→ When `override=True`, `enrich_activity_climbing` builds the message string per CONTEXT.md `<specifics>`:
`f"[enrich override] discipline: {old}→{new}, top_grade_sent: {old}→{new} (prior values preserved here)"`
and either calls `add_activity_message(activity_id, content, api_key)` directly (`add_activity_message` is `@mcp.tool()`-decorated but is just an `async def` underneath — direct call is fine and avoids re-routing through MCP) **or** issues the equivalent `make_intervals_request(url=f"/activity/{activity_id}/messages", method="POST", data={"content": ...})` inline. Either is acceptable; the direct-call route is one less HTTP hop pattern to copy. Note D-22 forbids `_`-prefix imports between sibling tool modules — `add_activity_message` is public (no underscore), so a normal `from intervals_mcp_server.tools.activities import add_activity_message` import is allowed.

**Readback equality verification (NEW pattern, no codebase analog)** — Phase 1's `_verify_custom_fields_setup_impl` checks key **presence** only (lines 67-72). Phase 2 needs **value equality** per D-15 / RESEARCH.md Pattern 3. After the PUT:
- GET `/activity/{activity_id}` (same pattern as `get_activity_details`).
- For each **supplied** field (NOT all custom fields — D-15 explicit), compare readback value to sent value. Watch for type-coercion drift per RESEARCH.md `## Pattern 3` (icu_rpe int↔float, indoor bool↔string, sends int).
- If any supplied field is missing or unequal → return error string listing each failing field on its own line, plus `_README_POINTER` **only if** the failing fields include any of the 7 climbing custom fields (per D-15 — RPE-only failure does NOT need the README pointer).

**Final success-string + format_climbing_activity render** — on full success, render the readback dict via `format_climbing_activity(activity)` (extended in this phase per D-24). Already imported by Phase 1 in `scripts/spike_write_endpoints.py`; for `tools/climbing.py` add `from intervals_mcp_server.utils.formatting import format_climbing_activity` to the imports.

---

### `src/intervals_mcp_server/utils/formatting.py::format_climbing_activity` (MODIFIED — extend additively per D-24)

**Analog:** the function itself, lines 552-592. Extend in place — do NOT rewrite. Per D-24 / Phase 1 D-15 carry-forward: additive only.

**Existing function** (lines 552-592):
```python
def format_climbing_activity(activity: dict[str, Any]) -> str:
    """Format a climbing activity (custom fields + RPE) into a readable string.

    Renders only the fields Phase 1 establishes: discipline, indoor,
    session_focus, top_grade_sent, top_grade_attempted, sends, attempts,
    icu_rpe. Activities without these fields render mostly-N/A lines, which
    is exactly what we want for a readback of a freshly-created activity
    before enrichment.
    ...
    """
    indoor = activity.get("indoor")
    if indoor is True:
        indoor_str = "Yes"
    elif indoor is False:
        indoor_str = "No"
    else:
        indoor_str = "N/A"

    rpe = activity.get("icu_rpe")
    rpe_str = f"{rpe}/10" if isinstance(rpe, (int, float)) else "N/A"

    return (
        f"Climbing Activity\n"
        f"  ID: {activity.get('id', 'N/A')}\n"
        ...
        f"  RPE: {rpe_str}\n"
    )
```
→ Phase 1 already renders all 11 fields (8 climbing + 3 metadata: id, name, date) including `icu_rpe`. The CONTEXT.md / RESEARCH.md note that Phase 2 "extends to handle `icu_rpe` post-enrichment readback rendering" is largely satisfied by the existing renderer. Phase 2's extension is therefore minimal — likely just a docstring update noting that the renderer is now used post-enrichment readback (per D-24, this is additive). If the planner identifies any new field surfaced by Plan 02-01 probe (e.g., a wellness-style "comments" line that should appear post-enrich), add it here following the **`isinstance` defensive-render pattern** already used for `indoor` and `rpe`. Do NOT touch `format_wellness_entry` (lines 271+).

---

### `tests/test_wellness_write.py` (NEW)

**Analog:** `tests/test_climbing.py` lines 122-217 (Phase 1 verify tool tests — exact same monkeypatch + `asyncio.run` shape).

**sys.path / env-default header** (`tests/test_climbing.py` lines 1-19):
```python
"""Unit tests for utils/climbing.py — enum ↔ CUSTOM_FIELD_KEYS alignment."""

import asyncio
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

import pytest  # pylint: disable=wrong-import-position

from intervals_mcp_server.utils.climbing import (  # pylint: disable=wrong-import-position
    CUSTOM_FIELD_KEYS,
    Discipline,
    FieldSpec,
    SessionFocus,
)
```
→ Copy verbatim. Replace the imports with `from intervals_mcp_server.utils.wellness import WELLNESS_RANGES, PARAM_TO_API_FIELD, build_wellness_put_body, sleep_hours_to_secs` and `from intervals_mcp_server.tools.wellness import write_wellness_entry`.

**Alignment test pattern** (`tests/test_climbing.py` lines 34-41 — `test_discipline_options_match_custom_field_spec`):
```python
def test_discipline_options_match_custom_field_spec() -> None:
    spec_options = CUSTOM_FIELD_KEYS["discipline"].options
    assert spec_options == tuple(d.value for d in Discipline)
```
→ Per CONTEXT.md `<specifics>` and D-19, mirror this for **WELLNESS_RANGES ↔ tool signature alignment**: introspect `write_wellness_entry`'s parameters via `inspect.signature` and assert that every numeric Optional param (`sleep_quality`, `soreness`, `fatigue`, `motivation`, `stress`, `mood`) has an entry in `WELLNESS_RANGES`. Changing one without the other fails the test.

**Async-tool monkeypatch + `asyncio.run` pattern** (`tests/test_climbing.py` lines 122-138):
```python
def test_verify_custom_fields_setup_all_present(monkeypatch: pytest.MonkeyPatch) -> None:
    from intervals_mcp_server.tools.climbing import verify_custom_fields_setup

    sample = _make_fake_all_present()

    async def fake_request(*_args: object, **_kwargs: object) -> object:
        return sample

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )
    result = asyncio.run(verify_custom_fields_setup(athlete_id="i1"))
    assert "All required" in result
```
→ Critical: monkeypatch in **both** `intervals_mcp_server.api.client.make_intervals_request` AND `intervals_mcp_server.tools.wellness.make_intervals_request` (the tool module re-imports the symbol). Required tests:
- Happy path: PUT succeeds + GET readback returns supplied fields verbatim → "Successfully wrote..." string with format_wellness_entry-rendered output.
- Empty-call rejection (D-10): only `date` supplied → error string.
- Out-of-range value (D-07): `fatigue=99` → ValueError or error-string (planner picks; ValueError is the validator pattern from `validate_grade`).
- `sleep_hours: 8.0` → readback receives `sleepSecs: 28800` (drop-None + unit conversion roundtrip).
- API error from PUT → user-facing error string includes API message.
- Readback shows missing/different value → user-facing readback-failure error string (D-11), no `_README_POINTER` (wellness, not custom fields).

**Tool-registration sanity test pattern** (`tests/test_climbing.py` lines 111-119):
```python
def test_verify_tool_registered() -> None:
    """verify_custom_fields_setup must be importable from the server module."""
    from intervals_mcp_server.server import (  # noqa: F401
        verify_custom_fields_setup as server_verify,
    )
    from intervals_mcp_server.tools.climbing import (
        verify_custom_fields_setup as tool_verify,
    )
    assert server_verify is tool_verify
```
→ Mirror for `write_wellness_entry`: confirms `pytest --collect-only` discovers it AND that `server.py` imports the new symbol via the existing `from intervals_mcp_server.tools.wellness import ...` line (no server.py edit needed if the existing import is `from intervals_mcp_server.tools.wellness import *` style — verify; otherwise add the symbol to that import per D-23).

---

### `tests/test_climbing_write.py` (NEW)

**Analog:** Same as `tests/test_wellness_write.py` — `tests/test_climbing.py` lines 22-69 (alignment) + 122-217 (monkeypatch + asyncio.run).

**Required tests:**
- Tool-registration sanity (mirrors `test_verify_tool_registered`).
- Empty-call rejection (D-12 at-least-one).
- Grade-without-discipline rejection (D-12).
- Font-on-route or French-on-boulder via `validate_grade` (D-13) — the existing `tests/test_grades.py` covers `validate_grade` itself, so this test only needs to confirm the tool wraps the ValueError into a user string.
- Verify-fields guard fires on custom-field write (D-20) — monkeypatch `_verify_custom_fields_setup_impl` to return `(False, ['discipline'], 'Missing...')` and assert tool returns `human_message`.
- Verify-fields guard SKIPS on RPE-only write (D-20) — monkeypatch `_verify_custom_fields_setup_impl` to raise; assert it is not called when only `rpe` is supplied.
- Conflict-scan default-deny (D-14): GET returns activity with `discipline="bouldering"` already set; tool refuses with conflicts list.
- `override=True` proceeds AND calls `add_activity_message` (D-14): assert the audit POST happens with the `[enrich override]` prefix and old→new values.
- Readback verification: PUT succeeds but GET shows `discipline=null` → error string includes `_README_POINTER` (custom-field readback failure).
- Readback verification (RPE-only): PUT succeeds but GET shows `icu_rpe=null` → error string does NOT include `_README_POINTER`.
- Type-coercion drift (RESEARCH.md Pattern 3): readback returns `icu_rpe=6.0` (float) when sent `6` (int) — comparison still passes (Python `6 == 6.0`).

**Planner discretion** (per CONTEXT.md `<decisions>` "Claude's Discretion"): may instead append these tests to `tests/test_climbing.py` if file size stays manageable; D-23 says the new file is the safer call.

---

### `scripts/spike_write_endpoints_phase2.py` OR extension to `scripts/spike_write_endpoints.py` (NEW — Plan 02-01)

**Analog:** `scripts/spike_write_endpoints.py` (Phase 1 — exact same scaffolding).

**Header + sys.path + `make_intervals_request` import + redaction helper** (`scripts/spike_write_endpoints.py` lines 1-69):
```python
#!/usr/bin/env python3
"""
Spike: confirm write-path contracts for Intervals.icu wellness + activities.

NOT A PYTEST TEST. ...
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

# Mirror the sys.path pattern used by tests/test_make_intervals_request.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from intervals_mcp_server.api.client import make_intervals_request  # noqa: E402
from intervals_mcp_server.config import get_config  # noqa: E402
from intervals_mcp_server.utils.formatting import format_climbing_activity  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("spike")

SPIKE_DATE = "2099-01-01"  # far-future, no real data here
ATHLETE_REDACTED = "{athlete_id}"  # placeholder used in findings file
FINDINGS_PATH = (
    Path(__file__).resolve().parents[1]
    / ".planning"
    / "phases"
    / "01-foundation-and-write-path-spike"
    / "01-SPIKE-FINDINGS.md"
)
```
→ Phase 2 spike copies the entire scaffolding. Two edits:
1. `FINDINGS_PATH` points to `.planning/phases/02-wellness-write-and-activity-enrichment/02-SPIKE-FINDINGS.md` (D-02 — Phase 2 owns its own findings).
2. Replace the three Phase 1 spike functions with the Phase 2 probes:
   - `spike_activity_custom_field_put_shapes(athlete_id)` — D-01a; iterate body-shape variants (top-level keys, nested `customFields: {...}` envelope, alternate URLs `PUT /athlete/{id}/activity/{id}`, `POST /activity/{id}`) until one roundtrips through readback.
   - `spike_wellness_subjective_scales(athlete_id)` — D-01b; probe `fatigue`, `stress`, `motivation`, `mood`, `soreness`, `sleep_quality` with values across 1-4 and 1-10; record which range each accepts.
   - `spike_icu_rpe_write_path(athlete_id)` — D-01c; try `icu_rpe: 6` in the same PUT as custom fields; if 422, isolate to its own PUT.

**Spike body iteration pattern** (`scripts/spike_write_endpoints.py` lines 180-196 — the Phase 1 attempt that returned 422 and is the seed for Phase 2's expanded probe):
```python
# A2: custom-field write as top-level keys on the activity
cf_write = await make_intervals_request(
    url=f"/activity/{activity_id}",
    data={"discipline": "bouldering", "icu_rpe": 6},
    method="PUT",
)
findings["custom_field_write_response"] = cf_write

readback_after_cf = await make_intervals_request(url=f"/activity/{activity_id}")
findings["readback_after_custom_field_put"] = readback_after_cf

roundtripped = (
    isinstance(readback_after_cf, dict)
    and readback_after_cf.get("discipline") == "bouldering"
    and readback_after_cf.get("icu_rpe") == 6
)
findings["custom_field_roundtripped"] = roundtripped
```
→ Phase 2 wraps this in a list of body-shape candidates and a list of URL/method candidates, iterating each combo until `roundtripped == True`. **First combo that roundtrips wins** (analogous to `DEFINITIONS_CANDIDATES` for-else pattern at lines 219-249).

**Findings-write pattern** (`scripts/spike_write_endpoints.py` lines 252-288 — `write_findings`):
```python
def write_findings(...) -> None:
    """Dump findings to 01-SPIKE-FINDINGS.md with copy-pasteable code fences.

    Redacts athlete_id everywhere.
    """
    FINDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    wellness_redacted = _redact(wellness, athlete_id)
    ...
    content = [
        "# Spike findings — write-path probes\n\n",
        f"**Spike date (target):** {SPIKE_DATE}\n\n",
        ...
        "```json\n",
        json.dumps(wellness_redacted, indent=2, default=str),
        "\n```\n\n",
    ]
    FINDINGS_PATH.write_text("".join(content), encoding="utf-8")
```
→ Copy verbatim. Output `02-SPIKE-FINDINGS.md` with three sections matching D-01 (a/b/c), each with a paste-ready JSON code block and (for the activity custom-field PUT section) a **paste-ready Python body shape that Plan 02-04 copies verbatim** per CONTEXT.md `<specifics>`.

---

### `.planning/phases/02-wellness-write-and-activity-enrichment/02-SPIKE-FINDINGS.md` (NEW)

**Analog:** `.planning/phases/01-foundation-and-write-path-spike/01-SPIKE-FINDINGS.md` — written by the spike script (NOT hand-edited by the planner).

Same shape: top-level title, spike date, redaction note, three top-level `## ...` sections (one per probe), each with a `\`\`\`json` fenced block of redacted findings, a manual-cleanup note at the end. The script's `write_findings` produces this artifact directly.

---

### Smoke-test script (NEW — Plan 02-05 / D-25, name TBD by planner)

**Analog:** `scripts/spike_write_endpoints.py` — same scaffolding (header, sys.path, `make_intervals_request` import, `SPIKE_DATE = "2099-01-01"`, redaction helper, DELETE cleanup).

**Distinction from Plan 02-01 spike:** Plan 02-01 PROBES unknowns; Plan 02-05 EXERCISES the locked tool surface end-to-end. Both are standalone scripts (not pytest, never in CI per D-25). Smoke-test script:
1. Calls `write_wellness_entry(date=SPIKE_DATE, sleep_hours=8.0, fatigue=2, ...)` — verifies tool path top to bottom.
2. POSTs a throwaway activity (mirrors `scripts/spike_write_endpoints.py::spike_activity_create` lines 132-213 — already CONFIRMED working in Phase 1 spike).
3. Calls `enrich_activity_climbing(activity_id=<from step 2>, discipline="bouldering", ...)`.
4. DELETE both — confirmed available by Phase 1 spike per `01-SPIKE-FINDINGS.md`.

No new HTTP patterns — all already in spike script analog.

---

## Shared Patterns

### Authentication / API key
**Source:** `src/intervals_mcp_server/api/client.py::make_intervals_request` (lines 152-223) — the single HTTP boundary, never bypassed.

**Apply to:** Both new tools, both new scripts. Tools accept `api_key: str | None = None` and pass it through; scripts resolve via `get_config().api_key` (already done by `make_intervals_request` if `api_key=None`).

```python
result = await make_intervals_request(
    url="/...",
    api_key=api_key,        # may be None — falls back to config
    params=params,          # GET only
    method="PUT",           # or "GET", "POST", "DELETE"
    data=body,              # PUT/POST only
)
```
Constraint per `PROJECT.md`: "All Intervals.icu HTTP goes through `make_intervals_request()`. Don't call `httpx` directly from tools." — Phase 2 honors this; no new httpx imports anywhere outside `api/client.py`.

---

### Athlete-ID resolution + early-return error
**Source:** `src/intervals_mcp_server/utils/validation.py::resolve_athlete_id` (lines 50-70).

**Apply to:** Both new tools (`write_wellness_entry`, `enrich_activity_climbing`). First operation in tool body:
```python
athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
if error_msg:
    return error_msg
```
Already used by `get_wellness_data` and `verify_custom_fields_setup` — established pattern.

---

### Error handling — API result → user-facing string
**Source:** `src/intervals_mcp_server/tools/wellness.py::get_wellness_data` (lines 51-52); `src/intervals_mcp_server/tools/climbing.py` (line 62-64).

**Apply to:** All `make_intervals_request` call sites in both new tools and both scripts.
```python
result = await make_intervals_request(...)
if isinstance(result, dict) and "error" in result:
    return f"Error <action>: {result.get('message', 'Unknown error')}"
```
Tools must return `str` per MCP protocol (CONVENTIONS.md "Tool functions (MCP endpoints) always return strings"). Validators raise `ValueError`; tools either let the exception propagate (for unrecoverable bugs) or catch and return the message string for user-recoverable input errors (per D-07/D-13).

---

### Validation-before-HTTP (fail-fast)
**Source:** `src/intervals_mcp_server/utils/grades.py::validate_grade` (lines 33-63 — pure ValueError on bad input; never makes a network call).

**Apply to:** Both new tools — all input validation runs BEFORE the first `make_intervals_request`. Per Pitfall #6 (LLM may misclassify) and CONVENTIONS.md "Validation functions raise `ValueError` with descriptive messages":
- `write_wellness_entry`: range check via `WELLNESS_RANGES`, empty-call check (D-10).
- `enrich_activity_climbing`: at-least-one-supplied check (D-12), grade↔discipline coupling (D-12), `validate_grade` call per supplied grade (D-13), `rpe` range 1-10.

---

### Test discovery + monkeypatch + asyncio.run
**Source:** `tests/test_climbing.py` lines 1-19 (sys.path + env defaults + import-after-path-setup) and lines 122-138 (dual-monkeypatch + `asyncio.run`).

**Apply to:** Both new test files (D-23 — `pytest --collect-only` MUST discover them, addresses Pitfall #14).

The dual-monkeypatch detail is critical: tools re-import the `make_intervals_request` symbol at module load, so both `intervals_mcp_server.api.client.make_intervals_request` AND `intervals_mcp_server.tools.<module>.make_intervals_request` need patching, OR the test will silently call the real API.

---

### Module-private import discipline
**Source:** Phase 1 D-18 (carried forward as Phase 2 D-22).

**Apply to:** `enrich_activity_climbing` and any utility extraction during Phase 2.
- `_verify_custom_fields_setup_impl` lives in `tools/climbing.py` and is consumed by `enrich_activity_climbing` from the **same module** — no cross-module `_`-prefix import.
- `add_activity_message` is **public** (no leading underscore) — `from intervals_mcp_server.tools.activities import add_activity_message` is allowed.
- If `tools/wellness.py` and `tools/climbing.py` ever want to share a helper (e.g., a generic readback-equality helper), promote it to `utils/` first per D-22.

---

## No Analog Found

| File / Pattern | Role | Data Flow | Reason | Mitigation |
|----------------|------|-----------|--------|------------|
| Activity custom-field PUT body shape | request-response | (write) | Phase 1 spike's `{"discipline": "bouldering", "icu_rpe": 6}` returned 422; no working example exists in the codebase | Plan 02-01 second probe MUST land a working shape; D-05 hard-stop if it can't. Once locked, the body shape is paste-ready into Plan 02-04. |
| Readback **value-equality** verification (vs Phase 1's presence-only heuristic) | utility helper (likely inline in tool) | transform | Phase 1's `_verify_custom_fields_setup_impl` only checks key presence on any recent activity — not value equality on a specific activity | New inline logic in `enrich_activity_climbing`; type-coercion drift caveats per RESEARCH.md `## Pattern 3`. |
| Conflict-scan / default-deny re-write guard | tool-internal validator | request-response (GET → compare) | Pitfall #10 mitigation; no existing tool implements default-deny re-write | New inline logic in `enrich_activity_climbing`; the per-line conflict-message format is in CONTEXT.md `<specifics>`. |
| Override audit-trail message format | string template | static | New format `[enrich override] field: old→new (prior values preserved here)` per CONTEXT.md `<specifics>` | Inline string format; the POST itself reuses `add_activity_message` exactly. |

---

## Metadata

**Analog search scope:**
- `src/intervals_mcp_server/tools/` — wellness.py (71 lines), climbing.py (145 lines), activities.py (382 lines, sections 100-208 + 320-381 read).
- `src/intervals_mcp_server/utils/` — grades.py (63 lines), climbing.py (98 lines), validation.py (88 lines), formatting.py (sections 265-355 + 552-592 read).
- `src/intervals_mcp_server/api/client.py` (242 lines).
- `scripts/spike_write_endpoints.py` (311 lines).
- `tests/test_climbing.py` (217 lines), `tests/test_formatting.py` (header read).
- `.planning/phases/01-foundation-and-write-path-spike/01-PATTERNS.md` (header read for shape consistency).

**Files scanned:** 11 source / 2 tests / 1 script / 1 doc.
**Pattern extraction date:** 2026-04-25.
