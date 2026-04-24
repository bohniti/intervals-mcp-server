---
phase: 01-foundation-and-write-path-spike
plan: 06
subsystem: documentation
tags: [documentation, climbing, setup, prerequisites, readme, custom-fields]

# Dependency graph
requires:
  - phase: 01-foundation-and-write-path-spike
    provides: "CUSTOM_FIELD_KEYS spec (Plan 01-01) — the canonical 7-field table the README mirrors"
  - phase: 01-foundation-and-write-path-spike
    provides: "verify_custom_fields_setup tool + docstring (Plan 01-05) — references the same README section heading Plan 01-06 establishes (D-13 twin)"
provides:
  - "User-facing README section documenting the 7 required Intervals.icu custom fields (SETUP-01 satisfied)"
  - "Case-sensitivity warning surfaced to the user (D-09 alignment point)"
  - "Pointer from README to verify_custom_fields_setup tool, completing the README ↔ verify-tool docstring doc twin (D-13)"
affects: [02-climbing-write-tools, 03-climbing-activity-creation, 04-status-report, 05-server-wiring]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Doc-twin pattern: README section + in-tool docstring manually kept in sync (D-13)"

key-files:
  created:
    - .planning/phases/01-foundation-and-write-path-spike/01-06-SUMMARY.md
  modified:
    - README.md

key-decisions:
  - "Inserted as sibling ## section between existing ## Setup block (ending L74) and ## Updating (starting L75). Adjacent to setup instructions where users look for setup steps; does not nest under ## Setup to preserve the 1–5 numbered-step structure there."
  - "Used em-dash (U+2014) in Options column for non-select fields per plan constraint — not 'N/A' or empty."
  - "Backtick-wrapped Key column values (e.g. `discipline`) per plan constraint; select option strings are also backticked."

patterns-established:
  - "README ↔ CUSTOM_FIELD_KEYS ↔ verify_custom_fields_setup docstring — three-way doc twin kept in manual sync. Future CUSTOM_FIELD_KEYS change must update README section and verify-tool docstring together."

requirements-completed: [SETUP-01]

# Metrics
duration: 4min
completed: 2026-04-24
---

# Phase 01 Plan 06: README climbing custom-fields setup documentation

