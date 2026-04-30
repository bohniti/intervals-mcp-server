# Phase 4: Training Status Report — Pattern Map

**Mapped:** 2026-04-28
**Files analyzed:** 3 new
**Analogs found:** 3 / 3 (all exact role + data-flow matches)

This map is anchored to CONTEXT.md (no RESEARCH.md exists for this phase). Every pattern below points to **real, current** code in the repo — line numbers are stable as of the commit at HEAD. The new code is **purely additive** (D-20): no existing module is modified.

---

## File Classification

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `src/intervals_mcp_server/tools/status.py` | tool (MCP entry point) | request-response (read-only, two GETs → one rendered string) | `src/intervals_mcp_server/tools/wellness.py` (`get_wellness_data`) | exact |
| `src/intervals_mcp_server/utils/status.py` | utility (constants + pure helpers) | transform (dict/list → string) | `src/intervals_mcp_server/utils/wellness.py` (`WELLNESS_RANGES`, helpers) + `src/intervals_mcp_server/utils/climbing.py` (`StrEnum` + `MappingProxyType` constants) | exact |
| `tests/test_status.py` | test | request-response (mocks `make_intervals_request`) | `tests/test_climbing_create.py` | exact |

Cross-cutting analogs (referenced from multiple new files):
- `src/intervals_mcp_server/utils/formatting.py` — shape of `format_*` helpers (pure, dict-in / string-out, bullet-list rendering)
- `src/intervals_mcp_server/tools/climbing.py` — `as_of_date` validation pattern, `oldest`/`newest` activities scan, MCP tool registration
- `src/intervals_mcp_server/utils/validation.py` — `validate_date()` and `resolve_athlete_id()` reused unchanged
- `src/intervals_mcp_server/server.py` lines 72–95 — tool re-export block where `status` must be added

---

## Pattern Assignments

### `src/intervals_mcp_server/tools/status.py` (tool, request-response)

**Primary analog:** `src/intervals_mcp_server/tools/wellness.py` (matches the read-only `oldest`/`newest` query against `/athlete/{id}/wellness`).

**Secondary analog:** `src/intervals_mcp_server/tools/climbing.py` (matches the `oldest`/`newest` activities scan used for the RPE-coverage check + the date-validation upfront pattern).

#### Pattern A: Module header + imports (mirror `tools/wellness.py` lines 1–28)

```python
"""
Training status MCP tool for Intervals.icu.

Single read-only tool — `get_training_status` — that returns one plain-text
report blending CTL/ATL/TSB training-load metrics, recent wellness signals,
and an RPE-coverage data-quality flag. Read-only: two GETs, no writes.
"""

from typing import Any

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.status import (
    # constants + helpers — defined in utils/status.py
    WINDOW_DAYS_LONG_TERM,
    WINDOW_DAYS_RPE,
    WINDOW_DAYS_WEEKLY,
    compute_rpe_coverage,
    format_status_report,
    tsb_band,
)
from intervals_mcp_server.utils.validation import resolve_athlete_id, validate_date

# Import mcp instance from shared module for tool registration
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401

config = get_config()
```

Key conventions captured:
- `from intervals_mcp_server.api.client import make_intervals_request` — D-17 / project rule.
- `from intervals_mcp_server.mcp_instance import mcp  # noqa: F401` — exact comment mirrors every other tool module (`activities.py:16`, `wellness.py:26`, `climbing.py:23`).
- `config = get_config()` at module level — every tool module does this.
- No `_`-prefix imports across sibling tool modules (D-22 carry-forward).

#### Pattern B: `as_of_date` validation + default (mirror `tools/wellness.py:147–149` + `utils/validation.py:31–47`)

`tools/wellness.py:146–149`:
```python
# Date format check first — fail fast before HTTP.
try:
    validate_date(date)
except ValueError as exc:
    return f"Error: {exc}"
```

`utils/validation.py:31–47`:
```python
def validate_date(date_str: str) -> str:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError as exc:
        raise ValueError("Invalid date format. Please use YYYY-MM-DD.") from exc
```

For `get_training_status`, when `as_of_date is None` default to today's UTC date *before* validation, then run `validate_date(as_of_date)` the same way. Per CONTEXT D-19, never derive the user-facing date from `datetime.now()` after this resolution step — the resolved string IS the contract.

