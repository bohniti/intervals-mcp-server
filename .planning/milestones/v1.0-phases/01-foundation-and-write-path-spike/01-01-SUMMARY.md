---
phase: 01-foundation-and-write-path-spike
plan: 01
subsystem: climbing
tags: [climbing, utilities, validation, grades, custom-fields, strenum, mappingproxytype, regex]

# Dependency graph
requires: []
provides:
  - Discipline StrEnum (bouldering / sport_lead / top_rope / trad)
  - SessionFocus StrEnum (power / endurance / technique / projecting / mileage)
  - FieldSpec @dataclass(frozen=True) — key / field_type / options / description
  - CUSTOM_FIELD_KEYS MappingProxyType — read-only 7-field spec (single source of truth)
  - FONT_RE regex (strict uppercase) + FRENCH_SPORT_RE regex (strict lowercase)
  - validate_grade(grade, discipline) — dispatch validator, string-in/string-out or ValueError
  - tests/test_grades.py + tests/test_climbing.py — regex matrix + enum/spec alignment + read-only guard
affects:
  - 01-02 (format_climbing_activity will render fields the spec establishes)
  - 01-03 (spike script can use the spec for readback rendering)
  - 01-04 (verify_custom_fields_setup iterates CUSTOM_FIELD_KEYS)
  - 01-05 (README table mirrors CUSTOM_FIELD_KEYS)
  - 02-* (write tools validate grades + use CUSTOM_FIELD_KEYS as payload keys)
  - 03-* (climbing activity POST tools validate grades + use CUSTOM_FIELD_KEYS)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "StrEnum with lowercase_snake values for custom-field option alignment (new pattern — TransportAliases precedent, but Discipline/SessionFocus tie their .value tuples into a spec table)"
    - "@dataclass(frozen=True) for immutable spec records (new pattern — existing types.py uses unfrozen @dataclass)"
    - "MappingProxyType wrapper on module-level spec dicts for runtime immutability (new pattern — no precedent in codebase)"
    - "Strict-case regex as cross-scale guard — Font uppercase, French sport lowercase, no re.IGNORECASE (new pattern for this repo)"
    - "Dispatch-style validator returning the validated input on success, raising ValueError naming the expected shape on failure (extends validation.py's validate_date pattern)"

key-files:
  created:
    - src/intervals_mcp_server/utils/climbing.py
    - src/intervals_mcp_server/utils/grades.py
    - tests/test_grades.py
    - tests/test_climbing.py
    - .planning/phases/01-foundation-and-write-path-spike/deferred-items.md
  modified: []

key-decisions:
  - "Used Python 3.12 Literal typing for FieldType; typing.Literal[\"select\",\"bool\",\"text\",\"integer\"] — tighter than plain str and readable as a bounded enumeration without introducing a fourth enum class"
  - "FieldSpec kept minimal (key / field_type / options / description) — no to_dict/from_dict/to_json like types.py dataclasses, because this is static configuration, never serialized across the wire"
  - "CUSTOM_FIELD_KEYS wrapped in MappingProxyType (D-10 resolution) — the context gave discretion (frozen dict vs NamedTuple vs plain dict + convention); MappingProxyType gives real runtime immutability at zero cost and a dedicated test (test_custom_field_keys_is_read_only) enforces it"
  - "FONT_RE uses ^[3-9][A-C]\\+?$|^[12]$ — covers Font's full published range plus defensive 1/2 entries (no + on 1/2 because those grades don't historically carry plus modifiers). 9C+ is the current top; easy to extend"
  - "FRENCH_SPORT_RE uses ^[3-9][abc]\\+?$ — covers French sport's full published range. No YDS or V-scale (deferred per Project Out of Scope)"

