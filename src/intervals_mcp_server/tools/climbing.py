"""
Climbing-related MCP tools for Intervals.icu.

This module contains tools for the climbing training loop: custom-field
prerequisite verification, and (in later phases) wellness writes,
activity enrichment, activity creation, and session completion.
"""

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.climbing import CUSTOM_FIELD_KEYS
from intervals_mcp_server.utils.validation import resolve_athlete_id

# Import mcp instance from shared module for tool registration
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401

config = get_config()


_README_POINTER = (
    "See README section 'Climbing setup — required Intervals.icu custom fields' "
    "for setup instructions."
)


# Activity readback parameters for the custom-field definitions heuristic.
# We inspect recent activities for the top-level presence of CUSTOM_FIELD_KEYS
# entries. Intervals.icu only returns a custom-field key on an activity when
# the field is (a) defined in the athlete account AND (b) has been populated
# on that activity, so we probe a reasonably sized window of recent work.
_READBACK_ACTIVITY_LIMIT = 50


async def _verify_custom_fields_setup_impl(
    athlete_id_to_use: str,
    api_key: str | None,
) -> tuple[bool, list[str], str]:
    """List which required climbing custom fields are defined in the athlete account.

    Strategy (per 01-SPIKE-FINDINGS.md): there is no definitions endpoint that
    exposes user-defined custom fields by key. `/sport-settings` returns
    sport-level config only; `/custom-fields` and `/activity-fields` are 404.
    We therefore use the readback heuristic: GET a window of recent activities
    and check whether each `CUSTOM_FIELD_KEYS` entry appears as a top-level
    key on any activity. A key present on ANY recent activity is considered
    defined; a key absent from ALL recent activities is reported missing.

    Returns:
        (ok, missing_field_keys, human_message)
            - ok: True if every CUSTOM_FIELD_KEYS key is defined
            - missing_field_keys: list of keys missing (empty when ok=True)
            - human_message: human-readable status string for MCP clients
    """
    required = set(CUSTOM_FIELD_KEYS.keys())

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/activities",
        api_key=api_key,
        params={"limit": _READBACK_ACTIVITY_LIMIT},
    )

    if isinstance(result, dict) and "error" in result:
        msg = f"Error fetching recent activities for readback: {result.get('message')}"
        return False, list(CUSTOM_FIELD_KEYS.keys()), msg

    defined_keys: set[str] = set()
    if isinstance(result, list):
        for activity in result:
            if isinstance(activity, dict):
                for key in required:
                    if key in activity:
                        defined_keys.add(key)

    # Build the missing list in CUSTOM_FIELD_KEYS insertion order for stable output.
    missing = [k for k in CUSTOM_FIELD_KEYS if k not in defined_keys]
    ok = not missing

    if ok:
        human_message = (
            "All required climbing custom fields are present "
            f"({len(required)}/{len(required)} defined)."
        )
    else:
        lines: list[str] = [
            "Missing required Intervals.icu custom fields "
            f"({len(missing)} of {len(required)} required):",
        ]
        for key in missing:
            spec = CUSTOM_FIELD_KEYS[key]
            opts = (
                f" options: {', '.join(spec.options)}"
                if spec.field_type == "select"
                else ""
            )
            lines.append(f"- {key} ({spec.field_type}){opts}")
        lines.append("")
        lines.append(_README_POINTER)
        human_message = "\n".join(lines)

    return ok, missing, human_message


@mcp.tool()
async def verify_custom_fields_setup(
    athlete_id: str | None = None,
    api_key: str | None = None,
) -> str:
    """Verify that required Intervals.icu climbing custom fields are defined.

    Before the climbing tools can write discipline, grades, session focus,
    sends, and attempts, the following custom fields must exist in the
    athlete's Intervals.icu account settings:

      - discipline (select: bouldering, sport_lead, top_rope, trad)
      - indoor (bool)
      - session_focus (select: power, endurance, technique, projecting, mileage)
      - top_grade_sent (text)
      - top_grade_attempted (text)
      - sends (integer)
      - attempts (integer)

    See the README section "Climbing setup — required Intervals.icu custom
    fields" for the full table and step-by-step setup instructions.

    Args:
        athlete_id: The Intervals.icu athlete ID (optional, uses ATHLETE_ID
            from .env if not provided).
        api_key: The Intervals.icu API key (optional, uses API_KEY from .env
            if not provided).

    Returns:
        A human-readable string reporting which required fields are defined
        and which (if any) are missing by name. If any required field is
        missing, the write tools added in Phase 2+ will refuse to run
        against this athlete account.
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    _ok, _missing, human_message = await _verify_custom_fields_setup_impl(
        athlete_id_to_use, api_key
    )
    return human_message
