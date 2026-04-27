"""Unit tests for utils/wellness.py + tools/wellness.py::write_wellness_entry (write tool, lands in Plan 02-03)."""

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

from intervals_mcp_server.utils.wellness import (  # pylint: disable=wrong-import-position
    PARAM_TO_API_FIELD,
    WELLNESS_RANGES,
    build_wellness_put_body,
    sleep_hours_to_secs,
)


# --------------------------------------------------------------------------- #
# Helper-layer tests (full bodies — verify utils/wellness.py behavior).
# --------------------------------------------------------------------------- #


def test_sleep_hours_to_secs_basic() -> None:
    assert sleep_hours_to_secs(8.0) == 28800
    assert sleep_hours_to_secs(7.5) == 27000
    assert sleep_hours_to_secs(0) == 0


def test_sleep_hours_to_secs_rejects_negative() -> None:
    with pytest.raises(ValueError):
        sleep_hours_to_secs(-1.0)


def test_build_wellness_put_body_drops_none() -> None:
    body = build_wellness_put_body({"soreness": 3, "fatigue": None, "stress": 2})
    assert body == {"soreness": 3, "stress": 2}


def test_build_wellness_put_body_translates_names() -> None:
    body = build_wellness_put_body({"resting_hr": 51, "sleep_quality": 3})
    assert body == {"restingHR": 51, "sleepQuality": 3}


def test_build_wellness_put_body_converts_sleep_hours() -> None:
    body = build_wellness_put_body({"sleep_hours": 8.0})
    assert body == {"sleepSecs": 28800}


def test_build_wellness_put_body_empty_input_returns_empty() -> None:
    assert build_wellness_put_body({}) == {}


def test_build_wellness_put_body_unknown_key_raises() -> None:
    with pytest.raises(KeyError):
        build_wellness_put_body({"finger_skin": 5})


def test_param_to_api_field_covers_all_public_params() -> None:
    expected = {
        "sleep_hours",
        "sleep_quality",
        "soreness",
        "fatigue",
        "motivation",
        "stress",
        "mood",
        "hrv",
        "resting_hr",
    }
    assert set(PARAM_TO_API_FIELD.keys()) == expected


def test_wellness_helpers() -> None:
    """Suite-meta entry point referenced in 02-VALIDATION.md row 02-02."""
    # Helpers exercised by all tests above; this anchor confirms collection works.
    assert callable(sleep_hours_to_secs)
    assert callable(build_wellness_put_body)
    # MappingProxyType-ish guard: read-only mapping rejects assignment.
    with pytest.raises(TypeError):
        WELLNESS_RANGES["x"] = (1, 5)  # type: ignore[index]


# --------------------------------------------------------------------------- #
# Wave-0 stubs — Plan 02-03 fills these once write_wellness_entry exists.
# Names referenced by 02-VALIDATION.md "Per-Requirement Falsifiable Assertions".
# --------------------------------------------------------------------------- #


def test_signature_aligns_with_wellness_ranges() -> None:
    """Locks WELLNESS_RANGES against write_wellness_entry's signature.

    Every subjective Optional param in the signature must have a key in
    WELLNESS_RANGES, and every WELLNESS_RANGES key must appear in the
    signature.
    """
    from intervals_mcp_server.tools.wellness import write_wellness_entry

    sig = inspect.signature(write_wellness_entry)
    subjective = {"sleep_quality", "soreness", "fatigue", "motivation", "stress", "mood"}
    sig_subjective = {name for name in sig.parameters if name in subjective}
    missing_in_ranges = sig_subjective - set(WELLNESS_RANGES.keys())
    extra_in_ranges = set(WELLNESS_RANGES.keys()) - sig_subjective
    assert not missing_in_ranges, (
        f"Subjective params present in signature but missing from WELLNESS_RANGES: "
        f"{sorted(missing_in_ranges)}"
    )
    assert not extra_in_ranges, (
        f"WELLNESS_RANGES has entries with no matching signature param: "
        f"{sorted(extra_in_ranges)}"
    )


def test_wellness_tool_registered() -> None:
    """Smoke: write_wellness_entry is importable + is a coroutine function."""
    from intervals_mcp_server.tools.wellness import write_wellness_entry

    assert inspect.iscoroutinefunction(write_wellness_entry)


