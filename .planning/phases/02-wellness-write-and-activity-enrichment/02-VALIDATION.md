---
phase: 02
slug: wellness-write-and-activity-enrichment
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-25
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (asyncio mode = strict) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/test_wellness_write.py tests/test_climbing_write.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~5 seconds (full suite, mocked HTTP) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest <test_file>::<test> -x` (single targeted test)
- **After every plan wave:** Run `uv run pytest tests/test_wellness_write.py tests/test_climbing_write.py`
- **Before `/gsd-verify-work`:** Full suite (`uv run pytest`) green + `uv run ruff check` + `uv run mypy src` clean
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

> Filled by planner after PLAN.md files are generated. Planner MUST add one row per task in every PLAN.md, mapping it to the requirement(s) it satisfies and the automated command that proves the assertion.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-* | 01 | 1 | (research artifact — Plan 02-01 produces 02-SPIKE-FINDINGS.md; no REQ binding) | — | N/A — discovery script | smoke (manual one-shot) | `uv run python scripts/spike_write_endpoints_phase2.py` | ❌ W0 | ⬜ pending |
| 02-02-* | 02 | 2 | WELL-01, WELL-02, WELL-03 | — | Hard-validate ranges; build_wellness_put_body drops None; sleep_hours→sleepSecs converts | unit | `uv run pytest tests/test_wellness_write.py::test_wellness_helpers -x` | ❌ W0 | ⬜ pending |
| 02-03-* | 03 | 2 | WELL-01, WELL-02, WELL-03 | — | Reject empty calls; readback verifies supplied fields; out-of-range raises ValueError; upsert via drop-None | unit | `uv run pytest tests/test_wellness_write.py -x` | ❌ W0 | ⬜ pending |
| 02-04-* | 04 | 3 | CLIMB-03, CLIMB-04, CLIMB-05, CLIMB-06, CLIMB-07, CLIMB-10 | — | Discipline-aware grade validation pre-API; verify-fields guard fires on custom-field writes; default-deny override; readback verifies supplied fields incl. icu_rpe; audit message on override | unit | `uv run pytest tests/test_climbing_write.py -x` | ❌ W0 | ⬜ pending |
| 02-05-* | 05 | 3 | CLIMB-03..07 (formatting) | — | format_climbing_activity renders icu_rpe + new fields without regressing existing 11 fields | unit | `uv run pytest tests/test_climbing.py tests/test_climbing_write.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Per-Requirement Falsifiable Assertions

Mirrors RESEARCH.md §"Validation Architecture". Every phase requirement maps to one falsifiable assertion verifiable by an automated command (or, for the smoke test, a one-shot manual command).

| REQ-ID | Layer | Assertion | Command |
|--------|-------|-----------|---------|
| WELL-01 | unit | `write_wellness_entry(date, sleep_hours=8.0)` issues `PUT /wellness/{date}` with body `{"sleepSecs": 28800}` (no other keys); subsequent `GET` returns `sleepSecs=28800` | `uv run pytest tests/test_wellness_write.py::test_sleep_hours_converts_to_secs_and_upserts -x` |
| WELL-02 | unit | A subset call (e.g., `fatigue=2`) PUTs only that field; readback confirms `fatigue=2` and unrelated fields untouched in the mocked response | `uv run pytest tests/test_wellness_write.py::test_subset_upsert_does_not_overwrite_unrelated_fields -x` |
| WELL-03 | unit | Out-of-range value (e.g., `fatigue=11` if probe locks 1..4 / 1..10) raises `ValueError` naming the expected range BEFORE any HTTP call | `uv run pytest tests/test_wellness_write.py::test_out_of_range_rejects_pre_api -x` |
| WELL-03 | unit | (specifics, 02-03) Wellness readback-failure error does NOT include `_README_POINTER` — the custom-field setup pointer is climbing-only; wellness fields are native to Intervals.icu | `uv run pytest tests/test_wellness_write.py::test_write_wellness_entry_readback_failure_no_readme_pointer -x` |
| CLIMB-03 | unit | `enrich_activity_climbing(activity_id, discipline="bouldering", top_grade_sent="V5")` produces a PUT body containing the configured `CUSTOM_FIELD_KEYS["discipline"]` and `top_grade_sent` keys with sent values | `uv run pytest tests/test_climbing_write.py::test_enrich_writes_custom_fields -x` |
| CLIMB-04 | unit | Calling with `discipline="sport_lead"` and `top_grade_sent="6A"` (Font grade on route) raises `ValueError` naming "French sport scale expected" BEFORE any HTTP call | `uv run pytest tests/test_climbing_write.py::test_grade_discipline_mismatch_rejects_pre_api -x` |
| CLIMB-05 | unit | When `_verify_custom_fields_setup_impl` returns missing fields, `enrich_activity_climbing` returns the named-field error message and never issues a PUT | `uv run pytest tests/test_climbing_write.py::test_missing_custom_fields_short_circuits -x` |
| CLIMB-06 | unit | Re-enriching an activity that already has `discipline` set, without `override=True`, returns a refusal listing the conflicting field and current value; no PUT issued | `uv run pytest tests/test_climbing_write.py::test_default_deny_re_enrichment -x` |
| CLIMB-06 | unit | With `override=True`, the PUT proceeds AND `add_activity_message` is called once with a `[enrich override]` message containing each old→new pair | `uv run pytest tests/test_climbing_write.py::test_override_writes_audit_message -x` |
| CLIMB-07 | unit | `enrich_activity_climbing(activity_id, rpe=6)` produces a body containing `"icu_rpe": 6`; readback simulates `icu_rpe=6` and the tool returns success without error | `uv run pytest tests/test_climbing_write.py::test_icu_rpe_writes_and_reads_back -x` |
| CLIMB-07 | unit | If the readback returns `icu_rpe` missing or differing, the tool returns an error explicitly listing `icu_rpe` as not landed | `uv run pytest tests/test_climbing_write.py::test_icu_rpe_readback_mismatch_errors -x` |
| CLIMB-10 | unit | (readback flavour, 02-04) Activity readback after PUT detects silent-ignore — supplied custom field comes back null — and the error names the field AND includes `_README_POINTER` so the LLM can guide the user to the setup README | `uv run pytest tests/test_climbing_write.py::test_readback_custom_field_failure_includes_readme_pointer -x` |
| CLIMB-10 | unit | (formatting flavour, 02-05) `format_climbing_activity` extension renders `icu_rpe` + supplied climbing fields after enrichment without regressing the 11 existing fields (snapshot-style assertion) | `uv run pytest tests/test_climbing.py::test_format_climbing_activity_renders_icu_rpe -x` |