patterns-established:
  - "StrEnum → CUSTOM_FIELD_KEYS option alignment: CUSTOM_FIELD_KEYS['discipline'].options == tuple(d.value for d in Discipline); future renames of either side fail loudly via test_discipline_options_match_custom_field_spec"
  - "MappingProxyType for module-level spec immutability, paired with a test that asserts mutation raises TypeError"
  - "Strict-case regex as the cross-scale guard; never add re.IGNORECASE or .lower()/.upper() normalization for climbing grades"
  - "Error messages name the expected scale explicitly: 'Expected Font grade (uppercase, e.g. 6A, 7B+)...' / 'Expected French sport grade (lowercase, e.g. 6a, 7b+)...' — so Claude can relay a usable correction hint"

requirements-completed:
  - CLIMB-08
  - SETUP-01

# Metrics
duration: ~17min
completed: 2026-04-24
---

# Phase 1 Plan 1: Climbing utility foundation — Discipline/SessionFocus StrEnums, FieldSpec, CUSTOM_FIELD_KEYS spec, and Font/French-sport grade validators Summary

**Two new utility modules (utils/climbing.py, utils/grades.py) + two new test modules (tests/test_grades.py, tests/test_climbing.py); establishes Discipline + SessionFocus StrEnums, a read-only 7-field CUSTOM_FIELD_KEYS MappingProxyType spec, and strict-case Font/French-sport regex with a dispatch validator — the single source of truth every Phase 2–4 climbing tool reads.**

## Performance

- **Duration:** ~17 min
- **Started:** 2026-04-24T08:52 UTC (approx — worktree init)
- **Completed:** 2026-04-24T09:09 UTC
- **Tasks:** 3
- **Files created:** 4
- **Files modified:** 0

## Accomplishments

