"""
Registration assertion test for the Phase 5 milestone tool surface.

Imports `intervals_mcp_server.server` (which transitively imports every
tool module, triggering @mcp.tool() decorator registration), then queries
the FastMCP instance for its registered tool list and asserts the full
expected name set is present. Catches the silent-removal failure mode:
if a `from .tools.X import Y` line is deleted in server.py, the tool
quietly drops off `tools/list` — this test fails before that ships.

Independent of:
- scripts/smoke_phase5.py — which catches API contract drift live
- .planning/phases/05-server-wiring-and-acceptance/05-LIVE-SMOKE.md —
  which catches Claude Desktop tool-list rendering manually

The three checks together cover the three independent failure modes.
"""

# pylint: disable=wrong-import-position

import asyncio
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

# Importing server triggers tool registration via @mcp.tool() decorators
# in every imported tool module. The unused-import is intentional — we
# need the side-effect, not the symbol.
from intervals_mcp_server import server  # noqa: F401  pylint: disable=unused-import
from intervals_mcp_server.mcp_instance import mcp


# Single source of truth for "what tools this milestone ships".
# Mirrors src/intervals_mcp_server/server.py __all__ minus the two
# non-tool re-exports (`make_intervals_request`, `httpx_client`).
EXPECTED_TOOLS: frozenset[str] = frozenset(
    {
        # Activities (Phase 0 baseline)
        "get_activities",
        "get_activity_details",
        "get_activity_intervals",
        "get_activity_streams",
        "get_activity_messages",
        "add_activity_message",
        # Events (Phase 0 baseline)
        "get_events",
        "get_event_by_id",
        "add_or_update_event",
        "delete_event",
        "delete_events_by_date_range",
        # Wellness
        "get_wellness_data",
        "write_wellness_entry",  # Phase 2
        # Custom items (Phase 0 baseline)
        "get_custom_items",
        "get_custom_item_by_id",
        "create_custom_item",
        "update_custom_item",
        "delete_custom_item",
        # Climbing (Phase 1 + Phase 2 + Phase 3)
        "verify_custom_fields_setup",
        "enrich_activity_climbing",
        "create_climbing_activity",
        "complete_climbing_session",
        # Status (Phase 4)
        "get_training_status",
    }
)


def _registered_tool_names() -> frozenset[str]:
    """Return the set of tool names FastMCP currently has registered."""
    tools = asyncio.run(mcp.list_tools())
    return frozenset(t.name for t in tools)


def test_all_expected_tools_registered() -> None:
    """Every milestone tool is reachable via FastMCP's public tool list.

    Failure of this test means a `from .tools.X import Y` line was
    likely deleted from `src/intervals_mcp_server/server.py` (or the
    tool module's `@mcp.tool()` decorator was removed). Re-add the
    named import or restore the decorator.
    """
    registered = _registered_tool_names()
    missing = EXPECTED_TOOLS - registered
    assert not missing, (
        f"Tools missing from FastMCP registry: {sorted(missing)}. "
        f"Likely cause: a `from .tools.X import Y` line was deleted "
        f"in src/intervals_mcp_server/server.py, or the corresponding "
        f"@mcp.tool() decorator was removed. Re-add the named import."
    )


def test_no_unexpected_tools_registered() -> None:
    """No surprise tools — the expected set IS the milestone surface.

    Failure of this test means a new @mcp.tool() registered a name that
    is not in EXPECTED_TOOLS. If the new tool is intentional, add its
    name to EXPECTED_TOOLS in this file. Otherwise remove the decorator.
    """
    registered = _registered_tool_names()
    extra = registered - EXPECTED_TOOLS
    assert not extra, (
        f"Unexpected tool names registered: {sorted(extra)}. "
        f"Either add them to EXPECTED_TOOLS in "
        f"tests/test_server_registration.py, or remove the @mcp.tool() "
        f"decorator that registered them."
    )
