"""
Climbing-domain types and custom-field specification.

Single source of truth for:
- Discipline and session-focus enums used across the climbing tools.
- The Intervals.icu custom-field key spec (`CUSTOM_FIELD_KEYS`) the user
  must pre-define in their athlete account before the climbing tools can
  write them.

The README section "Climbing setup — required Intervals.icu custom fields"
mirrors `CUSTOM_FIELD_KEYS`. A test asserts they match; if you change the
spec here, update the README (and vice versa).

## Intervals.icu encoding constraints (confirmed by phase 5 acceptance)

- **Field keys are PascalCase** — Intervals.icu auto-derives the API key
  from the display label and stores in PascalCase. snake_case keys 422
  with "Unknown custom field [<key>]" even when the field exists.
- **Select fields encode as integers** — Intervals.icu's "Select" type
  always pairs each option with a numeric value (so it can compute
  averages). The API expects the integer, not the option label string.
- **No native bool type** — Indoor is encoded as a Select with 1=yes /
  2=no.

The public Python tool surface still accepts strings (`"bouldering"`,
`True`/`False`); encoders translate to Intervals.icu's integer wire
format at the PUT boundary.
"""

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Literal

__all__ = [
    "Discipline",
    "SessionFocus",
    "FieldSpec",
    "CUSTOM_FIELD_KEYS",
    "DISCIPLINE_TO_INT",
    "SESSION_FOCUS_TO_INT",
    "INDOOR_TO_INT",
    "encode_discipline",
    "encode_session_focus",
    "encode_indoor",
]


class Discipline(StrEnum):
    """Climbing discipline. Values are the human-friendly tool API.

    Wire-format integers are looked up via `DISCIPLINE_TO_INT`.
    """

    BOULDERING = "bouldering"
    SPORT_CLIMBING = "sport_climbing"
    MULTI_PITCH_SPORT = "multi_pitch_sport"
    MULTI_PITCH_TRAD = "multi_pitch_trad"


class SessionFocus(StrEnum):
    """Session focus. Wire-format ints via `SESSION_FOCUS_TO_INT`."""

    POWER = "power"
    ENDURANCE = "endurance"
    TECHNIQUE = "technique"
    PROJECTING = "projecting"
    MILEAGE = "mileage"


# Wire-format integer encoders for Intervals.icu Select fields.
# These values must match what the user configured in their athlete
# settings (each Select option in Intervals.icu has an int value).
DISCIPLINE_TO_INT: MappingProxyType[Discipline, int] = MappingProxyType({
    Discipline.BOULDERING: 1,
    Discipline.SPORT_CLIMBING: 2,
    Discipline.MULTI_PITCH_SPORT: 3,
    Discipline.MULTI_PITCH_TRAD: 4,
})

SESSION_FOCUS_TO_INT: MappingProxyType[SessionFocus, int] = MappingProxyType({
    SessionFocus.POWER: 1,
    SessionFocus.ENDURANCE: 2,
    SessionFocus.TECHNIQUE: 3,
    SessionFocus.PROJECTING: 4,
    SessionFocus.MILEAGE: 5,
})

INDOOR_TO_INT: MappingProxyType[bool, int] = MappingProxyType({
    True: 1,
    False: 2,
})


def encode_discipline(value: str | Discipline) -> int:
    """Convert a discipline string/enum to its Intervals.icu Select int."""
    enum = value if isinstance(value, Discipline) else Discipline(value)
    return DISCIPLINE_TO_INT[enum]


def encode_session_focus(value: str | SessionFocus) -> int:
    """Convert a session-focus string/enum to its Intervals.icu Select int."""
    enum = value if isinstance(value, SessionFocus) else SessionFocus(value)
    return SESSION_FOCUS_TO_INT[enum]


def encode_indoor(value: bool) -> int:
    """Convert indoor bool to Intervals.icu Select int (1=yes, 2=no)."""
    return INDOOR_TO_INT[bool(value)]


FieldType = Literal["select", "select_int", "text", "integer"]


@dataclass(frozen=True)
class FieldSpec:
    """Specification of one required Intervals.icu custom activity field."""

    key: str
    field_type: FieldType
    options: tuple[str, ...] = ()
    description: str = ""


CUSTOM_FIELD_KEYS: MappingProxyType[str, FieldSpec] = MappingProxyType({
    "Discipline": FieldSpec(
        key="Discipline",
        field_type="select_int",
        options=tuple(d.value for d in Discipline),
        description="Climbing discipline (Select with int values: 1=bouldering, 2=sport_climbing, 3=multi_pitch_sport, 4=multi_pitch_trad).",
    ),
    "Indoor": FieldSpec(
        key="Indoor",
        field_type="select_int",
        options=("yes", "no"),
        description="Indoor vs outdoor session (Select with int values: 1=yes, 2=no).",
    ),
    "SessionFocus": FieldSpec(
        key="SessionFocus",
        field_type="select_int",
        options=tuple(f.value for f in SessionFocus),
        description="Primary training intent (Select with int values: 1=power, 2=endurance, 3=technique, 4=projecting, 5=mileage).",
    ),
    "TopGradeSent": FieldSpec(
        key="TopGradeSent",
        field_type="text",
        description="Hardest grade sent this session (Font for boulders, French sport for routes), e.g. '7a+' or '6A'.",
    ),
    "TopGradeAttempted": FieldSpec(
        key="TopGradeAttempted",
        field_type="text",
        description="Hardest grade attempted this session.",
    ),
    "Sends": FieldSpec(
        key="Sends",
        field_type="integer",
        description="Total successful sends (clean completions) this session.",
    ),
    "Attempts": FieldSpec(
        key="Attempts",
        field_type="integer",
        description="Total attempts (including sends) this session.",
    ),
})
