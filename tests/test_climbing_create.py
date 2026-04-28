"""Unit tests for tools/climbing.py::create_climbing_activity — CLIMB-02, CLIMB-09."""

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

from intervals_mcp_server.utils.climbing import (  # pylint: disable=wrong-import-position
    CUSTOM_FIELD_KEYS,
)


# ---------------------------------------------------------------------------
# Fake-response helpers (mirror tests/test_climbing_write.py).
# ---------------------------------------------------------------------------


def _make_fake_all_present() -> list[dict[str, object]]:
    """Verify-fields fake: all required CUSTOM_FIELD_KEYS keys appear top-level
    on at least one activity (so the verify-fields impl reports OK).
    """
    activity: dict[str, object] = {
        "id": "i142495224",
        "name": "Some prior session",
        "type": "WeightTraining",
    }
    for key in CUSTOM_FIELD_KEYS:
        activity[key] = None
    return [activity]


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


# ---------------------------------------------------------------------------
# Tool registration sanity.
# ---------------------------------------------------------------------------


def test_create_tool_registered() -> None:
    """create_climbing_activity is async with the 13-param signature; date + duration_minutes are required."""
    from intervals_mcp_server.tools.climbing import create_climbing_activity

    assert inspect.iscoroutinefunction(create_climbing_activity)
    sig = inspect.signature(create_climbing_activity)
    assert len(sig.parameters) == 13, list(sig.parameters)
    assert sig.parameters["date"].default is inspect.Parameter.empty
    assert sig.parameters["duration_minutes"].default is inspect.Parameter.empty


# ---------------------------------------------------------------------------
# CLIMB-02 happy path: no duplicates → POST runs → success.
# ---------------------------------------------------------------------------


def test_create_no_duplicate_proceeds_to_post(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLIMB-02: empty activities-list on the date → POST → success.
    No climbing fields supplied → no enrichment call."""
    from intervals_mcp_server.tools.climbing import create_climbing_activity

    counters = {"dup_get": 0, "post": 0, "put": 0, "enrich_get": 0}
    captured_post: dict[str, Any] = {}

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and url.endswith("/activities"):
            counters["dup_get"] += 1
            return []  # no duplicates
        if method == "POST" and url.endswith("/activities/manual"):
            counters["post"] += 1
            captured_post.update(data or {})
            return {
                "id": "i142495224",
                "start_date_local": "2026-04-27T00:00:00",
                "type": "WeightTraining",
                "name": (data or {}).get("name", ""),
            }
        if method == "PUT":
            counters["put"] += 1
            return {"id": "i142495224"}
        if method == "GET":
            # Any other GET — would be the post-enrich readback, must not run.
            counters["enrich_get"] += 1
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        create_climbing_activity(
            date="2026-04-27",
            duration_minutes=90,
            athlete_id="i1",
        )
    )
    assert result == "Successfully created activity i142495224 on 2026-04-27.", result
    assert counters["dup_get"] == 1
    assert counters["post"] == 1
    assert counters["put"] == 0
    assert counters["enrich_get"] == 0


# ---------------------------------------------------------------------------
# CLIMB-09: duplicate-guard fires → no POST.
# ---------------------------------------------------------------------------


def test_create_duplicate_guard_fires(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLIMB-09 / Pitfall #1: existing WeightTraining activity on the date →
    refuse with id/name/date + enrich hint, NO POST."""
    from intervals_mcp_server.tools.climbing import create_climbing_activity

    counters = {"dup_get": 0, "post": 0}

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and url.endswith("/activities"):
            counters["dup_get"] += 1
            return [
                {
                    "id": "i999",
                    "name": "Sport gym session",
                    "type": "WeightTraining",
                    "start_date_local": "2026-04-27T00:00:00",
                },
            ]
        if method == "POST":
            counters["post"] += 1
            raise AssertionError("POST must not happen on duplicate-guard refusal")
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        create_climbing_activity(
            date="2026-04-27",
            duration_minutes=90,
            athlete_id="i1",
        )
    )
    assert result.startswith("Error: a WeightTraining activity already exists on 2026-04-27"), result
    assert "i999" in result
    assert "Sport gym session" in result
    assert "2026-04-27T00:00:00" in result
    assert "Call enrich_activity_climbing" in result
    assert counters["dup_get"] == 1
    assert counters["post"] == 0


