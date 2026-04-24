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
]


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
    options: tuple[str, ...] = ()
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
