---
phase: 02-wellness-write-and-activity-enrichment
reviewed: 2026-04-25T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - src/intervals_mcp_server/utils/wellness.py
  - src/intervals_mcp_server/tools/wellness.py
  - src/intervals_mcp_server/tools/climbing.py
  - src/intervals_mcp_server/utils/formatting.py
  - tests/test_wellness_write.py
  - tests/test_climbing_write.py
  - tests/test_climbing.py
  - scripts/spike_write_endpoints_phase2.py
  - scripts/smoke_phase2.py
findings:
  critical: 0
  warning: 4
  info: 5
  total: 9
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-04-25T00:00:00Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Phase 2 adds two write-tools (`write_wellness_entry`, `enrich_activity_climbing`),
the `WELLNESS_RANGES` table + body builder, climbing-activity formatter
regression coverage, and two operator scripts (spike + smoke). The implementation
is structurally clean against the stated constraints:

- All HTTP goes through `make_intervals_request()` — `grep httpx`
  on `src/intervals_mcp_server/tools/` and `src/intervals_mcp_server/utils/`
  returns nothing. Only `src/intervals_mcp_server/api/client.py` imports
  `httpx`. (Verified.)
- Custom-field writes are readback-verified — `enrich_activity_climbing`
  does a post-PUT GET and per-field equality check before returning success
  (`tools/climbing.py` step 12-13).
- Wellness range pre-API validation uses `WELLNESS_RANGES` from
  `utils/wellness.py` and short-circuits before any HTTP call
  (`tools/wellness.py:170-185`).
- Drop-None upsert is implemented via `build_wellness_put_body` and locked
  by tests (`tests/test_wellness_write.py::test_build_wellness_put_body_drops_none`,
  `test_subset_upsert_does_not_overwrite_unrelated_fields`).
- Discipline-aware grade validation rejects mismatched grades pre-API
  (`tools/climbing.py:266-277`, locked by
  `tests/test_climbing_write.py::test_grade_discipline_mismatch_rejects_pre_api`).
- The spike script redacts `athlete_id` recursively before writing
  `02-SPIKE-FINDINGS.md`; the smoke script redacts before logging.

The findings below are correctness/quality concerns — none are blockers,
but two (WR-01, WR-02) describe partial-failure paths that can leave
orphaned state on the live account, and one (WR-03) is a stale-state
read after the conflict-scan that opens a small TOCTOU window.

## Warnings

### WR-01: Override audit message becomes orphaned/misleading on split-PUT custom-field failure

**File:** `src/intervals_mcp_server/tools/climbing.py:373-381` (audit) +
`tools/climbing.py:403-418` (CF PUT failure)

**Issue:** When `override=True` and conflicts exist, the audit message
(`[enrich override] discipline: bouldering→sport_lead, ...`) is posted via
`add_activity_message` BEFORE the PUT writes. If the icu_rpe PUT then
succeeds but the custom-field PUT fails (split-PUT partial failure path,
step 11), the tool returns the partial-enrichment error — but the audit
message has already landed on the activity log claiming the conflicting
custom fields were overwritten. They were not. A user reading the activity
log later sees a false claim. This is the inverse of D-14's design intent
("audit trail of intentional overwrites").

The existing test
`test_split_put_partial_failure_named` exercises rpe-only conflicts; it
does not assert behavior with `override=True` AND custom-field write
failure, so this hole is not currently covered.

**Fix:** Either (a) defer the audit message until AFTER both PUTs succeed,
posting it only on the success path; or (b) keep the current ordering but,
on partial CF failure, append a follow-up audit message correcting the
record (e.g. `[enrich override CORRECTION] CF write failed; prior values
preserved`). Option (a) is simpler and avoids the user ever seeing a false
claim. Sketch (option a):

```python
# --- 11. PUT writes ---
# (move the audit-write from step 10 to here, AFTER both PUTs)
if rpe is not None:
    rpe_result = await make_intervals_request(...)
    if isinstance(rpe_result, dict) and "error" in rpe_result:
        return f"Error writing icu_rpe: {...}"
if custom_field_supplied:
    cf_result = await make_intervals_request(...)
    if isinstance(cf_result, dict) and "error" in cf_result:
        return f"Error: partial enrichment ..."

# Both writes landed → safe to record audit.
if conflicts and override:
    parts = [f"{name}: {old}→{new}" for name, old, new in conflicts]
    await add_activity_message(
        activity_id=activity_id,
        content="[enrich override] " + ", ".join(parts),
        api_key=api_key,
    )
```

Add a test mirroring `test_split_put_partial_failure_named` with
`override=True` and a stale `discipline` on the pre-GET to lock the new
ordering.

---

### WR-02: Wellness write swallows partial silent-ignore for `hrv` and `resting_hr` (no setup-prereq guard, no readback-pointer)

**File:** `src/intervals_mcp_server/tools/wellness.py:189-191, 230-241`

