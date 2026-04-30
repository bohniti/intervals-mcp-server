# Phase 5: Server Wiring and Acceptance - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 05-CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-29
**Phase:** 05-server-wiring-and-acceptance
**Areas discussed:** Server.py wiring style, Doc refresh scope, Regression test approach, Live smoke-test format

---

## Server.py Wiring Style

### Q1: How should the four new write tools (write_wellness_entry, enrich_activity_climbing, create_climbing_activity, complete_climbing_session) be wired into server.py?

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit named imports + `__all__` (Recommended) | Add all 4 names to lines 87/95 imports and to `__all__` (lines 100–122). Mirrors existing pattern (activities/events/custom_items). Catches accidental removal loudly. | ✓ |
| Side-effect import only | Leave server.py as-is. Module imports already trigger `@mcp.tool()` registration; tools work end-to-end. Smallest diff but inconsistent with file conventions. | |
| Named imports without `__all__` | Half-measure; import names but skip `__all__`. | |

**User's choice:** Explicit named imports + `__all__` (Recommended)
**Notes:** Mirrors existing Activities/Events/Custom-items pattern; catches future silent breakage at import time.

### Q2: Should the server.py module docstring's 'MCP tools provided' list be refreshed to include the 5 new tools?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, list all 5 new tools (Recommended) | Add verify, write_wellness_entry, enrich, create, complete, get_training_status to the bullet list at top of server.py. | ✓ |
| No, leave docstring stale | List is already missing some existing tools; skip the cosmetic change. | |

**User's choice:** Yes, list all 5 new tools (Recommended)
**Notes:** While editing the file for D-01 anyway, the docstring refresh is cheap and keeps the file's self-documentation truthful.

---

## Doc Refresh Scope

### Q3: How much usage documentation should Phase 5 add to the README?

| Option | Description | Selected |
|--------|-------------|----------|
| One section per new tool (Recommended) | Add a "Climbing tools" section under the existing "Climbing setup" with one ~5-line subsection per new tool: name, what it does, example invocation. Five subsections. | ✓ |
| Single 'What's new' paragraph | Add one paragraph naming the new tools and pointing at tool docstrings. Lighter; relies on Claude reading docstrings at call time. | |
| Narrative workflow walkthrough | Add a docs/CLIMBING-WORKFLOW.md walking through "finish session → enrich → log wellness → ask for status". Heavier. | |
| No README changes | Tool docstrings cover usage. Skip README. | |

**User's choice:** One section per new tool (Recommended)
**Notes:** Surface the new tools in one discoverable place without becoming a tutorial. Five subsections — verify already documented in Phase 1.

### Q4: Should the list of MCP tools in the README's introduction also be updated?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, mention climbing + wellness write + status (Recommended) | First README paragraph currently undersells the milestone — refresh to name the new domains. | ✓ |
| No, leave introduction generic | Intro is product-positioning, not a tool catalog. | |

**User's choice:** Yes, mention climbing + wellness write + status (Recommended)

---

## Regression Test Approach

### Q5: How should Phase 5 verify no regressions and prevent future silent breakage?

| Option | Description | Selected |
|--------|-------------|----------|
| Tool-registration test + suite pass (Recommended) | Add tests/test_server_registration.py asserting full expected tool name set is registered with FastMCP. Plus run existing suite. | ✓ |
| Suite pass only | Just run pytest. Smallest diff, no guard against drift. | |
| Tool-registration test + per-tool import smoke | Belt-and-suspenders; mostly redundant if `__all__` is added in D-01. | |

**User's choice:** Tool-registration test + suite pass (Recommended)
**Notes:** Catches the "imported but not registered" silent failure mode for free. Cheap, narrow, no mocking needed.

---

## Live Smoke-Test Format

### Q6: How should Phase 5 capture the live-API smoke test of each new tool?

| Option | Description | Selected |
|--------|-------------|----------|
| Automated script + manual checklist (Recommended) | scripts/smoke_phase5.py exercises every new tool via make_intervals_request() (far-future date, DELETE cleanup). Plus 05-LIVE-SMOKE.md checklist for Claude Desktop human-in-the-loop verification. Findings file documents both. | ✓ |
| Automated script only | Script covers API contract end-to-end. Skip manual checklist; registration test proves the surface is registered. | |
| Manual checklist only | 05-LIVE-SMOKE.md with a checkbox per tool, user runs each in Claude Desktop. Maximum fidelity, no reproducible artifact. | |
| Neither — Claude's Discretion | Existing scripts + registration test cover it. | |

**User's choice:** Automated script + manual checklist (Recommended)
**Notes:** Three independent checks at different layers — registration test catches structural drift, script catches API contract drift, manual checklist catches Claude Desktop tool-list rendering.

### Q7: How should the smoke-test cleanup be handled?

| Option | Description | Selected |
|--------|-------------|----------|
| Far-future date + DELETE cleanup (Recommended) | 2099-01-01; DELETE /activity/{id} (Phase 1 confirmed). Wellness far-future entry left in place — zero training impact. Status read-only. | ✓ |
| Real recent date + manual cleanup | Higher fidelity but contaminates real training data. | |
| Read-only smoke | Skip the write tools live; unit tests cover them. | |

**User's choice:** Far-future date + DELETE cleanup (Recommended)
**Notes:** Carries forward Phase 1/2/3 spike pattern — proven, idempotent, never touches real training data.

---

## Claude's Discretion

- Exact prose for README "Climbing tools" subsections (~5 lines each).
- FastMCP registration query mechanics (`mcp.list_tools()` async vs internal registry attribute vs `server.__all__` introspection).
- Smoke-script CLI ergonomics (`--no-cleanup` flag, summary table, findings format).
- Whether `05-SMOKE-FINDINGS.md` is auto-written by the script or hand-curated.
- Bullet ordering of `server.py` docstring tools list (alphabetical, grouped by domain, or insertion order).
- Whether `05-LIVE-SMOKE.md` captures Claude Desktop's exact text response or just thumbs-up.

## Deferred Ideas

- Narrative `docs/CLIMBING-WORKFLOW.md` (per-tool sections cover v1).
- CHANGELOG.md (single-user project).
- Automated Claude Desktop test harness (manual checklist enough).
- CI integration of `scripts/smoke_phase5.py` (Phase 2 D-25 carry-forward — smoke scripts run on demand, never CI).
- Property-based / fuzz tests for the registration test (overkill).
- Package version bump / release tag (lives in `/gsd-complete-milestone`).
- Tool-count assertions on top of name assertions (redundant).
- Refresh of `tools/__init__.py` `__all__` (out of scope unless stale and breaking).