def test_create_duplicate_guard_ignores_non_weight_training(monkeypatch: pytest.MonkeyPatch) -> None:
    """The duplicate-guard filter is (date, type='WeightTraining'); a Ride on the same date does not block."""
    from intervals_mcp_server.tools.climbing import create_climbing_activity

    counters = {"post": 0}

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and url.endswith("/activities"):
            return [
                {
                    "id": "i777",
                    "name": "Recovery ride",
                    "type": "Ride",  # different type → must NOT block
                    "start_date_local": "2026-04-27T00:00:00",
                },
            ]
        if method == "POST":
            counters["post"] += 1
            return {"id": "i100", "start_date_local": "2026-04-27T00:00:00", "type": "WeightTraining"}
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        create_climbing_activity(date="2026-04-27", duration_minutes=60, athlete_id="i1")
    )
    assert result.startswith("Successfully created activity i100"), result
    assert counters["post"] == 1


# ---------------------------------------------------------------------------
# Pitfall #4: start_date_local format is exactly {date}T00:00:00, never derived from clock.
# ---------------------------------------------------------------------------


def test_create_pitfall4_timezone_format(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pitfall #4 / D-17: POST body uses '2026-04-27T00:00:00' from user input.
    String-equality assertion (not 'contains')."""
    from intervals_mcp_server.tools.climbing import create_climbing_activity

    captured: list[dict[str, Any]] = []

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and url.endswith("/activities"):
            return []
        if method == "POST":
            captured.append(dict(data or {}))
            return {"id": "iX", "start_date_local": "2026-04-27T00:00:00", "type": "WeightTraining"}
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    asyncio.run(
        create_climbing_activity(date="2026-04-27", duration_minutes=90, athlete_id="i1")
    )
    assert len(captured) == 1
    body = captured[0]
    assert body["start_date_local"] == "2026-04-27T00:00:00", body
    assert body["type"] == "WeightTraining", body
    assert body["moving_time"] == 5400, body  # 90 min * 60 sec


def test_create_pitfall4_never_uses_utcnow(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pitfall #4: even if system clock is patched to a different date, the
    POST body uses the user-supplied date verbatim."""
    import datetime as dt_module

    from intervals_mcp_server.tools.climbing import create_climbing_activity

    class FakeDatetime(dt_module.datetime):
        @classmethod
        def utcnow(cls) -> "FakeDatetime":
            return cls(2099, 1, 1, 0, 30)  # next-day UTC noise

        @classmethod
        def now(cls, tz: Any = None) -> "FakeDatetime":  # type: ignore[override]
            return cls(2099, 1, 1, 0, 30)

    monkeypatch.setattr(dt_module, "datetime", FakeDatetime)

    captured: list[dict[str, Any]] = []

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and url.endswith("/activities"):
            return []
        if method == "POST":
            captured.append(dict(data or {}))
            return {"id": "iX", "start_date_local": "2026-04-27T00:00:00", "type": "WeightTraining"}
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    asyncio.run(
        create_climbing_activity(date="2026-04-27", duration_minutes=90, athlete_id="i1")
    )
    assert len(captured) == 1
    # The user input wins, regardless of system-clock noise.
    assert captured[0]["start_date_local"] == "2026-04-27T00:00:00", captured[0]


# ---------------------------------------------------------------------------
# D-16: name template defaults.
# ---------------------------------------------------------------------------


def test_create_name_template_with_discipline(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-16: no name + discipline=bouldering → 'Climbing — Bouldering — 2026-04-27'."""
    from intervals_mcp_server.tools.climbing import create_climbing_activity

    captured: list[dict[str, Any]] = []

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and url.endswith("/activities"):
            # Could be duplicate-guard OR verify-fields GET — both go here.
            # Return _make_fake_all_present so verify-fields passes; duplicate-guard
            # filters by type='WeightTraining' AND start_date_local prefix, so
            # this won't accidentally fire the duplicate refusal for our target date.
            if params and params.get("oldest") == "2026-04-27":
                return []  # no duplicates on the target date
            return _make_fake_all_present()
        if method == "GET" and url.startswith("/activity/"):
            return _make_fake_clean_activity("iX")
        if method == "POST" and url.endswith("/activities/manual"):
            captured.append(dict(data or {}))
            return {"id": "iX", "name": (data or {}).get("name", ""), "start_date_local": "2026-04-27T00:00:00", "type": "WeightTraining"}
        if method == "PUT":
            return {"id": "iX"}
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    # No name supplied; discipline=bouldering → human title with discipline.
    # We need readback to roundtrip discipline so _enrich_impl reports success.
    # Patch _make_fake_clean_activity in place by returning a discipline-set version
    # via a small wrapper:
    asyncio.run(
        create_climbing_activity(
            date="2026-04-27",
            duration_minutes=90,
            discipline="bouldering",
            athlete_id="i1",
        )
    )
    assert len(captured) >= 1
    assert captured[0]["name"] == "Climbing — Bouldering — 2026-04-27", captured[0]


def test_create_name_template_without_discipline(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-16: no name, no discipline → 'Climbing — 2026-04-27'."""
    from intervals_mcp_server.tools.climbing import create_climbing_activity

    captured: list[dict[str, Any]] = []

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and url.endswith("/activities"):
            return []
        if method == "POST" and url.endswith("/activities/manual"):
            captured.append(dict(data or {}))
            return {"id": "iX", "start_date_local": "2026-04-27T00:00:00", "type": "WeightTraining"}
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    asyncio.run(
        create_climbing_activity(date="2026-04-27", duration_minutes=90, athlete_id="i1")
    )
    assert captured[0]["name"] == "Climbing — 2026-04-27", captured[0]


def test_create_user_name_used_verbatim(monkeypatch: pytest.MonkeyPatch) -> None:
    """User-supplied `name` is used verbatim; template not invoked."""
    from intervals_mcp_server.tools.climbing import create_climbing_activity

    captured: list[dict[str, Any]] = []

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and url.endswith("/activities"):
            return []
        if method == "POST" and url.endswith("/activities/manual"):
            captured.append(dict(data or {}))
            return {"id": "iX", "name": (data or {}).get("name", ""), "start_date_local": "2026-04-27T00:00:00", "type": "WeightTraining"}
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    asyncio.run(
        create_climbing_activity(
            date="2026-04-27",
            duration_minutes=90,
            name="My session",
            discipline="bouldering",  # template would use this if name=None
            athlete_id="i1",
        )
    )
    assert captured[0]["name"] == "My session", captured[0]


# ---------------------------------------------------------------------------
# D-10: POST error → return error verbatim, no enrich call.
# ---------------------------------------------------------------------------


def test_create_post_error_returns_error_no_activity_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-10: POST returns error dict → tool returns 'Error creating activity: <msg>'."""
    from intervals_mcp_server.tools.climbing import create_climbing_activity

    counters = {"put": 0}

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and url.endswith("/activities"):
            return []
        if method == "POST":
            return {"error": True, "status_code": 500, "message": "boom"}
        if method == "PUT":
            counters["put"] += 1
            raise AssertionError("PUT must not happen after POST error")
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        create_climbing_activity(date="2026-04-27", duration_minutes=90, athlete_id="i1")
    )
    assert result == "Error creating activity: boom", result
    assert counters["put"] == 0


# ---------------------------------------------------------------------------
# D-09: enrichment fails after POST → activity preserved, error names id + retry hint.
# ---------------------------------------------------------------------------


def test_create_enrichment_fails_after_post_keeps_activity(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-09: POST succeeds, _enrich_impl returns an error → tool returns
    'Created activity {id} but enrichment failed:\\n<err>\\n\\nCall enrich_activity_climbing(activity_id={id}, override=True, ...)'.
    Activity is NOT deleted."""
    from intervals_mcp_server.tools.climbing import create_climbing_activity

    counters = {"delete": 0}

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and url.endswith("/activities"):
            # Verify-fields GET returns []  → all CUSTOM_FIELD_KEYS missing → enrich short-circuits.
            if params and params.get("oldest") == "2026-04-27":
                return []  # no duplicates for the target date
            return []  # verify-fields returns empty → custom fields "missing"
        if method == "POST" and url.endswith("/activities/manual"):
            return {"id": "iCREATED", "start_date_local": "2026-04-27T00:00:00", "type": "WeightTraining"}
        if method == "DELETE":
            counters["delete"] += 1
            raise AssertionError("DELETE must not happen on enrichment failure (D-09)")
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        create_climbing_activity(
            date="2026-04-27",
            duration_minutes=90,
            discipline="bouldering",  # custom field → triggers verify-fields guard
            athlete_id="i1",
        )
    )
    assert "iCREATED" in result, result
    assert "but enrichment failed" in result, result
    assert "Call enrich_activity_climbing(activity_id=iCREATED, override=True" in result, result
    assert counters["delete"] == 0


# ---------------------------------------------------------------------------
# D-08 / D-12: no climbing fields → no enrich; with fields → enrich with skip flag.
# ---------------------------------------------------------------------------


def test_create_no_climbing_fields_skips_enrich_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """No climbing fields → success right after POST, no PUT, no readback GET."""
    from intervals_mcp_server.tools.climbing import create_climbing_activity

    counters = {"put": 0, "post_post_get": 0, "post": 0}

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and url.endswith("/activities"):
            return []
        if method == "POST" and url.endswith("/activities/manual"):
            counters["post"] += 1
            return {"id": "iX", "start_date_local": "2026-04-27T00:00:00", "type": "WeightTraining"}
        if method == "GET" and url.startswith("/activity/"):
            counters["post_post_get"] += 1
            return _make_fake_clean_activity("iX")
        if method == "PUT":
            counters["put"] += 1
            return {"id": "iX"}
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        create_climbing_activity(date="2026-04-27", duration_minutes=90, athlete_id="i1")
    )
    assert result == "Successfully created activity iX on 2026-04-27.", result
    assert counters["post"] == 1
    assert counters["put"] == 0, "no PUT — no climbing fields supplied"
    assert counters["post_post_get"] == 0, "no readback GET — _enrich_impl was not called"