**New README section 'Climbing setup — required Intervals.icu custom fields' with 7-row markdown table mirroring CUSTOM_FIELD_KEYS, case-sensitivity warning, grade-scale note, and pointer to verify_custom_fields_setup — closing SETUP-01 as the single user-facing artifact that tells a new operator which Intervals.icu custom fields to create.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-24T09:53:16Z
- **Completed:** 2026-04-24T09:56:35Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Added `## Climbing setup — required Intervals.icu custom fields` as a sibling `##` section inserted after `## Setup` and before `## Updating`.
- Produced a 7-row markdown table matching CUSTOM_FIELD_KEYS insertion order exactly: `discipline`, `indoor`, `session_focus`, `top_grade_sent`, `top_grade_attempted`, `sends`, `attempts`.
- Listed the exact enum option strings for the two `select` fields: `bouldering, sport_lead, top_rope, trad` for `discipline` and `power, endurance, technique, projecting, mileage` for `session_focus`.
- Called out case-sensitivity explicitly (D-09 alignment guard: uppercase-vs-lowercase-snake-case mismatch will be silently ignored by Intervals.icu).
- Noted grade-scale guidance (Font for bouldering, French sport for sport_lead / top_rope / trad) tying the text-field rows to the validate_grade contract.
- Added a `### Verifying the setup` subsection pointing users to `verify_custom_fields_setup` (D-13 twin — the tool's docstring references this same heading by name).

## Task Commits

Each task was committed atomically:

1. **Task 1: Append 'Climbing setup — required Intervals.icu custom fields' section to README.md** - `a9789c3` (docs)

_(This plan is single-task; no plan-metadata commit will be made by this executor — worktree mode: orchestrator owns downstream state writes.)_

## Files Created/Modified
- `README.md` - Added new top-level section (44 additions, 0 deletions) documenting the 7 required Intervals.icu custom fields with types, enum options, case-sensitivity warning, grade-scale guidance, and pointer to the verification MCP tool.

## Insertion Point Chosen

The new section was inserted as a **sibling `##`-level section** placed between the end of the existing `## Setup` block (which ends at the athlete-ID bullet around line 74 of the pre-edit file) and the start of `## Updating` (pre-edit line 75). Rationale:

- Adjacent to setup instructions — readers reach this section while still in "setup mode".
- Kept at sibling (`##`) level rather than nested (`### N.`) under `## Setup` because `## Setup` uses a numbered 1–5 step flow; dropping a heterogeneous subsection into that flow would force a renumbering and break the convention that Plan 01-06 was explicitly forbidden from touching (Pitfall #12 byte-identical guard).
- Matches the naming in `verify_custom_fields_setup`'s docstring pointer: `"See README section 'Climbing setup — required Intervals.icu custom fields'"`.

## Exact Section Heading

```
## Climbing setup — required Intervals.icu custom fields
```

Confirmed byte-identical to the heading referenced by `verify_custom_fields_setup` (tools/climbing.py from Plan 01-05). Both strings use the em-dash character (U+2014), not a hyphen-minus.

## Git-Diff Additions-Only Confirmation

```
$ git diff HEAD~1 -- README.md | grep -cE "^-[^-]"
0
```

Zero deletions — the diff is purely additive. The file grew by 44 lines; no pre-existing section was modified, re-ordered, or had its heading level changed (Pitfall #12 satisfied).

## Acceptance-Criteria Grep Evidence

| Criterion | Command | Result |
|-----------|---------|--------|
| Exact section heading present | `grep -c "^## Climbing setup — required Intervals.icu custom fields$" README.md` | `1` |
| All 7 field keys as table rows | `grep -cE '^\| \`(discipline\|indoor\|session_focus\|top_grade_sent\|top_grade_attempted\|sends\|attempts)\`' README.md` | `7` |
| Discipline options in order | `grep -cE "bouldering.*sport_lead.*top_rope.*trad" README.md` | `1` |
| Session-focus options in order | `grep -cE "power.*endurance.*technique.*projecting.*mileage" README.md` | `1` |
| References the diagnostic tool | `grep -c "verify_custom_fields_setup" README.md` | `2` |
| Mentions grade-scale validation | `grep -cE "Font grade\|French sport grade" README.md` | `1` |
| Calls out case-sensitivity (D-09) | `grep -c "case-sensitive" README.md` | `1` |
| No pre-existing content deleted | `git diff README.md \| grep -cE "^-[^-]"` | `0` |
| Regression test suite clean | `uv run pytest -q tests/` | `86 passed in 0.53s` |

## Decisions Made
- **Sibling `##` placement over nested `### N. …` under `## Setup`.** The numbered Setup sub-sections are a tightly sequential "do these 5 steps" flow; inserting a heterogeneous step would either force renumbering (forbidden: Pitfall #12) or appear as an un-numbered sibling inside a numbered flow (visually inconsistent). A top-level sibling keeps the content discoverable right below `## Setup` without disturbing it.
- **Em-dash literal (`—`, U+2014), not typed `---` or `N/A`.** The plan text explicitly specified the em-dash in Options column for non-select fields; using any substitute would fail the plan's acceptance constraint.

## Deviations from Plan

None - plan executed exactly as written.

The plan provided the exact markdown to insert VERBATIM, and the README already had a natural insertion point between `## Setup` and `## Updating` that matched the plan's placement guidance ("after the existing `## Setup` block"). No auto-fixes needed; no architectural decisions triggered.

---

**Total deviations:** 0
**Impact on plan:** None — plan text inserted verbatim and verified by all 9 acceptance-criteria greps.

## Issues Encountered

One transient environment issue: `uv run pytest` initially failed with `error: Failed to spawn: pytest — No such file or directory` because the freshly-initialized worktree `.venv` only had the production deps synced. Resolved by running `uv sync --all-extras` per AGENTS.md guidance; test suite subsequently ran green (86 passed in 0.53s). This is not a project code issue — just a worktree bootstrap step.

## Note on Three-Way Doc Sync (CUSTOM_FIELD_KEYS ↔ README ↔ verify-tool docstring)

Phase 1 ships with these three sources kept in sync **manually**:

1. `src/intervals_mcp_server/utils/climbing.py` — `CUSTOM_FIELD_KEYS` (canonical machine-readable spec).
2. `README.md` — `## Climbing setup — required Intervals.icu custom fields` (user-facing setup checklist).
3. `src/intervals_mcp_server/tools/climbing.py` — `verify_custom_fields_setup` docstring (Claude-facing in-context checklist).

An **optional auto-generation test** that would assert the README table and the tool docstring both match `CUSTOM_FIELD_KEYS` programmatically is **explicitly deferred** per `.planning/phases/01-foundation-and-write-path-spike/01-CONTEXT.md` "Deferred Ideas" → _"Auto-generating the README field table from `CUSTOM_FIELD_KEYS`"_. The reasoning recorded there: adding a doc-generation / doc-assertion step isn't worth the build complexity at v1; the three sources are small enough and change rarely enough that manual sync plus the acceptance-grep tests in each plan suffices. Any future change to `CUSTOM_FIELD_KEYS` must update README Section and verify-tool docstring in the same commit — the commit diff itself is the enforcement mechanism at v1.

## Threat Flags

None — section describes public setup prerequisites only (field keys are already visible in the athlete's custom-fields UI). No new trust boundaries, no secrets, no schema changes at a security edge. T-06-01/02/03 in the plan's threat register remain dispositioned as planned (mitigate (weak), mitigate, accept respectively).

## Next Phase Readiness

- **SETUP-01 closed** — the single user-facing artifact required to close the SETUP-01 requirement now exists. A new operator can follow the README to create the 7 custom fields in their Intervals.icu athlete account, and then run `verify_custom_fields_setup` via Claude to confirm.
- **Phase 2 unblocked** — Phase 2's write tools (`write_wellness_entry`, `enrich_activity_climbing`) can reference the README section by name in error messages when `_verify_custom_fields_setup_impl` returns missing fields. The error-message string they'll want is already in the `verify_custom_fields_setup` tool from Plan 01-05.
- **Doc-twin maintenance reminder** — any future edit to `CUSTOM_FIELD_KEYS` must also update the README section (this file) and the `verify_custom_fields_setup` docstring in the same commit. No automated check yet — enforced by code review + commit-diff visibility.

## Self-Check: PASSED

**File-existence verification:**
```
$ test -f README.md && echo "FOUND: README.md"
FOUND: README.md
$ test -f .planning/phases/01-foundation-and-write-path-spike/01-06-SUMMARY.md && echo "FOUND: SUMMARY"
FOUND: SUMMARY
```

**Commit-existence verification:**
```
$ git log --oneline -1 --all | grep -q "a9789c3" && echo "FOUND: a9789c3"
FOUND: a9789c3
```

All claimed files exist; the claimed commit hash (`a9789c3`) is present in the git log.

---
*Phase: 01-foundation-and-write-path-spike*
*Plan: 06*
*Completed: 2026-04-24*
