# Milestones

## v1.0 Climbing Training Loop (Shipped: 2026-04-30)

**Delivered:** Closed the climbing training loop on top of an existing read-dominant Intervals.icu MCP server — Claude can now complete a planned session, create or enrich a climbing activity with discipline/grades/RPE, log subjective wellness conversationally, and return a single-call training-status report blending CTL/ATL/TSB with wellness signals.

**Stats:**

- Phases: 5 (1 Foundation → 2 Wellness/Enrich → 3 Create/Complete → 4 Status → 5 Wiring)
- Plans: 22 (all complete)
- Timeline: 2026-04-24 → 2026-04-30 (7 days from `/gsd-new-project` to ship)
- Source LOC (`src/`): 5,030 Python
- Test LOC (`tests/`): 4,399 Python (197 passing, 7 xfail snake_case-shape locks documented as test-debt)
- v1 requirements: 19/19 shipped (CLIMB-01..10, WELL-01..03, STAT-01..04, SETUP-01..02)

**Key accomplishments:**

- **Live API spike** (Phase 1) confirmed `PUT /athlete/{id}/wellness/{date}` upsert semantics, locked the activity-create endpoint to `POST /athlete/{id}/activities/manual`, and discovered no custom-field-definitions endpoint exists — forcing the readback-heuristic verify strategy that ships in `verify_custom_fields_setup`.
- **Climbing utility layer** (Phase 1): `utils/climbing.py` with `Discipline`/`SessionFocus` StrEnums, a read-only 7-field `CUSTOM_FIELD_KEYS` `MappingProxyType` spec; `utils/grades.py` with strict-case Font + French-sport regex and a dispatch validator. Single source of truth read by every Phase 2–4 climbing tool.
- **Wellness write tool** (Phase 2): `write_wellness_entry` lets Claude log any subset of 9 fields (sleep_hours, sleep_quality, soreness, fatigue, stress, mood, motivation, hrv, restingHR) with hard pre-API range validation, drop-None upsert (omitted ≠ cleared), and PUT-then-GET-readback per-field equality verification.
- **Activity enrichment tool** (Phase 2): `enrich_activity_climbing` writes climbing metadata + native `icu_rpe` to an existing activity via split-PUT (RPE first, custom fields second), with default-deny conflict scan, override audit via `add_activity_message`, and value-equality readback on every supplied field.
- **Activity creation tools** (Phase 3): `create_climbing_activity` (manual entry with duplicate-guard GET before POST) and `complete_climbing_session` (event GET → POST with explicit `paired_event_id` → readback verifies link), both layering on the Phase 2 enrichment helper without duplication.
- **Training status report** (Phase 4): `get_training_status` returns a single ~250-token report (well under the 600-token budget) blending TSB band + verbal label + 7-day wellness, weekly CTL/ATL trend, 42-day long-term means/deltas, and an RPE data-quality flag firing when >30% of recent activities lack `icu_rpe`.
- **Server wiring + structural drift gate** (Phase 5): explicit named imports + `__all__` re-export of every milestone tool in `server.py`, plus `tests/test_server_registration.py` asserting all 23 tools register with FastMCP — silent tool removal becomes loud `ImportError` or test failure.
- **Setup documentation** (Phases 1, 5): README "Climbing setup" section with the 7-row custom-field table, case-sensitivity warning, grade-scale note, and pointer to `verify_custom_fields_setup`. Operator can stand up the tool against a fresh Intervals.icu account without reading source.
- **Live smoke acceptance** (Phase 5): `scripts/smoke_phase5.py` exercises every milestone tool end-to-end against the live Intervals.icu account on a far-future date with try/finally cleanup; documented in `05-LIVE-SMOKE.md` and `05-SMOKE-FINDINGS.md`.

**Known deferred items at close:** 3 (see STATE.md Deferred Items)

- Phase 02 UAT — 3 pending human-UAT scenarios (functionally covered by Phase 5 live smoke against the live account)
- Phase 02 VERIFICATION — `human_needed` (functionally covered by Phase 5 live smoke)
- Phase 01 UAT — `resolved` flag (cosmetic SDK report shape; 0 pending scenarios)

**Test debt:** 7 xfail tests in `test_climbing_create.py` / `test_climbing_write.py` lock the pre-rekey snake_case wire shape; deferred to a follow-up phase to either rekey the snapshots to the shipped PascalCase keys or remove. Documented in `.planning/phases/05-server-wiring-and-acceptance/05-05-SUMMARY.md`.

**Archived:**

- `.planning/milestones/v1.0-ROADMAP.md` — full phase details
- `.planning/milestones/v1.0-REQUIREMENTS.md` — all 19 v1 requirements ticked + traceability final

---
