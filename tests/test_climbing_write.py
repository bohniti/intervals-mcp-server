"""Unit tests for tools/climbing.py::enrich_activity_climbing — CLIMB-03..07, CLIMB-10."""

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
    Discipline,
    SessionFocus,
)


# ---------------------------------------------------------------------------
# Fake-response helpers (mirror tests/test_climbing.py:82-108).
# ---------------------------------------------------------------------------


def _make_fake_all_present() -> list[dict[str, object]]:
    """Fake activities-list response: every required CUSTOM_FIELD_KEYS key is
    present as a top-level field on at least one activity (verify-fields all
    present).
    """
    activity: dict[str, object] = {
        "id": "i1",
        "name": "Session with all climbing fields",
        "type": "WeightTraining",
    }
    for key in CUSTOM_FIELD_KEYS:
        activity[key] = None
    return [activity]


def _make_fake_clean_activity(activity_id: str = "i1") -> dict[str, object]:
    """Activity dict with no climbing fields set (pre-enrichment shape)."""
    activity: dict[str, object] = {
        "id": activity_id,
        "name": "Sample",
        "type": "WeightTraining",
        "start_date_local": "2099-01-01T00:00:00",
    }
    for key in CUSTOM_FIELD_KEYS:
        activity[key] = None
    activity["icu_rpe"] = None
    return activity


# ---------------------------------------------------------------------------
# Tool registration sanity.
# ---------------------------------------------------------------------------


def test_enrich_tool_registered() -> None:
    """enrich_activity_climbing is an async function with the 12-param signature."""
    from intervals_mcp_server.tools.climbing import enrich_activity_climbing

    assert inspect.iscoroutinefunction(enrich_activity_climbing)
    sig = inspect.signature(enrich_activity_climbing)
    assert len(sig.parameters) == 12, sig.parameters
    assert sig.parameters["override"].default is False


# ---------------------------------------------------------------------------
# CLIMB-03: enrich writes custom fields and roundtrips through readback.
# ---------------------------------------------------------------------------


def test_enrich_writes_custom_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLIMB-03: discipline + top_grade_sent supplied → PUT body contains those
    keys, readback returns same values, success string returned.
    """
    from intervals_mcp_server.tools.climbing import enrich_activity_climbing

    pre = _make_fake_clean_activity("i1")
    post = dict(pre)
    post["discipline"] = "bouldering"
    post["top_grade_sent"] = "6A"

    counters = {"pre_get": 0, "post_get": 0, "verify_get": 0, "put": 0}
    captured_put_bodies: list[dict[str, Any]] = []

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and url == "/activity/i1":
            if counters["put"] == 0:
                counters["pre_get"] += 1
                return pre
            counters["post_get"] += 1
            return post
        if method == "GET" and "/activities" in url:
            counters["verify_get"] += 1
            return _make_fake_all_present()
        if method == "PUT":
            counters["put"] += 1
            captured_put_bodies.append(data or {})
            return {"id": "i1"}
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        enrich_activity_climbing(
            activity_id="i1",
            discipline="bouldering",
            top_grade_sent="6A",
            athlete_id="i1",
        )
    )
    assert result.startswith("Successfully enriched activity i1."), result
    # Find the custom-field PUT body (no icu_rpe in this call → exactly one PUT).
    assert counters["put"] == 1
    body = captured_put_bodies[0]
    assert body.get("discipline") == "bouldering", body
    assert body.get("top_grade_sent") == "6A", body


# ---------------------------------------------------------------------------
# CLIMB-04: discipline-aware grade validation rejects pre-API.
# ---------------------------------------------------------------------------


def test_grade_discipline_mismatch_rejects_pre_api(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLIMB-04: Font-on-route raises ValueError naming 'French sport scale' BEFORE
    any HTTP call. The tool wraps the ValueError into an Error string.
    """
    from intervals_mcp_server.tools.climbing import enrich_activity_climbing

    async def fake_request(*_args: object, **_kwargs: object) -> Any:
        raise AssertionError("HTTP must not be called when grade-discipline mismatches")

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        enrich_activity_climbing(
            activity_id="i1",
            discipline="sport_lead",
            top_grade_sent="6A",  # Font on a route discipline → reject
            athlete_id="i1",
        )
    )
    assert "French sport" in result, result
    assert result.startswith("Error"), result


# ---------------------------------------------------------------------------
# CLIMB-05: missing-custom-fields short-circuits before any PUT.
# ---------------------------------------------------------------------------


