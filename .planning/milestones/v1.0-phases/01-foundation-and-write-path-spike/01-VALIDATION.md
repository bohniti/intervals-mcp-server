---
phase: 1
slug: foundation-and-write-path-spike
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-24
updated: 2026-04-24
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Filled in after plans 01-01..01-06 were written.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.5+ with pytest-asyncio 0.21+ (no `@pytest.mark.asyncio` in this repo — tests use `asyncio.run(...)` inside sync `def test_*`) |
| **Config file** | `pyproject.toml` under `[tool.pytest.ini_options]`; `asyncio_default_fixture_loop_scope = "function"` |
| **Quick run command** | `uv run pytest tests/test_grades.py tests/test_climbing.py -q` |
| **Full suite command** | `uv run pytest -q tests/` |
| **Estimated runtime** | ~5 seconds (existing suite ~3s; new tests pure sync, no network) |

---

## Sampling Rate

- **After every task commit:** Run quick command scoped to files touched (new-test subset)
- **After every plan merge:** Run full suite (`uv run pytest -q tests/`) — catches Pitfall #12 regressions
- **Before `/gsd-verify-work`:** Full suite must be green AND `pytest --collect-only` count must have increased by the expected delta (see Wave 0 section)
- **Max feedback latency:** 5 seconds for scoped, ~10 seconds for full suite

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-T1 | 01-01 | 1 | SETUP-01 | T-01-02 | CUSTOM_FIELD_KEYS is read-only MappingProxyType | unit | `uv run python -c "from intervals_mcp_server.utils.climbing import CUSTOM_FIELD_KEYS; import pytest; exec('try:\n CUSTOM_FIELD_KEYS[\"x\"]=1\nexcept TypeError: print(\"OK\")')"` | ❌ pending (Task 1 creates utils/climbing.py) | ⬜ pending |
| 01-01-T2 | 01-01 | 1 | CLIMB-08 | T-01-01, T-01-03 | validate_grade rejects cross-scale with case-aware regex | unit | `uv run python -c "from intervals_mcp_server.utils.climbing import Discipline; from intervals_mcp_server.utils.grades import validate_grade; try: validate_grade('6a', Discipline.BOULDERING); raise SystemExit(1)\nexcept ValueError as e: assert 'Font' in str(e); print('OK')"` | ❌ pending (Task 2 creates utils/grades.py) | ⬜ pending |
| 01-01-T3 | 01-01 | 1 | CLIMB-08, SETUP-01 | T-01-01, T-01-02, T-01-03 | Tests cover regex matrix + enum/spec alignment + MappingProxyType guard | unit (parametrized) | `uv run pytest tests/test_grades.py tests/test_climbing.py -v` | ❌ pending (Task 3 creates both test files) | ⬜ pending |
| 01-02-T1 | 01-02 | 1 | CLIMB-08 (indirect — formatter for readback) | T-02-01 | format_climbing_activity additive; existing formatters unchanged | unit | `uv run pytest -q tests/` (full suite — regression guard) + `uv run python -c "from intervals_mcp_server.utils.formatting import format_climbing_activity; assert 'N/A' in format_climbing_activity({})"` | ❌ pending (Task 1 extends utils/formatting.py) | ⬜ pending |
| 01-03-T1 | 01-03 | 2 | SETUP-02 (indirect — spike is prerequisite research for verify tool) | T-03-01, T-03-02, T-03-03, T-03-04 | Spike script exists, uses make_intervals_request exclusively, redacts athlete_id, invisible to pytest | smoke | `uv run python -c "import ast; ast.parse(open('scripts/spike_write_endpoints.py').read())"` + `uv run pytest --collect-only -q 2>&1 \| grep -c spike_write_endpoints` (must return `0`) + `grep -c 'SPIKE_DATE = "2099-01-01"' scripts/spike_write_endpoints.py` (must return `1`) | ❌ pending (Task 1 creates scripts/spike_write_endpoints.py) | ⬜ pending |
| 01-04-T1 | 01-04 | 3 | SETUP-02 (direct — live-API confirmation) | T-04-01, T-04-02, T-04-03, T-04-05 | Spike executed, findings committed, no secrets leaked, no orphan data | manual + grep | `test -s .planning/phases/01-foundation-and-write-path-spike/01-SPIKE-FINDINGS.md && ! grep -qE '"[0-9]{5,}"\|"i[0-9]{4,}"' .planning/phases/01-foundation-and-write-path-spike/01-SPIKE-FINDINGS.md` | ❌ pending (checkpoint task — human runs spike) | ⬜ pending |
| 01-05-T1 | 01-05 | 4 | SETUP-02 | T-05-01, T-05-02, T-05-03, T-05-07 | verify_custom_fields_setup + _impl both async; docstring mirrors 7-field table; no warn-and-proceed | unit | `uv run python -c "import inspect; from intervals_mcp_server.tools.climbing import verify_custom_fields_setup, _verify_custom_fields_setup_impl; assert inspect.iscoroutinefunction(verify_custom_fields_setup) and inspect.iscoroutinefunction(_verify_custom_fields_setup_impl)"` + `! grep -iE "warn and proceed\|continuing anyway" src/intervals_mcp_server/tools/climbing.py` | ❌ pending (Task 1 creates tools/climbing.py) | ⬜ pending |
| 01-05-T2 | 01-05 | 4 | SETUP-02 | T-05-07 | verify_custom_fields_setup is registered via server.py import; __all__ extended | integration | `uv run python -c "from intervals_mcp_server.server import verify_custom_fields_setup; import intervals_mcp_server.server as s; assert 'verify_custom_fields_setup' in s.__all__"` + `uv run pytest -q tests/` (full regression) | ❌ pending (Task 2 edits server.py) | ⬜ pending |
| 01-05-T3 | 01-05 | 4 | SETUP-02 | T-05-01, T-05-07 | Tool tests cover happy / all-missing / some-missing / error / registration / tuple-shape | unit + integration (monkeypatched) | `uv run pytest -q tests/test_climbing.py -v` (expect 13+ tests passing) | ❌ pending (Task 3 appends to tests/test_climbing.py) | ⬜ pending |
| 01-06-T1 | 01-06 | 5 | SETUP-01 | T-06-01, T-06-02 | README documents the 7 required custom fields; case-sensitivity called out; references verify_custom_fields_setup | smoke (grep) | `test "$(grep -c '^## Climbing setup — required Intervals.icu custom fields$' README.md)" = "1" && test "$(grep -cE '^\| \`(discipline\|indoor\|session_focus\|top_grade_sent\|top_grade_attempted\|sends\|attempts)\`' README.md)" = "7"` | ❌ pending (Task 1 appends section to README.md) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