def test_create_with_climbing_fields_calls_enrich_with_skip_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-12: when _enrich_impl runs after POST, the conflict-scan GET on the new
    activity_id MUST NOT fire (counter == 0). Only the verify-fields GET (against
    /activities) and the readback GET (after PUT) should hit /activity/{id} routes.
    """
    from intervals_mcp_server.tools.climbing import create_climbing_activity

    pre_put_get_on_new_id = {"count": 0}
    put_done = {"flag": False}

    post_activity = _make_fake_clean_activity("iNEW")
    post_activity["discipline"] = "bouldering"

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and url.endswith("/activities"):
            if params and params.get("oldest") == "2026-04-27":
                return []  # duplicate-guard miss
            return _make_fake_all_present()  # verify-fields OK
        if method == "POST" and url.endswith("/activities/manual"):
            return {"id": "iNEW", "start_date_local": "2026-04-27T00:00:00", "type": "WeightTraining"}
        if method == "GET" and url == "/activity/iNEW":
            if not put_done["flag"]:
                # This is a pre-PUT GET on the freshly-POSTed activity. With
                # _skip_conflict_scan=True it MUST NOT happen.
                pre_put_get_on_new_id["count"] += 1
                return _make_fake_clean_activity("iNEW")
            return post_activity
        if method == "PUT":
            put_done["flag"] = True
            return {"id": "iNEW"}
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        create_climbing_activity(
            date="2026-04-27",
            duration_minutes=90,
            discipline="bouldering",
            athlete_id="i1",
        )
    )
    assert result.startswith("Successfully enriched activity iNEW"), result
    assert pre_put_get_on_new_id["count"] == 0, (
        "D-12 — _skip_conflict_scan=True must skip the pre-PUT GET on a fresh activity"
    )


# ===========================================================================
# complete_climbing_session — CLIMB-01, CLIMB-09, paired_event_id readback.
# ===========================================================================


def _make_fake_event(
    event_id: str = "ev123",
    *,
    paired_event_id: object = None,
    start_date_local: str = "2026-04-27T00:00:00",
    event_type: str = "WeightTraining",
    name: str = "Sport bouldering",
    moving_time: object = 5400,
) -> dict[str, object]:
    """Fake planned-event GET response."""
    return {
        "id": event_id,
        "start_date_local": start_date_local,
        "type": event_type,
        "name": name,
        "paired_event_id": paired_event_id,
        "moving_time": moving_time,
        "category": "WORKOUT",
    }


def test_complete_tool_registered() -> None:
    """complete_climbing_session is async; signature has 11 params; event_id is required."""
    from intervals_mcp_server.tools.climbing import complete_climbing_session

    assert inspect.iscoroutinefunction(complete_climbing_session)
    sig = inspect.signature(complete_climbing_session)
    assert len(sig.parameters) == 11, list(sig.parameters)
    assert sig.parameters["event_id"].default is inspect.Parameter.empty
    # No `date`, `type`, `duration_minutes`, `name` — those come from the event.
    for forbidden in ("date", "type", "duration_minutes", "name"):
        assert forbidden not in sig.parameters, (
            f"complete_climbing_session must NOT accept {forbidden!r} — "
            "the event is the source of truth (D-07)."
        )


def test_complete_event_provides_date_type_name_and_paired_event_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLIMB-01: event GET → POST with explicit paired_event_id → readback OK → success.
    Asserts POST body fields all come verbatim from the event."""
    from intervals_mcp_server.tools.climbing import complete_climbing_session

    captured_post: list[dict[str, Any]] = []
    counters = {"event_get": 0, "dup_get": 0, "post": 0, "readback_get": 0}

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and "/event/" in url and "/events" not in url:
            counters["event_get"] += 1
            return _make_fake_event("ev123")
        if method == "GET" and url.endswith("/activities"):
            counters["dup_get"] += 1
            return []
        if method == "POST" and url.endswith("/activities/manual"):
            counters["post"] += 1
            captured_post.append(dict(data or {}))
            return {
                "id": "iX",
                "start_date_local": "2026-04-27T00:00:00",
                "type": "WeightTraining",
                "name": "Sport bouldering",
                "paired_event_id": "ev123",  # Intervals.icu accepted the explicit set
            }
        if method == "GET" and url == "/activity/iX":
            counters["readback_get"] += 1
            activity = _make_fake_clean_activity("iX")
            activity["paired_event_id"] = "ev123"
            return activity
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        complete_climbing_session(event_id="ev123", athlete_id="i1")
    )
    assert result == (
        "Successfully completed session: created activity iX paired to event ev123."
    ), result
    # Order of HTTP calls.
    assert counters["event_get"] == 1
    assert counters["dup_get"] == 1
    assert counters["post"] == 1
    assert counters["readback_get"] == 1
    # POST body must use event values verbatim and set paired_event_id explicitly.
    assert len(captured_post) == 1
    body = captured_post[0]
    assert body["paired_event_id"] == "ev123", body
    assert body["start_date_local"] == "2026-04-27T00:00:00", body
    assert body["type"] == "WeightTraining", body
    assert body["name"] == "Sport bouldering", body
    assert body["moving_time"] == 5400, body  # event-supplied


