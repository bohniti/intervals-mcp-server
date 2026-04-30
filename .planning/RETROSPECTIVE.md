# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — Climbing Training Loop

**Shipped:** 2026-04-30
**Phases:** 5 | **Plans:** 22

### What Was Built

- Six new MCP tools wired into FastMCP: `verify_custom_fields_setup`, `write_wellness_entry`, `enrich_activity_climbing`, `create_climbing_activity`, `complete_climbing_session`, `get_training_status`.
- Climbing-aware utility layer: `utils/climbing.py` (Discipline/SessionFocus StrEnums + read-only `CUSTOM_FIELD_KEYS` MappingProxyType spec), `utils/grades.py` (strict-case Font + French-sport regex with dispatch validator), `utils/wellness.py` (locked WELLNESS_RANGES + drop-None PUT body builder), `utils/status.py` (TSB bands + 4 pure formatters).
- Live API research instruments: Phase 1 spike (`scripts/spike_write_endpoints.py`) + Phase 2 second-probe + Phase 5 acceptance smoke (`scripts/smoke_phase5.py`) — all routed through `make_intervals_request()`, all redacting athlete_id before writing findings to disk.
- README "Climbing setup" section + `verify_custom_fields_setup` diagnostic — operator can stand up the tool against a fresh Intervals.icu account without reading source.
- 197 passing tests + structural drift gate asserting all 23 milestone tools register with FastMCP.

### What Worked

- **Spike-before-build paid for itself in Phase 1.** `POST /activities` body shape was MEDIUM confidence; the 30-minute live probe locked the endpoint to `/activities/manual`, surfaced that the activity DELETE endpoint actually works (so cleanup is automated rather than manual), and discovered there is no custom-field-definitions endpoint — which forced the readback-heuristic verify strategy that ended up shipping. Building Phase 2 against assumptions would have wasted at least one full plan cycle.
- **Single source of truth via `MappingProxyType`.** `CUSTOM_FIELD_KEYS` and `WELLNESS_RANGES` are read-only at runtime and tested for read-only-ness. Every climbing/wellness tool reads through them; the alignment tests caught two signature drifts during refactors before they reached the API layer.
- **Default-deny conflict scan with override audit.** Adding `[enrich override] field: old→new` messages via `add_activity_message` turned an invisible failure mode (silently overwriting a wearable-synced field) into a visible paper trail. Cheap to add, high blast-radius reduction.
- **Split-PUT for `icu_rpe` + custom fields.** Discovered during Phase 2 spike: `icu_rpe` writes via PUT `/activity/{id}` with the field at the top level, custom fields write via the same PUT but in a separate body. Combining them into one body fails silently for one or the other. Locking the split early prevented intermittent test failures downstream.
- **Readback-verification on every write.** Every write tool reads back the supplied fields and asserts equality before returning success. Caught the snake_case → PascalCase rekey issue in Phase 5 immediately; a "did the API say 200?" check would have shipped silently broken writes.
- **`uv run` everywhere.** Single command for ruff/mypy/pytest with consistent venv resolution. No "works on my machine" flakes during the milestone.

### What Was Inefficient

- **CUSTOM_FIELD_KEYS rekey landed in Phase 5 instead of Phase 1.** The Intervals.icu wire shape is PascalCase (`Discipline`, not `discipline`); we built Phases 1–4 against snake_case keys and rekeyed in a Phase 5 gap-closure commit (`fd7db62`). The Phase 1 spike captured the readback shape but the planning didn't propagate "PascalCase is the wire format" into the spec table. Result: 7 tests now xfail locking the old shape until they're rekeyed or removed — explicit test debt.
- **Phase 02 UAT + VERIFICATION not ticked off.** The functional verification happened via Phase 5 live smoke against the live account, but the Phase 02 artifact files were left in `partial`/`human_needed` state. Required acknowledging-and-deferring at milestone close rather than closing cleanly. Lesson: when Phase N's verification gets folded into Phase M's smoke, update Phase N's artifacts at that point, not later.
- **Spike findings were reproduced in multiple PLAN files instead of being pointed at.** Each Phase 2 plan re-stated the locked endpoint and body shape from the spike; one source-of-truth findings doc with `@`-references would have shrunk plan files and reduced drift risk.

### Patterns Established

- **Spike-first for any unverified API contract.** The two write endpoints in Phase 1 + the wellness/icu_rpe second probe in Phase 2 were both cheap and high-leverage. Any future write-path work against Intervals.icu should start with a `scripts/spike_*.py` against a far-future date with `make_intervals_request()` + recursive athlete_id redaction.
- **Far-future date + try/finally cleanup for live tests.** `SPIKE_DATE = 2099-01-01` (and the matching pattern in Phase 5 smoke) means tests can't collide with real data and cleanup is bounded.
- **Drop-None upsert in body builders, not in tool layer.** Keeps tool functions thin; centralizes the `null = clear` semantic in one place per resource.
- **Readback-heuristic when introspection isn't available.** When Intervals.icu doesn't expose a definitions endpoint, write-then-read-and-name-missing is the next-best UX — clearly better than silent 422s.
- **Structural drift gate via `mcp.list_tools()`.** Catches silent tool removal at unit-test speed without HTTP. Worth adding to any FastMCP project that registers tools in more than one module.
- **Standalone `scripts/smoke_*.py` are not pytest-discoverable.** No `def test_*`; they're invoked manually or by an acceptance gate. Keeps live API calls out of CI by default.

### Key Lessons

1. **Capture wire shape, not Python shape, in custom-field specs.** A spike that round-trips a write must record the exact key the API echoed back, not the key your validator happens to use. The Phase 1 → Phase 5 rekey was avoidable.
2. **Verification artifacts have to be ticked when verification happens, not at milestone close.** If a later phase's smoke covers an earlier phase's UAT, update the earlier phase's UAT/VERIFICATION at that moment.
3. **Override flags + audit messages > hard refusals or silent overwrites.** Default-deny with explicit override is the right shape for any write tool that touches existing data.
4. **One-source-of-truth tables (`MappingProxyType` + alignment tests) catch drift cheaply.** Adopt this pattern early in any milestone with multiple downstream consumers of a spec.
5. **Two-monkeypatch trick for re-imported symbols.** When tool modules `from api.client import make_intervals_request` and tests want to mock the HTTP boundary, monkeypatch _both_ `api.client.make_intervals_request` AND `tools.<module>.make_intervals_request`. Single-site monkeypatch will appear to work and then silently hit the real API.

### Cost Observations

- Model mix: predominantly Opus 4.7 (1M context) for planning + execution; sonnet for parallel sub-tasks via Agent.
- Sessions: ~1 session per phase (5 phases) plus ad-hoc gap-closure during Phase 5 acceptance.
- Notable: 7-day calendar timeline (2026-04-24 → 2026-04-30) on a 5,030-LOC source / 4,399-LOC test footprint suggests the spike-first + readback-verify pattern is high-leverage on closed-loop API integration work; the alternative (build → discover wire shape mismatch in production → rebuild) would have stretched the milestone significantly.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 5 | 22 | Established spike-before-build, readback-verify-everything, single-source-of-truth specs (`MappingProxyType`), and structural drift gate via FastMCP introspection |

### Cumulative Quality

| Milestone | Tests Passing | Source LOC | Test LOC | Notes |
|-----------|---------------|------------|----------|-------|
| v1.0 | 197 | 5,030 | 4,399 | 7 xfail tests lock pre-rekey snake_case wire shape; deferred to follow-up |
