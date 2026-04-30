---
phase: 01-foundation-and-write-path-spike
reviewed: 2026-04-24T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - README.md
  - scripts/spike_write_endpoints.py
  - src/intervals_mcp_server/server.py
  - src/intervals_mcp_server/tools/climbing.py
  - src/intervals_mcp_server/utils/climbing.py
  - src/intervals_mcp_server/utils/formatting.py
  - src/intervals_mcp_server/utils/grades.py
  - tests/test_climbing.py
  - tests/test_format_climbing_activity.py
  - tests/test_grades.py
findings:
  critical: 0
  warning: 3
  info: 6
  total: 9
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-04-24
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Phase 01 (Foundation and Write-Path Spike) introduces a climbing-focused custom-field spec, the `verify_custom_fields_setup` MCP tool, a grade-validation module, a climbing activity formatter, and a throwaway live-API spike script. Overall the code is well-structured, type-annotated, documented, and adheres to project conventions:

- All HTTP goes through `make_intervals_request()` (no direct `httpx`) — constraint respected.
- `CUSTOM_FIELD_KEYS` is exposed via a `MappingProxyType` wrapper, with a test asserting immutability.
- Grade validation uses strict case as the cross-scale guard; tests cover both accept- and reject-paths.
- The spike script redacts the athlete id before writing findings to disk, keeps the target on a far-future date (2099-01-01), and attempts DELETE cleanup.
- No hard-coded secrets; API key and athlete id come from `.env` via `get_config()`.
- README documents the user-defined custom-field prerequisite (SETUP-01) clearly.

No critical (security / data-loss / crash) issues were found. The findings below are about (a) a few correctness gaps in the spike script's error-shape assumptions, (b) the `verify_custom_fields_setup` readback-heuristic producing a false-positive "missing" result for defined-but-never-populated fields without flagging that caveat to the user, (c) a quirky Font regex edge case, and (d) minor code-quality polish.

## Warnings

### WR-01: Spike script inflates all non-error responses to HTTP 200 regardless of actual status

**File:** `scripts/spike_write_endpoints.py:223-234`

**Issue:** In `spike_custom_field_definitions`, the `status_code` recorded for each candidate endpoint is derived as:

```python
"status_code": result.get("status_code")
    if isinstance(result, dict) and "error" in result
    else 200,
```

When `make_intervals_request` returns a `list` or a non-error `dict`, the script hard-codes `200`. But `make_intervals_request` can also return a 2xx with a non-JSON or empty body that surfaces as an empty dict/list — and, more importantly, any non-error path (including, for example, a redirect-followed 204) will be recorded as `200` even when it wasn't. This makes the findings file misleading about which endpoint actually returned 2xx, and conflates "succeeded" with "got status 200".

**Fix:** Either have `make_intervals_request` thread the real status code through on success, or record a tri-state (`"success" | "error" | "unknown"`) rather than a fabricated number. Simplest narrow fix:

```python
if isinstance(result, dict) and "error" in result:
    status_repr = result.get("status_code")
else:
    status_repr = "2xx"  # don't fabricate a specific code we didn't observe
findings["candidates_tried"].append({
    "endpoint": pattern.format(id=ATHLETE_REDACTED),
    "status_code": status_repr,
    ...
})
```

### WR-02: `verify_custom_fields_setup` can report defined fields as "missing" with no caveat

**File:** `src/intervals_mcp_server/tools/climbing.py:34-100`