def test_missing_custom_fields_short_circuits(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLIMB-05: when verify-fields impl returns missing fields, no PUT happens
    and the user sees the named-field error + README pointer.
    """
    from intervals_mcp_server.tools.climbing import enrich_activity_climbing

    counters = {"verify_get": 0, "put": 0, "activity_get": 0}

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and "/activities" in url:
            counters["verify_get"] += 1
            return []  # No activities → all fields missing
        if method == "GET" and url == "/activity/i1":
            counters["activity_get"] += 1
            return _make_fake_clean_activity("i1")
        if method == "PUT":
            counters["put"] += 1
            return {"id": "i1"}
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        enrich_activity_climbing(
            activity_id="i1",
            discipline="bouldering",
            athlete_id="i1",
        )
    )
    assert "Missing required Intervals.icu custom fields" in result, result
    assert "See README section 'Climbing setup" in result, result
    assert counters["put"] == 0, "PUT must not happen when custom fields missing"
    assert counters["activity_get"] == 0, (
        "conflict-scan GET must not happen when verify-fields short-circuits"
    )


# ---------------------------------------------------------------------------
# CLIMB-06: default-deny re-enrichment.
# ---------------------------------------------------------------------------


def test_default_deny_re_enrichment(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLIMB-06 (first): re-enriching an already-set field without override=True
    refuses with conflicts list and no PUT.
    """
    from intervals_mcp_server.tools.climbing import enrich_activity_climbing

    pre = _make_fake_clean_activity("i1")
    pre["discipline"] = "bouldering"  # already set

    counters = {"put": 0}

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and "/activities" in url:
            return _make_fake_all_present()
        if method == "GET" and url == "/activity/i1":
            return pre
        if method == "PUT":
            counters["put"] += 1
            raise AssertionError("PUT must not happen on conflict refusal")
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        enrich_activity_climbing(
            activity_id="i1",
            discipline="sport_lead",  # conflicts with pre's bouldering
            athlete_id="i1",
        )
    )
    assert result.startswith("Error: activity i1 already has values"), result
    assert "discipline" in result, result
    assert "Pass override=True" in result, result
    assert counters["put"] == 0


def test_override_writes_audit_message(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLIMB-06 (second): override=True proceeds AND posts audit via
    add_activity_message with [enrich override] prefix containing old→new.
    """
    from intervals_mcp_server.tools.climbing import enrich_activity_climbing

    pre = _make_fake_clean_activity("i1")
    pre["discipline"] = "bouldering"
    post = dict(pre)
    post["discipline"] = "sport_lead"

    counters = {"put": 0, "audit_post": 0}
    captured_audit_content: list[str] = []

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and "/activities" in url:
            return _make_fake_all_present()
        if method == "GET" and url == "/activity/i1":
            return pre if counters["put"] == 0 else post
        if method == "POST" and url == "/activity/i1/messages":
            counters["audit_post"] += 1
            if data is not None and "content" in data:
                captured_audit_content.append(str(data["content"]))
            return {"id": "msg1"}
        if method == "PUT":
            counters["put"] += 1
            return {"id": "i1"}
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )
    # add_activity_message lives in tools.activities and re-imports
    # make_intervals_request at module load — patch there too.
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )

    result = asyncio.run(
        enrich_activity_climbing(
            activity_id="i1",
            discipline="sport_lead",
            override=True,
            athlete_id="i1",
        )
    )
    assert result.startswith("Successfully enriched"), result
    assert counters["audit_post"] == 1, counters
    assert len(captured_audit_content) == 1
    audit = captured_audit_content[0]
    assert audit.startswith("[enrich override] "), audit
    assert "discipline: bouldering→sport_lead" in audit, audit


# ---------------------------------------------------------------------------
# CLIMB-07: icu_rpe writes to native field and roundtrips.
# ---------------------------------------------------------------------------


def test_icu_rpe_writes_and_reads_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLIMB-07 (first): rpe=6 lands on icu_rpe and roundtrips. RPE-only writes
    skip the verify-fields guard (D-20).
    """
    from intervals_mcp_server.tools.climbing import enrich_activity_climbing

    pre = _make_fake_clean_activity("i1")
    post = dict(pre)
    post["icu_rpe"] = 6

    counters = {"pre_get": 0, "post_get": 0, "verify_get": 0, "put": 0}

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and url == "/activity/i1":
            if counters["put"] == 0:
                counters["pre_get"] += 1
                return pre
            counters["post_get"] += 1
            return post
        if method == "GET" and "/activities" in url:
            counters["verify_get"] += 1
            return _make_fake_all_present()
        if method == "PUT":
            counters["put"] += 1
            return {"id": "i1", "icu_rpe": 6}
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        enrich_activity_climbing(activity_id="i1", rpe=6, athlete_id="i1")
    )
    assert result.startswith("Successfully enriched activity i1."), result
    assert counters["verify_get"] == 0, (
        "verify-fields guard must NOT fire on RPE-only writes (D-20)"
    )
    assert counters["put"] == 1
    assert counters["pre_get"] == 1
    assert counters["post_get"] == 1


