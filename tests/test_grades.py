"""Unit tests for utils/grades.py — regex matrix + cross-scale rejection."""

import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

import pytest  # pylint: disable=wrong-import-position

from intervals_mcp_server.utils.climbing import Discipline  # pylint: disable=wrong-import-position
from intervals_mcp_server.utils.grades import (  # pylint: disable=wrong-import-position
    FONT_RE,
    FRENCH_SPORT_RE,
    validate_grade,
)


@pytest.mark.parametrize("grade", ["3A", "6A", "6A+", "7B", "7C+", "8A", "9C+"])
def test_font_re_accepts_canonical_grades(grade: str) -> None:
    assert FONT_RE.match(grade) is not None


@pytest.mark.parametrize("grade", ["6a", "6A/6B", "V5", "hard 6A", "6D", "6", "6A +"])
def test_font_re_rejects_non_canonical(grade: str) -> None:
    assert FONT_RE.match(grade) is None


@pytest.mark.parametrize("grade", ["3a", "6a", "6a+", "7b", "7c+", "8a", "9c+"])
def test_french_sport_re_accepts_canonical_grades(grade: str) -> None:
    assert FRENCH_SPORT_RE.match(grade) is not None


@pytest.mark.parametrize("grade", ["6A", "5.11a", "6a/6b", "6d", "6a +"])
def test_french_sport_re_rejects_non_canonical(grade: str) -> None:
    assert FRENCH_SPORT_RE.match(grade) is None


def test_validate_grade_font_on_boulder_ok() -> None:
    assert validate_grade("6A+", Discipline.BOULDERING) == "6A+"


def test_validate_grade_french_on_route_ok() -> None:
    assert validate_grade("6a+", Discipline.SPORT_LEAD) == "6a+"
    assert validate_grade("7b", Discipline.TOP_ROPE) == "7b"
    assert validate_grade("6c", Discipline.TRAD) == "6c"


def test_validate_grade_font_on_route_rejected() -> None:
    with pytest.raises(ValueError, match="French sport"):
        validate_grade("6A", Discipline.SPORT_LEAD)


def test_validate_grade_french_on_boulder_rejected() -> None:
    with pytest.raises(ValueError, match="Font"):
        validate_grade("6a", Discipline.BOULDERING)


def test_validate_grade_gibberish_rejected() -> None:
    with pytest.raises(ValueError):
        validate_grade("hard 6A", Discipline.BOULDERING)
