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

from statistics import fmean
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


# TSB bands locked from CONTEXT D-03. Tuple = (lower_exclusive, upper_inclusive, label).
# Order matters: tsb_band() walks them in order and returns the first match where
# lower < tsb <= upper (with float('-inf') / float('inf') as open ends).
TSB_BANDS: tuple[tuple[float, float, str], ...] = (
    (25.0, float("inf"), "Burnt out / Detraining"),
    (5.0, 25.0, "Fresh"),
    (-10.0, 5.0, "Balanced"),
    (-25.0, -10.0, "Fatigued (productive load)"),
    (float("-inf"), -25.0, "Risk"),
)

# Window sizes (CONTEXT D-06). Hardcoded for v1; window-override params are deferred to v2.
WINDOW_DAYS_WEEKLY: int = 7        # Weekly load review AND wellness blend
WINDOW_DAYS_LONG_TERM: int = 42    # Long-term trend (one typical 6-week training block)
WINDOW_DAYS_RPE: int = 14          # RPE coverage data-quality check

# RPE coverage flag (CONTEXT D-08, D-11).
RPE_MISSING_THRESHOLD: float = 0.30  # >30% of climbing activities missing icu_rpe -> warn
MIN_RPE_SAMPLE: int = 3              # below this many climbing activities, suppress warning


def tsb_band(tsb: float) -> str:
    """Return the verbal TSB band label for a numeric TSB value.

    Bands locked from CONTEXT D-03 (standard TrainingPeaks/Friel literature
    values). Boundary semantics:
      - TSB > 25                -> "Burnt out / Detraining"
      - 5 < TSB <= 25           -> "Fresh"
      - -10 <= TSB <= 5         -> "Balanced"
      - -25 <= TSB < -10        -> "Fatigued (productive load)"
      - TSB < -25               -> "Risk"

    Args:
        tsb: Training-stress balance (CTL - ATL).

    Returns:
        One of the five band labels above, exactly as written.
    """
    if tsb > 25.0:
        return "Burnt out / Detraining"
    if tsb > 5.0:        # i.e. 5 < tsb <= 25
        return "Fresh"
    if tsb >= -10.0:     # i.e. -10 <= tsb <= 5
        return "Balanced"
    if tsb >= -25.0:     # i.e. -25 <= tsb < -10
        return "Fatigued (productive load)"
    return "Risk"


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
    missing = sum(1 for a in activities if a.get("icu_rpe") is None)
    return missing, total