- Discipline and SessionFocus StrEnums with exactly 4 + 5 canonical members, values aligned with the Intervals.icu custom-field option strings they'll be compared to (D-07, D-08)
- CUSTOM_FIELD_KEYS as a `MappingProxyType[str, FieldSpec]` with exactly the 7 canonical field keys — discipline, indoor, session_focus, top_grade_sent, top_grade_attempted, sends, attempts — and runtime-enforced immutability (D-09, D-10)
- FONT_RE = `^[3-9][A-C]\+?$|^[12]$` and FRENCH_SPORT_RE = `^[3-9][abc]\+?$` — strict-case regex as the cross-scale guard (Pitfall #3 mitigation; no re.IGNORECASE, no normalization)
- validate_grade(grade, discipline) — string-in/string-out on success; ValueError naming "Font" or "French sport" on cross-scale or gibberish input
- 38 new tests across both test modules: regex matrix, cross-scale rejection (4 quadrants), dispatch outcomes for all 4 disciplines, enum↔spec alignment, 7-key completeness, FieldSpec type invariants, and MappingProxyType read-only assertion
- Full existing suite still passes (34 baseline → 72 total); ruff + mypy green on both new source files
- D-16 honored: `utils/types.py`, `utils/validation.py`, `utils/formatting.py` are untouched (`git diff` empty)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create utils/climbing.py with Discipline, SessionFocus, FieldSpec, CUSTOM_FIELD_KEYS** — `b10c274` (feat)
2. **Task 2: Create utils/grades.py with FONT_RE, FRENCH_SPORT_RE, validate_grade** — `12b0374` (feat)
3. **Task 3: Create tests/test_grades.py and tests/test_climbing.py** — `e60aafb` (test)
4. **Deferred-items log** (out-of-scope finding) — `ae07af1` (docs)

## Files Created/Modified

- `src/intervals_mcp_server/utils/climbing.py` — Discipline + SessionFocus StrEnums, FieldSpec @dataclass(frozen=True), CUSTOM_FIELD_KEYS MappingProxyType spec table (98 lines)
- `src/intervals_mcp_server/utils/grades.py` — FONT_RE / FRENCH_SPORT_RE compiled regex, validate_grade dispatch (63 lines)
- `tests/test_grades.py` — regex matrix + cross-scale rejection + dispatch outcomes (26 tests)
- `tests/test_climbing.py` — enum/spec alignment + 7-key completeness + MappingProxyType read-only guard (7 tests)
- `.planning/phases/01-foundation-and-write-path-spike/deferred-items.md` — logs pre-existing `utils/formatting.py` mypy errors (out of scope for this plan)

## Exact Patterns Committed

### FONT_RE
```python
FONT_RE = re.compile(r"^[3-9][A-C]\+?$|^[12]$")
```
- Accepts: `3A`, `6A`, `6A+`, `7B`, `7C+`, `8A`, `9C+`, `1`, `2`
- Rejects: lowercase (`6a`), cross-scale (`V5`, `5.11a`), slashes (`6A/6B`), descriptors (`hard 6A`), letter out of range (`6D`), missing letter (`6`), stray whitespace (`6A +`)

### FRENCH_SPORT_RE
```python
FRENCH_SPORT_RE = re.compile(r"^[3-9][abc]\+?$")
```
- Accepts: `3a`, `6a`, `6a+`, `7b`, `7c+`, `8a`, `9c+`
- Rejects: uppercase (`6A`), YDS (`5.11a`), slashes (`6a/6b`), letter out of range (`6d`), stray whitespace (`6a +`)

### Regex-range rationale / deviations
- **Font top bound:** committed at `9C+` (regex matches `[3-9][A-C]\+?`). Timo's actual range sits far below this, but the extra headroom costs nothing and covers any future personal bests without a patch.
- **Font low bound:** defensive `[12]` alternation accepts bare `1` and `2` (no letter, no `+`) for grade-scale completeness, even though those levels are essentially inert for an experienced climber.
- **French sport top bound:** `9c+` by the same reasoning. 9c+ is the world's hardest route as of 2026, so this is genuinely the ceiling.
- **No V-scale / YDS:** confirmed deferred per PROJECT.md Out of Scope. Structure supports adding more regex + dispatch arms without rewriting.

### FieldSpec.field_type values used in CUSTOM_FIELD_KEYS
```
select   → discipline, session_focus     (2 fields)
bool     → indoor                        (1 field)
text     → top_grade_sent, top_grade_attempted  (2 fields)
integer  → sends, attempts               (2 fields)
```
Total: 7 fields, 4 distinct field types, `Literal["select","bool","text","integer"]` exhausted.

### Test-count delta (Pitfall #14 discoverability guard)

| Before | After | Delta |
|--------|-------|-------|
| 34 tests | 72 tests | +38 |

Breakdown of new nodes:
- `tests/test_grades.py`: 31 test node IDs (7+7+7+5 parametrized regex cases + 5 dispatch tests)
- `tests/test_climbing.py`: 7 test node IDs (2 StrEnum value checks + 2 alignment + 1 seven-key + 1 FieldSpec type invariant + 1 read-only)
- Parametrize expands to 26 regex cases, so `pytest -q` reports 38 collected in the two new files combined. (Plan acceptance mentioned ≥ 20, we exceed by a wide margin.)

## Decisions Made

- **FieldSpec as `@dataclass(frozen=True)`** — chosen over NamedTuple per CONTEXT discretion. Matches the `types.py` dataclass convention while adding `frozen=True` so instances are hashable and immutable.
- **`typing.Literal` for FieldType** — gives the spec table a compile-time-checkable enumeration without introducing another enum class.
- **`MappingProxyType` over plain dict + convention** — the plan explicitly required runtime immutability so a test could assert mutation fails. MappingProxyType is the canonical Python mechanism; no new dependencies.
- **`field_type` (not `type`) as the FieldSpec attribute name** — the plan in `PATTERNS.md` hinted at `type: str`, but the plan's verbatim file contents use `field_type: FieldType`. Avoids shadowing Python's builtin `type` and keeps attribute lookups unambiguous.
- **Left existing `utils/types.py`, `utils/validation.py`, `utils/formatting.py` untouched** — D-16 / D-20 compliance, confirmed by empty `git diff` on those files.

## Deviations from Plan

None — plan executed exactly as written. All three tasks produced the canonical artifacts specified in the plan's `<action>` blocks verbatim, all acceptance criteria grep-guards passed, and the automated verification commands succeeded on first run for all three tasks.

One out-of-scope observation was logged (not a deviation): pre-existing mypy errors in `src/intervals_mcp_server/utils/formatting.py` on lines 28 and 358 exist on main (confirmed via `git stash` baseline check) and are explicitly out of scope per D-16. Documented in `deferred-items.md` for Plan 01-02's consideration.

---

**Total deviations:** 0
**Impact on plan:** No deviations. Plan quality: the verbatim action blocks and explicit acceptance-criteria grep-guards made execution fully deterministic — no judgement calls needed inside the tasks.

## Issues Encountered

- **`uv run pytest` failed initially** — the worktree's virtualenv didn't have dev extras installed. Resolved by running `uv sync --all-extras`. Not a plan issue; a worktree-bootstrap issue.
- **`mypy src/intervals_mcp_server/utils/` surfaced pre-existing errors in `formatting.py`** — confirmed pre-existing on main via `git stash`. Not caused by this plan; logged to `deferred-items.md`. Plan-level verification narrowed to `mypy src/intervals_mcp_server/utils/climbing.py src/intervals_mcp_server/utils/grades.py` (the two new files), which passes clean.

## User Setup Required

None — this plan adds pure-utility code with no external service dependencies. The `CUSTOM_FIELD_KEYS` spec DOCUMENTS the fields the user must pre-create in Intervals.icu (SETUP-01 requirement), but the actual README section mirroring the spec is deferred to Plan 01-05 per phase structure.

## Threat Flags

None — no new trust boundaries beyond those already declared in the plan's `<threat_model>`. Both threats in the register (T-01-01 case-as-guard regex, T-01-02 MappingProxyType immutability) are mitigated as specified; tests `test_validate_grade_font_on_route_rejected`, `test_validate_grade_french_on_boulder_rejected`, and `test_custom_field_keys_is_read_only` enforce the mitigations.

## Next Phase Readiness

**Ready for Plan 01-02 (format_climbing_activity):**
- `from intervals_mcp_server.utils.climbing import CUSTOM_FIELD_KEYS` — formatter iterates these keys to render field values
- `from intervals_mcp_server.utils.climbing import Discipline` — formatter can pretty-print `activity["discipline"]` against the canonical enum

**Ready for Plan 01-03 (spike script):**
- `from intervals_mcp_server.utils.climbing import CUSTOM_FIELD_KEYS` — spike payload builder reads the 7 keys
- `from intervals_mcp_server.utils.grades import validate_grade` — spike can dry-run validation against sample data

**Ready for Plan 01-04 (verify_custom_fields_setup tool):**
- `from intervals_mcp_server.utils.climbing import CUSTOM_FIELD_KEYS, FieldSpec` — verify tool iterates CUSTOM_FIELD_KEYS and returns missing FieldSpec list

**Ready for Plan 01-05 (README section + SETUP-01 docs):**
- README table copies the 7 rows of CUSTOM_FIELD_KEYS directly; alignment test already in place to catch future drift

**No blockers.** All four acceptance commits (`b10c274`, `12b0374`, `e60aafb`, `ae07af1`) are present in the worktree branch; parent-agent can merge this wave safely.

## Self-Check

Verified the four claimed commits exist and their artifacts are present:

- `b10c274` (feat: utils/climbing.py) — FOUND in git log; `src/intervals_mcp_server/utils/climbing.py` present
- `12b0374` (feat: utils/grades.py) — FOUND in git log; `src/intervals_mcp_server/utils/grades.py` present
- `e60aafb` (test: test_grades.py + test_climbing.py) — FOUND in git log; both test files present
- `ae07af1` (docs: deferred-items.md) — FOUND in git log; deferred-items file present

**Self-Check: PASSED**

---
*Phase: 01-foundation-and-write-path-spike*
*Plan: 01*
*Completed: 2026-04-24*