```python
# Inside get_training_status, after resolve_athlete_id:
if as_of_date is None:
    from datetime import datetime, timezone  # local import keeps top section clean
    as_of_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
try:
    validate_date(as_of_date)
except ValueError as exc:
    return f"Error: {exc}"
```

#### Pattern C: Athlete-ID resolution (verbatim from every prior tool, see `tools/wellness.py:52–54`)

```python
athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
if error_msg:
    return error_msg
```

Three lines, copy unchanged. D-22 / Pitfall carry-forward.

#### Pattern D: Range query against `/athlete/{id}/wellness` (verbatim from `tools/wellness.py:58–62`)

```python
params = {"oldest": start_date, "newest": end_date}

result = await make_intervals_request(
    url=f"/athlete/{athlete_id_to_use}/wellness", api_key=api_key, params=params
)

if isinstance(result, dict) and "error" in result:
    return f"Error fetching wellness data: {result.get('message')}"
```

For Phase 4: `start_date` = `as_of_date - WINDOW_DAYS_LONG_TERM days` (covers the 42-day window — D-04 says one wellness call covers every section of the report). `end_date` = `as_of_date`.

Date arithmetic uses `datetime.strptime(as_of_date, "%Y-%m-%d") - timedelta(days=N)` then `.strftime("%Y-%m-%d")` — same shape as `tools/activities.py:56–58`:

```python
oldest_date = datetime.fromisoformat(start_date)
older_start_date = (oldest_date - timedelta(days=60)).strftime("%Y-%m-%d")
older_end_date = (oldest_date - timedelta(days=1)).strftime("%Y-%m-%d")
```

#### Pattern E: Range query against `/athlete/{id}/activities` (verbatim from `tools/climbing.py:625–636`)

`tools/climbing.py:626–636`:
```python
dup_params: dict[str, Any] = {"oldest": date, "newest": date}
dup_result = await make_intervals_request(
    url=f"/athlete/{athlete_id_to_use}/activities",
    api_key=api_key,
    params=dup_params,
)
if isinstance(dup_result, dict) and "error" in dup_result:
    return (
        f"Error checking for duplicate activities: "
        f"{dup_result.get('message', 'Unknown error')}"
    )
```

For Phase 4 the window is `WINDOW_DAYS_RPE` (14 days) ending on `as_of_date`. After the GET, filter to climbing only — same field check the duplicate-guard uses (`activity.get("type") != "WeightTraining"`):

```python
# tools/climbing.py:638-647 — the type-filter shape to mirror.
matches: list[dict[str, Any]] = []
if isinstance(dup_result, list):
    for activity in dup_result:
        if not isinstance(activity, dict):
            continue
        if activity.get("type") != "WeightTraining":
            continue
        ...
```

For status, the loop populates `climbing_activities` instead of `matches`, then passes them to `compute_rpe_coverage()`.

#### Pattern F: Unified MCP tool decorator + signature shape (mirror `tools/wellness.py:31–51`)

```python
@mcp.tool()
async def get_training_status(
    athlete_id: str | None = None,
    api_key: str | None = None,
    as_of_date: str | None = None,
) -> str:
    """Return a plain-text training-status report blending CTL/ATL/TSB,
    recent wellness signals, and a climbing RPE-coverage data-quality flag.

    Reads (no writes):
      - GET /athlete/{id}/wellness?oldest=...&newest=... (42-day window)
      - GET /athlete/{id}/activities?oldest=...&newest=... (14-day window)

    Args:
        athlete_id: Optional Intervals.icu athlete ID (falls back to ATHLETE_ID env).
        api_key: Optional Intervals.icu API key (falls back to API_KEY env).
        as_of_date: Optional YYYY-MM-DD; defaults to today (UTC). Lets Claude ask
            'what was my readiness on 2026-04-21'.

    Returns:
        A single plain-text report (~400-600 tokens) with three labeled
        sections (## Today / ## This Week / ## Long-Term Trend). Always returns
        SOME report — never errors on sparse data; per-section graceful degradation.
    """
```

D-16 spec exactly. Three params, all optional. Public signature is the contract.

#### Pattern G: Tool registration in `server.py` (mirror line 95)

`server.py:95`:
```python
from intervals_mcp_server.tools.climbing import verify_custom_fields_setup  # pylint: disable=wrong-import-position  # noqa: E402
```

Add a sibling line (preserving the same trailing comment):
```python
from intervals_mcp_server.tools.status import get_training_status  # pylint: disable=wrong-import-position  # noqa: E402
```