def test_write_wellness_entry_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """PUT + GET readback succeed; supplied fields roundtrip; success string returned."""
    from intervals_mcp_server.tools.wellness import write_wellness_entry

    calls: list[dict[str, Any]] = []

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        calls.append({"url": url, "method": method, "data": data, "params": params})
        if method == "PUT":
            return {"id": "2099-01-01", "sleepSecs": 28800, "fatigue": 2}
        return [{"id": "2099-01-01", "sleepSecs": 28800, "fatigue": 2}]

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.wellness.make_intervals_request", fake_request
    )

    result = asyncio.run(
        write_wellness_entry(
            date="2099-01-01", sleep_hours=8.0, fatigue=2, athlete_id="i1"
        )
    )
    assert result.startswith("Successfully wrote wellness entry for 2099-01-01.")
    assert calls[0]["method"] == "PUT"
    assert calls[0]["url"] == "/athlete/i1/wellness/2099-01-01"
    assert calls[0]["data"] == {"sleepSecs": 28800, "fatigue": 2}
    assert calls[1]["method"] == "GET"
    assert calls[1]["url"] == "/athlete/i1/wellness"
    assert calls[1]["params"] == {"oldest": "2099-01-01", "newest": "2099-01-01"}


def test_write_wellness_entry_rejects_empty_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-10: only `date` supplied → error before any HTTP call."""
    from intervals_mcp_server.tools.wellness import write_wellness_entry

    calls: list[dict[str, Any]] = []

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        calls.append({"url": url, "method": method, "data": data, "params": params})
        return {}

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.wellness.make_intervals_request", fake_request
    )

    result = asyncio.run(write_wellness_entry(date="2099-01-01", athlete_id="i1"))
    assert "at least one wellness field must be supplied" in result
    assert calls == []  # no HTTP performed


def test_write_wellness_entry_rejects_out_of_range(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-07: out-of-range value short-circuits before any HTTP call."""
    from intervals_mcp_server.tools.wellness import write_wellness_entry

    async def fake_request(*_args: object, **_kwargs: object) -> Any:
        raise AssertionError("HTTP must not be called")

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.wellness.make_intervals_request", fake_request
    )

    result = asyncio.run(
        write_wellness_entry(date="2099-01-01", fatigue=99, athlete_id="i1")
    )
    assert result.startswith("Error: fatigue=99 out of range")


def test_write_wellness_entry_readback_failure_no_readme_pointer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-11: readback mismatch surfaces error WITHOUT README pointer (wellness is native)."""
    from intervals_mcp_server.tools.wellness import write_wellness_entry

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        if method == "PUT":
            return {"id": "2099-01-01", "fatigue": 2}
        # Readback returns a DIFFERENT value for fatigue → mismatch.
        return [{"id": "2099-01-01", "fatigue": 99}]

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.wellness.make_intervals_request", fake_request
    )

    result = asyncio.run(
        write_wellness_entry(date="2099-01-01", fatigue=2, athlete_id="i1")
    )
    assert "did not roundtrip" in result
    assert "README" not in result


def test_write_wellness_entry_api_error_on_put(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PUT returns error envelope → tool surfaces it with the API message."""
    from intervals_mcp_server.tools.wellness import write_wellness_entry

    async def fake_request(*_args: object, **_kwargs: object) -> Any:
        return {"error": True, "status_code": 500, "message": "boom"}

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.wellness.make_intervals_request", fake_request
    )

    result = asyncio.run(
        write_wellness_entry(date="2099-01-01", fatigue=2, athlete_id="i1")
    )
    assert result.startswith("Error writing wellness entry")
    assert "boom" in result


