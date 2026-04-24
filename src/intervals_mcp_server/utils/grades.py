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

# Font bouldering: 3A .. 9C+ (bare uppercase letter A/B/C, optional '+').
# Low end [1-2] included defensively (grade-scale completeness); real use
# starts much higher. Adjust top end if user's range grows past 9C+.
FONT_RE = re.compile(r"^[3-9][A-C]\+?$|^[12]$")

# French sport: 3a .. 9c+ (lowercase letter a/b/c, optional '+').
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
        # Defensive — mypy does not prove exhaustiveness for StrEnum.
        raise ValueError(f"Unknown discipline: {discipline!r}")
    return grade