All Wave 0 test files are created BEFORE implementation by their respective Wave 1 tasks (this phase does TDD per-task via `tdd="true"` — the test file is authored as part of the same task that writes the implementation, with the test written first).

- [ ] `tests/test_grades.py` — regex matrix (parametrized) + 4-dispatch cross-scale rejection for CLIMB-08 — created in Plan 01 Task 3
- [ ] `tests/test_climbing.py` utility-layer tests — enum/spec alignment (D-09) + MappingProxyType guard + 7-key coverage for SETUP-01 — created in Plan 01 Task 3
- [ ] `tests/test_climbing.py` tool-layer tests — registration + happy/missing/error paths for SETUP-02 — appended in Plan 05 Task 3
- [ ] No new framework install — pytest + pytest-asyncio + pytest-mock already in `[project.optional-dependencies].dev`

**Expected test-count delta:** `pytest --collect-only -q | tail -1` count should increase by approximately **30+ tests** after Phase 1 (5 regex parametrize groups × ~5 cases + 4 validate_grade + 7 climbing utility + 6 climbing tool = ~30). Plan 01 SUMMARY records the exact pre/post delta.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Spike writes to live Intervals.icu account | SETUP-02 (indirect — spike produces the contracts `verify_custom_fields_setup` is built against) | Live API write requires real credentials and writes to a real (if far-future) date on the real athlete account; must not run in CI | Plan 01-04 is a human-action checkpoint: `uv run scripts/spike_write_endpoints.py`, then grep-scan `01-SPIKE-FINDINGS.md` for athlete-id/API-key leakage, then perform manual cleanup via Intervals.icu web UI if the spike's DELETE attempt did not clean up. Findings file committed. |
| README "Climbing setup" section is operationally correct | SETUP-01 | Human must follow the README end-to-end in a real Intervals.icu account to confirm the 7 fields can actually be created as specified (field type names in Intervals.icu UI may differ from API type names) | In Phase 5 (acceptance), user follows the README instructions against a test account; Phase 1 ships the documentation, Phase 5 validates real-world setup. For Phase 1: `verify_custom_fields_setup` running green against the real athlete account confirms the documented keys match the account's actual custom-field definitions. |
| No orphan activity/wellness at 2099-01-01 after spike | T-04-01 / T-03-06 | The spike attempts DELETE but Intervals.icu DELETE for activities may be unavailable; cleanup-residue detection requires looking at the account UI | Plan 01-04 resume-signal confirms user has visually verified no orphan data remains. |

---

## Wave 0 Gaps

| Gap | Closed By | Status |
|-----|-----------|--------|
| No test exists for grade validation | Plan 01 Task 3 creates `tests/test_grades.py` with parametrized matrix + 4 dispatch tests | ⬜ pending |
| No test exists for CUSTOM_FIELD_KEYS alignment | Plan 01 Task 3 creates `tests/test_climbing.py` utility tests | ⬜ pending |
| No test exists for verify_custom_fields_setup | Plan 05 Task 3 appends tool-layer tests | ⬜ pending |
| No test exists for format_climbing_activity | Plan 02 Task 1 includes inline verify command; formal test file deferred (function is trivial; spike readback + downstream usage in Phase 2 provide integration coverage) | ⬜ accepted |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or manual-checkpoint documentation (Plan 04 is the one checkpoint-gated manual task; its acceptance criteria are grep-scannable)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify — Plan 04's checkpoint acceptance uses grep gates on the findings file (SPIKE-FINDINGS.md), which is automated
- [x] Wave 0 covers all MISSING references — SETUP-01 (Plans 01, 06), SETUP-02 (Plans 01, 05), CLIMB-08 (Plan 01)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planner-approved 2026-04-24. Ready for `/gsd-execute-phase 1`.