def test_write_wellness_entry_unsupplied_field_dropped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-09: unsupplied (None) fields do NOT appear in PUT body — drop-None upsert."""
    from intervals_mcp_server.tools.wellness import write_wellness_entry

    calls: list[dict[str, Any]] = []

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        calls.append({"url": url, "method": method, "data": data, "params": params})
        if method == "PUT":
            return {"id": "2099-01-01", "sleepSecs": 28800, "soreness": 3}
        return [{"id": "2099-01-01", "sleepSecs": 28800, "soreness": 3}]

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.wellness.make_intervals_request", fake_request
    )

    result = asyncio.run(
        write_wellness_entry(
            date="2099-01-01",
            sleep_hours=8.0,
            fatigue=None,
            soreness=3,
            athlete_id="i1",
        )
    )
    assert result.startswith("Successfully wrote wellness entry for 2099-01-01.")
    put_call = calls[0]
    assert put_call["method"] == "PUT"
    assert set(put_call["data"].keys()) == {"sleepSecs", "soreness"}
    assert put_call["data"] == {"sleepSecs": 28800, "soreness": 3}


def test_subset_upsert_does_not_overwrite_unrelated_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WELL-02: subset call (fatigue=2) PUTs only that field; readback confirms upsert.

    The mocked readback can include additional fields the API kept from prior writes
    — those untouched fields must not show up in the PUT body, only `fatigue`.
    """
    from intervals_mcp_server.tools.wellness import write_wellness_entry

    calls: list[dict[str, Any]] = []

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        calls.append({"url": url, "method": method, "data": data, "params": params})
        if method == "PUT":
            return {"id": "2099-01-01", "fatigue": 2}
        # Readback also surfaces unrelated fields the day already had — they MUST
        # be untouched (we don't check them, but they're allowed to coexist).
        return [{"id": "2099-01-01", "fatigue": 2, "soreness": 3, "sleepSecs": 27000}]

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.wellness.make_intervals_request", fake_request
    )

    result = asyncio.run(
        write_wellness_entry(date="2099-01-01", fatigue=2, athlete_id="i1")
    )
    assert result.startswith("Successfully wrote wellness entry for 2099-01-01.")
    put_call = calls[0]
    assert put_call["method"] == "PUT"
    # Only fatigue was supplied — only fatigue lands in the PUT body.
    assert put_call["data"] == {"fatigue": 2}


def test_sleep_hours_converts_to_secs_and_upserts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WELL-01: sleep_hours=8.0 → PUT body {sleepSecs: 28800}; readback confirms it."""
    from intervals_mcp_server.tools.wellness import write_wellness_entry

    calls: list[dict[str, Any]] = []

    async def fake_request(
        url: str,
        api_key: str | None = None,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> Any:
        calls.append({"url": url, "method": method, "data": data, "params": params})
        if method == "PUT":
            return {"id": "2099-01-01", "sleepSecs": 28800}
        return [{"id": "2099-01-01", "sleepSecs": 28800}]

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.wellness.make_intervals_request", fake_request
    )

    result = asyncio.run(
        write_wellness_entry(date="2099-01-01", sleep_hours=8.0, athlete_id="i1")
    )
    assert result.startswith("Successfully wrote wellness entry for 2099-01-01.")
    assert calls[0]["method"] == "PUT"
    assert calls[0]["url"] == "/athlete/i1/wellness/2099-01-01"
    assert calls[0]["data"] == {"sleepSecs": 28800}
    assert calls[1]["method"] == "GET"
    assert calls[1]["url"] == "/athlete/i1/wellness"
    assert calls[1]["params"] == {"oldest": "2099-01-01", "newest": "2099-01-01"}


def test_out_of_range_rejects_pre_api(monkeypatch: pytest.MonkeyPatch) -> None:
    """WELL-03: out-of-range value (fatigue=99) rejected BEFORE any HTTP call.

    Any HTTP attempt fails the test (the fake raises AssertionError).
    """
    from intervals_mcp_server.tools.wellness import write_wellness_entry

    async def fake_request(*_args: object, **_kwargs: object) -> Any:
        raise AssertionError("HTTP must not be called")

    monkeypatch.setattr(
        "intervals_mcp_server.api.client.make_intervals_request", fake_request
    )
    monkeypatch.setattr(
        "intervals_mcp_server.tools.wellness.make_intervals_request", fake_request
    )

    result = asyncio.run(
        write_wellness_entry(date="2099-01-01", fatigue=99, athlete_id="i1")
    )
    assert result.startswith("Error: fatigue=99 out of range")
    # The locked range (1, 4) must be named in the message.
    assert "1..4" in result