def test_complete_already_paired_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    """specifics: event GET returns paired_event_id non-null → tool refuses.
    No duplicate-guard GET, no POST."""
    from intervals_mcp_server.tools.climbing import complete_climbing_session

    counters = {"event_get": 0, "dup_get": 0, "post": 0}

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and "/event/" in url and "/events" not in url:
            counters["event_get"] += 1
            return _make_fake_event("ev123", paired_event_id="i999")
        if method == "GET" and url.endswith("/activities"):
            counters["dup_get"] += 1
            raise AssertionError("duplicate-guard GET must not run on already-paired refusal")
        if method == "POST":
            counters["post"] += 1
            raise AssertionError("POST must not run on already-paired refusal")
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        complete_climbing_session(event_id="ev123", athlete_id="i1")
    )
    assert result == (
        "Event ev123 is already paired to activity i999. "
        "Call enrich_activity_climbing(activity_id=i999, ...) "
        "to add climbing metadata."
    ), result
    assert counters["event_get"] == 1
    assert counters["dup_get"] == 0
    assert counters["post"] == 0


def test_complete_duplicate_guard_on_event_date(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLIMB-09 / D-03: even with a planned event, if a WeightTraining activity
    already exists on the event's date, refuse without POSTing."""
    from intervals_mcp_server.tools.climbing import complete_climbing_session

    counters = {"post": 0}

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and "/event/" in url and "/events" not in url:
            return _make_fake_event("ev123")  # event is valid, not paired
        if method == "GET" and url.endswith("/activities"):
            return [
                {
                    "id": "i777",
                    "name": "Garmin-synced session",
                    "type": "WeightTraining",
                    "start_date_local": "2026-04-27T00:00:00",
                },
            ]
        if method == "POST":
            counters["post"] += 1
            raise AssertionError("POST must not happen on duplicate-guard refusal")
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        complete_climbing_session(event_id="ev123", athlete_id="i1")
    )
    assert result.startswith("Error: a WeightTraining activity already exists on 2026-04-27"), result
    assert "i777" in result
    assert "Garmin-synced session" in result
    assert "Call enrich_activity_climbing" in result
    assert counters["post"] == 0