The import-side-effect drives `@mcp.tool()` registration — no further wiring.

#### What to NOT carry over from these analogs

- **No PUT/POST.** Phase 4 is read-only (D-17, D-20). Skip everything wellness.py / climbing.py do after the GET (PUT body building, readback, conflict scan, duplicate guard refusal, audit messages, override paths).
- **No `_`-prefix cross-tool helpers.** Pull constants/helpers from `utils/status.py`, never reach into `tools/wellness.py::_something`.
- **No `verify_custom_fields_setup` invocation.** Status writes nothing — the custom-field guard is irrelevant (and `icu_rpe` is native, not custom; D-21 carry-forward).
- **No `format_climbing_activity` / `format_wellness_entry` reuse.** Those formatters render *single entities* in long form; the status report is a synthesis across many entries with a strict token budget. New helpers in `utils/status.py` produce the section-bullet shape.
- **No `_skip_conflict_scan` / `override` flags.** Read-only.

---

### `src/intervals_mcp_server/utils/status.py` (utility, transform)

**Primary analog:** `src/intervals_mcp_server/utils/wellness.py` (constants table at top + leaf-module discipline: no HTTP / no tool / no API client imports).

**Secondary analog:** `src/intervals_mcp_server/utils/climbing.py` (StrEnum + `MappingProxyType` frozen constants + `__all__` export discipline).

**Tertiary analog:** `src/intervals_mcp_server/utils/formatting.py` (shape of `format_*` helpers: pure, take dict, return string).

#### Pattern H: Module header + leaf-module rule (mirror `utils/wellness.py:1–14`)

```python
"""
Training-status constants + pure rendering helpers.

Single source of truth for:
- TSB band thresholds (TSB_BANDS) — locked from CONTEXT D-03.
- Window constants (WINDOW_DAYS_*) — locked from CONTEXT D-06.
- RPE coverage threshold + small-sample floor — locked from CONTEXT D-08, D-11.
- Pure formatters (format_today_section / format_weekly_section /
  format_longterm_section / format_status_report) — dict/list in, string out.

No HTTP, no tool, no API client imports. Leaf module.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any

__all__ = [
    "TSB_BANDS",
    "WINDOW_DAYS_WEEKLY",
    "WINDOW_DAYS_LONG_TERM",
    "WINDOW_DAYS_RPE",
    "RPE_MISSING_THRESHOLD",
    "MIN_RPE_SAMPLE",
    "tsb_band",
    "compute_rpe_coverage",
    "format_today_section",
    "format_weekly_section",
    "format_longterm_section",
    "format_status_report",
]
```

The "No HTTP, no tool, no API client imports. Leaf module." sentence is verbatim from `utils/wellness.py:13`. Every public symbol in `__all__`.

#### Pattern I: Constants table at module top (mirror `utils/wellness.py:29–41` and `utils/climbing.py:60–98`)

`utils/wellness.py:34–41` (the "single source of truth dict at module top" pattern):
```python
WELLNESS_RANGES: MappingProxyType[str, tuple[int, int]] = MappingProxyType({
    "fatigue": (1, 4),
    "stress": (1, 4),
    "motivation": (1, 4),
    "mood": (1, 4),
    "soreness": (1, 4),
    "sleep_quality": (1, 4),
})
```

`utils/climbing.py:60–98` (frozen-dict-of-dataclasses pattern):
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

Apply to TSB bands. Recommended shape (CONTEXT D-03):
```python
# TSB bands locked from CONTEXT D-03. Tuple = (lower_exclusive, upper_inclusive, label).
# Order matters: tsb_band() walks them in order and returns the first match.
TSB_BANDS: tuple[tuple[float, float, str], ...] = (
    (25.0, float("inf"), "Burnt out / Detraining"),
    (5.0, 25.0,          "Fresh"),
    (-10.0, 5.0,         "Balanced"),
    (-25.0, -10.0,       "Fatigued (productive load)"),
    (float("-inf"), -25.0, "Risk"),
)

WINDOW_DAYS_WEEKLY: int = 7
WINDOW_DAYS_LONG_TERM: int = 42
WINDOW_DAYS_RPE: int = 14
RPE_MISSING_THRESHOLD: float = 0.30  # CONTEXT D-08
MIN_RPE_SAMPLE: int = 3              # CONTEXT D-11
```

