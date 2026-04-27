"""
Wellness range table + PUT-body construction for Intervals.icu wellness writes.

The range table (`WELLNESS_RANGES`) is the single source of truth for hard
scale validation. Locked from 02-SPIKE-FINDINGS.md (Phase 2 second probe).
Out-of-range values are rejected by `tools/wellness.py::write_wellness_entry`
BEFORE any HTTP call (Pitfall #2 / D-07).

Drop-None semantics (`build_wellness_put_body`) is the only correct upsert
path - Intervals.icu treats `null` as "clear this field", so unsupplied
fields must be omitted from the PUT body, not sent as null (D-09).

No HTTP, no tool, no API client imports. Leaf module.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any

__all__ = [
    "WELLNESS_RANGES",
    "PARAM_TO_API_FIELD",
    "sleep_hours_to_secs",
    "build_wellness_put_body",
]


# Locked from .planning/phases/02-wellness-write-and-activity-enrichment/02-SPIKE-FINDINGS.md
# Section: "## Wellness subjective-field ranges (LOCKED)".
# Keys are PUBLIC param names on write_wellness_entry; values are (min_inclusive, max_inclusive).
# Adding a numeric param to write_wellness_entry without an entry here fails the alignment
# test in tests/test_wellness_write.py.
WELLNESS_RANGES: MappingProxyType[str, tuple[int, int]] = MappingProxyType({
    "fatigue": (1, 4),
    "stress": (1, 4),
    "motivation": (1, 4),
    "mood": (1, 4),
    "soreness": (1, 4),
    "sleep_quality": (1, 4),
})


# Public param name -> Intervals.icu wellness field name. Confirmed by Phase 1 readback shape
# (01-SPIKE-FINDINGS.md). `sleep_hours` is converted to `sleepSecs` before lookup -
# build_wellness_put_body handles that special case.
PARAM_TO_API_FIELD: dict[str, str] = {
    "sleep_hours": "sleepSecs",
    "sleep_quality": "sleepQuality",
    "soreness": "soreness",
    "fatigue": "fatigue",
    "motivation": "motivation",
    "stress": "stress",
    "mood": "mood",
    "hrv": "hrv",
    "resting_hr": "restingHR",
}


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


def build_wellness_put_body(params: dict[str, Any]) -> dict[str, Any]:
    """Build the wellness PUT body from a dict of public-param-name -> value.

    Drops entries whose value is None (upsert semantics: unsupplied fields
    do NOT clobber existing values - sending `null` would clear them per
    Intervals.icu API contract). Translates public param names to API
    field names via PARAM_TO_API_FIELD. Converts `sleep_hours` (float) to
    `sleepSecs` (int) along the way.

    Args:
        params: Mapping of public param name -> value (or None to omit).

    Returns:
        A dict suitable as the `data` argument to `make_intervals_request`.

    Raises:
        KeyError: If a non-None param name is not in PARAM_TO_API_FIELD.
    """
    body: dict[str, Any] = {}
    for key, value in params.items():
        if value is None:
            continue
        if key == "sleep_hours":
            body["sleepSecs"] = sleep_hours_to_secs(value)
            continue
        if key not in PARAM_TO_API_FIELD:
            raise KeyError(f"Unknown wellness param: {key!r}")
        api_name = PARAM_TO_API_FIELD[key]
        body[api_name] = value
    return body