def test_complete_paired_event_id_readback_mismatch_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """specifics: POST OK but readback shows different paired_event_id (or null)
    → return the mismatch error. No DELETE on the activity."""
    from intervals_mcp_server.tools.climbing import complete_climbing_session

    counters = {"delete": 0}

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and "/event/" in url and "/events" not in url:
            return _make_fake_event("ev123")
        if method == "GET" and url.endswith("/activities"):
            return []
        if method == "POST" and url.endswith("/activities/manual"):
            return {"id": "iX", "start_date_local": "2026-04-27T00:00:00", "type": "WeightTraining", "paired_event_id": None}
        if method == "GET" and url == "/activity/iX":
            activity = _make_fake_clean_activity("iX")
            activity["paired_event_id"] = None  # mismatch — explicit-set didn't take
            return activity
        if method == "DELETE":
            counters["delete"] += 1
            raise AssertionError("DELETE must not happen on paired-event-id mismatch")
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        complete_climbing_session(event_id="ev123", athlete_id="i1")
    )
    assert result.startswith("Error: paired_event_id mismatch on activity iX"), result
    assert "sent 'ev123'" in result, result
    assert counters["delete"] == 0


def test_complete_enrichment_fails_after_post_keeps_activity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-09: POST OK, readback verifies paired_event_id, but _enrich_impl fails
    (verify-fields GET returns [] → 'missing fields' error). Activity preserved,
    error names activity_id, retry hint included, NO DELETE."""
    from intervals_mcp_server.tools.climbing import complete_climbing_session

    counters = {"delete": 0}

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and "/event/" in url and "/events" not in url:
            return _make_fake_event("ev123")
        if method == "GET" and url.endswith("/activities"):
            # On the duplicate-guard call (filtered by oldest=2026-04-27): empty.
            # On the verify-fields call (filtered by limit, no oldest): also empty.
            # Returning [] for both means duplicate-guard miss AND verify-fields
            # reports all custom fields missing → enrich short-circuits.
            return []
        if method == "POST" and url.endswith("/activities/manual"):
            return {"id": "iCREATED", "start_date_local": "2026-04-27T00:00:00", "type": "WeightTraining", "paired_event_id": "ev123"}
        if method == "GET" and url == "/activity/iCREATED":
            activity = _make_fake_clean_activity("iCREATED")
            activity["paired_event_id"] = "ev123"  # readback confirms link took
            return activity
        if method == "DELETE":
            counters["delete"] += 1
            raise AssertionError("DELETE must not happen on enrichment failure")
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        complete_climbing_session(
            event_id="ev123",
            discipline="bouldering",  # custom field → triggers verify-fields guard
            athlete_id="i1",
        )
    )
    assert "iCREATED" in result, result
    assert "ev123" in result, result
    assert "but enrichment failed" in result, result
    assert "Call enrich_activity_climbing(activity_id=iCREATED, override=True" in result, result
    assert counters["delete"] == 0