def format_today_section(
    today_entry: dict[str, Any] | None,
    wellness_recent: list[dict[str, Any]],
    walk_back_days: int,
) -> str:
    """Render the Today section of the training status report.

    Per CONTEXT D-13: each section renders a graceful one-line note when data is
    absent — never raises, never returns empty string.

    Args:
        today_entry: The wellness daily entry resolved for "today" via walk-back
            (None if no entry found within 7-day window per D-07).
        wellness_recent: The 7-day window of wellness entries for the blend bullets.
        walk_back_days: 0 if today_entry is the actual as_of_date entry; N if
            the tool walked back N days to find one (per D-07, max 7).

    Returns:
        A string starting with '## Today' and ending with '\\n'.
        Always returns SOME content — never empty per D-13.
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

    # Wellness blend bullets (7-day mean per field). Defensive against missing/non-numeric
    # values per T-04-01 — isinstance check before arithmetic.
    field_specs = [
        ("sleepSecs", "Sleep (7d avg)", lambda v: f"{v / 3600:.1f} h"),
        ("soreness", "Soreness (7d avg)", lambda v: f"{v:.1f}/4"),
        ("fatigue", "Fatigue (7d avg)", lambda v: f"{v:.1f}/4"),
        ("hrv", "HRV (7d avg)", lambda v: f"{v:.0f} ms"),
        ("restingHR", "Resting HR (7d avg)", lambda v: f"{v:.0f} bpm"),
    ]
    for field_key, label, fmt in field_specs:
        values: list[float] = [
            float(e[field_key])
            for e in wellness_recent
            if isinstance(e.get(field_key), (int, float))
        ]
        if values:
            mean_val = fmean(values)
            lines.append(f"- {label}: {fmt(mean_val)}")

    return "\n".join(lines) + "\n"


def format_weekly_section(
    weekly_entries: list[dict[str, Any]],
) -> str:
    """Render the This Week section of the training status report.

    Per CONTEXT D-13: returns a graceful one-liner when data is absent.

    Args:
        weekly_entries: The 7-day window of wellness/fitness daily entries.
            Each entry should have 'ctl', 'atl', and 'date' keys.
            Order is not assumed — this function sorts by date.

    Returns:
        A string starting with '## This Week' and ending with '\\n'.
        Always returns SOME content — never empty per D-13.
    """
    # Filter to entries with numeric ctl and atl. Defensive isinstance check per T-04-01.
    filtered = [
        e for e in weekly_entries
        if isinstance(e.get("ctl"), (int, float)) and isinstance(e.get("atl"), (int, float))
    ]

    if len(filtered) < 2:
        return "## This Week\n- No CTL/ATL trend data in last 7 days.\n"

    # Sort by date string ascending (YYYY-MM-DD sorts correctly lexicographically).
    filtered.sort(key=lambda e: e.get("date", ""))
    start = filtered[0]
    end = filtered[-1]

    ctl_delta = end["ctl"] - start["ctl"]
    atl_delta = end["atl"] - start["atl"]
    tsb_end = end["ctl"] - end["atl"]

    bullets = [
        f"- CTL: {start['ctl']:.1f} → {end['ctl']:.1f} ({ctl_delta:+.1f})",
        f"- ATL: {start['atl']:.1f} → {end['atl']:.1f} ({atl_delta:+.1f})",
        f"- TSB (end of week): {tsb_end:+.1f}",
    ]
    return "## This Week\n" + "\n".join(bullets) + "\n"


def format_longterm_section(
    longterm_entries: list[dict[str, Any]],
) -> str:
    """Render the Long-Term Trend section of the training status report.

    Per CONTEXT D-13: returns a graceful one-liner when data is absent.

    Args:
        longterm_entries: The 42-day window of wellness/fitness daily entries.
            Each entry should have 'ctl', 'atl', and 'date' keys.
            Order is not assumed — this function sorts by date.

    Returns:
        A string starting with '## Long-Term Trend' and ending with '\\n'.
        Always returns SOME content — never empty per D-13.
    """
    # Filter to entries with numeric ctl and atl. Defensive isinstance check per T-04-01.
    filtered = [
        e for e in longterm_entries
        if isinstance(e.get("ctl"), (int, float)) and isinstance(e.get("atl"), (int, float))
    ]

    if len(filtered) < 2:
        return "## Long-Term Trend\n- No CTL/ATL trend data in last 42 days.\n"

    # Sort by date string ascending (YYYY-MM-DD sorts correctly lexicographically).
    filtered.sort(key=lambda e: e.get("date", ""))
    start = filtered[0]
    end = filtered[-1]

    mean_ctl = fmean(float(e["ctl"]) for e in filtered)
    mean_atl = fmean(float(e["atl"]) for e in filtered)

    bullets = [
        f"- CTL: {start['ctl']:.1f} → {end['ctl']:.1f} ({end['ctl'] - start['ctl']:+.1f}) over 42 days",
        f"- ATL: {start['atl']:.1f} → {end['atl']:.1f} ({end['atl'] - start['atl']:+.1f}) over 42 days",
        f"- 42d mean CTL: {mean_ctl:.1f}, mean ATL: {mean_atl:.1f}",
    ]
    return "## Long-Term Trend\n" + "\n".join(bullets) + "\n"


def format_status_report(
    today_section: str,
    weekly_section: str,
    longterm_section: str,
    rpe_warning: str | None,
) -> str:
    """Assemble the full training-status report from pre-rendered sections.

    This is a thin orchestrator. Each section arg is already rendered (ending
    in '\\n'). The extra '\\n' between sections creates a blank-line separator.

    Args:
        today_section: Rendered '## Today' section string.
        weekly_section: Rendered '## This Week' section string.
        longterm_section: Rendered '## Long-Term Trend' section string.
        rpe_warning: Optional data-quality note (None if no warning needed).
            Appended at the bottom of the report when present.

    Returns:
        The complete plain-text report string.
    """
    report = today_section + "\n" + weekly_section + "\n" + longterm_section
    if rpe_warning is not None:
        report += "\n" + rpe_warning + ("" if rpe_warning.endswith("\n") else "\n")
    return report