**Issue:** The comment at line 189-191 says "wellness fields are native to
Intervals.icu's wellness model" and intentionally skips a verify-fields
guard. This is correct for the locked subjective fields and `sleepSecs`.
However, the wellness PUT body builder accepts `hrv` and `resting_hr`
(`utils/wellness.py:55-56`) and the tool passes them through without
range validation or readback hand-holding. If an Intervals.icu account is
configured such that HRV/RHR are not surfaced (e.g., tied to device sync
config), the PUT might 200 OK but the field never lands — the readback
mismatch surfaces, but with NO README pointer (line 237 says "Wellness
fields are native — do NOT include the README pointer"). The user gets
"sent X, got None" with no actionable next step.

This is a smaller-blast-radius mirror of Pitfall #2: the tool catches the
silent-ignore (good — readback verification works) but does not give the
user a path to remediate. Probability is low (HRV/RHR are typically
populated by device sync), so this is a polish issue, not a blocker.

**Fix:** When a readback mismatch occurs and the only mismatched fields
are `hrv` / `restingHR`, append a one-line hint pointing the user to the
Intervals.icu wellness device-sync settings (or a README section if one
exists). Sketch:

```python
device_sourced = {"hrv", "restingHR"}
if mismatches and all(
    api_name.split(":")[0].split()[0] in device_sourced
    for line in mismatches
    for api_name in [line.lstrip().split(":")[0]]
):
    return (
        f"Error: wellness fields did not roundtrip for {date}:\n"
        + "\n".join(mismatches)
        + "\n\nNote: hrv/resting_hr may be device-sync-controlled on this "
          "account; manual writes can be silently overwritten."
    )
```

Or simpler: drop the guard at line 237 entirely and always include a
generic "verify the field is enabled in your Intervals.icu wellness
settings" hint when a wellness field doesn't roundtrip. Existing test
`test_write_wellness_entry_readback_failure_no_readme_pointer` will need
to be updated to match the new message body.

---

### WR-03: TOCTOU between pre-PUT conflict scan and write — concurrent edits not detected

**File:** `src/intervals_mcp_server/tools/climbing.py:316-370`

**Issue:** The default-deny re-enrichment guard reads the activity (step
7), decides whether `override=True` is required, and then issues PUT
writes (step 11). Between the GET and the PUT, another client (Garmin
sync, the Intervals.icu web UI, another MCP call) can populate the
fields. The pre-GET sees them as None ("safe to write"); the PUT
overwrites the new value with the user's intended value silently — no
audit, no override required. The post-PUT readback then matches the sent
value, so the tool returns success. The previously-set value is lost.

This is a race window of ~hundreds of ms (one round-trip + body build).
Probability against a single user is low, but the design intent of
default-deny is to never silently overwrite — and right now we silently
overwrite anything that lands in the gap.

Intervals.icu does not expose a conditional-PUT (If-Match / ETag) header
that I can see in the API client. So perfect defense isn't free.

**Fix:** A pragmatic mitigation is to do the readback-equality check
against `pre` AS WELL as `post` — if the supplied field had a different
value in `pre.get(api_name)` than what we sent, we expected to be
overwriting nothing, but if `post.get(api_name) != pre.get(api_name)` AND
the diff is for a field WE didn't supply, that's a noisy log entry
worth surfacing. For supplied fields, compare `pre.get(api_name)` is
None (or matches sent_value) and surface a "concurrent edit detected"
warning if the pre-value silently changed during the window.

Lower-cost alternative: document the race in a code comment / the
tool's docstring as a known limitation, since the climbing-write tool
is single-user / single-session by design (PROJECT.md "stateless,
single-shot tools"). Either approach is acceptable; document explicitly
which one was chosen.

---

### WR-04: `format_wellness_entry` uses `id` field for "Date:" label — pre-existing bug, surfaced by Phase 2 readback success path

**File:** `src/intervals_mcp_server/utils/formatting.py:302`

**Issue:** Line 302 reads:
```python
lines.append(f"Date: {entries.get('id', 'N/A')}")
```

The wellness API uses `id` for the date string (e.g., `"2099-01-01"`) on
some endpoints. Phase 2's `write_wellness_entry` returns a success message
that includes `format_wellness_entry(entry)` (line 245). The smoke test
showed wellness readback returns `{"id": "2099-01-01", ...}` from
`/athlete/{id}/wellness`. So the label HAPPENS to render the right
string, but the SEMANTICS are wrong — the renderer uses the `id` field
for a "Date:" label by relying on a coincidence of API shape. Other
wellness GET shapes return `"date": "..."` (see `get_wellness_data` line
77, which sets `data["date"] = date_str` if absent), and this branch
would render "Date: N/A" because the renderer doesn't fall back to
`entries.get("date")`.

This is a pre-existing bug that Phase 2 did not introduce, but Phase 2
makes the success path of `write_wellness_entry` traverse it (so it's
now in the hot path). I am flagging it because it lives in a file Phase 2
modified.

**Fix:**
```python
lines.append(f"Date: {entries.get('id', entries.get('date', 'N/A'))}")
```

---

## Info

### IN-01: `_verify_custom_fields_setup_impl` heuristic is silently weak when no recent activities exist

**File:** `src/intervals_mcp_server/tools/climbing.py:42-108`

**Issue:** The verify-fields guard inspects up to 50 recent activities for
top-level presence of `CUSTOM_FIELD_KEYS` entries. If the athlete has zero
recent activities (new account, just-cleared sandbox, post-DELETE smoke
state) — `_verify_custom_fields_setup_impl` returns
`(False, all_keys, "Missing required ...")` even though the schemas
might be correctly defined. The error message blames the user for missing
schemas they may already have. This is documented in the docstring
("there is no definitions endpoint that exposes user-defined custom
fields by key") but the failure mode is opaque to the user.

**Fix:** Add a one-line clarifier to the missing-fields message when
`result` was an empty list (no activities at all in the window), e.g.
"No activities returned in the last N — heuristic cannot confirm field
definitions. If you have just set up climbing fields and have no
activities yet, create one manually first." This is a docs-in-error
fix; no behavior change.

---

### IN-02: Magic number `_READBACK_ACTIVITY_LIMIT = 50` — heuristic window not tied to a stated rationale

**File:** `src/intervals_mcp_server/tools/climbing.py:39`

**Issue:** The constant is documented ("a reasonably sized window of
recent work") but 50 is a magic value. If a user has > 50 recent
non-climbing activities (very common for cyclists who started using
climbing tracking), the heuristic will never see climbing-field-bearing
activities and will declare the schemas missing. The Phase 2
verification plan does not appear to cover this drift.

**Fix:** Either (a) raise to 200 to better tolerate non-climber athletes
who started using climbing fields, or (b) filter by activity type
(`type=WeightTraining`) in the request params if the API supports it.
Cheaper option: leave at 50 and document the limitation in the
verify-fields docstring.

---

### IN-03: Spike script: `_redact()` does not redact athlete_id inside numeric/`tuple`/`set` containers

**File:** `scripts/spike_write_endpoints_phase2.py:121-129`

**Issue:** `_redact()` recursively handles `str`, `dict`, `list` only.
`tuple`, `set`, `frozenset`, `bytes`, and dataclass instances pass
through unchanged. Today's findings shape uses only str/dict/list, so
this is theoretical — but a future addition (e.g., serializing a
`FieldSpec` dataclass into findings) would silently leak the athlete_id.
The `default=str` in `json.dumps` would convert the dataclass to its
repr — which, if the repr ever included the athlete_id, would also leak.

**Fix:** Either (a) add tuple/set handling, or (b) gate the leak by
asserting at write-time that `athlete_id not in findings_text`:

```python
findings_text = "".join(content)
assert athlete_id not in findings_text, (
    "athlete_id leaked into findings file — fix _redact()"
)
FINDINGS_PATH.write_text(findings_text, encoding="utf-8")
```

The assert is cheap and fails fast on any future drift.

---

### IN-04: Smoke script: cleanup path does not redact `delete_resp` failures with diagnostic detail

**File:** `scripts/smoke_phase2.py:167-186`

**Issue:** Cleanup runs in `finally`, which is good. The DELETE response
and wellness-cleanup PUT response are logged via `_redact()` — also
good. But if the DELETE fails (e.g., 404 because activity already gone,
or 500), the exit code is still 1 only via the `failures` list; the
DELETE failure is not added to `failures`. So a user could see
"SMOKE PHASE 2 — all steps OK" even though cleanup failed and an
orphan activity is sitting in their account.

**Fix:** Check `delete_resp` for an error envelope and add `"cleanup"`
to `failures` if the DELETE didn't succeed:

```python
if isinstance(delete_resp, dict) and delete_resp.get("error"):
    failures.append("cleanup_delete")
if isinstance(wellness_cleanup, dict) and wellness_cleanup.get("error"):
    failures.append("cleanup_wellness")
```

---

### IN-05: Repeated `monkeypatch.setattr` boilerplate across enrichment tests — extract a fixture

**File:** `tests/test_climbing_write.py` (entire file)

**Issue:** Every test (~12 of them) repeats the four-line monkeypatch
block:

```python
monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
monkeypatch.setattr("intervals_mcp_server.tools.climbing.make_intervals_request", fake_request)
```

Plus, `test_override_writes_audit_message` adds a third `setattr` for
`tools.activities`. This is fine for test clarity, but it means a future
import-path refactor requires editing 12+ test sites. A pytest fixture
that takes a `fake_request` callable and patches all three locations
would localize the change. Not urgent — flagging for cleanup later.

**Fix:** Add a fixture in `conftest.py` or near the top of the test file:

```python
@pytest.fixture
def patch_intervals_request(monkeypatch: pytest.MonkeyPatch):
    def _patch(fake: Callable):
        for path in (
            "intervals_mcp_server.api.client.make_intervals_request",
            "intervals_mcp_server.tools.climbing.make_intervals_request",
            "intervals_mcp_server.tools.wellness.make_intervals_request",
            "intervals_mcp_server.tools.activities.make_intervals_request",
        ):
            monkeypatch.setattr(path, fake)
    return _patch
```

---

_Reviewed: 2026-04-25T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