def test_icu_rpe_readback_mismatch_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLIMB-07 (second): if readback returns icu_rpe missing or different,
    error names icu_rpe AND does NOT include _README_POINTER (RPE is native;
    not a custom-field setup issue per <specifics>).
    """
    from intervals_mcp_server.tools.climbing import enrich_activity_climbing

    pre = _make_fake_clean_activity("i1")
    post = dict(pre)
    post["icu_rpe"] = None  # silent-ignore simulation

    counters = {"put": 0}

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and url == "/activity/i1":
            return pre if counters["put"] == 0 else post
        if method == "GET" and "/activities" in url:
            return _make_fake_all_present()
        if method == "PUT":
            counters["put"] += 1
            return {"id": "i1"}
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        enrich_activity_climbing(activity_id="i1", rpe=6, athlete_id="i1")
    )
    assert result.startswith("Error: enrichment fields did not roundtrip"), result
    assert "icu_rpe" in result, result
    assert "See README section 'Climbing setup" not in result, (
        "RPE-only readback failure must NOT include the README pointer"
    )


# ---------------------------------------------------------------------------
# Pre-API validation: empty call, grade-without-discipline, unknown enums,
# rpe-out-of-range.
# ---------------------------------------------------------------------------


def test_enrich_rejects_empty_call(monkeypatch: pytest.MonkeyPatch) -> None:
    from intervals_mcp_server.tools.climbing import enrich_activity_climbing

    async def fake_request(*_args: object, **_kwargs: object) -> Any:
        raise AssertionError("HTTP must not be called for empty call")

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        enrich_activity_climbing(activity_id="i1", athlete_id="i1")
    )
    assert result.startswith("Error: nothing to write"), result


def test_enrich_rejects_grade_without_discipline(monkeypatch: pytest.MonkeyPatch) -> None:
    from intervals_mcp_server.tools.climbing import enrich_activity_climbing

    async def fake_request(*_args: object, **_kwargs: object) -> Any:
        raise AssertionError("HTTP must not be called when grade has no discipline")

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        enrich_activity_climbing(
            activity_id="i1",
            top_grade_sent="6A",
            athlete_id="i1",
        )
    )
    assert "discipline must be supplied" in result, result


def test_enrich_rejects_unknown_discipline(monkeypatch: pytest.MonkeyPatch) -> None:
    from intervals_mcp_server.tools.climbing import enrich_activity_climbing

    async def fake_request(*_args: object, **_kwargs: object) -> Any:
        raise AssertionError("HTTP must not be called for unknown discipline")

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        enrich_activity_climbing(
            activity_id="i1",
            discipline="alpine",
            athlete_id="i1",
        )
    )
    assert "unknown discipline" in result, result
    for d in Discipline:
        assert d.value in result, f"discipline value {d.value} should be listed"


def test_enrich_rejects_unknown_session_focus(monkeypatch: pytest.MonkeyPatch) -> None:
    from intervals_mcp_server.tools.climbing import enrich_activity_climbing

    async def fake_request(*_args: object, **_kwargs: object) -> Any:
        raise AssertionError("HTTP must not be called for unknown session_focus")

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        enrich_activity_climbing(
            activity_id="i1",
            session_focus="napping",
            athlete_id="i1",
        )
    )
    assert "unknown session_focus" in result, result
    for f in SessionFocus:
        assert f.value in result, f"session_focus value {f.value} should be listed"


def test_enrich_rejects_rpe_out_of_range(monkeypatch: pytest.MonkeyPatch) -> None:
    from intervals_mcp_server.tools.climbing import enrich_activity_climbing

    async def fake_request(*_args: object, **_kwargs: object) -> Any:
        raise AssertionError("HTTP must not be called for rpe out of range")

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        enrich_activity_climbing(activity_id="i1", rpe=11, athlete_id="i1")
    )
    assert result.startswith("Error: rpe=11 out of range"), result


# ---------------------------------------------------------------------------
# CLIMB-10 readback flavour: silent-ignore on custom-field write surfaces
# the README pointer.
# ---------------------------------------------------------------------------


def test_readback_custom_field_failure_includes_readme_pointer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLIMB-10 readback: PUT succeeds, readback shows discipline=null (silent
    ignore — Pitfall #2). Error names the field AND includes _README_POINTER
    so the LLM can guide the user to the setup README.
    """
    from intervals_mcp_server.tools.climbing import enrich_activity_climbing

    pre = _make_fake_clean_activity("i1")
    post = dict(pre)
    post["discipline"] = None  # silent-ignore: PUT accepted but field missing post

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and "/activities" in url:
            return _make_fake_all_present()
        if method == "GET" and url == "/activity/i1":
            return pre if not getattr(fake_request, "_put_done", False) else post
        if method == "PUT":
            fake_request._put_done = True  # type: ignore[attr-defined]
            return {"id": "i1"}
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        enrich_activity_climbing(
            activity_id="i1",
            discipline="bouldering",
            athlete_id="i1",
        )
    )
    assert "did not roundtrip" in result, result
    assert "discipline" in result, result
    assert "See README section 'Climbing setup" in result, result


