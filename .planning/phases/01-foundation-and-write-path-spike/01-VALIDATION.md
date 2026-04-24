---
phase: 1
slug: foundation-and-write-path-spike
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-24
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Draft scaffold — planner fills Per-Task Verification Map and Wave 0 rows.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (asyncio; see AGENTS.md) |
| **Config file** | `pyproject.toml` (pytest config) |
| **Quick run command** | `uv run pytest tests/test_grades.py tests/test_climbing.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~30 seconds (existing suite) |

---

## Sampling Rate

- **After every task commit:** Run quick command scoped to files touched
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

> Planner fills this table once tasks are defined in PLAN.md files. Every task with automated verification must appear here with grep-verifiable acceptance criteria.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| _TBD by planner_ | — | — | — | — | — | — | — | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_grades.py` — grade validation coverage for CLIMB-08 (Font vs French cross-scale rejection, strict case, bare-modifier rules)
- [ ] `tests/test_climbing.py` — StrEnum alignment with `CUSTOM_FIELD_KEYS`, FieldSpec shape, `verify_custom_fields_setup` behaviour (happy + missing-field hard-block per Pitfall #2)
- [ ] `tests/test_server.py` extension — assert `verify_custom_fields_setup` is registered (no new conftest expected; mirror existing registration assertions)
- [ ] No new framework install — pytest already in `pyproject.toml`

*If the planner determines `tests/test_format_climbing_activity.py` is warranted by the formatter surface, add it here in Wave 0.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Spike writes to live Intervals.icu account | SETUP-02 (indirect; spike backs the write contracts) | Live API write requires real credentials and a human-confirmed far-future date; must not run in CI | Run `uv run scripts/spike_write_endpoints.py`; confirm outputs in `01-SPIKE-FINDINGS.md`; perform manual cleanup per checklist if activity DELETE is unavailable |
| README "Climbing setup" section is accurate against Intervals.icu UI | SETUP-01 | Human must verify the 7 documented field names/types/options actually appear in the Intervals.icu custom-fields UI | Follow README checklist in an Intervals.icu test account; confirm each field is created as documented |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (SETUP-01, SETUP-02, CLIMB-08)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