**Issue:** The readback heuristic inspects the last 50 activities and calls a field "defined" only if it appears as a top-level key on at least one of them. Intervals.icu returns custom-field keys on an activity only when that field has been populated on that activity. So a field that is correctly defined in the athlete account but has never been populated on any of the 50 most recent activities (e.g. a brand-new athlete who has just defined the fields, or a cyclist with many recent rides that don't use climbing fields) will be reported as missing — causing the Phase 2+ write tools to incorrectly refuse to run.

The docstring internal to `_verify_custom_fields_setup_impl` acknowledges this is a heuristic, but the user-facing message produced in the `missing` branch (lines 84-98) does not disclose the limitation. Claude/the user will see "Missing required Intervals.icu custom fields" with no hint that the diagnosis may be a false negative.

**Fix:** Append a one-line caveat to the human message when fields appear missing, so the user knows to check the athlete settings even if they believe the fields are defined:

```python
lines.append("")
lines.append(
    "Note: this check inspects your last "
    f"{_READBACK_ACTIVITY_LIMIT} activities for the presence of these fields. "
    "Fields that are defined in your athlete settings but have never been "
    "populated on a recent activity may be falsely reported here; please "
    "verify manually in Intervals.icu > Settings > Custom Fields."
)
lines.append(_README_POINTER)
```

### WR-03: Spike wellness cleanup is unconditional and destructive even if earlier steps failed

**File:** `scripts/spike_write_endpoints.py:122-127`

**Issue:** The cleanup PUT that zeroes `sleepSecs`, `soreness`, and `fatigue` with `-1` runs unconditionally at the end of `spike_wellness_put` — even if `write_body_1` or `write_body_2` errored out. If a previous operator left real data at `2099-01-01` by hand (unlikely but the script's own guard against this is only the future date), the cleanup would silently blank it. More practically, if the readback calls error out and the spike is re-run later, the script will happily clobber whatever is there.

The spike is documented as a one-shot throwaway, and the SPIKE_DATE is far-future, so the blast radius is minimal. But as written the cleanup is not gated on "we actually wrote data."

**Fix:** Guard cleanup on success of the writes, and skip it if either write returned an error dict:

```python
wrote_successfully = not any(
    isinstance(r, dict) and r.get("error")
    for r in (findings["write_1_response"], findings["write_2_response"])
)
if wrote_successfully:
    findings["cleanup_response"] = await make_intervals_request(...)
else:
    findings["cleanup_response"] = "skipped — earlier writes errored"
```

## Info

### IN-01: Font regex accepts bare "1" and "2" which aren't real grades

**File:** `src/intervals_mcp_server/utils/grades.py:24`

**Issue:** The regex `^[3-9][A-C]\+?$|^[12]$` accepts bare `"1"` and `"2"` as valid Font grades (the comment says "included defensively (grade-scale completeness)"). These aren't grades people actually write — Font nomenclature starts in practice at `3A` / `4A`. Worse, the tests in `tests/test_grades.py` neither accept nor reject `"1"` / `"2"`, so the behavior is untested. If someone types `6` (with no letter) in error, the regex correctly rejects it; but `1` silently validates as a Font grade, leading to a meaningless `top_grade_sent`.

**Fix:** Drop the `|^[12]$` alternation unless there is a concrete source requiring it. If kept, add an explicit accept-test so the intent is checkable.

### IN-02: RPE formatter treats `True`/`False` as numeric RPE values

**File:** `src/intervals_mcp_server/utils/formatting.py:576-577`

**Issue:** `isinstance(rpe, (int, float))` is `True` for `bool` (since `bool` subclasses `int` in Python). If a readback accidentally returns `icu_rpe: True`, the formatter will render `True/10`. Low likelihood given Intervals.icu's API, but costs nothing to harden.

**Fix:**

```python
rpe_str = (
    f"{rpe}/10"
    if isinstance(rpe, (int, float)) and not isinstance(rpe, bool)
    else "N/A"
)
```

### IN-03: Spike redaction is substring-based

**File:** `scripts/spike_write_endpoints.py:61-69`

**Issue:** `_redact` does a plain `str.replace(athlete_id, ATHLETE_REDACTED)`. If `athlete_id` happens to be a short numeric string that also appears as a substring of another id or value in the response (e.g. an activity id ending in the same digits), the redaction will over-match. Harmless for the spike's actual content but worth a note if this redactor is ever lifted into non-throwaway code.

**Fix:** Not required for the spike. If the redactor migrates to production, use a word-boundary regex or redact structurally (walk dicts and redact only fields known to contain athlete ids).

### IN-04: `activity_id_for_manual_cleanup` is only set inside `if activity_id:` — findings writer must defend against it being missing

**File:** `scripts/spike_write_endpoints.py:205-211, 285-286`

**Issue:** `activity_id_for_manual_cleanup` is only assigned to `findings` when `activity_id` is truthy. If the initial POST never returns an id (primary 404 + fallback also failing), the key is absent from `activity` when `write_findings` later calls `activity.get('activity_id_for_manual_cleanup')`. The `.get(...)` returns `None`, which renders as the literal string `None` in the findings markdown — a confusing artifact in the output.

**Fix:** Default-initialize the key at the top of `spike_activity_create` and branch the rendering in `write_findings`:

```python
findings: dict[str, Any] = {"activity_id_for_manual_cleanup": None}
# ...
manual_id = activity.get("activity_id_for_manual_cleanup")
content.append(
    f"- Activity id for manual cleanup: "
    f"{manual_id if manual_id else 'n/a (activity was not created or was deleted)'}\n"
)
```

### IN-05: README's ChatGPT SSE section contains shell-sourced secrets with no warning

**File:** `README.md:223-227`

**Issue:** The ChatGPT SSE usage block instructs users to `export FASTMCP_HOST=127.0.0.1 FASTMCP_PORT=8765 ...`. This is fine. But immediately afterwards the instructions have users expose the MCP server to ChatGPT via `ngrok http 8765` with authentication "No authentication". Since the MCP server fronts an API that can *write* to Intervals.icu (Phase 2+), a public ngrok tunnel with no auth is a credential-proxy to the user's athlete account for anyone who guesses the random ngrok subdomain. This is pre-existing (not introduced in Phase 1), but worth flagging because Phase 2 adds write tools which widen the blast radius.

**Fix:** Add a callout recommending ngrok basic auth (`ngrok http --basic-auth "user:pass" 8765`) or the explicit note that the tunnel URL is a secret.

### IN-06: `_KeyTracker.get` signature narrows the default type compared to `dict.get`

**File:** `src/intervals_mcp_server/utils/formatting.py:12-30`

**Issue:** `_KeyTracker.get` annotates `default: Any = None` but the base `dict.get` return overload depends on `default`. Not a runtime bug, but the signature will trip `mypy --strict`'s overload inference on callers that rely on `get(key)` returning `Optional[V]`. Purely a typing / ergonomics note.

**Fix:** Either drop the overriding `get` signature annotation entirely (let dict's stubs carry through) or add proper overloads if the strict-typing lint is ever turned on.

---

_Reviewed: 2026-04-24_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