# ---------------------------------------------------------------------------
# Type-coercion drift: int vs float.
# ---------------------------------------------------------------------------


def test_type_coercion_drift_int_vs_float_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Python `6 == 6.0` is True — the readback returning float when sent int
    must NOT trigger a false mismatch (RESEARCH.md Pattern 3).
    """
    from intervals_mcp_server.tools.climbing import enrich_activity_climbing

    pre = _make_fake_clean_activity("i1")
    post = dict(pre)
    post["icu_rpe"] = 6.0  # float — sent int 6

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and "/activities" in url:
            return _make_fake_all_present()
        if method == "GET" and url == "/activity/i1":
            return pre if not getattr(fake_request, "_put_done", False) else post
        if method == "PUT":
            fake_request._put_done = True  # type: ignore[attr-defined]
            return {"id": "i1"}
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        enrich_activity_climbing(activity_id="i1", rpe=6, athlete_id="i1")
    )
    assert result.startswith("Successfully enriched"), result


# ---------------------------------------------------------------------------
# PUT body shape: top-level keys via PUT /activity/{id}.
# ---------------------------------------------------------------------------


def test_enrich_uses_locked_put_body_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    """The PUT body shape Task 1 sends must be top-level keys via
    PUT /activity/{id} per 02-SPIKE-FINDINGS.md (working hypothesis).
    Defensive against future drift.
    """
    from intervals_mcp_server.tools.climbing import enrich_activity_climbing

    pre = _make_fake_clean_activity("i1")
    post = dict(pre)
    post["discipline"] = "bouldering"
    post["sends"] = 5

    captured_puts: list[dict[str, Any]] = []

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and "/activities" in url:
            return _make_fake_all_present()
        if method == "GET" and url == "/activity/i1":
            return pre if not captured_puts else post
        if method == "PUT":
            captured_puts.append({"url": url, "data": data})
            return {"id": "i1"}
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        enrich_activity_climbing(
            activity_id="i1",
            discipline="bouldering",
            sends=5,
            athlete_id="i1",
        )
    )
    assert result.startswith("Successfully enriched"), result
    # Exactly one PUT (no rpe → no rpe PUT, only the custom-field PUT).
    assert len(captured_puts) == 1, captured_puts
    put = captured_puts[0]
    assert put["url"] == "/activity/i1", put
    body = put["data"]
    assert body is not None
    # Top-level keys (not wrapped in an envelope).
    assert "discipline" in body, body
    assert body["discipline"] == "bouldering", body
    assert body["sends"] == 5, body
    # No nesting envelopes.
    assert "custom_fields" not in body
    assert "customFields" not in body
    assert "fields" not in body


# ---------------------------------------------------------------------------
# CONDITIONAL: split-PUT partial-failure (D-16, I-03 fix).
# Required because Task 0 selected the SPLIT-PUT branch.
# ---------------------------------------------------------------------------


def test_split_put_partial_failure_named(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-16 split-PUT partial-failure: icu_rpe lands, custom-fields PUT errors →
    explicit error names what landed (icu_rpe=N) and what didn't.
    """
    from intervals_mcp_server.tools.climbing import enrich_activity_climbing

    counters = {"put_rpe": 0, "put_cf": 0, "post_get": 0}

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "GET" and url == "/activity/i1":
            if counters["put_cf"] == 0:
                # Pre-PUT GET (conflict scan).
                return _make_fake_clean_activity("i1")
            # Post-PUT GET should NOT happen on partial failure.
            counters["post_get"] += 1
            raise AssertionError("post-PUT GET must not be called on partial failure")
        if method == "GET" and "/activities" in url:
            return _make_fake_all_present()
        if method == "PUT" and isinstance(data, dict) and set(data.keys()) == {"icu_rpe"}:
            counters["put_rpe"] += 1
            return {"id": "i1", "icu_rpe": 6}
        if method == "PUT":
            counters["put_cf"] += 1
            return {"error": True, "status_code": 500, "message": "boom"}
        return []

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.climbing.make_intervals_request", fake_request
    )

    result = asyncio.run(
        enrich_activity_climbing(
            activity_id="i1",
            discipline="bouldering",
            rpe=6,
            athlete_id="i1",
        )
    )
    assert result.startswith(
        "Error: partial enrichment — icu_rpe wrote successfully"
    ), result
    assert "icu_rpe=6" in result, result
    assert "boom" in result, result
    assert "no climbing metadata" in result, result
    assert counters["put_rpe"] == 1
    assert counters["put_cf"] == 1
    assert counters["post_get"] == 0