> **Cross-cutting alignment test (Phase 2 mirrors Phase 1's `Discipline.value` ↔ `CUSTOM_FIELD_KEYS["discipline"].options`):**
> Every numeric Optional param in `write_wellness_entry`'s signature has a key in `WELLNESS_RANGES`. Adding a param without a range entry (or vice versa) fails the test.
> Command: `uv run pytest tests/test_wellness_write.py::test_signature_aligns_with_wellness_ranges -x`

---

## Wave 0 Requirements

- [ ] `tests/test_wellness_write.py` — new file (D-23). Stubs for WELL-01..WELL-03 + signature/range alignment test
- [ ] `tests/test_climbing_write.py` — new file (D-23). Stubs for CLIMB-03..CLIMB-07
- [ ] `src/intervals_mcp_server/utils/wellness.py` — new file (D-19). Empty module with `WELLNESS_RANGES = {}` placeholder so unit tests can import; populated after Plan 02-01 lands probe results
- [ ] `pyproject.toml` — already configured; no install required
- [ ] No new pytest plugins required (asyncio mode strict already in place)

> **Probe-dependent ranges note:** `WELLNESS_RANGES` final values come from Plan 02-01's probe (D-01b). Wave 0 lands the file shape and an alignment test; Plan 02-02 fills the table from `02-SPIKE-FINDINGS.md`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Activity custom-field PUT body roundtrips through readback against live Intervals.icu | (Plan 02-01 probe; informs CLIMB-03..CLIMB-07) | Live API; non-deterministic across accounts; mocking would hide the unknown body shape we're discovering | `uv run python scripts/spike_write_endpoints_phase2.py` against `SPIKE_DATE=2099-01-01`; inspect printed status codes; cleanup via DELETE confirmed in Phase 1 |
| Wellness subjective-field accepted ranges (`fatigue`, `stress`, `motivation`, `mood`, `soreness`, `sleep_quality`) | (Plan 02-01 probe; informs WELL-03) | Live API range discovery; cannot be mocked because we don't yet know the answer | Probe each field at values 1..10 against `SPIKE_DATE`; record min/max accepted in `02-SPIKE-FINDINGS.md` |
| `icu_rpe` write path — single-PUT vs split-PUT decision (D-16) | (Plan 02-01 probe; informs CLIMB-07) | Behavior is undocumented; D-16 routes the implementation based on outcome | Try `icu_rpe=6` co-located with custom fields; if 422, isolate to its own PUT; record chosen path |
| End-to-end smoke test (Plan 02-05) | All Phase 2 REQs | Live API; not safe in CI; uses far-future date with DELETE cleanup | `uv run python scripts/smoke_phase2.py` (or whatever Plan 02-05 names it); verify printed readback matches sent values |
| Hard-stop fallback (D-05) — if probe cannot land custom fields, stop and re-discuss | All CLIMB-* in Phase 2 | Decision-level escalation; cannot be automated | If Plan 02-01 exits with status 2 (D-05), do NOT proceed to Plan 02-04; surface to user |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies (planner fills Per-Task Verification Map)
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify (planner enforces during plan generation)
- [ ] Wave 0 covers all MISSING references (`tests/test_wellness_write.py`, `tests/test_climbing_write.py`, `utils/wellness.py` skeleton)
- [ ] No watch-mode flags (pytest in single-shot only; no `--watch`)
- [ ] Feedback latency < 5s (pytest mocked, no live HTTP in CI)
- [ ] `nyquist_compliant: true` set in frontmatter (only after Plan 02-01 lands `02-SPIKE-FINDINGS.md` AND all per-task rows are populated)

**Approval:** pending