`MappingProxyType` for `TSB_BANDS` is overkill (sequence not mapping); a plain tuple is fine and matches Python convention. The other constants are bare scalars per `utils/wellness.py` precedent (`WELLNESS_RANGES` is the only `MappingProxyType` there — it wraps the table because it's a *mapping*).

#### Pattern J: Pure helper functions (mirror `utils/wellness.py:60–74` for `sleep_hours_to_secs`)

```python
def sleep_hours_to_secs(hours: float) -> int:
    """Convert user-friendly sleep hours to API-native sleepSecs.

    Args:
        hours: Hours of sleep (e.g. 8.0). Negative values are invalid.

    Returns:
        Integer seconds rounded to the nearest whole second.

    Raises:
        ValueError: If hours is negative.
    """
    if hours < 0:
        raise ValueError(f"sleep_hours must be non-negative, got {hours}")
    return int(round(hours * 3600))
```

`tsb_band(tsb: float) -> str` and `compute_rpe_coverage(activities: list[dict]) -> tuple[int, int]` follow the same shape:
- One-line summary, multi-line docstring with Args/Returns/(Raises).
- No mutation of inputs.
- Explicit Python types in signature (`float`, `list[dict]`, `tuple[int, int]`).
- No HTTP, no I/O.

`compute_rpe_coverage` returns `(missing_count, total_count)` so the caller can branch on `MIN_RPE_SAMPLE` and `RPE_MISSING_THRESHOLD` separately. Per CONTEXT D-10: "Lacks RPE" = `icu_rpe` absent OR `None`; literal `0` is logged data:

```python
def compute_rpe_coverage(activities: list[dict[str, Any]]) -> tuple[int, int]:
    """Count climbing activities lacking RPE.

    Per CONTEXT D-10: an activity 'lacks RPE' when the dict has no `icu_rpe`
    key OR the value is None. A literal 0 IS logged data (some climbers use
    0 for no perceived effort). Caller is responsible for pre-filtering to
    climbing activities only (type == 'WeightTraining', CONTEXT D-09).

    Args:
        activities: List of climbing-activity dicts (already filtered).

    Returns:
        (missing_count, total_count). Caller branches on MIN_RPE_SAMPLE and
        RPE_MISSING_THRESHOLD against this.
    """
    total = len(activities)
    missing = sum(
        1 for a in activities
        if a.get("icu_rpe") is None
    )
    return missing, total
```

#### Pattern K: Section formatters mirror `utils/formatting.py` shape

`utils/formatting.py:133–145` is the cleanest in-repo example of the "build list of bullet lines" idiom:

```python
def _format_training_metrics(entries: dict[str, Any]) -> list[str]:
    """Format training metrics section."""
    training_metrics = []
    for k, label in [
        ("ctl", "Fitness (CTL)"),
        ("atl", "Fatigue (ATL)"),
        ("rampRate", "Ramp Rate"),
        ("ctlLoad", "CTL Load"),
        ("atlLoad", "ATL Load"),
    ]:
        if entries.get(k) is not None:
            training_metrics.append(f"- {label}: {entries[k]}")
    return training_metrics
```

And `utils/formatting.py:301–310` shows the "section heading + bullet lines + blank separator" assembly:

```python
lines = ["Wellness Data:"]
lines.append(f"Date: {entries.get('id', 'N/A')}")
lines.append("")

training_metrics = _format_training_metrics(entries)
if training_metrics:
    lines.append("Training Metrics:")
    lines.extend(training_metrics)
    lines.append("")
```

For Phase 4, swap the section heading to markdown-style `## Today` (per CONTEXT D-01 — minimal markdown, three labeled sections), keep the bullet-list shape, and apply CONTEXT D-13's graceful-empty rule (each section renders its own one-liner when data is empty rather than skipping):

```python
def format_today_section(
    today_entry: dict[str, Any] | None,
    wellness_recent: list[dict[str, Any]],   # last 7 days for blend
    walk_back_days: int,                      # 0 if today entry is fresh, N if walked back
) -> str:
    """Render the Today section. Always returns at least one bullet — never empty.

    Per CONTEXT D-13: if there is no usable wellness within 7 days, return:
        '## Today\\n- No wellness data in last 7 days.\\n'
    """
    lines = ["## Today"]
    if today_entry is None:
        lines.append("- No wellness data in last 7 days.")
        return "\n".join(lines) + "\n"

    ctl = today_entry.get("ctl")
    atl = today_entry.get("atl")
    if ctl is None or atl is None:
        lines.append("- No CTL/ATL trend data in last 7 days.")
        return "\n".join(lines) + "\n"

    tsb = ctl - atl
    band = tsb_band(tsb)
    # CONTEXT D-02 — show number AND verbal band.
    lines.append(f"- Readiness: {band} (TSB {tsb:+.1f})")
    if walk_back_days > 0:
        lines.append(f"- Latest fitness data: {walk_back_days} day(s) ago.")

    # ... wellness-blend bullets from wellness_recent (Claude's discretion shape).
    return "\n".join(lines) + "\n"
```

`format_weekly_section` and `format_longterm_section` follow the same shape — one heading, one bullet list, graceful one-liner on empty. `format_status_report` is the orchestrator: calls all three, joins with a blank line.

#### What to NOT carry over from these analogs

- **No `_KeyTracker` / accessed-key tracking** (`utils/formatting.py:12–29`). That's a special-purpose tool for the `include_all_fields` path of `format_wellness_entry`; status has a *fixed* set of fields per the token budget.
- **No long verbose `format_wellness_entry`-style multi-section dump.** The token budget (400–600) forbids it. Status sections are tight bullet lists.
- **No `MappingProxyType` over `TSB_BANDS`.** It's an ordered sequence, not a mapping; a tuple is correct.
- **No range-validation table** like `WELLNESS_RANGES`. Status reads, doesn't write — there's nothing to validate against.
- **No Discipline / SessionFocus enums.** Those belong to climbing-write paths. The only enum-style data in status is the TSB band labels, which are string literals living in `TSB_BANDS`.

---

### `tests/test_status.py` (test, request-response)

**Primary analog:** `tests/test_climbing_create.py` (matches: monkeypatch `make_intervals_request`, dict-literal fakes, `asyncio.run` driver, no httpx, no recorded JSON fixtures).

**Secondary reference:** `tests/test_wellness_write.py` (sibling test for the wellness module — same scaffolding pattern).

#### Pattern L: Test-file header + path bootstrapping (mirror `tests/test_climbing_create.py:1–18`)

```python
"""Unit tests for tools/status.py::get_training_status — STAT-01..STAT-04."""

import asyncio
import inspect
import os
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

import pytest  # pylint: disable=wrong-import-position

from intervals_mcp_server.utils.status import (  # pylint: disable=wrong-import-position
    MIN_RPE_SAMPLE,
    RPE_MISSING_THRESHOLD,
    TSB_BANDS,
    WINDOW_DAYS_LONG_TERM,
    WINDOW_DAYS_RPE,
    WINDOW_DAYS_WEEKLY,
    compute_rpe_coverage,
    tsb_band,
)
```

Verbatim copy of the bootstrap block (lines 1–18 of `test_climbing_create.py`). The `sys.path.insert` and env-var defaults are required for the test to resolve imports without a full install.

#### Pattern M: Hand-crafted dict fakes for fixtures (mirror `tests/test_climbing_create.py:26–51`)

Per CONTEXT "Claude's Discretion" — "project convention so far has been mostly hand-crafted dicts (see `tests/test_climbing_create.py`)." Confirmed:

`tests/test_climbing_create.py:40–51`:
```python
def _make_fake_clean_activity(activity_id: str = "i142495224") -> dict[str, object]:
    """Activity dict with no climbing fields set (post-create, pre-enrich shape)."""
    activity: dict[str, object] = {
        "id": activity_id,
        "name": "Climbing — 2026-04-27",
        "type": "WeightTraining",
        "start_date_local": "2026-04-27T00:00:00",
    }
    for key in CUSTOM_FIELD_KEYS:
        activity[key] = None
    activity["icu_rpe"] = None
    return activity
```

Apply to status. Recommended fixture helpers:

```python
def _make_fake_wellness_entries(
    end_date: str = "2026-04-28",
    days: int = 42,
    *,
    ctl_seed: float = 50.0,
    atl_seed: float = 45.0,
) -> list[dict[str, Any]]:
    """List of wellness daily entries with ctl/atl populated.

    Newest entry has date == end_date; oldest is `days-1` days earlier.
    Mirrors the Intervals.icu /athlete/{id}/wellness shape from 01-SPIKE-FINDINGS.md.
    """
    from datetime import datetime, timedelta
    end = datetime.strptime(end_date, "%Y-%m-%d")
    entries: list[dict[str, Any]] = []
    for i in range(days):
        d = (end - timedelta(days=i)).strftime("%Y-%m-%d")
        entries.append({
            "id": d,
            "date": d,
            "ctl": ctl_seed + i * 0.1,
            "atl": atl_seed + i * 0.05,
        })
    return entries


def _make_fake_climbing_activity(
    activity_id: str,
    date: str,
    *,
    icu_rpe: int | None = 7,
) -> dict[str, Any]:
    """Climbing activity (type=WeightTraining) with optional rpe."""
    return {
        "id": activity_id,
        "type": "WeightTraining",
        "start_date_local": f"{date}T00:00:00",
        "icu_rpe": icu_rpe,
    }
```

#### Pattern N: Monkeypatching `make_intervals_request` (mirror `tests/test_climbing_create.py:75–115`)

Verbatim shape from `test_climbing_create.py:83–115`:

```python
async def fake_request(
    url: str,
    api_key: str | None = None,
    params: dict[str, Any] | None = None,
    method: str = "GET",
    data: dict[str, Any] | None = None,
) -> Any:
    if method == "GET" and url.endswith("/wellness"):
        return _make_fake_wellness_entries()
    if method == "GET" and url.endswith("/activities"):
        return [_make_fake_climbing_activity("i1", "2026-04-27", icu_rpe=7)]
    return []

monkeypatch.setattr(
    "intervals_mcp_server.api.client.make_intervals_request", fake_request
)
monkeypatch.setattr(
    "intervals_mcp_server.tools.status.make_intervals_request", fake_request
)
```

The two-monkeypatch trick (patch both `api.client` and the tool module's local binding) is critical and copy-pasted from every climbing test — `make_intervals_request` is imported into the tool module namespace, so patching only `api.client` would miss the call site.

#### Pattern O: Async-test driver + tool registration sanity (mirror `tests/test_climbing_create.py:59–67` + `:117–128`)

```python
def test_status_tool_registered() -> None:
    """get_training_status is async; signature has 3 params; all optional."""
    from intervals_mcp_server.tools.status import get_training_status

    assert inspect.iscoroutinefunction(get_training_status)
    sig = inspect.signature(get_training_status)
    assert len(sig.parameters) == 3, list(sig.parameters)
    for name in ("athlete_id", "api_key", "as_of_date"):
        assert name in sig.parameters
        assert sig.parameters[name].default is None


def test_status_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """STAT-01: full data → 3 sections, all rendered, in 400-600 token band."""
    from intervals_mcp_server.tools.status import get_training_status

    # ... fake_request, monkeypatch as above ...
    result = asyncio.run(
        get_training_status(athlete_id="i1", as_of_date="2026-04-28")
    )
    assert "## Today" in result
    assert "## This Week" in result
    assert "## Long-Term Trend" in result
```

Function-level test functions (no class). `pytest.MonkeyPatch` type annotation. `asyncio.run` to drive async tools. Counter dicts for HTTP-call assertions where needed (see `test_climbing_create.py:80, 141, 460` — `counters = {...}` pattern for "exactly N calls of type X").

#### Pattern P: tiktoken token-budget test (CONTEXT D-12, no in-repo precedent)

CONTEXT D-12 adds `tiktoken` (cl100k_base) as a NEW project dep. No existing test uses it — this is the one place where the planner does NOT mirror an in-repo pattern. Recommended shape (asserted but not enforced at runtime per CONTEXT):

```python
def test_status_token_budget_full_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """CONTEXT D-12: representative full-data report renders in 400-600 tokens."""
    import tiktoken
    from intervals_mcp_server.tools.status import get_training_status

    # ... full-data fakes ...
    result = asyncio.run(
        get_training_status(athlete_id="i1", as_of_date="2026-04-28")
    )
    enc = tiktoken.get_encoding("cl100k_base")
    n = len(enc.encode(result))
    assert 400 <= n <= 600, f"token count {n} outside 400-600 band:\n{result}"


def test_status_token_budget_empty_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """CONTEXT D-12: empty-data variant ALSO lands in the band."""
    # ... fakes return [] for both wellness and activities ...
```

#### What to NOT carry over from these analogs

- **No httpx-level mocking.** Tests stop at `make_intervals_request`; never go below it. (`test_make_intervals_request.py` is the dedicated test for the HTTP boundary itself; status tests don't need to touch it.)
- **No recorded JSON fixtures.** CONTEXT confirms the project convention is hand-crafted dicts. `tests/ressources/` exists but is not used by climbing tests.
- **No `delete_activity` / cleanup paths.** Status tests are pure read flows — every test ends after the rendered string is asserted.
- **No conflict-scan / override / readback-mismatch test cases.** Those are write-side concerns from `test_climbing_create.py` (the analog) that have no analog in a read-only tool.
- **No tests of `_skip_conflict_scan` flag.** Status has no such flag — and shouldn't.

---

## Shared Patterns

### Project rule: All HTTP through `make_intervals_request()`
**Source:** `src/intervals_mcp_server/api/client.py` (re-exported via `intervals_mcp_server.api.client.make_intervals_request`).
**Apply to:** `tools/status.py` only. `utils/status.py` MUST NOT import this — it's the leaf-module rule (`utils/wellness.py:13` mirrors this).

```python
# Every tool module starts with this exact import:
from intervals_mcp_server.api.client import make_intervals_request
```

CONTEXT D-17 / project-level rule. Do not call `httpx` directly.

### Athlete-ID + API-key resolution
**Source:** `src/intervals_mcp_server/utils/validation.py:50–70` (`resolve_athlete_id`).
**Apply to:** `tools/status.py` (entry of `get_training_status`).

```python
athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
if error_msg:
    return error_msg
```

`api_key` is passed through to `make_intervals_request` directly — same as `tools/wellness.py:61`. The HTTP client falls back to env if `api_key is None`; no separate resolve call is needed.

### Error responses are returned strings, not raised exceptions
**Source:** Every existing tool. Examples: `tools/wellness.py:54, 65, 149`; `tools/climbing.py:154, 163, 178, 632`.
**Apply to:** Every error path in `tools/status.py`.

Pattern: validate → if invalid, `return f"Error: {message}"`. The MCP transport surfaces the string verbatim to Claude. Never `raise`.

Status's failure modes:
- `Error: Invalid date format. Please use YYYY-MM-DD.` (from `validate_date`)
- `Error: No athlete ID provided ...` (from `resolve_athlete_id`)
- `Error fetching wellness data: <msg>` / `Error fetching activities: <msg>` (HTTP errors)

But **per CONTEXT D-13**, sparse data is **not** an error — it's a graceful per-section degradation. Empty wellness → returns a valid report with one-line "no data" notes per section.

### Date-format constant (`YYYY-MM-DD`)
**Source:** `src/intervals_mcp_server/utils/validation.py:31–47` (`validate_date`).
**Apply to:** `tools/status.py` for `as_of_date`.

CONTEXT D-19: `as_of_date` is `YYYY-MM-DD`; validate up front, raise `ValueError` (caught and returned as `Error: ...` per the pattern above). When defaulting to today, use UTC: `datetime.now(timezone.utc).strftime("%Y-%m-%d")` — never local time, never derived from the clock for any user-facing comparison post-resolution.

### Module placement (utils/<domain>.py + tools/<domain>.py split)
**Source:** Phase 1 D-14 + Phase 2 D-19 (carry-forward). In-repo example: `tools/climbing.py` + `utils/climbing.py`, `tools/wellness.py` + `utils/wellness.py`.

`tools/status.py` registers MCP tools and orchestrates HTTP + formatting.
`utils/status.py` houses constants + pure helpers; never imports tool modules or `make_intervals_request`.

---

## No Analog Found

| Concern | Note |
|---------|------|
| `tiktoken`-based token-budget test | New dep per CONTEXT D-12. No existing test uses it. Pattern P above is the planner's invention; loose convention only. |

That's the only piece without an in-repo analog. Everything else has at least one exact match.

---

## Metadata

**Analog search scope:**
- `src/intervals_mcp_server/tools/` (all 6 modules — wellness, climbing, activities, events, custom_items, plus `__init__.py`)
- `src/intervals_mcp_server/utils/` (all 7 modules — wellness, climbing, formatting, validation, dates, grades, types)
- `tests/` (test_climbing_create.py, test_wellness_write.py reviewed; test_climbing_write.py and test_climbing.py spot-checked)
- `src/intervals_mcp_server/server.py` lines 68–96 (tool re-export block)

**Files scanned:** 14 source files, 2 test files (deep), 4 spot-checks.
**Pattern extraction date:** 2026-04-28.
